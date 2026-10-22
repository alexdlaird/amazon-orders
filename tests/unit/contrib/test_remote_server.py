__copyright__ = "Copyright (c) 2026 Alex Laird"
__license__ = "MIT"

import http.client
import json
import socket
import threading
from typing import Any, Dict, Optional, Tuple
from unittest.mock import patch

from amazonorders.contrib.browser.remote_server import RemoteLoginServer, _RemoteLoginView, parse_input_event
from amazonorders.exception import AmazonOrdersError
from tests.unittestcase import UnitTestCase


class TestParseInputEvent(UnitTestCase):
    def test_pointer_events(self):
        self.assertEqual({"t": "move", "x": 10.5, "y": 20.0}, parse_input_event({"t": "move", "x": 10.5, "y": 20}))
        self.assertEqual({"t": "down", "x": 1.0, "y": 2.0, "button": "left"},
                         parse_input_event({"t": "down", "x": 1, "y": 2}))
        self.assertEqual({"t": "up", "x": 1.0, "y": 2.0, "button": "right"},
                         parse_input_event({"t": "up", "x": 1, "y": 2, "button": "right"}))
        self.assertEqual({"t": "wheel", "x": 0.0, "y": 10000.0, "dx": -5000.0, "dy": 30.0},
                         parse_input_event({"t": "wheel", "x": -5, "y": 99999, "dx": -10 ** 9, "dy": 30}))

    def test_text_events(self):
        self.assertEqual({"t": "type", "text": "a"}, parse_input_event({"t": "type", "text": "a"}))
        self.assertEqual({"t": "insert", "text": "ß✓"}, parse_input_event({"t": "insert", "text": "ß✓"}))
        self.assertEqual({"t": "insert", "text": "a" * 1000}, parse_input_event({"t": "insert", "text": "a" * 1000}))

    def test_key_events(self):
        self.assertEqual({"t": "key", "key": "Enter", "mods": []}, parse_input_event({"t": "key", "key": "Enter"}))
        self.assertEqual({"t": "key", "key": "Tab", "mods": ["Shift"]},
                         parse_input_event({"t": "key", "key": "Tab", "mods": ["Shift"]}))
        # Cmd+A on a Mac and Ctrl+A elsewhere are both whichever the browser here uses
        self.assertEqual({"t": "key", "key": "a", "mods": ["ControlOrMeta"]},
                         parse_input_event({"t": "key", "key": "a", "mods": ["Meta"]}))
        self.assertEqual({"t": "key", "key": "a", "mods": ["ControlOrMeta", "Shift"]},
                         parse_input_event({"t": "key", "key": "a", "mods": ["Shift", "Meta", "Control"]}))

    def test_size_event(self):
        self.assertEqual({"t": "size", "w": 390, "h": 700, "dpr": 3.0},
                         parse_input_event({"t": "size", "w": 390.4, "h": 700, "dpr": 3}))
        self.assertEqual(4, parse_input_event({"t": "size", "w": 1, "h": 1, "dpr": 10})["dpr"])

    def test_invalid_events(self):
        for event in (
                "move",
                {"t": "eval"},
                {"x": 1, "y": 1},
                {"t": "move", "x": "1", "y": 1},
                {"t": "move", "x": True, "y": 1},
                {"t": "move", "x": float("nan"), "y": 1},
                {"t": "move", "y": 1},
                {"t": "down", "x": 1, "y": 1, "button": "back"},
                {"t": "type", "text": ""},
                {"t": "type", "text": 1},
                {"t": "type", "text": "ab"},
                {"t": ["move"]},
                {"t": "down", "x": 1, "y": 1, "button": ["left"]},
                {"t": "key", "key": ["Enter"]},
                {"t": "key", "key": "Enter", "mods": [["Shift"]]},
                {"t": "insert", "text": "a" * 1001},
                {"t": "key", "key": "F12"},
                {"t": "key", "key": "a"},
                {"t": "key", "key": "a", "mods": ["Alt"]},
                {"t": "key", "key": "ab", "mods": ["Control"]},
                {"t": "key", "key": "Enter", "mods": ["Hyper"]},
                {"t": "key", "key": "Enter", "mods": "Shift"},
                {"t": "size", "w": 100},
        ):
            with self.assertRaises(ValueError, msg=event):
                parse_input_event(event)


class TestRemoteLoginView(UnitTestCase):
    def test_claim(self):
        # GIVEN
        view = _RemoteLoginView("amazon.com")

        # WHEN
        allowed, claim = view.claim(None)

        # THEN
        self.assertTrue(allowed)
        self.assertTrue(view.claimed)
        self.assertTrue(view.holds_claim(claim))
        self.assertFalse(view.holds_claim(None))
        self.assertFalse(view.holds_claim("other"))
        self.assertEqual((True, None), view.claim(claim))
        self.assertEqual((False, None), view.claim(None))
        self.assertEqual((False, None), view.claim("other"))

    def test_final_state_is_kept(self):
        # GIVEN
        view = _RemoteLoginView("amazon.com")
        view.set_state("signed_in")

        # WHEN
        view.set_state("failed")

        # THEN
        self.assertEqual("signed_in", view.state)

    def test_wait(self):
        # GIVEN
        view = _RemoteLoginView("amazon.com")
        threading.Timer(0.1, view.set_frame, (b"jpeg", (390, 700))).start()

        # WHEN
        snapshot = view.wait(0, "starting", 5)

        # THEN
        self.assertEqual({"state": "starting", "seq": 1, "viewport": (390, 700), "frame": b"jpeg"}, snapshot)
        self.assertIsNone(view.wait(1, "starting", 0)["frame"])
        view.set_state("signing_in")
        self.assertEqual("signing_in", view.wait(1, "starting", 0)["state"])


class _Client:
    """Requests to a :class:`RemoteLoginServer`, as the sign-in page makes them."""

    def __init__(self, server: RemoteLoginServer) -> None:
        self.port = server._httpd.server_address[1]
        self.cookie: Optional[str] = None

    def request(self, method: str, path: str, body: Optional[bytes] = None,
                headers: Optional[Dict[str, str]] = None) -> Tuple[Any, bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        all_headers = dict(headers or {})
        if self.cookie:
            all_headers["Cookie"] = self.cookie
        connection.request(method, path, body=body, headers=all_headers)
        response = connection.getresponse()
        content = response.read()
        connection.close()
        set_cookie = response.getheader("Set-Cookie")
        if set_cookie:
            self.cookie = set_cookie.split(";")[0]
        return response, content


class TestRemoteLoginServer(UnitTestCase):
    def setUp(self):
        super().setUp()
        self.server = RemoteLoginServer(port=0)
        self.server.start()
        self.view = _RemoteLoginView("amazon.de")
        self.server.add(self.view)
        self.client = _Client(self.server)
        self.path = f"/{self.view.token}"

    def tearDown(self):
        self.server.stop()
        super().tearDown()

    def claim(self):
        # The first input other than a size claims the sign-in
        response, _ = self.client.request("POST", f"{self.path}/input", json.dumps([{"t": "move", "x": 0, "y": 0}])
                                          .encode())
        self.assertEqual(204, response.status)
        self.view.inputs.get_nowait()

    def raw_request(self, request: bytes) -> bytes:
        # Everything the server sends back on one connection, until it closes it
        with socket.create_connection(("127.0.0.1", self.client.port), timeout=10) as sock:
            sock.sendall(request)
            received = b""
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    return received
                received += chunk

    def test_url(self):
        self.assertEqual(f"http://localhost:{self.client.port}/", self.server.url)
        self.assertEqual(f"http://localhost:{self.client.port}/{self.view.token}", self.server.link(self.view))
        self.assertEqual("http://localhost:8765/", RemoteLoginServer().url)
        self.assertEqual("https://example.com/sign-in/", RemoteLoginServer(url="https://example.com/sign-in").url)
        self.assertEqual("https://example.com/sign-in/", RemoteLoginServer(url="https://example.com/sign-in/").url)
        with self.assertRaises(AmazonOrdersError):
            RemoteLoginServer(url="example.com/sign-in")

    def test_start_and_stop(self):
        # GIVEN
        httpd = self.server._httpd

        # WHEN
        self.server.start()

        # THEN
        self.assertIs(httpd, self.server._httpd)
        self.assertTrue(self.server.running)
        self.server.stop()
        self.assertFalse(self.server.running)
        self.server.stop()

    def test_start_on_a_port_in_use(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            sock.listen()

            with self.assertRaises(AmazonOrdersError) as cm:
                RemoteLoginServer(port=sock.getsockname()[1]).start()

        self.assertIn("Could not serve the sign-in page", str(cm.exception))

    def test_page(self):
        # GIVEN
        self.view.site = "<amazon.de>"

        # WHEN
        response, content = self.client.request("GET", self.path)

        # THEN
        self.assertEqual(200, response.status)
        self.assertEqual("text/html; charset=utf-8", response.getheader("Content-Type"))
        self.assertIn("frame-ancestors 'none'", response.getheader("Content-Security-Policy"))
        self.assertEqual("no-store", response.getheader("Cache-Control"))
        self.assertEqual("no-referrer", response.getheader("Referrer-Policy"))
        self.assertEqual("DENY", response.getheader("X-Frame-Options"))
        self.assertIn(b"data-site=\"&lt;amazon.de&gt;\"", content)
        self.assertNotIn(b"{site}", content)

    def test_page_under_a_prefix(self):
        response, _ = self.client.request("GET", f"/amazon/sign-in{self.path}/")
        self.assertEqual(200, response.status)
        response, _ = self.client.request("POST", f"/amazon/sign-in{self.path}/input",
                                          json.dumps([{"t": "move", "x": 0, "y": 0}]).encode())
        self.assertEqual(204, response.status)
        response, content = self.client.request("GET", "/amazon/sign-in/_static/remote-login.css")
        self.assertEqual(200, response.status)
        self.assertIn(b"#canvas", content)

    def test_static_files(self):
        response, content = self.client.request("GET", "/_static/remote-login.js")
        self.assertEqual(200, response.status)
        self.assertEqual("text/javascript; charset=utf-8", response.getheader("Content-Type"))
        self.assertIn(b"use strict", content)
        response, _ = self.client.request("GET", "/_static/remote.py")
        self.assertEqual(404, response.status)

    def test_unknown_paths(self):
        for method, path in (("GET", "/"), ("GET", f"/{'a' * 32}"), ("POST", f"/{'a' * 32}/input"),
                             ("GET", "/favicon.ico"), ("POST", "/"), ("GET", f"{self.path}/nothing")):
            response, content = self.client.request(method, path)
            self.assertEqual(404, response.status, path)
            self.assertIn(b"isn't valid anymore", content)

    def test_wrong_methods(self):
        self.claim()
        response, _ = self.client.request("GET", f"{self.path}/input")
        self.assertEqual(405, response.status)
        response, _ = self.client.request("POST", f"{self.path}/frame")
        self.assertEqual(405, response.status)
        response, _ = self.client.request("POST", self.path)
        self.assertEqual(405, response.status)

    def test_input_claims_the_sign_in(self):
        # GIVEN
        move = json.dumps([{"t": "move", "x": 0, "y": 0}]).encode()

        # WHEN
        response, _ = self.client.request("POST", f"{self.path}/input", move)

        # THEN
        self.assertEqual(204, response.status)
        set_cookie = response.getheader("Set-Cookie")
        self.assertTrue(set_cookie.startswith(f"{self.view.cookie_name}="))
        self.assertIn("HttpOnly", set_cookie)
        self.assertIn("SameSite=Strict", set_cookie)
        self.assertNotIn("Secure", set_cookie)
        self.assertTrue(self.view.claimed)

        # The same browser again, e.g. after a reload
        response, _ = self.client.request("POST", f"{self.path}/input", move)
        self.assertEqual(204, response.status)
        self.assertIsNone(response.getheader("Set-Cookie"))

        # Another browser
        response, content = _Client(self.server).request("POST", f"{self.path}/input", move)
        self.assertEqual(409, response.status)
        self.assertEqual({"state": "claimed"}, json.loads(content))

    def test_input_claims_the_sign_in_behind_https(self):
        response, _ = self.client.request("POST", f"{self.path}/input", json.dumps([{"t": "type", "text": "a"}])
                                          .encode(), {"X-Forwarded-Proto": "https"})
        self.assertIn("; Secure", response.getheader("Set-Cookie"))

    def test_page_can_be_seen_until_someone_types(self):
        # GIVEN a link scanner opens the link, and passes on the size of its window
        scanner = _Client(self.server)
        self.view.set_frame(b"jpeg", (390, 700))

        # WHEN
        response, content = scanner.request("GET", f"{self.path}/frame?after=0&state=starting")
        size_response, _ = scanner.request("POST", f"{self.path}/input",
                                           json.dumps([{"t": "size", "w": 390, "h": 700, "dpr": 3}]).encode())

        # THEN it claims nothing, so the person can still use the link
        self.assertEqual((200, b"jpeg"), (response.status, content))
        self.assertEqual(204, size_response.status)
        self.assertIsNone(size_response.getheader("Set-Cookie"))
        self.assertFalse(self.view.claimed)
        self.claim()

    def test_unclaimed_browser_gets_nothing(self):
        self.claim()
        other = _Client(self.server)
        response, _ = other.request("GET", f"{self.path}/frame")
        self.assertEqual(409, response.status)
        response, _ = other.request("POST", f"{self.path}/input", b"[]")
        self.assertEqual(409, response.status)
        other.cookie = f"{self.view.cookie_name}=guess; other=1"
        response, _ = other.request("GET", f"{self.path}/frame")
        self.assertEqual(409, response.status)

    @patch("amazonorders.contrib.browser.remote_server.MAX_FRAME_WAITS", 1)
    def test_frame_waits_are_limited(self):
        # GIVEN
        self.assertTrue(self.view.start_frame_wait())

        # WHEN
        response, _ = self.client.request("GET", f"{self.path}/frame")

        # THEN
        self.assertEqual(429, response.status)
        self.view.end_frame_wait()
        self.view.set_frame(b"jpeg", (390, 700))
        response, _ = self.client.request("GET", f"{self.path}/frame")
        self.assertEqual(200, response.status)

    def test_unread_body_closes_the_connection(self):
        # GIVEN a body that's another request, which the server mustn't read as one
        smuggled = b"GET /_static/remote-login.css HTTP/1.1\r\nHost: x\r\n\r\n"

        # WHEN
        for path in ("/not-a-token", f"{self.path}/frame", self.path):
            received = self.raw_request(b"POST " + path.encode() + b" HTTP/1.1\r\nHost: x\r\nContent-Length: "
                                        + str(len(smuggled)).encode() + b"\r\n\r\n" + smuggled)

            # THEN one response, and the connection is closed
            self.assertEqual(1, received.count(b"HTTP/1.1 "), path)
            self.assertIn(b"Connection: close", received)

    def test_chunked_body_is_refused(self):
        # WHEN
        received = self.raw_request(b"POST " + self.path.encode() + b"/input HTTP/1.1\r\nHost: x\r\n"
                                    b"Transfer-Encoding: chunked\r\n\r\n2\r\n[]\r\n0\r\n\r\n")

        # THEN
        self.assertTrue(received.startswith(b"HTTP/1.1 400 "))
        self.assertEqual(1, received.count(b"HTTP/1.1 "))
        self.assertTrue(self.view.inputs.empty())

    def test_chunked_get_is_refused(self):
        received = self.raw_request(b"GET " + self.path.encode() + b" HTTP/1.1\r\nHost: x\r\n"
                                    b"Transfer-Encoding: chunked\r\n\r\n0\r\n\r\n")
        self.assertTrue(received.startswith(b"HTTP/1.1 400 "))

    def test_malformed_length_closes_the_connection(self):
        received = self.raw_request(b"GET " + self.path.encode() + b" HTTP/1.1\r\nHost: x\r\nContent-Length: x\r\n"
                                    b"\r\nGET / HTTP/1.1\r\nHost: x\r\n\r\n")
        self.assertTrue(received.startswith(b"HTTP/1.1 200 "))
        self.assertIn(b"Connection: close", received)
        self.assertEqual(1, received.count(b"HTTP/1.1 "))

    def test_input_when_another_browser_claims_first(self):
        # GIVEN another browser claims the sign-in between the checks
        with patch.object(_RemoteLoginView, "claim", return_value=(False, None)):
            # WHEN
            response, content = self.client.request("POST", f"{self.path}/input",
                                                    json.dumps([{"t": "type", "text": "a"}]).encode())

        # THEN
        self.assertEqual(409, response.status)
        self.assertTrue(self.view.inputs.empty())

    def test_unsupported_method_closes_the_connection(self):
        # WHEN
        received = self.raw_request(b"PUT " + self.path.encode() + b" HTTP/1.1\r\nHost: x\r\nContent-Length: 2\r\n"
                                    b"\r\n[]GET / HTTP/1.1\r\nHost: x\r\n\r\n")

        # THEN
        self.assertTrue(received.startswith(b"HTTP/1.1 501 "))
        self.assertEqual(1, received.count(b"HTTP/1.1 "))

    def test_frame(self):
        # GIVEN
        self.claim()
        self.view.set_state("signing_in")
        self.view.set_frame(b"jpeg", (390, 700))

        # WHEN
        response, content = self.client.request("GET", f"{self.path}/frame?after=0&state=signing_in")

        # THEN
        self.assertEqual(200, response.status)
        self.assertEqual("image/jpeg", response.getheader("Content-Type"))
        self.assertEqual(b"jpeg", content)
        self.assertEqual("1", response.getheader("X-Frame-Seq"))
        self.assertEqual("390", response.getheader("X-Viewport-Width"))
        self.assertEqual("700", response.getheader("X-Viewport-Height"))
        self.assertEqual("signing_in", response.getheader("X-Sign-In-State"))

    @patch("amazonorders.contrib.browser.remote_server.FRAME_WAIT_SECONDS", 0.1)
    def test_frame_wait_passes_without_one(self):
        # GIVEN
        self.claim()
        self.view.set_frame(b"jpeg", (390, 700))

        # WHEN
        response, content = self.client.request("GET", f"{self.path}/frame?after=1&state=starting")

        # THEN
        self.assertEqual(204, response.status)
        self.assertEqual(b"", content)
        self.assertEqual("starting", response.getheader("X-Sign-In-State"))
        # A malformed sequence asks for any frame
        response, content = self.client.request("GET", f"{self.path}/frame?after=x&state=starting")
        self.assertEqual(b"jpeg", content)

    def test_frame_once_the_sign_in_ends(self):
        # GIVEN
        self.claim()
        self.view.set_state("signed_in")

        # WHEN
        response, content = self.client.request("GET", f"{self.path}/frame?after=0&state=signing_in")

        # THEN
        self.assertEqual(200, response.status)
        self.assertEqual({"state": "signed_in"}, json.loads(content))
        self.assertTrue(self.view.outcome_fetched.is_set())

    def test_input(self):
        # GIVEN
        self.claim()
        events = [{"t": "move", "x": 1, "y": 2}, {"t": "type", "text": "a"}]

        # WHEN
        response, _ = self.client.request("POST", f"{self.path}/input", json.dumps(events).encode(),
                                          {"Content-Type": "application/json"})

        # THEN
        self.assertEqual(204, response.status)
        self.assertEqual({"t": "move", "x": 1.0, "y": 2.0}, self.view.inputs.get_nowait())
        self.assertEqual({"t": "type", "text": "a"}, self.view.inputs.get_nowait())

    def test_input_rejected(self):
        # GIVEN
        self.claim()

        # WHEN
        for body, status in ((b"not json", 400), (b"{}", 400), (json.dumps([{"t": "eval"}]).encode(), 400),
                             (json.dumps([{"t": "move", "x": 1, "y": 1}] * 201).encode(), 400),
                             (b"[" * 60000, 400), (json.dumps([{"t": "key", "key": ["Enter"]}]).encode(), 400)):
            response, _ = self.client.request("POST", f"{self.path}/input", body)

            # THEN
            self.assertEqual(status, response.status, body[:20])
        self.assertTrue(self.view.inputs.empty())

    def test_input_too_large(self):
        self.claim()
        response, _ = self.client.request("POST", f"{self.path}/input", b"[" + b" " * (64 * 1024) + b"]")
        self.assertEqual(413, response.status)

    def test_input_without_length(self):
        self.claim()
        connection = http.client.HTTPConnection("127.0.0.1", self.client.port, timeout=10)
        connection.putrequest("POST", f"{self.path}/input")
        connection.putheader("Cookie", self.client.cookie)
        connection.endheaders()
        self.assertEqual(411, connection.getresponse().status)
        connection.close()

    @patch("amazonorders.contrib.browser.remote_server.MAX_QUEUED_INPUTS", 1)
    def test_input_queue_full(self):
        # GIVEN
        self.server.remove(self.view)
        self.view = _RemoteLoginView("amazon.de")
        self.server.add(self.view)
        self.path = f"/{self.view.token}"
        self.claim()

        # WHEN
        response, _ = self.client.request("POST", f"{self.path}/input", json.dumps([{"t": "type", "text": "a"}] * 2)
                                          .encode())

        # THEN
        self.assertEqual(503, response.status)

    def test_requests_are_logged_without_the_link(self):
        with self.assertLogs("amazonorders.contrib.browser.remote_server", level="DEBUG") as cm:
            self.client.request("GET", self.path)

        self.assertIn("<token>", "\n".join(cm.output))
        self.assertNotIn(self.view.token, "\n".join(cm.output))

    def test_failed_requests_are_logged(self):
        with self.assertLogs("amazonorders.contrib.browser.remote_server", level="DEBUG") as cm:
            self.server._httpd.handle_error(None, ("127.0.0.1", 1))

        self.assertIn("Sign-in page request failed", "\n".join(cm.output))

    def test_removed_view_is_gone(self):
        self.server.remove(self.view)
        response, _ = self.client.request("GET", self.path)
        self.assertEqual(404, response.status)
