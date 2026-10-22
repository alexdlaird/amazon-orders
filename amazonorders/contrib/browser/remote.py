__copyright__ = "Copyright (c) 2026 Alex Laird"
__license__ = "MIT"

import base64
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
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

from amazonorders.contrib.browser.playwright import PlaywrightBrowserLogin
from amazonorders.exception import AmazonOrdersBrowserNotInstalledError, AmazonOrdersError

if TYPE_CHECKING:
    from amazonorders.session import AmazonSession

logger = logging.getLogger(__name__)

#: Hosts beside the site's own that the browser may navigate to while signing in, all of them Amazon's.
NAVIGATION_HOST_SUFFIXES = ("amazon.com",)
#: Hosts beside those that Amazon's sign-in pages load images, scripts, metrics and AWS WAF challenges from. The
#: browser requests nothing from any other host, so the sign-in page can't be used to browse anywhere else.
RESOURCE_HOST_SUFFIXES = ("media-amazon.com", "ssl-images-amazon.com", "images-amazon.com", "awswaf.com",
                          "cloudfront.net", "a2z.com")

#: The keys, beside a character combined with ``Control`` or ``Meta``, that the sign-in page passes to the browser.
SPECIAL_KEYS = frozenset({"Enter", "Tab", "Backspace", "Delete", "Escape", "ArrowLeft", "ArrowRight", "ArrowUp",
                          "ArrowDown", "Home", "End", "PageUp", "PageDown"})
MODIFIER_KEYS = ("Alt", "Control", "Meta", "Shift")
MOUSE_BUTTONS = frozenset({"left", "middle", "right"})
#: The browsers Playwright supports that can't be shown on the sign-in page, since that takes Chromium's screencast.
NON_CHROMIUM_BROWSERS = frozenset({"firefox", "webkit"})

#: The browser's viewport is sized to the person's window, within these bounds.
MIN_VIEWPORT = (320, 400)
MAX_VIEWPORT = (1280, 1200)
DEFAULT_VIEWPORT = (1280, 800)
#: The pixel density pages are drawn at, so text stays sharp on high-density screens.
DEVICE_SCALE_FACTOR = 2
SCREENCAST_QUALITY = 70

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
#: How long the sign-in, once over, waits for the page to fetch how it ended.
OUTCOME_GRACE_SECONDS = 5
REMOTE_SIGN_IN_POLL_INTERVAL_SECONDS = 1
REMOTE_PUMP_INTERVAL_MS = 25

#: Every state a sign-in passes through, and the ones it ends in.
STATES = ("starting", "signing_in", "verifying", "signed_in", "failed", "timed_out")
FINAL_STATES = frozenset({"signed_in", "failed", "timed_out"})

TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32}$")
#: The environment variables that name the proxy the browser connects through, if any.
PROXY_ENVIRONMENT_VARIABLES = ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy")

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
    remote_login_server: "RemoteLoginServer"

    def handle_error(self,
                     request: Any,
                     client_address: Any) -> None:
        # The default prints a traceback to stderr, e.g. each time a page is closed while it waits for a frame
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
        # The standard library's own errors (an unknown method, a malformed request) leave any body unread
        self.close_connection = True
        super().send_error(code, message, explain)

    def log_message(self,
                    format: str,
                    *args: Any) -> None:
        # The default logs each path to stderr, and every path but the static files' carries a sign-in's secret
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
        segments = [segment for segment in urlparse(self.path).path.split("/") if segment]
        if len(segments) >= 2 and segments[-2] == "_static":
            return segments[-1], "static"
        if len(segments) >= 2 and segments[-1] in ACTIONS and TOKEN_PATTERN.match(segments[-2]):
            return segments[-2], segments[-1]
        if segments and TOKEN_PATTERN.match(segments[-1]):
            return segments[-1], None

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

        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self._send(411, b"", "text/plain")
            return
        if length > MAX_INPUT_BODY_BYTES or length < 0:
            self.close_connection = True
            self._send(413, b"", "text/plain")
            return

        body = self.rfile.read(length)
        self._body_read = True
        try:
            events = json.loads(body)
            if not isinstance(events, list) or len(events) > MAX_INPUT_EVENTS:
                raise ValueError("Expected a list of events")
            checked = [parse_input_event(event) for event in events]
        except (ValueError, RecursionError) as e:
            logger.debug(f"Sign-in page input rejected: {e}")
            self._send(400, b"", "text/plain")
            return

        # The first browser to pass on more than its size claims the sign-in, and only it may use it from then on
        headers = {}
        if any(event["t"] != "size" for event in checked) and not view.holds_claim(claim):
            allowed, new_claim = view.claim(claim)
            if not allowed or new_claim is None:
                self._send_json(409, {"state": "claimed"})
                return

            secure = "; Secure" if self.headers.get("X-Forwarded-Proto", "").lower() == "https" else ""
            headers["Set-Cookie"] = f"{view.cookie_name}={new_claim}; Path=/; HttpOnly; SameSite=Strict{secure}"

        for event in checked:
            try:
                view.inputs.put_nowait(event)
            except queue.Full:
                self._send(503, b"", "text/plain", headers)
                return
        self._send(204, b"", None, headers)

    def _send_page(self,
                   view: _RemoteLoginView) -> None:
        page = _read_static("remote-login.html").decode().replace("{site}", html.escape(view.site))
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

    One server can serve several sign-ins at once. :class:`PlaywrightRemoteLogin` starts and stops a server of its own
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


class PlaywrightRemoteLogin(PlaywrightBrowserLogin):
    """
    Signs in to Amazon on Amazon's own page, like
    :class:`~amazonorders.contrib.browser.playwright.PlaywrightBrowserLogin`, for a machine without a display, like a
    server or a container. The browser runs headless on this machine, and the person signs in from a browser anywhere,
    like their phone, through a one-time link to a page that shows Amazon's sign-in page and passes their clicks and
    typing on to it. What they type passes through this machine on its way to Amazon's page, so open the link over
    HTTPS (e.g. behind a reverse proxy) or through ``localhost`` (e.g. an SSH tunnel). ``amazon-orders`` keeps and logs
    none of it.

    .. code-block:: python

        from amazonorders.contrib.browser.remote import PlaywrightRemoteLogin
        from amazonorders.session import AmazonSession

        amazon_session = AmazonSession()
        PlaywrightRemoteLogin(amazon_session).login()

    The link is echoed when the sign-in starts, and is :attr:`url`. Without a ``server``, the page is served while the
    sign-in runs, as the ``remote_login_host``, ``remote_login_port`` and ``remote_login_url`` config values say.

    The browser can only reach Amazon's hosts, so it loads nothing but Amazon's pages and what they need, even through
    a redirect, and it opens no other windows. Passkeys can't be used from another device, so sign in with a password
    (and a one-time passcode, if asked for one).

    Requires the ``[browser]`` extra: ``pip install amazon-orders[browser]``. The browser must be Chromium-based, as
    Chrome, Edge and Playwright's Chromium are.

    :param amazon_session: The session to sign in.
    :param server: The server to serve the page on, if not one of its own.
    """

    def __init__(self,
                 amazon_session: "AmazonSession",
                 server: Optional[RemoteLoginServer] = None) -> None:
        super().__init__(amazon_session)
        self.headless = True
        #: The server the page is served on.
        self.server: RemoteLoginServer = server or RemoteLoginServer(host=self.config.remote_login_host,
                                                                     port=self.config.remote_login_port,
                                                                     url=self.config.remote_login_url)

        self._owns_server = server is None
        self._view = _RemoteLoginView(self.config.site)
        self._cancelled = threading.Event()
        self._viewport = DEFAULT_VIEWPORT
        self._cdp: Any = None
        self._frame_acks: List[int] = []

    @property
    def url(self) -> str:
        """The sign-in's link."""
        return self.server.link(self._view)

    @property
    def state(self) -> str:
        """How far the sign-in has got: one of :data:`STATES`."""
        return self._view.state

    def cancel(self) -> None:
        """
        End the sign-in from another thread: :func:`login` raises once it notices, or straight away if it hasn't
        started.
        """
        self._cancelled.set()

    def login(self,
              timeout: Optional[int] = None) -> None:
        """
        Serve the sign-in's link, open Amazon's sign-in page in a headless browser, wait for the sign-in to be
        completed there through the link, then persist the resulting session. On success, ``is_authenticated`` is set
        to ``True`` on the session.

        :param timeout: The number of seconds to wait for the sign-in to be completed. By default, the
            ``remote_login_timeout`` config value.
        :raises AmazonOrdersBrowserNotInstalledError: If no browser is installed to sign in with.
        :raises AmazonOrdersError: If the ``[browser]`` extra is not installed, the page can't be served, the browser
            stops or the timeout passes before the sign-in completes, or Amazon does not accept the browser's session.
        """
        if self.config.browser in NON_CHROMIUM_BROWSERS:
            raise AmazonOrdersError(f"Signing in from another device needs a Chromium-based browser, not "
                                    f"{self.config.browser}. Set `browser` to `chromium`, or leave it unset.")
        if timeout is None:
            timeout = self.config.remote_login_timeout
        if self._view.state in FINAL_STATES:
            self._view = _RemoteLoginView(self.config.site)
            self._cancelled.clear()
        if self._cancelled.is_set():
            self._view.set_state("failed")
            raise AmazonOrdersError("The sign-in was cancelled.")
        self._frame_acks = []

        if self._owns_server:
            self.server.start()
        self.server.add(self._view)
        try:
            message = (f"Info: To sign in to {self.config.site}, open this link in a browser within "
                       f"{_describe_duration(timeout)}. It works once, in the first browser that uses it.\n\n"
                       f"    {self.url}\n")
            logger.info(message.replace(self._view.token, "<token>"))
            self.amazon_session.io.echo(message)

            try:
                super().login(timeout)
            except AmazonOrdersBrowserNotInstalledError as e:
                self._view.set_state("failed")
                # Only a Chromium-based browser can be shown on the sign-in page, so it's the only one to download
                browser_types = [name for name in (e.meta or {}).get("browser_types", [])
                                 if name not in NON_CHROMIUM_BROWSERS]
                raise AmazonOrdersBrowserNotInstalledError(str(e), meta={**(e.meta or {}),
                                                                         "browser_types": browser_types}) from e
            except BaseException:
                self._view.set_state("failed")
                raise
            self._view.set_state("signed_in")
        finally:
            if self._view.claimed:
                self._view.outcome_fetched.wait(OUTCOME_GRACE_SECONDS)
            self.server.remove(self._view)
            if self._owns_server:
                self.server.stop()

    def _launch_args(self) -> Optional[List[str]]:
        # The allowlist in _route() sees a request's first URL, but not the ones it redirects to, so the browser can
        # only look up the same hosts' addresses too: any other host, and any IP address, resolves to nothing. A proxy
        # looks up the hosts it connects to itself, so behind one, only the proxy's own host is looked up here
        hosts = self._allowed_hosts(top_level=False)
        rules = (["MAP * ~NOTFOUND"] + [f"EXCLUDE {pattern}" for host in hosts for pattern in (host, f"*.{host}")]
                 + [f"EXCLUDE {host}" for host in _proxy_hosts()])
        return [f"--host-resolver-rules={', '.join(rules)}"]

    def _new_context(self,
                     browser: Any) -> Any:
        context = browser.new_context(user_agent=self.config.constants.BASE_HEADERS.get("User-Agent"),
                                      viewport={"width": self._viewport[0], "height": self._viewport[1]},
                                      device_scale_factor=DEVICE_SCALE_FACTOR,
                                      accept_downloads=False,
                                      service_workers="block")
        context.route("**/*", self._route)
        return context

    def _on_sign_in_page(self,
                         context: Any,
                         page: Any) -> None:
        self._cdp = context.new_cdp_session(page)
        self._cdp.on("Page.screencastFrame", self._on_frame)
        self._start_screencast(DEVICE_SCALE_FACTOR)
        self._view.set_state("signing_in")

    def _wait_for_sign_in(self,
                          context: Any,
                          page: Any,
                          timeout: int) -> None:
        deadline = time.monotonic() + timeout
        next_check = 0.0
        while time.monotonic() < deadline:
            if self._cancelled.is_set():
                raise AmazonOrdersError("The sign-in was cancelled.")
            if time.monotonic() >= next_check:
                if self._is_signed_in(context.cookies()):
                    self._view.set_state("verifying")
                    return
                next_check = time.monotonic() + REMOTE_SIGN_IN_POLL_INTERVAL_SECONDS

            self._ack_frames()
            self._close_other_pages(context, page)
            self._dispatch_inputs(page)
            page.wait_for_timeout(REMOTE_PUMP_INTERVAL_MS)

        self._view.set_state("timed_out")
        raise AmazonOrdersError(f"Timed out after {timeout} seconds waiting for sign-in to complete in the browser.")

    def _route(self,
               route: Any) -> None:
        request = route.request
        top_level = request.is_navigation_request() and request.frame.parent_frame is None
        if self._is_allowed_url(request.url, top_level):
            route.continue_()
        else:
            logger.debug(f"Blocked the sign-in browser's request to {urlparse(request.url).hostname}")
            route.abort("blockedbyclient")

    def _is_allowed_url(self,
                        url: str,
                        top_level: bool) -> bool:
        """
        Whether the sign-in browser may request ``url``: only the site's own pages and Amazon's, and for what those
        pages load, the hosts they load it from.

        :param url: The URL requested.
        :param top_level: Whether the request navigates the page itself, rather than loading part of it.
        :return: Whether the request is allowed.
        """
        parsed = urlparse(url)
        if parsed.scheme not in ("https", urlparse(self.config.constants.BASE_URL).scheme):
            return False

        host = (parsed.hostname or "").lower()

        return any(self._is_domain_or_subdomain(host, suffix) for suffix in self._allowed_hosts(top_level))

    def _allowed_hosts(self,
                       top_level: bool) -> Tuple[str, ...]:
        """
        The hosts the sign-in browser may request, with their subdomains: the site's own and Amazon's, and for what
        their pages load, the hosts they load it from.
        """
        hosts: Tuple[str, ...] = (self.config.site,) + NAVIGATION_HOST_SUFFIXES

        return hosts if top_level else hosts + RESOURCE_HOST_SUFFIXES

    def _start_screencast(self,
                          density: float) -> None:
        scale = min(density, DEVICE_SCALE_FACTOR)
        self._cdp.send("Page.startScreencast", {"format": "jpeg", "quality": SCREENCAST_QUALITY,
                                                "maxWidth": int(self._viewport[0] * scale),
                                                "maxHeight": int(self._viewport[1] * scale)})

    def _on_frame(self,
                  params: Dict[str, Any]) -> None:
        # The size the frame was drawn at, which a frame drawn before a resize has from before it
        metadata = params.get("metadata") or {}
        viewport = (round(metadata.get("deviceWidth") or self._viewport[0]),
                    round(metadata.get("deviceHeight") or self._viewport[1]))
        self._view.set_frame(base64.b64decode(params["data"]), viewport)
        self._frame_acks.append(params["sessionId"])

    def _ack_frames(self) -> None:
        # Chromium sends the next frame once this one is acknowledged, which the sync API can only do outside of the
        # frame's event handler
        while self._frame_acks:
            self._cdp.send("Page.screencastFrameAck", {"sessionId": self._frame_acks.pop(0)})

    @staticmethod
    def _close_other_pages(context: Any,
                           page: Any) -> None:
        for other_page in context.pages:
            if other_page is not page:
                other_page.close()

    def _dispatch_inputs(self,
                         page: Any) -> None:
        from playwright.sync_api import Error as PlaywrightError  # type: ignore[import-not-found]

        # Only what's already queued, so input that keeps coming can't keep the sign-in from timing out or ending
        for _ in range(self._view.inputs.qsize()):
            try:
                event = self._view.inputs.get_nowait()
            except queue.Empty:  # pragma: no cover
                return

            try:
                self._dispatch_input(page, event)
            except PlaywrightError as e:
                logger.debug(f"Could not pass on input to the sign-in page: {e}")

    def _dispatch_input(self,
                        page: Any,
                        event: Dict[str, Any]) -> None:
        kind = event["t"]
        if kind == "size":
            self._resize(page, event["w"], event["h"], event["dpr"])
        elif kind == "key":
            page.keyboard.press("+".join(event["mods"] + [event["key"]]))
        elif kind == "type":
            page.keyboard.type(event["text"])
        elif kind == "insert":
            page.keyboard.insert_text(event["text"])
        else:
            page.mouse.move(event["x"], event["y"])
            if kind == "down":
                page.mouse.down(button=event["button"])
            elif kind == "up":
                page.mouse.up(button=event["button"])
            elif kind == "wheel":
                page.mouse.wheel(event["dx"], event["dy"])

    def _resize(self,
                page: Any,
                width: int,
                height: int,
                density: float) -> None:
        viewport = (min(max(width, MIN_VIEWPORT[0]), MAX_VIEWPORT[0]),
                    min(max(height, MIN_VIEWPORT[1]), MAX_VIEWPORT[1]))
        if viewport != self._viewport:
            self._viewport = viewport
            page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
            # Keep the field being typed in on screen, as a phone's keyboard opening shrinks the window
            page.evaluate("() => { const el = document.activeElement; "
                          "if (el && el !== document.body) el.scrollIntoView({block: 'center'}); }")

        self._cdp.send("Page.stopScreencast")
        self._start_screencast(density)


def parse_input_event(event: Any) -> Dict[str, Any]:
    """
    Check one event of the input the sign-in page sends, and normalize it for the browser.

    :param event: The event, as decoded from JSON.
    :return: The checked event.
    :raises ValueError: If the event isn't one the page sends.
    """
    if not isinstance(event, dict):
        raise ValueError("An event must be an object")

    kind = event.get("t")
    if not isinstance(kind, str):
        raise ValueError(f"Unknown event: {kind!r}")
    if kind in ("move", "down", "up", "wheel"):
        checked: Dict[str, Any] = {"t": kind, "x": _number(event, "x", 0, MAX_COORDINATE),
                                   "y": _number(event, "y", 0, MAX_COORDINATE)}
        if kind in ("down", "up"):
            button = event.get("button", "left")
            if not isinstance(button, str) or button not in MOUSE_BUTTONS:
                raise ValueError(f"Unknown mouse button: {button!r}")
            checked["button"] = button
        elif kind == "wheel":
            checked["dx"] = _number(event, "dx", -MAX_WHEEL_DELTA, MAX_WHEEL_DELTA)
            checked["dy"] = _number(event, "dy", -MAX_WHEEL_DELTA, MAX_WHEEL_DELTA)
        return checked
    elif kind in ("type", "insert"):
        text = event.get("text")
        maximum = 1 if kind == "type" else MAX_TEXT_LENGTH
        if not isinstance(text, str) or not text or len(text) > maximum:
            raise ValueError(f"Text to {kind} must be 1 to {maximum} characters")
        return {"t": kind, "text": text}
    elif kind == "key":
        return {"t": kind, **_parse_key(event)}
    elif kind == "size":
        return {"t": kind, "w": int(_number(event, "w", 1, MAX_COORDINATE)),
                "h": int(_number(event, "h", 1, MAX_COORDINATE)), "dpr": _number(event, "dpr", 1, 4)}

    raise ValueError(f"Unknown event: {kind!r}")


def _parse_key(event: Dict[str, Any]) -> Dict[str, Any]:
    key = event.get("key")
    mods = event.get("mods", [])
    if not isinstance(key, str):
        raise ValueError(f"Unsupported key: {key!r}")
    if not isinstance(mods, list) or any(not isinstance(mod, str) or mod not in MODIFIER_KEYS for mod in mods):
        raise ValueError(f"Unknown modifiers: {mods!r}")
    shortcut = len(key) == 1 and key.isalnum() and ("Control" in mods or "Meta" in mods)
    if key not in SPECIAL_KEYS and not shortcut:
        raise ValueError(f"Unsupported key: {key!r}")

    # A shortcut like Cmd+A on a Mac is Ctrl+A in the browser here, so either modifier means whichever this one uses
    names = ["ControlOrMeta" if mod in ("Control", "Meta") else mod for mod in MODIFIER_KEYS if mod in mods]
    return {"key": key, "mods": list(dict.fromkeys(names))}


def _proxy_hosts() -> List[str]:
    hosts = []
    for name in PROXY_ENVIRONMENT_VARIABLES:
        value = os.environ.get(name, "").strip()
        host = urlparse(value if "://" in value else f"//{value}").hostname if value else None
        if host and host not in hosts:
            hosts.append(host)
    return hosts


def _describe_duration(seconds: int) -> str:
    if seconds % 60 or seconds < 120:
        return f"{seconds} second{'' if seconds == 1 else 's'}"
    return f"{seconds // 60} minutes"


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
