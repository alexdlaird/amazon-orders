__copyright__ = "Copyright (c) 2026 Alex Laird"
__license__ = "MIT"

import os
import sys
import time
from unittest.mock import MagicMock, patch

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.contrib.browser import remote
from amazonorders.contrib.browser.playwright import PlaywrightBrowserLogin
from amazonorders.contrib.browser.remote import PlaywrightRemoteLogin, RemoteLoginServer
from amazonorders.exception import AmazonOrdersBrowserNotInstalledError, AmazonOrdersError
from amazonorders.session import AmazonSession
from tests.unit.contrib.test_playwright import _FakePlaywrightError, _make_mock_playwright, _playwright_module
from tests.unittestcase import UnitTestCase

SIGNED_IN_COOKIES = [{"name": "x-main", "value": "signed-in", "domain": ".amazon.com", "path": "/"}]


class TestDescribeDuration(UnitTestCase):
    def test_describe_duration(self):
        self.assertEqual("1 second", remote._describe_duration(1))
        self.assertEqual("90 seconds", remote._describe_duration(90))
        self.assertEqual("10 minutes", remote._describe_duration(600))
        self.assertEqual("630 seconds", remote._describe_duration(630))


class TestPlaywrightRemoteLogin(UnitTestCase):
    def setUp(self):
        super().setUp()
        self.amazon_session = AmazonSession(config=self.test_config)
        self.server = MagicMock(spec=RemoteLoginServer)
        self.server.link.side_effect = lambda view: f"https://example.com/sign-in/{view.token}"
        self.remote_login = PlaywrightRemoteLogin(self.amazon_session, server=self.server)

    def given_playwright(self, pw_cookies=None):
        mock_sync_playwright, page, context, browser = _make_mock_playwright(
            pw_cookies=SIGNED_IN_COOKIES if pw_cookies is None else pw_cookies)
        page.wait_for_timeout.side_effect = lambda ms: None
        context.pages = [page]
        modules = {"playwright": MagicMock(), "playwright.sync_api": _playwright_module(mock_sync_playwright)}
        self.pw = mock_sync_playwright.return_value.__enter__.return_value
        return patch.dict(sys.modules, modules), page, context, browser

    def test_defaults_from_config(self):
        # GIVEN
        config = AmazonOrdersConfig(config_path=self.test_config.config_path,
                                    data={**self.test_config._data, "remote_login_host": "192.0.2.10",
                                          "remote_login_port": 9000,
                                          "remote_login_url": "https://example.com/sign-in"})

        # WHEN
        remote_login = PlaywrightRemoteLogin(AmazonSession(config=config))

        # THEN
        self.assertTrue(remote_login.headless)
        self.assertEqual("192.0.2.10", remote_login.server.host)
        self.assertEqual(9000, remote_login.server.port)
        self.assertTrue(remote_login.url.startswith("https://example.com/sign-in/"))
        self.assertEqual("starting", remote_login.state)

    @patch.object(PlaywrightBrowserLogin, "_verify_session")
    def test_login(self, mock_verify_session):
        # GIVEN
        modules, page, context, browser = self.given_playwright()
        self.amazon_session.io = MagicMock()
        url = self.remote_login.url

        # WHEN
        with modules:
            self.remote_login.login(timeout=60)

        # THEN
        self.assertEqual("signed_in", self.remote_login.state)
        mock_verify_session.assert_called_once()
        self.server.start.assert_not_called()
        self.server.add.assert_called_once_with(self.remote_login._view)
        self.server.remove.assert_called_once_with(self.remote_login._view)
        echoed = self.amazon_session.io.echo.call_args[0][0]
        self.assertIn("within 60 seconds.", echoed)
        self.assertIn(url, echoed)
        # The browser is headless, loads only what's allowed, and is shown through a screencast
        self.assertTrue(browser.new_context.call_args.kwargs["device_scale_factor"] > 1)
        self.assertFalse(browser.new_context.call_args.kwargs["accept_downloads"])
        context.route.assert_called_once_with("**/*", self.remote_login._route)
        cdp = context.new_cdp_session.return_value
        cdp.send.assert_any_call("Page.startScreencast", {"format": "jpeg", "quality": 70, "maxWidth": 2560,
                                                          "maxHeight": 1600})
        browser.close.assert_called_once()

    def test_launch_args_limit_name_resolution(self):
        # WHEN
        args = self.remote_login._launch_args()

        # THEN
        self.assertEqual(1, len(args))
        self.assertTrue(args[0].startswith("--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE amazon.com, "
                                           "EXCLUDE *.amazon.com, "))
        for host in ("media-amazon.com", "awswaf.com", "cloudfront.net"):
            self.assertIn(f"EXCLUDE {host}, EXCLUDE *.{host}", args[0])

        # WHEN
        self.amazon_session.config.set_domain("amazon.de")

        # THEN
        self.assertIn("EXCLUDE amazon.de, EXCLUDE *.amazon.de, EXCLUDE amazon.com",
                      self.remote_login._launch_args()[0])

    def test_launch_args_let_the_proxy_be_looked_up(self):
        # GIVEN (one case of each name, since Windows reads them case-insensitively)
        with patch.dict(os.environ):
            for name in remote.PROXY_ENVIRONMENT_VARIABLES:
                os.environ.pop(name, None)
            os.environ.update({"HTTPS_PROXY": "http://user:secret@proxy.example.com:1080", "HTTP_PROXY": "proxy:3128"})

            # WHEN
            args = self.remote_login._launch_args()

        # THEN
        self.assertTrue(args[0].endswith(", EXCLUDE proxy.example.com, EXCLUDE proxy"))
        self.assertNotIn("secret", args[0])

    @patch.object(PlaywrightBrowserLogin, "_verify_session")
    def test_login_launches_with_the_launch_args(self, mock_verify_session):
        # GIVEN
        modules, _, _, _ = self.given_playwright()

        # WHEN
        with modules:
            self.remote_login.login(timeout=60)

        # THEN
        self.pw.chromium.launch.assert_called_once_with(channel="chrome", headless=True,
                                                        args=self.remote_login._launch_args())

    def test_login_without_a_browser_offers_only_chromium(self):
        # GIVEN
        modules, _, _, _ = self.given_playwright()
        not_installed = AmazonOrdersBrowserNotInstalledError("No default browser was found.",
                                                             meta={"browser_types": ["chromium", "firefox", "webkit"]})

        # WHEN
        with modules, patch("amazonorders.contrib.browser.playwright.PlaywrightBrowserLauncher") as mock_launcher, \
                self.assertRaises(AmazonOrdersBrowserNotInstalledError) as cm:
            mock_launcher.return_value.launch.side_effect = not_installed
            self.remote_login.login(timeout=60)

        # THEN
        self.assertEqual("No default browser was found.", str(cm.exception))
        self.assertEqual(["chromium"], cm.exception.meta["browser_types"])
        self.assertEqual("failed", self.remote_login.state)

    def test_frame_has_the_size_it_was_drawn_at(self):
        # WHEN
        self.remote_login._on_frame({"data": "anBlZw==", "sessionId": 1,
                                     "metadata": {"deviceWidth": 390.4, "deviceHeight": 700}})

        # THEN
        self.assertEqual((390, 700), self.remote_login._view.wait(0, "", 0)["viewport"])

        # WHEN a frame has no size
        self.remote_login._on_frame({"data": "anBlZw==", "sessionId": 2})

        # THEN
        self.assertEqual(remote.DEFAULT_VIEWPORT, self.remote_login._view.wait(0, "", 0)["viewport"])
        self.assertEqual([1, 2], self.remote_login._frame_acks)

    def test_dispatch_inputs_passes_on_only_what_was_queued(self):
        # GIVEN input that keeps coming while it's passed on
        page = MagicMock()
        page.keyboard.type.side_effect = lambda text: self.remote_login._view.inputs.put({"t": "type", "text": "b"})
        self.remote_login._view.inputs.put({"t": "type", "text": "a"})

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(),
                                      "playwright.sync_api": _playwright_module(MagicMock())}):
            self.remote_login._dispatch_inputs(page)

        # THEN
        page.keyboard.type.assert_called_once_with("a")
        self.assertEqual(1, self.remote_login._view.inputs.qsize())

    def test_login_with_its_own_server(self):
        # GIVEN
        modules, _, _, _ = self.given_playwright(pw_cookies=[])
        remote_login = PlaywrightRemoteLogin(self.amazon_session)
        remote_login.server = MagicMock(spec=RemoteLoginServer)

        # WHEN
        with modules, self.assertRaises(AmazonOrdersError) as cm:
            remote_login.login(timeout=0)

        # THEN
        self.assertIn("Timed out after 0 seconds", str(cm.exception))
        self.assertEqual("timed_out", remote_login.state)
        remote_login.server.start.assert_called_once()
        remote_login.server.stop.assert_called_once()

    def test_login_timeout_from_config(self):
        # GIVEN
        modules, _, _, _ = self.given_playwright(pw_cookies=[])
        self.amazon_session.config._data["remote_login_timeout"] = 0

        # WHEN
        with modules, self.assertRaises(AmazonOrdersError):
            self.remote_login.login()

        # THEN
        self.assertEqual("timed_out", self.remote_login.state)

    def test_login_again_gets_a_new_link(self):
        # GIVEN
        modules, _, _, _ = self.given_playwright(pw_cookies=[])
        first_url = self.remote_login.url
        with modules, self.assertRaises(AmazonOrdersError):
            self.remote_login.login(timeout=0)

        # WHEN
        with modules, self.assertRaises(AmazonOrdersError):
            self.remote_login.login(timeout=0)

        # THEN
        self.assertNotEqual(first_url, self.remote_login.url)

    def test_login_failure(self):
        # GIVEN
        modules, _, context, _ = self.given_playwright()
        context.new_page.side_effect = _FakePlaywrightError("Browser closed")

        # WHEN
        with modules, self.assertRaises(AmazonOrdersError) as cm:
            self.remote_login.login(timeout=60)

        # THEN
        self.assertIn("The browser stopped", str(cm.exception))
        self.assertEqual("failed", self.remote_login.state)
        self.server.remove.assert_called_once()

    def test_login_needs_chromium(self):
        # GIVEN
        self.amazon_session.config._data["browser"] = "firefox"

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.remote_login.login(timeout=60)

        # THEN
        self.assertIn("needs a Chromium-based browser", str(cm.exception))
        self.server.add.assert_not_called()

    def test_cancel(self):
        # GIVEN
        modules, page, _, _ = self.given_playwright(pw_cookies=[])
        page.wait_for_timeout.side_effect = lambda ms: self.remote_login.cancel()

        # WHEN
        with modules, self.assertRaises(AmazonOrdersError) as cm:
            self.remote_login.login(timeout=60)

        # THEN
        self.assertIn("cancelled", str(cm.exception))
        self.assertEqual("failed", self.remote_login.state)

    def test_cancel_before_login(self):
        # GIVEN
        self.remote_login.cancel()

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.remote_login.login(timeout=60)

        # THEN
        self.assertIn("cancelled", str(cm.exception))
        self.assertEqual("failed", self.remote_login.state)
        self.server.add.assert_not_called()

    def test_login_again_after_cancel(self):
        # GIVEN
        modules, page, _, _ = self.given_playwright(pw_cookies=[])
        self.remote_login.cancel()
        with self.assertRaises(AmazonOrdersError):
            self.remote_login.login(timeout=60)
        self.remote_login._frame_acks = [1]

        # WHEN
        with modules, self.assertRaises(AmazonOrdersError) as cm:
            self.remote_login.login(timeout=0)

        # THEN
        self.assertIn("Timed out", str(cm.exception))
        self.assertEqual([], self.remote_login._frame_acks)

    @patch.object(PlaywrightBrowserLogin, "_verify_session")
    @patch("amazonorders.contrib.browser.remote.OUTCOME_GRACE_SECONDS", 0)
    def test_login_waits_for_the_page_to_see_the_outcome(self, mock_verify_session):
        # GIVEN
        modules, _, _, _ = self.given_playwright()
        self.remote_login._view.claim(None)

        # WHEN
        with modules, patch.object(self.remote_login._view.outcome_fetched, "wait") as mock_wait:
            self.remote_login.login(timeout=60)

        # THEN
        mock_wait.assert_called_once_with(0)

    @patch.object(PlaywrightBrowserLogin, "_verify_session")
    def test_waiting_passes_on_input_and_frames(self, mock_verify_session):
        # GIVEN
        modules, page, context, _ = self.given_playwright()
        other_page = MagicMock()
        context.pages = [page, other_page]
        context.cookies.side_effect = [[], [], SIGNED_IN_COOKIES, SIGNED_IN_COOKIES]
        self.remote_login._view.inputs.put({"t": "type", "text": "a"})
        frame = {"data": "anBlZw==", "sessionId": 7}

        def on_wait(ms):
            self.remote_login._on_frame(frame)
            time.sleep(0.01)

        page.wait_for_timeout.side_effect = on_wait

        # WHEN
        with modules, patch("amazonorders.contrib.browser.remote.REMOTE_SIGN_IN_POLL_INTERVAL_SECONDS", 0):
            self.remote_login.login(timeout=60)

        # THEN
        page.keyboard.type.assert_called_once_with("a")
        other_page.close.assert_called()
        cdp = context.new_cdp_session.return_value
        cdp.send.assert_any_call("Page.screencastFrameAck", {"sessionId": 7})
        self.assertEqual(b"jpeg", self.remote_login._view.wait(0, "", 0)["frame"])

    def test_dispatch_input(self):
        # GIVEN
        page = MagicMock()
        self.remote_login._cdp = MagicMock()

        # WHEN
        for event in ({"t": "move", "x": 1.0, "y": 2.0},
                      {"t": "down", "x": 1.0, "y": 2.0, "button": "left"},
                      {"t": "up", "x": 1.0, "y": 2.0, "button": "left"},
                      {"t": "wheel", "x": 1.0, "y": 2.0, "dx": 0.0, "dy": 100.0},
                      {"t": "key", "key": "Tab", "mods": ["Shift"]},
                      {"t": "type", "text": "a"},
                      {"t": "insert", "text": "ß"}):
            self.remote_login._dispatch_input(page, event)

        # THEN
        self.assertEqual(4, page.mouse.move.call_count)
        page.mouse.down.assert_called_once_with(button="left")
        page.mouse.up.assert_called_once_with(button="left")
        page.mouse.wheel.assert_called_once_with(0.0, 100.0)
        page.keyboard.press.assert_called_once_with("Shift+Tab")
        page.keyboard.type.assert_called_once_with("a")
        page.keyboard.insert_text.assert_called_once_with("ß")

    def test_dispatch_size(self):
        # GIVEN
        page = MagicMock()
        cdp = self.remote_login._cdp = MagicMock()

        # WHEN
        self.remote_login._dispatch_input(page, {"t": "size", "w": 200, "h": 5000, "dpr": 3.0})

        # THEN
        self.assertEqual((320, 1200), self.remote_login._viewport)
        page.set_viewport_size.assert_called_once_with({"width": 320, "height": 1200})
        page.evaluate.assert_called_once()
        cdp.send.assert_any_call("Page.stopScreencast")
        cdp.send.assert_called_with("Page.startScreencast", {"format": "jpeg", "quality": 70, "maxWidth": 640,
                                                             "maxHeight": 2400})

        # WHEN the window's density changes, but not its size
        self.remote_login._dispatch_input(page, {"t": "size", "w": 320, "h": 1200, "dpr": 1.0})

        # THEN
        page.set_viewport_size.assert_called_once()
        cdp.send.assert_called_with("Page.startScreencast", {"format": "jpeg", "quality": 70, "maxWidth": 320,
                                                             "maxHeight": 1200})

    def test_dispatch_inputs_carries_on_after_a_failure(self):
        # GIVEN
        page = MagicMock()
        page.keyboard.type.side_effect = [_FakePlaywrightError("Navigating"), None]
        self.remote_login._view.inputs.put({"t": "type", "text": "a"})
        self.remote_login._view.inputs.put({"t": "type", "text": "b"})

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(),
                                      "playwright.sync_api": _playwright_module(MagicMock())}):
            self.remote_login._dispatch_inputs(page)

        # THEN
        self.assertEqual(2, page.keyboard.type.call_count)
        self.assertTrue(self.remote_login._view.inputs.empty())

    def test_allowed_urls(self):
        for url, top_level, allowed in (
                ("https://www.amazon.com/ap/signin", True, True),
                ("https://amazon.com/", True, True),
                ("https://m.media-amazon.com/images/a.png", False, True),
                ("https://abc.token.awswaf.com/challenge.js", False, True),
                ("https://abc.profile.cdg55-p1.cloudfront.net/x", False, True),
                ("https://m.media-amazon.com/images/a.png", True, False),
                ("https://abc.cloudfront.net/x", True, False),
                ("http://www.amazon.com/ap/signin", True, False),
                ("https://example.com/", True, False),
                ("https://example.com/", False, False),
                ("https://evilamazon.com/", True, False),
                ("https://amazon.com.example.com/", True, False),
                ("https://192.168.1.1/", False, False),
                ("file:///etc/passwd", True, False),
        ):
            self.assertEqual(allowed, self.remote_login._is_allowed_url(url, top_level), (url, top_level))

    def test_allowed_urls_for_another_site(self):
        # GIVEN
        self.amazon_session.config.set_domain("amazon.de")

        # THEN
        self.assertTrue(self.remote_login._is_allowed_url("https://www.amazon.de/ap/signin", True))
        self.assertTrue(self.remote_login._is_allowed_url("https://fls-eu.amazon.de/1/batch", False))
        self.assertTrue(self.remote_login._is_allowed_url("https://unagi-eu.amazon.com/1/events", False))
        self.assertFalse(self.remote_login._is_allowed_url("https://www.amazon.fr/ap/signin", True))

    def test_route(self):
        # GIVEN
        allowed, blocked, resource = MagicMock(), MagicMock(), MagicMock()
        allowed.request.url = "https://www.amazon.com/ap/signin"
        allowed.request.is_navigation_request.return_value = True
        allowed.request.frame.parent_frame = None
        blocked.request.url = "https://example.com/"
        blocked.request.is_navigation_request.return_value = True
        blocked.request.frame.parent_frame = None
        resource.request.url = "https://m.media-amazon.com/a.png"
        resource.request.is_navigation_request.return_value = False

        # WHEN
        for route in (allowed, blocked, resource):
            self.remote_login._route(route)

        # THEN
        allowed.continue_.assert_called_once()
        blocked.abort.assert_called_once_with("blockedbyclient")
        blocked.continue_.assert_not_called()
        resource.continue_.assert_called_once()


class TestPlaywrightBrowserLoginHooks(UnitTestCase):
    @patch("amazonorders.contrib.browser.playwright.has_display", return_value=True)
    @patch.object(PlaywrightBrowserLogin, "_verify_session")
    def test_login(self, mock_verify_session, mock_has_display):
        # GIVEN
        mock_sync_playwright, page, context, browser = _make_mock_playwright(pw_cookies=SIGNED_IN_COOKIES)
        amazon_session = AmazonSession(config=self.test_config)
        amazon_session.io = MagicMock()

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(),
                                      "playwright.sync_api": _playwright_module(mock_sync_playwright)}):
            PlaywrightBrowserLogin(amazon_session).login()

        # THEN
        browser.new_context.assert_called_once_with(
            user_agent=amazon_session.config.constants.BASE_HEADERS.get("User-Agent"))
        self.assertIn("A browser window has opened", amazon_session.io.echo.call_args[0][0])
        mock_verify_session.assert_called_once()
        self.assertEqual("signed-in", amazon_session.session.cookies.get("x-main"))
