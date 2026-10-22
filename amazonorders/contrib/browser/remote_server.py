__copyright__ = "Copyright (c) 2026 Alex Laird"
__license__ = "MIT"

import hashlib
import hmac
import html
import json
import logging
import os
import queue
import re
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from amazonorders.exception import AmazonOrdersError

logger = logging.getLogger(__name__)

#: The keys, beside a character combined with ``Control`` or ``Meta``, that the sign-in page passes to the browser.
SPECIAL_KEYS = frozenset({"Enter", "Tab", "Backspace", "Delete", "Escape", "ArrowLeft", "ArrowRight", "ArrowUp",
                          "ArrowDown", "Home", "End", "PageUp", "PageDown"})
MODIFIER_KEYS = ("Alt", "Control", "Meta", "Shift")
MOUSE_BUTTONS = frozenset({"left", "middle", "right"})

#: The size of the browser's viewport until the page says how big its window is.
DEFAULT_VIEWPORT = (1280, 800)

MAX_INPUT_BODY_BYTES = 64 * 1024
MAX_INPUT_EVENTS = 200
#: The most characters an ``insert`` event (a paste, or a phone keyboard's text) holds. A ``type`` event, which types
#: with key presses, holds one.
MAX_TEXT_LENGTH = 1000
MAX_COORDINATE = 10000
MAX_WHEEL_DELTA = 5000
MAX_QUEUED_INPUTS = 1000

#: How long a request for a new frame waits for one before returning without it.
FRAME_WAIT_SECONDS = 20
#: How many requests for a new frame may wait at once, for each sign-in.
MAX_FRAME_WAITS = 3

#: Every state a sign-in passes through, and the ones it ends in.
STATES = ("starting", "signing_in", "verifying", "signed_in", "failed", "timed_out")
FINAL_STATES = frozenset({"signed_in", "failed", "timed_out"})

TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32}$")
STATIC_FILES = {"remote-login.js": "text/javascript; charset=utf-8", "remote-login.css": "text/css; charset=utf-8"}
ACTIONS = frozenset({"frame", "input"})

PAGE_CONTENT_SECURITY_POLICY = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' blob:; "
                                "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")

GONE_PAGE = ("<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" "
             "content=\"width=device-width, initial-scale=1\"><title>Sign in to Amazon</title></head><body>"
             "<p>This sign-in link isn't valid anymore. Start a new sign-in for a new link.</p></body></html>")


class _RemoteLoginView:
    """
    One sign-in's state, shared between the browser's thread and the server's request threads: the latest frame of
    the page, the input waiting for the browser, and how far the sign-in has got.
    """

    def __init__(self,
                 site: str) -> None:
        #: The secret in the sign-in's link.
        self.token: str = secrets.token_urlsafe(24)
        #: The Amazon site being signed in to, e.g. ``amazon.de``.
        self.site: str = site
        #: The cookie that holds the claim of the first browser to pass on input.
        self.cookie_name: str = f"amazon_orders_sign_in_{hashlib.sha256(self.token.encode()).hexdigest()[:12]}"
        #: The input waiting for the browser, already checked.
        self.inputs: "queue.Queue[Dict[str, Any]]" = queue.Queue(maxsize=MAX_QUEUED_INPUTS)
        #: Set once a page has fetched how the sign-in ended.
        self.outcome_fetched: threading.Event = threading.Event()

        self._changed = threading.Condition()
        self._state = "starting"
        self._frame: Optional[bytes] = None
        self._frame_seq = 0
        self._viewport = DEFAULT_VIEWPORT
        self._claim: Optional[str] = None
        self._frame_waits = 0

    @property
    def state(self) -> str:
        with self._changed:
            return self._state

    @property
    def claimed(self) -> bool:
        with self._changed:
            return self._claim is not None

    def set_state(self,
                  state: str) -> None:
        with self._changed:
            if self._state in FINAL_STATES:
                return

            self._state = state
            self._changed.notify_all()

    def set_frame(self,
                  frame: bytes,
                  viewport: Tuple[int, int]) -> None:
        with self._changed:
            self._frame = frame
            self._frame_seq += 1
            self._viewport = viewport
            self._changed.notify_all()

    def claim(self,
              claim: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Let the first browser that passes on input use the sign-in, and only that browser after it.

        :param claim: The claim the browser holds, if any.
        :return: Whether the browser may use the sign-in, and a new claim to give it, if it was the first.
        """
        with self._changed:
            if self._claim is None:
                self._claim = secrets.token_urlsafe(24)
                return True, self._claim

            return claim is not None and hmac.compare_digest(claim, self._claim), None

    def holds_claim(self,
                    claim: Optional[str]) -> bool:
        with self._changed:
            return self._claim is not None and claim is not None and hmac.compare_digest(claim, self._claim)

    def may_view(self,
                 claim: Optional[str]) -> bool:
        """
        Whether a browser may see the page: any browser with the link until one claims it, by passing on input, and
        only that browser after. Seeing it before anyone types gives nothing away, and a link scanner that opens the
        link can't lock its person out.
        """
        with self._changed:
            return self._claim is None or (claim is not None and hmac.compare_digest(claim, self._claim))

    def start_frame_wait(self) -> bool:
        with self._changed:
            if self._frame_waits >= MAX_FRAME_WAITS:
                return False
            self._frame_waits += 1
            return True

    def end_frame_wait(self) -> None:
        with self._changed:
            self._frame_waits -= 1

    def wait(self,
             after_seq: int,
             known_state: str,
             timeout: float) -> Dict[str, Any]:
        """
        Wait until there's a frame newer than ``after_seq``, the state is no longer ``known_state``, or the timeout
        passes.

        :return: The state, and the latest frame, if it's newer than ``after_seq``.
        """
        with self._changed:
            self._changed.wait_for(lambda: self._frame_seq > after_seq or self._state != known_state, timeout)

            newer = self._frame is not None and self._frame_seq > after_seq
            return {"state": self._state, "seq": self._frame_seq,
                    "viewport": self._viewport, "frame": self._frame if newer else None}


class _RemoteLoginHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    # On Windows, reusing an address lets another program listen on the same port and take the page's requests
    allow_reuse_address = os.name != "nt"
    remote_login_server: "RemoteLoginServer"

    def handle_error(self,
                     request: Any,
                     client_address: Any) -> None:
        """
        Log a request that failed. The default prints a traceback to ``stderr``, e.g. each time a page is closed
        while it waits for a frame.
        """
        logger.debug("Sign-in page request failed", exc_info=True)


class _RemoteLoginRequestHandler(BaseHTTPRequestHandler):
    """Serves one sign-in's page, its frames and its input, each found by the token in its path."""

    server: _RemoteLoginHTTPServer
    protocol_version = "HTTP/1.1"
    server_version = "amazon-orders"
    sys_version = ""
    timeout = 60

    def do_GET(self) -> None:  # noqa: N802
        if not self._check_framing():
            return

        route = self._route()
        if route is None:
            self._send_gone()
            return

        target, action = route
        if target in STATIC_FILES and action == "static":
            self._send_static(target)
            return

        view = self.server.remote_login_server.find(target)
        if view is None:
            self._send_gone()
        elif action is None:
            self._send_page(view)
        elif action == "frame":
            self._send_frame(view)
        else:
            self._send(405, b"", "text/plain")

    def do_POST(self) -> None:  # noqa: N802
        if not self._check_framing():
            return

        route = self._route()
        view = self.server.remote_login_server.find(route[0]) if route is not None else None
        if route is None or view is None:
            self._send_gone()
        elif route[1] == "input":
            self._receive_input(view)
        else:
            self._send(405, b"", "text/plain")

    def send_error(self,
                   code: int,
                   message: Optional[str] = None,
                   explain: Optional[str] = None) -> None:
        """
        Answer with one of the standard library's own errors, like an unknown method or a malformed request, and
        close the connection, since the request's body is left unread.
        """
        self.close_connection = True
        super().send_error(code, message, explain)

    def log_message(self,
                    format: str,
                    *args: Any) -> None:
        """
        Log a request without its link's secret. The default logs each path to ``stderr``, and every path but the
        static files' carries one.
        """
        logger.debug("Sign-in page request: %s", re.sub(r"[A-Za-z0-9_-]{32}", "<token>", format % args))

    def _check_framing(self) -> bool:
        """
        Make sure a request's body can't be read as another request, since behind a reverse proxy the connection may
        carry other people's requests next. A chunked body is refused, and a body that isn't read closes the
        connection after the response (see :func:`_send`).
        """
        self._body_read = False
        if self.headers.get("Transfer-Encoding"):
            self.close_connection = True
            self._send(400, b"", "text/plain")
            return False

        return True

    def _route(self) -> Optional[Tuple[str, Optional[str]]]:
        """
        Find what the path asks for. The path's last segments decide, so the page works behind a proxy that serves it
        under any prefix: ``.../<token>`` is the page, ``.../<token>/<action>`` its calls, and
        ``.../_static/<file>`` the page's script and style.
        """
        segments = [""] + [segment for segment in urlparse(self.path).path.split("/") if segment]
        previous, last = segments[-2:] if len(segments) >= 2 else ("", "")
        if previous == "_static":
            return last, "static"
        if last in ACTIONS and TOKEN_PATTERN.match(previous):
            return previous, last
        if TOKEN_PATTERN.match(last):
            return last, None

        return None

    def _send_frame(self,
                    view: _RemoteLoginView) -> None:
        if not view.may_view(self._claim_cookie(view)):
            self._send_json(409, {"state": "claimed"})
            return

        query = parse_qs(urlparse(self.path).query)
        try:
            after_seq = int(query.get("after", ["0"])[0])
        except ValueError:
            after_seq = 0
        known_state = query.get("state", [""])[0]

        if not view.start_frame_wait():
            self._send(429, b"", "text/plain")
            return
        try:
            snapshot = view.wait(after_seq, known_state, FRAME_WAIT_SECONDS)
        finally:
            view.end_frame_wait()
        headers = {"X-Sign-In-State": snapshot["state"]}
        if snapshot["state"] in FINAL_STATES:
            view.outcome_fetched.set()
            self._send_json(200, {"state": snapshot["state"]}, headers)
        elif snapshot["frame"] is None:
            self._send(204, b"", None, headers)
        else:
            headers.update({"X-Frame-Seq": str(snapshot["seq"]),
                            "X-Viewport-Width": str(snapshot["viewport"][0]),
                            "X-Viewport-Height": str(snapshot["viewport"][1])})
            self._send(200, snapshot["frame"], "image/jpeg", headers)

    def _receive_input(self,
                       view: _RemoteLoginView) -> None:
        claim = self._claim_cookie(view)
        if not view.may_view(claim):
            self._send_json(409, {"state": "claimed"})
            return

        events = self._read_input()
        if events is None:
            return

        headers = self._claim_for(view, claim, events)
        if headers is None:
            self._send_json(409, {"state": "claimed"})
        elif not _queue_inputs(view, events):
            self._send(503, b"", "text/plain", headers)
        else:
            self._send(204, b"", None, headers)

    def _read_input(self) -> Optional[List[Dict[str, Any]]]:
        """
        Read and check the input the page sends, or answer with why it can't be.

        :return: The checked events, or ``None`` if the request was answered.
        """
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self._send(411, b"", "text/plain")
            return None
        if not 0 <= length <= MAX_INPUT_BODY_BYTES:
            self.close_connection = True
            self._send(413, b"", "text/plain")
            return None

        body = self.rfile.read(length)
        self._body_read = True
        try:
            return parse_input(body)
        except (ValueError, RecursionError) as e:
            logger.debug(f"Sign-in page input rejected: {e}")
            self._send(400, b"", "text/plain")
            return None

    def _claim_for(self,
                   view: _RemoteLoginView,
                   claim: Optional[str],
                   events: List[Dict[str, Any]]) -> Optional[Dict[str, str]]:
        """
        Let the first browser to pass on more than its size claim the sign-in, so only it may use it from then on.

        :return: The headers that give the browser its claim, if it was the first, or ``None`` if another browser
            claimed the sign-in first.
        """
        if all(event["t"] == "size" for event in events) or view.holds_claim(claim):
            return {}

        allowed, new_claim = view.claim(claim)
        if not allowed or new_claim is None:
            return None

        secure = "; Secure" if self.headers.get("X-Forwarded-Proto", "").lower() == "https" else ""
        return {"Set-Cookie": f"{view.cookie_name}={new_claim}; Path=/; HttpOnly; SameSite=Strict{secure}"}

    def _send_page(self,
                   view: _RemoteLoginView) -> None:
        page = (_read_static("remote-login.html").decode().replace("{site}", html.escape(view.site))
                .replace("{token}", view.token))
        self._send(200, page.encode(), "text/html; charset=utf-8",
                   {"Content-Security-Policy": PAGE_CONTENT_SECURITY_POLICY})

    def _send_static(self,
                     name: str) -> None:
        self._send(200, _read_static(name), STATIC_FILES[name])

    def _send_gone(self) -> None:
        self._send(404, GONE_PAGE.encode(), "text/html; charset=utf-8",
                   {"Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'"})

    def _send_json(self,
                   status: int,
                   body: Dict[str, Any],
                   headers: Optional[Dict[str, str]] = None) -> None:
        self._send(status, json.dumps(body).encode(), "application/json", headers)

    def _send(self,
              status: int,
              body: bytes,
              content_type: Optional[str],
              headers: Optional[Dict[str, str]] = None) -> None:
        if self._unread_body():
            self.close_connection = True

        self.send_response(status)
        if self.close_connection:
            self.send_header("Connection", "close")
        if content_type:
            self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _unread_body(self) -> bool:
        if getattr(self, "_body_read", False):
            return False

        length = self.headers.get("Content-Length")
        try:
            return length is not None and int(length) != 0
        except ValueError:
            return True

    def _claim_cookie(self,
                      view: _RemoteLoginView) -> Optional[str]:
        for cookie in self.headers.get_all("Cookie") or []:
            for pair in cookie.split(";"):
                name, _, value = pair.strip().partition("=")
                if name == view.cookie_name:
                    return value
        return None


class RemoteLoginServer:
    """
    Serves the page through which a person signs in to Amazon from a browser anywhere, like their phone, while the
    browser doing the sign-in runs headless on this machine, e.g. a server or a container. Each sign-in has its own
    link, which works once: the first browser to click or type on its page is the only one that can use it, until the
    sign-in ends.

    One server can serve several sign-ins at once.
    :class:`~amazonorders.contrib.browser.remote.PlaywrightRemoteLogin` starts and stops a server of its own
    when it isn't given one.

    :param host: The address to listen on. Listen on all of a container's interfaces (``0.0.0.0``) only with its port
        published to a single address, e.g. ``-p 127.0.0.1:8765:8765``.
    :param port: The port to listen on, or ``0`` for any free one.
    :param url: The address people open the links at, e.g. ``https://example.com/amazon-sign-in/`` behind a reverse
        proxy. By default, ``http://localhost:<port>/``.
    """

    def __init__(self,
                 host: str = "127.0.0.1",
                 port: int = 8765,
                 url: Optional[str] = None) -> None:
        if url is not None and urlparse(url).scheme not in ("http", "https"):
            raise AmazonOrdersError(f"The sign-in page's URL must start with http:// or https://, not: {url}")

        #: The address to listen on.
        self.host: str = host
        #: The port to listen on.
        self.port: int = port

        self._url = url
        self._views: Dict[str, _RemoteLoginView] = {}
        self._lock = threading.Lock()
        self._httpd: Optional[_RemoteLoginHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def url(self) -> str:
        """The address people open the links at, ending with ``/``."""
        if self._url is not None:
            return self._url if self._url.endswith("/") else f"{self._url}/"

        port = self._httpd.server_address[1] if self._httpd is not None else self.port
        return f"http://localhost:{port}/"

    @property
    def running(self) -> bool:
        return self._httpd is not None

    def start(self) -> None:
        """
        Start serving, in a background thread.

        :raises AmazonOrdersError: If the server can't listen on its address.
        """
        if self._httpd is not None:
            return

        try:
            httpd = _RemoteLoginHTTPServer((self.host, self.port), _RemoteLoginRequestHandler)
        except OSError as e:
            raise AmazonOrdersError(f"Could not serve the sign-in page on {self.host}:{self.port}: {e}") from e
        httpd.remote_login_server = self

        self._httpd = httpd
        self._thread = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.1},
                                        name="amazon-orders-sign-in-page", daemon=True)
        self._thread.start()
        logger.debug(f"Serving sign-in pages on {self.host}:{httpd.server_address[1]}")

    def stop(self) -> None:
        """Stop serving."""
        httpd, self._httpd = self._httpd, None
        if httpd is None:
            return

        httpd.shutdown()
        httpd.server_close()
        if self._thread is not None:
            self._thread.join()

    def link(self,
             view: _RemoteLoginView) -> str:
        return f"{self.url}{view.token}"

    def add(self,
            view: _RemoteLoginView) -> None:
        with self._lock:
            self._views[view.token] = view

    def remove(self,
               view: _RemoteLoginView) -> None:
        with self._lock:
            self._views.pop(view.token, None)

    def find(self,
             token: str) -> Optional[_RemoteLoginView]:
        with self._lock:
            views = list(self._views.values())

        return next((view for view in views if hmac.compare_digest(view.token, token)), None)


def parse_input(body: bytes) -> List[Dict[str, Any]]:
    """
    Check the input the sign-in page sends: a JSON list of events.

    :param body: The request's body.
    :return: The checked events.
    :raises ValueError: If the body isn't a list of events the page sends.
    """
    events = json.loads(body)
    if not isinstance(events, list) or len(events) > MAX_INPUT_EVENTS:
        raise ValueError("Expected a list of events")

    return [parse_input_event(event) for event in events]


def _queue_inputs(view: _RemoteLoginView,
                  events: List[Dict[str, Any]]) -> bool:
    for event in events:
        try:
            view.inputs.put_nowait(event)
        except queue.Full:
            return False
    return True


def parse_input_event(event: Any) -> Dict[str, Any]:
    """
    Check one event of the input the sign-in page sends, and normalize it for the browser.

    :param event: The event, as decoded from JSON.
    :return: The checked event.
    :raises ValueError: If the event isn't one the page sends.
    """
    kind = event.get("t") if isinstance(event, dict) else None
    parser = _EVENT_PARSERS.get(kind) if isinstance(kind, str) else None
    if parser is None:
        raise ValueError(f"Unknown event: {kind!r}")

    return {"t": kind, **parser(event)}


def _parse_point(event: Dict[str, Any]) -> Dict[str, Any]:
    return {"x": _number(event, "x", 0, MAX_COORDINATE), "y": _number(event, "y", 0, MAX_COORDINATE)}


def _parse_button(event: Dict[str, Any]) -> Dict[str, Any]:
    button = event.get("button", "left")
    if not isinstance(button, str) or button not in MOUSE_BUTTONS:
        raise ValueError(f"Unknown mouse button: {button!r}")
    return {**_parse_point(event), "button": button}


def _parse_wheel(event: Dict[str, Any]) -> Dict[str, Any]:
    return {**_parse_point(event), "dx": _number(event, "dx", -MAX_WHEEL_DELTA, MAX_WHEEL_DELTA),
            "dy": _number(event, "dy", -MAX_WHEEL_DELTA, MAX_WHEEL_DELTA)}


def _parse_text(event: Dict[str, Any],
                maximum: int) -> Dict[str, Any]:
    text = event.get("text")
    if not isinstance(text, str) or not 1 <= len(text) <= maximum:
        raise ValueError(f"Text must be 1 to {maximum} characters")
    return {"text": text}


def _parse_key(event: Dict[str, Any]) -> Dict[str, Any]:
    key = event.get("key")
    mods = _parse_modifiers(event.get("mods", []))
    if not isinstance(key, str) or (key not in SPECIAL_KEYS and not _is_shortcut(key, mods)):
        raise ValueError(f"Unsupported key: {key!r}")

    # A shortcut like Cmd+A on a Mac is Ctrl+A in the browser here, so either modifier means whichever this one uses
    names = ["ControlOrMeta" if mod in ("Control", "Meta") else mod for mod in MODIFIER_KEYS if mod in mods]
    return {"key": key, "mods": list(dict.fromkeys(names))}


def _is_shortcut(key: str,
                 mods: List[str]) -> bool:
    return len(key) == 1 and key.isalnum() and ("Control" in mods or "Meta" in mods)


def _parse_modifiers(mods: Any) -> List[str]:
    if not isinstance(mods, list) or not all(isinstance(mod, str) and mod in MODIFIER_KEYS for mod in mods):
        raise ValueError(f"Unknown modifiers: {mods!r}")
    return mods


def _parse_size(event: Dict[str, Any]) -> Dict[str, Any]:
    return {"w": int(_number(event, "w", 1, MAX_COORDINATE)), "h": int(_number(event, "h", 1, MAX_COORDINATE)),
            "dpr": _number(event, "dpr", 1, 4)}


#: How each kind of event the page sends is checked.
_EVENT_PARSERS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "move": _parse_point,
    "down": _parse_button,
    "up": _parse_button,
    "wheel": _parse_wheel,
    "type": lambda event: _parse_text(event, 1),
    "insert": lambda event: _parse_text(event, MAX_TEXT_LENGTH),
    "key": _parse_key,
    "size": _parse_size,
}


def _number(event: Dict[str, Any],
            key: str,
            minimum: float,
            maximum: float) -> float:
    value = event.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        raise ValueError(f"{key} must be a number")
    return float(min(max(value, minimum), maximum))


def _read_static(name: str) -> bytes:
    return resources.files("amazonorders.contrib.browser").joinpath("static").joinpath(name).read_bytes()
