__copyright__ = "Copyright (c) 2026 Alex Laird"
__license__ = "MIT"

import html
import os
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.contrib.browser.remote import PlaywrightRemoteLogin, RemoteLoginServer
from amazonorders.session import AmazonSession
from tests.unittestcase import UnitTestCase

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

EMAIL = "person@example.com"
# Pasted, so it may hold any character
PASSWORD = "pässwörd ß✓"


class _FakeAmazon(ThreadingHTTPServer):
    """A two-step sign-in, an orders page that needs it, and a page the sign-in browser mustn't reach."""

    daemon_threads = True

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _FakeAmazonHandler)
        self.emails: List[str] = []
        self.passwords: List[str] = []
        self.elsewhere_requests = 0
        threading.Thread(target=self.serve_forever, daemon=True).start()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}"


def _page(body: str) -> bytes:
    return ("<!DOCTYPE html><html><head><meta charset='utf-8'><style>"
            "body{margin:0;font:16px sans-serif} .at{position:absolute;left:20px;width:280px;height:40px;"
            "box-sizing:border-box;font-size:16px}</style></head>"
            f"<body>{body}</body></html>").encode()


class _FakeAmazonHandler(BaseHTTPRequestHandler):
    server: _FakeAmazon

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/ap/signin"):
            self._send(200, _page(
                "<form name='signIn' method='post' action='/ap/signin'>"
                "<input class='at' style='top:80px' name='email' id='email' autocomplete='off'>"
                "<button class='at' style='top:140px' type='submit'>Continue</button></form>"
                f"<a class='at' style='top:200px' id='away' href='http://localhost:{self.server.server_address[1]}"
                "/elsewhere'>Elsewhere</a>"
                "<a class='at' style='top:260px' id='hop' href='/redirect'>Elsewhere, by a redirect</a>"
                "<img src='/redirect' alt=''>"))
        elif self.path.startswith("/redirect"):
            self._redirect(f"http://localhost:{self.server.server_address[1]}/elsewhere")
        elif self.path.startswith("/your-orders/orders"):
            if "x-main=signed-in" in (self.headers.get("Cookie") or ""):
                self._send(200, _page("<h1>Your Orders</h1>"))
            else:
                self._redirect("/ap/signin")
        elif self.path.startswith("/elsewhere"):
            self.server.elsewhere_requests += 1
            self._send(200, _page("<p>Elsewhere</p>"))
        else:
            self._send(200, _page("<p>Hello</p>"))

    def do_POST(self) -> None:  # noqa: N802
        form = parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())
        if "password" in form:
            self.server.passwords.append(form["password"][0])
            self._redirect("/", {"Set-Cookie": "x-main=signed-in; Path=/"})
        else:
            email = form.get("email", [""])[0]
            self.server.emails.append(email)
            self._send(200, _page(
                "<form name='signIn' method='post' action='/ap/signin'>"
                f"<p>{html.escape(email)}</p>"
                "<input class='at' style='top:80px' type='password' name='password' id='password'>"
                "<button class='at' style='top:140px' type='submit'>Sign in</button></form>"))

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def _redirect(self, location: str, headers: Optional[Dict[str, str]] = None) -> None:
        self._send(302, b"", {"Location": location, **(headers or {})})

    def _send(self, status: int, body: bytes, headers: Optional[Dict[str, str]] = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)


class TestPlaywrightRemoteLoginInBrowsers(UnitTestCase):
    """
    Signs in to a fake Amazon through the sign-in page, from another browser, as a person would. Needs the browser
    extra and Chromium (``playwright install chromium``), and is skipped without them.
    """

    @classmethod
    def setUpClass(cls) -> None:
        # CI's browser build sets BROWSER_TESTS=required, so these fail there rather than skip
        required = os.environ.get("BROWSER_TESTS") == "required"
        if sync_playwright is None and not required:
            raise unittest.SkipTest("Needs the browser extra")  # pragma: no cover
        try:
            with sync_playwright() as pw:
                pw.chromium.launch(headless=True).close()
        except Exception as e:  # pragma: no cover
            if required:
                raise
            raise unittest.SkipTest(f"Needs Chromium (playwright install chromium): {e}")

    def setUp(self) -> None:
        super().setUp()
        self.amazon = _FakeAmazon()
        self.server = RemoteLoginServer(port=0)
        self.server.start()
        config = AmazonOrdersConfig(config_path=self.test_config.config_path,
                                    data={**self.test_config._data, "domain": self.amazon.base_url,
                                          "cookie_jar_path": self.test_cookie_jar_path})
        self.amazon_session = AmazonSession(config=config)
        self.remote_login = PlaywrightRemoteLogin(self.amazon_session, server=self.server)
        self.failure: Optional[BaseException] = None
        self.login_thread = threading.Thread(target=self._login, daemon=True)
        self.login_thread.start()

    def tearDown(self) -> None:
        self.login_thread.join(60)
        self.server.stop()
        self.amazon.shutdown()
        self.amazon.server_close()
        super().tearDown()

    def _login(self) -> None:
        try:
            self.remote_login.login(timeout=60)
        except BaseException as e:  # pragma: no cover
            self.failure = e

    def _wait_for(self, condition: Any, what: str, timeout: float = 30) -> None:
        deadline = time.monotonic() + timeout
        while not condition():
            if time.monotonic() > deadline:
                self.fail(f"Timed out waiting for {what}")  # pragma: no cover
            time.sleep(0.1)

    def _open(self, pw: Any, width: int, height: int, **context_options: Any) -> Any:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": width, "height": height}, **context_options).new_page()
        page.goto(self.remote_login.url)
        page.wait_for_function("() => document.getElementById('status').textContent.startsWith('Sign in to')")
        # The sign-in browser's page takes the size of the window showing it, then is shown at that size
        self._wait_for(lambda: self.remote_login._viewport[0] == width and self._shown_size(page) == "{}x{}".format(
            *self.remote_login._viewport), "the page to be shown at the window's size")
        return page

    @staticmethod
    def _shown_size(page: Any) -> str:
        return page.evaluate("() => { const style = document.getElementById('canvas').style; "
                             "return `${parseFloat(style.width)}x${parseFloat(style.height)}`; }")

    def _at(self, page: Any, x: float, y: float) -> Dict[str, float]:
        # Where a point of the sign-in browser's page is, on the page showing it
        box = page.locator("#canvas").bounding_box()
        width = float(page.evaluate("() => document.getElementById('canvas').style.width.replace('px', '')"))
        viewport_width = self.remote_login._viewport[0]
        scale = width / viewport_width
        return {"x": box["x"] + x * scale, "y": box["y"] + y * scale}

    def _assert_signed_in(self, page: Any) -> None:
        self.login_thread.join(60)
        self.assertIsNone(self.failure)
        self.assertTrue(self.amazon_session.is_authenticated)
        self.assertEqual("signed_in", self.remote_login.state)
        with open(self.amazon_session.config.cookie_jar_path) as cookie_jar:
            self.assertIn("signed-in", cookie_jar.read())
        page.wait_for_function("() => document.getElementById('status').textContent.startsWith(\"You're signed in\")")

    def test_sign_in_from_a_computer(self):
        with sync_playwright() as pw:
            # GIVEN a link scanner opened the link first, which leaves it to the person
            self._open(pw, 600, 500).context.browser.close()
            page = self._open(pw, 900, 700)

            # WHEN
            page.mouse.click(**self._at(page, 160, 100))
            page.keyboard.type(EMAIL)
            page.keyboard.press("Enter")
            self._wait_for(lambda: self.amazon.emails, "the email to be submitted")

            # THEN
            self.assertEqual([EMAIL], self.amazon.emails)
            # The browser goes nowhere off Amazon: not by a link, nor by a redirect, for the page or an image on it
            page.mouse.click(**self._at(page, 160, 220))
            page.mouse.click(**self._at(page, 160, 280))
            time.sleep(1)
            self.assertEqual(0, self.amazon.elsewhere_requests)

            # WHEN
            page.mouse.click(**self._at(page, 160, 100))
            page.evaluate("text => { const data = new DataTransfer(); data.setData('text/plain', text); "
                          "document.getElementById('input').dispatchEvent(new ClipboardEvent('paste', "
                          "{clipboardData: data, bubbles: true, cancelable: true})); }", PASSWORD)
            page.keyboard.press("Enter")

            # THEN
            self._assert_signed_in(page)
            self.assertEqual([PASSWORD], self.amazon.passwords)

    def test_sign_in_from_a_phone(self):
        with sync_playwright() as pw:
            # GIVEN
            page = self._open(pw, 390, 700, is_mobile=True, has_touch=True, device_scale_factor=3,
                              permissions=["clipboard-read", "clipboard-write"])

            # WHEN
            page.touchscreen.tap(**self._at(page, 160, 100))
            page.wait_for_function("() => document.activeElement.id === 'input'")
            # A phone's keyboard sends text, not keys, and Backspace as the text box getting shorter
            for character in EMAIL + "x":
                page.keyboard.insert_text(character)
            page.evaluate("() => { const input = document.getElementById('input'); "
                          "input.value = input.value.slice(0, -1); "
                          "input.dispatchEvent(new InputEvent('input', {inputType: 'deleteContentBackward'})); }")
            page.keyboard.insert_text("\n")
            self._wait_for(lambda: self.amazon.emails, "the email to be submitted")

            # THEN
            self.assertEqual([EMAIL], self.amazon.emails)

            # WHEN the password is pasted with the Paste button, as on a phone with no paste key
            page.touchscreen.tap(**self._at(page, 160, 100))
            page.evaluate("text => navigator.clipboard.writeText(text)", PASSWORD)
            page.tap("#paste")
            page.wait_for_function("() => document.activeElement.id === 'input'")
            page.keyboard.insert_text("\n")

            # THEN
            self._assert_signed_in(page)
            self.assertEqual([PASSWORD], self.amazon.passwords)

    def test_link_works_in_one_browser_only(self):
        with sync_playwright() as pw:
            # GIVEN someone has used the link
            page = self._open(pw, 800, 600)
            page.mouse.click(**self._at(page, 160, 100))
            self._wait_for(lambda: self.remote_login._view.claimed, "the link to be claimed")

            # WHEN
            other_page = pw.chromium.launch(headless=True).new_page()
            other_page.goto(self.remote_login.url)

            # THEN
            other_page.wait_for_function(
                "() => document.getElementById('status').textContent.includes('open in another browser')")

            # Ends the sign-in, so tearDown needn't wait for its timeout
            self.remote_login.cancel()
            self.login_thread.join(30)
            self.assertIn("cancelled", str(self.failure))
            self.assertEqual("failed", self.remote_login.state)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
