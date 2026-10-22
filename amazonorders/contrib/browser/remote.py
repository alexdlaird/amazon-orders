__copyright__ = "Copyright (c) 2026 Alex Laird"
__license__ = "MIT"

import base64
import logging
import os
import queue
import threading
import time
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from urllib.parse import urlparse

from amazonorders.contrib.browser.playwright import PlaywrightBrowserLogin
from amazonorders.contrib.browser.remote_server import (  # noqa: F401 (STATES and parse_input_event are re-exported)
    DEFAULT_VIEWPORT,
    FINAL_STATES,
    STATES,
    RemoteLoginServer,
    _RemoteLoginView,
    parse_input_event,
)
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
#: The environment variables that name the proxy the browser connects through, if any.
PROXY_ENVIRONMENT_VARIABLES = ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy")

#: The browsers Playwright supports that can't be shown on the sign-in page, since that takes Chromium's screencast.
NON_CHROMIUM_BROWSERS = frozenset({"firefox", "webkit"})

#: The browser's viewport is sized to the person's window, within these bounds.
MIN_VIEWPORT = (320, 400)
MAX_VIEWPORT = (1280, 1200)
#: The pixel density pages are drawn at, so text stays sharp on high-density screens.
DEVICE_SCALE_FACTOR = 2
SCREENCAST_QUALITY = 70

#: How long the sign-in, once over, waits for the page to fetch how it ended.
OUTCOME_GRACE_SECONDS = 5
REMOTE_SIGN_IN_POLL_INTERVAL_SECONDS = 1
REMOTE_PUMP_INTERVAL_MS = 25


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
        """How far the sign-in has got: one of :data:`~amazonorders.contrib.browser.remote_server.STATES`."""
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
        self._prepare()
        if timeout is None:
            timeout = self.config.remote_login_timeout

        if self._owns_server:
            self.server.start()
        self.server.add(self._view)
        try:
            message = (f"Info: To sign in to {self.config.site}, open this link in a browser within "
                       f"{_describe_duration(timeout)}. It works once, in the first browser that uses it.\n\n"
                       f"    {self.url}\n")
            logger.info(message.replace(self._view.token, "<token>"))
            self.amazon_session.io.echo(message)

            self._sign_in(timeout)
        finally:
            if self._view.claimed:
                self._view.outcome_fetched.wait(OUTCOME_GRACE_SECONDS)
            self.server.remove(self._view)
            if self._owns_server:
                self.server.stop()

    def _prepare(self) -> None:
        """
        Check that the sign-in can start, and give it a new link if it ran before.

        :raises AmazonOrdersError: If the browser isn't Chromium-based, or the sign-in was cancelled.
        """
        if self.config.browser in NON_CHROMIUM_BROWSERS:
            raise AmazonOrdersError(f"Signing in from another device needs a Chromium-based browser, not "
                                    f"{self.config.browser}. Set `browser` to `chromium`, or leave it unset.")
        if self._view.state in FINAL_STATES:
            self._view = _RemoteLoginView(self.config.site)
            self._cancelled.clear()
        if self._cancelled.is_set():
            self._view.set_state("failed")
            raise AmazonOrdersError("The sign-in was cancelled.")
        self._frame_acks = []

    def _sign_in(self,
                 timeout: int) -> None:
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
