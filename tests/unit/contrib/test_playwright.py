__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
import sys
from unittest.mock import call, MagicMock, patch

from bs4 import BeautifulSoup

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.contrib.browser.playwright import (
    PlaywrightAcicForm,
    PlaywrightBrowserLauncher,
    PlaywrightJSAuthForm,
    PlaywrightManualWafForm,
)
from amazonorders.contrib.waf.base import AwsWafForm
from amazonorders.exception import (
    AmazonOrdersBrowserNotInstalledError,
    AmazonOrdersError,
    AmazonOrdersWafSolverError,
)
from amazonorders.session import AmazonSession
from tests.unittestcase import UnitTestCase


class _FakeBrowserType:
    name = ""
    executable_path = ""

    def launch(self, **kwargs):
        pass  # pragma: no cover


class _FakePlaywrightError(Exception):
    pass


def _make_mock_playwright(final_url="https://www.amazon.com/ap/success",
                          timeout_error_cls=None,
                          pw_cookies=None):
    """Build a minimal Playwright mock hierarchy for submit() tests."""
    if pw_cookies is None:
        pw_cookies = [{"name": "at-main", "value": "auth-token", "domain": ".amazon.com", "path": "/"}]

    mock_page = MagicMock()
    mock_page.url = final_url
    if timeout_error_cls:
        mock_page.wait_for_url.side_effect = timeout_error_cls("timed out")

    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_context.cookies.return_value = pw_cookies

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    mock_pw_instance = MagicMock()
    for browser_type_name in ("chromium", "firefox", "webkit"):
        browser_type = MagicMock(spec=_FakeBrowserType)
        browser_type.name = browser_type_name
        browser_type.executable_path = sys.executable
        browser_type.launch.return_value = mock_browser
        setattr(mock_pw_instance, browser_type_name, browser_type)

    mock_sync_playwright_cm = MagicMock()
    mock_sync_playwright_cm.__enter__ = MagicMock(return_value=mock_pw_instance)
    mock_sync_playwright_cm.__exit__ = MagicMock(return_value=False)

    mock_sync_playwright = MagicMock(return_value=mock_sync_playwright_cm)

    return mock_sync_playwright, mock_page, mock_context, mock_browser


class _FakeTimeoutError(Exception):
    pass


def _playwright_module(sync_playwright, timeout_error_cls=None):
    """Build a fake playwright.sync_api module for sys.modules patching."""
    fake = MagicMock()
    fake.sync_playwright = sync_playwright
    fake.TimeoutError = timeout_error_cls or type("TimeoutError", (Exception,), {})
    fake.BrowserType = _FakeBrowserType
    fake.Error = _FakePlaywrightError
    return fake


class TestLaunchBrowser(UnitTestCase):
    def given_playwright(self):
        mock_sync_playwright, _, _, mock_browser = _make_mock_playwright()
        pw = mock_sync_playwright.return_value.__enter__.return_value
        return pw, _playwright_module(mock_sync_playwright), mock_browser

    def test_launches_installed_chrome_by_default(self):
        # GIVEN
        pw, fake_module, mock_browser = self.given_playwright()

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            browser = PlaywrightBrowserLauncher(AmazonOrdersConfig(data={})).launch(pw, headless=True)

        # THEN
        self.assertEqual(mock_browser, browser)
        pw.chromium.launch.assert_called_once_with(headless=True, channel="chrome")

    def test_falls_back_to_playwright_chromium_without_chrome(self):
        # GIVEN
        pw, fake_module, mock_browser = self.given_playwright()
        pw.chromium.launch.side_effect = [_FakePlaywrightError("Chromium distribution 'chrome' is not found"),
                                          mock_browser]

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            browser = PlaywrightBrowserLauncher(AmazonOrdersConfig(data={})).launch(pw, headless=True)

        # THEN
        self.assertEqual(mock_browser, browser)
        self.assertEqual([call(headless=True, channel="chrome"), call(headless=True)],
                         pw.chromium.launch.call_args_list)

    def test_default_without_chrome_or_chromium_offers_every_browser_type(self):
        # GIVEN
        pw, fake_module, _ = self.given_playwright()
        pw.chromium.launch.side_effect = _FakePlaywrightError("Chromium distribution 'chrome' is not found")
        pw.chromium.executable_path = "/not/installed/chromium"

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            with self.assertRaises(AmazonOrdersBrowserNotInstalledError) as cm:
                PlaywrightBrowserLauncher(AmazonOrdersConfig(data={})).launch(pw, headless=True)

        # THEN
        self.assertEqual("Chrome isn't installed, and neither is Playwright's Chromium. Install Chrome, or run: "
                         "`playwright install chromium`", str(cm.exception))
        self.assertEqual(["chromium", "firefox", "webkit"], cm.exception.meta["browser_types"])
        pw.chromium.launch.assert_called_once_with(headless=True, channel="chrome")

    def test_explicit_browser_type_not_installed_offers_only_it(self):
        # GIVEN
        pw, fake_module, _ = self.given_playwright()
        pw.firefox.executable_path = "/not/installed/firefox"

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            with self.assertRaises(AmazonOrdersBrowserNotInstalledError) as cm:
                PlaywrightBrowserLauncher(AmazonOrdersConfig(data={"browser": "firefox"})).launch(pw, headless=True)

        # THEN
        self.assertEqual("firefox isn't installed. Install it with: `playwright install firefox`",
                         str(cm.exception))
        self.assertEqual(["firefox"], cm.exception.meta["browser_types"])
        pw.firefox.launch.assert_not_called()

    def test_explicit_browser_does_not_fall_back(self):
        # GIVEN
        pw, fake_module, _ = self.given_playwright()
        pw.chromium.launch.side_effect = _FakePlaywrightError("Chromium distribution 'chrome' is not found")

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            with self.assertRaises(AmazonOrdersError):
                PlaywrightBrowserLauncher(AmazonOrdersConfig(data={"browser": "chrome"})).launch(pw, headless=True)

        # THEN
        pw.chromium.launch.assert_called_once_with(headless=True, channel="chrome")

    def test_launches_installed_browser_as_chromium_channel(self):
        # GIVEN
        pw, fake_module, _ = self.given_playwright()

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            PlaywrightBrowserLauncher(AmazonOrdersConfig(data={"browser": "chrome"})).launch(pw, headless=False)

        # THEN
        pw.chromium.launch.assert_called_once_with(headless=False, channel="chrome")

    def test_launches_playwright_browser_type_without_channel(self):
        # GIVEN
        pw, fake_module, _ = self.given_playwright()

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            PlaywrightBrowserLauncher(AmazonOrdersConfig(data={"browser": "firefox"})).launch(pw, headless=True)

        # THEN
        pw.firefox.launch.assert_called_once_with(headless=True)
        pw.chromium.launch.assert_not_called()

    def test_passes_executable_path_to_playwright(self):
        # GIVEN
        pw, fake_module, _ = self.given_playwright()
        config = AmazonOrdersConfig(data={"browser_executable_path": "/opt/brave/brave"})

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            PlaywrightBrowserLauncher(config).launch(pw, headless=False)

        # THEN
        pw.chromium.launch.assert_called_once_with(headless=False, executable_path="/opt/brave/brave")

    def test_reads_browser_settings_from_environment(self):
        # GIVEN
        pw, fake_module, _ = self.given_playwright()

        # WHEN
        with patch.dict(os.environ, {"AMAZON_BROWSER": "msedge", "AMAZON_BROWSER_EXECUTABLE_PATH": "/opt/edge"}):
            with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
                PlaywrightBrowserLauncher(AmazonOrdersConfig(data={})).launch(pw, headless=True)

        # THEN
        pw.chromium.launch.assert_called_once_with(headless=True, channel="msedge", executable_path="/opt/edge")

    def test_environment_wins_over_config(self):
        # GIVEN
        pw, fake_module, _ = self.given_playwright()

        # WHEN
        with patch.dict(os.environ, {"AMAZON_BROWSER": "firefox"}):
            with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
                PlaywrightBrowserLauncher(AmazonOrdersConfig(data={"browser": "chrome"})).launch(pw, headless=True)

        # THEN
        pw.firefox.launch.assert_called_once_with(headless=True)
        pw.chromium.launch.assert_not_called()

    def test_launch_failure_of_installed_browser_names_it(self):
        # GIVEN
        pw, fake_module, _ = self.given_playwright()
        pw.chromium.launch.side_effect = _FakePlaywrightError("Chromium distribution 'msedge' is not found\nmore")

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            with self.assertRaises(AmazonOrdersError) as cm:
                PlaywrightBrowserLauncher(AmazonOrdersConfig(data={"browser": "msedge"})).launch(pw, headless=True)

        # THEN
        self.assertEqual("Could not launch msedge. Check that it is installed, or set `browser` to `chromium` and "
                         "run: `playwright install chromium`. (Chromium distribution 'msedge' is not found)",
                         str(cm.exception))

    def test_launch_failure_of_playwright_browser_suggests_install(self):
        # GIVEN
        pw, fake_module, _ = self.given_playwright()
        pw.firefox.launch.side_effect = _FakePlaywrightError("Executable doesn't exist")

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            with self.assertRaises(AmazonOrdersError) as cm:
                PlaywrightBrowserLauncher(AmazonOrdersConfig(data={"browser": "firefox"})).launch(pw, headless=True)

        # THEN
        self.assertEqual("Could not launch firefox. If it is not installed, run: `playwright install firefox`. "
                         "(Executable doesn't exist)", str(cm.exception))


class TestInstallBrowser(UnitTestCase):
    @patch("amazonorders.contrib.browser.playwright.subprocess.run")
    def test_install_runs_playwright_install(self, mock_run):
        # GIVEN
        mock_run.return_value.returncode = 0

        # WHEN
        selected = PlaywrightBrowserLauncher(self.test_config).install("chromium")

        # THEN
        mock_run.assert_called_once_with([sys.executable, "-m", "playwright", "install", "chromium"])
        self.assertFalse(selected)
        self.assertIsNone(self.test_config.browser)

    @patch("amazonorders.contrib.browser.playwright.subprocess.run")
    def test_install_of_non_default_browser_type_selects_and_persists_it(self, mock_run):
        # GIVEN
        mock_run.return_value.returncode = 0
        self.test_config.save()

        # WHEN
        selected = PlaywrightBrowserLauncher(self.test_config).install("firefox")

        # THEN
        self.assertTrue(selected)
        self.assertEqual("firefox", self.test_config.browser)
        self.assertEqual("firefox", AmazonOrdersConfig(config_path=self.test_config.config_path).browser)

    @patch("amazonorders.contrib.browser.playwright.subprocess.run")
    def test_install_of_configured_browser_type_keeps_config(self, mock_run):
        # GIVEN
        mock_run.return_value.returncode = 0
        self.test_config.update_config("browser", "firefox", save=False)

        # WHEN
        selected = PlaywrightBrowserLauncher(self.test_config).install("firefox")

        # THEN
        self.assertFalse(selected)

    @patch("amazonorders.contrib.browser.playwright.subprocess.run")
    def test_install_failure_says_how_to_retry(self, mock_run):
        # GIVEN
        mock_run.return_value.returncode = 1

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            PlaywrightBrowserLauncher(self.test_config).install("webkit")

        # THEN
        self.assertEqual("Could not download webkit. To try again yourself, run: `playwright install webkit`",
                         str(cm.exception))
        self.assertIsNone(self.test_config.browser)


class TestPlaywrightAcicForm(UnitTestCase):
    def setUp(self):
        super().setUp()
        self.amazon_session = AmazonSession("user", "pass", config=self.test_config)

        with open(os.path.join(self.RESOURCES_DIR, "auth", "acic-challenge.html"),
                  "r", encoding="utf-8") as f:
            self.acic_html = f.read()

    def test_select_form_detects_acic_challenge(self):
        # GIVEN
        form = PlaywrightAcicForm(self.test_config)
        parsed = BeautifulSoup(self.acic_html, self.test_config.bs4_parser)

        # WHEN
        result = form.select_form(self.amazon_session, parsed)

        # THEN
        self.assertTrue(result)
        self.assertEqual(self.amazon_session, form.amazon_session)

    def test_select_form_returns_false_on_normal_page(self):
        # GIVEN
        form = PlaywrightAcicForm(self.test_config)
        parsed = BeautifulSoup("<html><body>nothing special here</body></html>",
                               self.test_config.bs4_parser)

        # WHEN
        result = form.select_form(self.amazon_session, parsed)

        # THEN
        self.assertFalse(result)

    def test_fill_form_is_noop(self):
        # GIVEN
        form = PlaywrightAcicForm(self.test_config)

        # WHEN / THEN (no error, no form state)
        form.fill_form()
        self.assertIsNone(form.form)
        self.assertIsNone(form.data)

    def test_missing_playwright_package_raises(self):
        # GIVEN
        form = PlaywrightAcicForm(self.test_config)
        parsed = BeautifulSoup(self.acic_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"

        # WHEN / THEN
        with patch.dict(sys.modules, {"playwright": None, "playwright.sync_api": None}):
            with self.assertRaises(AmazonOrdersError) as cm:
                form.submit(last_response)
        self.assertIn("playwright", str(cm.exception).lower())
        self.assertIn("browser", str(cm.exception).lower())

    def test_submit_launches_chromium_headless(self):
        # GIVEN
        form = PlaywrightAcicForm(self.test_config)
        parsed = BeautifulSoup(self.acic_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"
        self.amazon_session.get = MagicMock(return_value="refetched")

        mock_sync_playwright, _, _, mock_browser = _make_mock_playwright()
        fake_module = _playwright_module(mock_sync_playwright)

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            form.submit(last_response)

        # THEN
        mock_browser.new_context.assert_called_once()
        mock_browser.close.assert_called_once()
        launch_kwargs = mock_sync_playwright.return_value.__enter__.return_value.chromium.launch.call_args
        self.assertEqual(True, launch_kwargs.kwargs.get("headless"))

    def test_submit_goes_headful_when_manual_solver_registered(self):
        # GIVEN
        form = PlaywrightAcicForm(self.test_config)
        self.amazon_session.auth_forms.append(PlaywrightManualWafForm(self.test_config))
        parsed = BeautifulSoup(self.acic_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"
        self.amazon_session.get = MagicMock(return_value="refetched")

        mock_sync_playwright, _, _, _ = _make_mock_playwright()
        fake_module = _playwright_module(mock_sync_playwright)

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            form.submit(last_response)

        # THEN
        launch_kwargs = mock_sync_playwright.return_value.__enter__.return_value.chromium.launch.call_args
        self.assertEqual(False, launch_kwargs.kwargs.get("headless"))

    def test_manual_mode_skips_automated_solve_loop(self):
        # GIVEN
        form = PlaywrightAcicForm(self.test_config)
        self.amazon_session.auth_forms.append(PlaywrightManualWafForm(self.test_config))
        parsed = BeautifulSoup(self.acic_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"
        self.amazon_session.get = MagicMock(return_value="refetched")
        self.amazon_session.io = MagicMock()

        mock_sync_playwright, mock_page, _, _ = _make_mock_playwright()
        fake_module = _playwright_module(mock_sync_playwright, timeout_error_cls=_FakeTimeoutError)

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            result = form.submit(last_response)

        # THEN
        mock_page.wait_for_function.assert_not_called()
        mock_page.reload.assert_not_called()
        echoed = [call.args[0] for call in self.amazon_session.io.echo.call_args_list]
        self.assertTrue(any("solve the challenge" in msg for msg in echoed))
        self.assertEqual("refetched", result)

    def test_automated_solver_takes_precedence_over_manual(self):
        # GIVEN
        form = PlaywrightAcicForm(self.test_config)
        self.amazon_session.auth_forms.append(PlaywrightManualWafForm(self.test_config))
        mock_waf = MagicMock(spec=AwsWafForm)
        mock_waf.PROVIDER_NAME = "TestSolver"
        mock_waf._solve_token.return_value = "waf-token-value"
        self.amazon_session.auth_forms.append(mock_waf)
        parsed = BeautifulSoup(self.acic_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"
        self.amazon_session.get = MagicMock(return_value="refetched")

        goku = {"key": "k", "iv": "i", "context": "c"}
        mock_sync_playwright, mock_page, _, _ = _make_mock_playwright()
        mock_page.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"
        mock_page.evaluate.side_effect = [goku, "https://challenge.awswaf.com/challenge.js"]
        fake_module = _playwright_module(mock_sync_playwright, timeout_error_cls=_FakeTimeoutError)

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            form.submit(last_response)

        # THEN
        launch_kwargs = mock_sync_playwright.return_value.__enter__.return_value.chromium.launch.call_args
        self.assertEqual(True, launch_kwargs.kwargs.get("headless"))
        mock_waf._solve_token.assert_called_once()

    def test_submit_launches_firefox_when_configured(self):
        # GIVEN
        config = AmazonOrdersConfig(data={
            "output_dir": self.test_config.output_dir,
            "cookie_jar_path": self.test_config.cookie_jar_path,
            "browser": "firefox",
        })
        form = PlaywrightAcicForm(config)
        parsed = BeautifulSoup(self.acic_html, config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"
        self.amazon_session.get = MagicMock(return_value="refetched")

        mock_sync_playwright, _, _, _ = _make_mock_playwright()
        fake_module = _playwright_module(mock_sync_playwright)

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            form.submit(last_response)

        # THEN — firefox launched, not chromium
        pw_instance = mock_sync_playwright.return_value.__enter__.return_value
        self.assertTrue(pw_instance.firefox.launch.called)
        self.assertFalse(pw_instance.chromium.launch.called)

    def test_submit_injects_session_cookies(self):
        # GIVEN
        form = PlaywrightAcicForm(self.test_config)
        parsed = BeautifulSoup(self.acic_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        self.amazon_session.session.cookies.set("session-id", "sid-value", domain=".amazon.com", path="/")

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"
        self.amazon_session.get = MagicMock(return_value="refetched")

        mock_sync_playwright, _, mock_context, _ = _make_mock_playwright()
        fake_module = _playwright_module(mock_sync_playwright)

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            form.submit(last_response)

        # THEN
        injected_calls = mock_context.add_cookies.call_args_list
        session_cookie_call = next(
            (c[0][0] for c in injected_calls
             if any(ck.get("name") == "session-id" for ck in c[0][0])),
            None,
        )
        self.assertIsNotNone(session_cookie_call)
        self.assertTrue(any(c["name"] == "session-id" and c["value"] == "sid-value" for c in session_cookie_call))

    def test_submit_harvests_browser_cookies_into_session(self):
        # GIVEN
        form = PlaywrightAcicForm(self.test_config)
        parsed = BeautifulSoup(self.acic_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"
        self.amazon_session.get = MagicMock(return_value="refetched")

        pw_cookies = [
            {"name": "at-main", "value": "auth-token-value", "domain": ".amazon.com", "path": "/"},
            {"name": "session-token", "value": "sess-token-value", "domain": ".amazon.com", "path": "/"},
        ]
        mock_sync_playwright, _, _, _ = _make_mock_playwright(pw_cookies=pw_cookies)
        fake_module = _playwright_module(mock_sync_playwright)

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            form.submit(last_response)

        # THEN
        session_cookies = {c.name: c.value for c in self.amazon_session.session.cookies}
        self.assertEqual("auth-token-value", session_cookies.get("at-main"))
        self.assertEqual("sess-token-value", session_cookies.get("session-token"))

    def test_submit_refetches_final_url(self):
        # GIVEN
        form = PlaywrightAcicForm(self.test_config)
        parsed = BeautifulSoup(self.acic_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"
        self.amazon_session.get = MagicMock(return_value="refetched")

        final_url = "https://www.amazon.com/ap/signin?done=success"
        mock_sync_playwright, _, _, _ = _make_mock_playwright(final_url=final_url)
        fake_module = _playwright_module(mock_sync_playwright)

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            result = form.submit(last_response)

        # THEN
        self.assertEqual("refetched", result)
        self.amazon_session.get.assert_called_once_with(final_url, persist_cookies=True)

    def test_submit_timeout_raises(self):
        # GIVEN
        form = PlaywrightAcicForm(self.test_config)
        parsed = BeautifulSoup(self.acic_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"

        mock_sync_playwright, _, _, _ = _make_mock_playwright(timeout_error_cls=_FakeTimeoutError)
        fake_module = _playwright_module(mock_sync_playwright, timeout_error_cls=_FakeTimeoutError)

        # WHEN / THEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            with self.assertRaises(AmazonOrdersError) as cm:
                form.submit(last_response)
        self.assertIn("timed out", str(cm.exception).lower())

    def test_is_challenge_url_matches_acic_path(self):
        # GIVEN
        form = PlaywrightAcicForm(self.test_config)

        # WHEN / THEN
        self.assertTrue(form._is_challenge_url(
            "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=x", ""))
        self.assertFalse(form._is_challenge_url(
            "https://www.amazon.com/ap/signin", ""))

    def test_embedded_waf_solved_when_waf_form_configured(self):
        # GIVEN
        form = PlaywrightAcicForm(self.test_config)
        parsed = BeautifulSoup(self.acic_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"
        self.amazon_session.get = MagicMock(return_value="refetched")

        mock_waf = MagicMock(spec=AwsWafForm)
        mock_waf.PROVIDER_NAME = "TestSolver"
        mock_waf._solve_token.return_value = "waf-token-value"
        self.amazon_session.auth_forms.append(mock_waf)

        goku = {"key": "k", "iv": "i", "context": "c"}
        mock_sync_playwright, mock_page, mock_context, _ = _make_mock_playwright()
        mock_page.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"
        mock_page.evaluate.side_effect = [goku, "https://challenge.awswaf.com/challenge.js"]
        fake_module = _playwright_module(mock_sync_playwright, timeout_error_cls=_FakeTimeoutError)

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            result = form.submit(last_response)

        # THEN
        mock_waf._solve_token.assert_called_once_with(
            mock_page.url, goku, "https://challenge.awswaf.com/challenge.js"
        )
        injected_calls = mock_context.add_cookies.call_args_list
        waf_cookie_call = next(
            (c for c in injected_calls
             if any(ck.get("name") == "aws-waf-token" for ck in c[0][0])),
            None,
        )
        self.assertIsNotNone(waf_cookie_call)
        waf_cookie = next(ck for ck in waf_cookie_call[0][0] if ck["name"] == "aws-waf-token")
        self.assertEqual("waf-token-value", waf_cookie["value"])
        mock_page.reload.assert_called_once_with(wait_until="load")
        self.assertEqual("refetched", result)

    def test_embedded_waf_skipped_when_no_waf_form_configured(self):
        # GIVEN
        form = PlaywrightAcicForm(self.test_config)
        parsed = BeautifulSoup(self.acic_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"
        self.amazon_session.get = MagicMock(return_value="refetched")

        goku = {"key": "k", "iv": "i", "context": "c"}
        mock_sync_playwright, mock_page, mock_context, _ = _make_mock_playwright()
        mock_page.evaluate.side_effect = [goku, "https://challenge.awswaf.com/challenge.js"]
        fake_module = _playwright_module(mock_sync_playwright, timeout_error_cls=_FakeTimeoutError)

        # WHEN — no AwsWafForm in auth_forms, should not raise
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            result = form.submit(last_response)

        # THEN — reload never called, submit still completes
        mock_page.reload.assert_not_called()
        self.assertEqual("refetched", result)

    def test_embedded_waf_skipped_when_no_goku_props(self):
        # GIVEN
        form = PlaywrightAcicForm(self.test_config)
        parsed = BeautifulSoup(self.acic_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"
        self.amazon_session.get = MagicMock(return_value="refetched")

        mock_sync_playwright, mock_page, _, _ = _make_mock_playwright()
        # wait_for_function raises TimeoutError — no gokuProps in page
        mock_page.wait_for_function.side_effect = _FakeTimeoutError("timeout")
        fake_module = _playwright_module(mock_sync_playwright, timeout_error_cls=_FakeTimeoutError)

        # WHEN — no WAF CAPTCHA on page, should not raise
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            result = form.submit(last_response)

        # THEN
        mock_page.reload.assert_not_called()
        self.assertEqual("refetched", result)

    def test_embedded_waf_solver_failure_raises(self):
        # GIVEN
        form = PlaywrightAcicForm(self.test_config)
        parsed = BeautifulSoup(self.acic_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"
        self.amazon_session.get = MagicMock(return_value="refetched")

        mock_waf = MagicMock(spec=AwsWafForm)
        mock_waf.PROVIDER_NAME = "TestSolver"
        mock_waf._solve_token.side_effect = AmazonOrdersWafSolverError(
            "TestSolver failed to solve AWS WAF challenge: ERROR_ZERO_BALANCE",
            meta={"provider": "TestSolver", "provider_error": "ERROR_ZERO_BALANCE"})
        self.amazon_session.auth_forms.append(mock_waf)

        goku = {"key": "k", "iv": "i", "context": "c"}
        mock_sync_playwright, mock_page, _, _ = _make_mock_playwright()
        mock_page.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"
        mock_page.evaluate.side_effect = [goku, "https://challenge.awswaf.com/challenge.js"]
        fake_module = _playwright_module(mock_sync_playwright, timeout_error_cls=_FakeTimeoutError)

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            with self.assertRaises(AmazonOrdersWafSolverError) as cm:
                form.submit(last_response)

        # THEN
        self.assertEqual("ERROR_ZERO_BALANCE", cm.exception.meta["provider_error"])
        mock_page.reload.assert_not_called()
        self.amazon_session.get.assert_not_called()

    def test_embedded_waf_other_solve_error_is_skipped(self):
        # GIVEN
        form = PlaywrightAcicForm(self.test_config)
        parsed = BeautifulSoup(self.acic_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"
        self.amazon_session.get = MagicMock(return_value="refetched")

        mock_waf = MagicMock(spec=AwsWafForm)
        mock_waf.PROVIDER_NAME = "TestSolver"
        mock_waf._solve_token.side_effect = AmazonOrdersError("TestSolverWafForm requires the [testsolver] extra.")
        self.amazon_session.auth_forms.append(mock_waf)

        goku = {"key": "k", "iv": "i", "context": "c"}
        mock_sync_playwright, mock_page, _, _ = _make_mock_playwright()
        mock_page.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"
        mock_page.evaluate.side_effect = [goku, "https://challenge.awswaf.com/challenge.js"]
        fake_module = _playwright_module(mock_sync_playwright, timeout_error_cls=_FakeTimeoutError)

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            result = form.submit(last_response)

        # THEN
        mock_page.reload.assert_not_called()
        self.assertEqual("refetched", result)

    def test_visual_captcha_solved_after_waf_token(self):
        """
        After the WAF token challenge is solved and the page reloads, Amazon may
        escalate to a visual grid CAPTCHA (still delivered via gokuProps). The
        library should loop and pass the new challenge to the solver again.
        """
        # GIVEN
        form = PlaywrightAcicForm(self.test_config)
        parsed = BeautifulSoup(self.acic_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"
        self.amazon_session.get = MagicMock(return_value="refetched")

        mock_waf = MagicMock(spec=AwsWafForm)
        mock_waf.PROVIDER_NAME = "CapSolver"
        mock_waf._solve_token.return_value = "waf-token-value"
        self.amazon_session.auth_forms.append(mock_waf)

        goku_1 = {"key": "k1", "iv": "i1", "context": "c1"}
        goku_2 = {"key": "k2", "iv": "i2", "context": "c2"}

        mock_sync_playwright, mock_page, mock_context, _ = _make_mock_playwright()
        mock_page.url = "https://www.amazon.com/ax/aaut/verify/ap/challenge?aamationToken=test"

        # wait_for_function is called each loop iteration to detect gokuProps.
        # Succeed twice (two challenges), then timeout (no more challenges).
        wait_calls = [None, None, _FakeTimeoutError("no more challenges")]

        def wait_for_function_side_effect(*args, **kwargs):
            action = wait_calls.pop(0)
            if action is not None:
                raise action

        mock_page.wait_for_function.side_effect = wait_for_function_side_effect

        # evaluate is called twice per solve: once for gokuProps, once for challenge_script
        mock_page.evaluate.side_effect = [
            goku_1, "https://challenge.awswaf.com/challenge.js",
            goku_2, "https://challenge.awswaf.com/challenge.js",
        ]

        fake_module = _playwright_module(mock_sync_playwright, timeout_error_cls=_FakeTimeoutError)

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            result = form.submit(last_response)

        # THEN
        self.assertEqual(2, mock_waf._solve_token.call_count)
        self.assertEqual(
            mock_waf._solve_token.call_args_list[0][0][1], goku_1)
        self.assertEqual(
            mock_waf._solve_token.call_args_list[1][0][1], goku_2)
        self.assertEqual(2, mock_page.reload.call_count)
        self.assertEqual("refetched", result)


class TestPlaywrightJSAuthForm(UnitTestCase):
    def setUp(self):
        super().setUp()
        self.amazon_session = AmazonSession("user", "pass", config=self.test_config)

        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-js-bot-challenge.html"),
                  "r", encoding="utf-8") as f:
            self.js_html = f.read()

    def test_select_form_detects_js_robot_challenge(self):
        # GIVEN
        form = PlaywrightJSAuthForm(self.test_config)
        parsed = BeautifulSoup(self.js_html, self.test_config.bs4_parser)

        # WHEN
        result = form.select_form(self.amazon_session, parsed)

        # THEN
        self.assertTrue(result)
        self.assertEqual(self.amazon_session, form.amazon_session)

    def test_select_form_returns_false_on_normal_page(self):
        # GIVEN
        form = PlaywrightJSAuthForm(self.test_config)
        parsed = BeautifulSoup("<html><body>nothing special here</body></html>",
                               self.test_config.bs4_parser)

        # WHEN
        result = form.select_form(self.amazon_session, parsed)

        # THEN
        self.assertFalse(result)

    def test_regex_sourced_from_config_constants(self):
        # GIVEN / WHEN
        form = PlaywrightJSAuthForm(self.test_config)

        # THEN
        self.assertEqual(self.test_config.constants.JS_ROBOT_TEXT_REGEX, form.regex)

    def test_is_challenge_url_always_false(self):
        # GIVEN
        form = PlaywrightJSAuthForm(self.test_config)

        original = "https://www.amazon.com/ap/signin?openid.return_to=abc"

        # WHEN / THEN
        self.assertFalse(form._is_challenge_url(original, original),
                         "an unchanged URL must still report resolved, since this challenge reloads its own URL")
        self.assertFalse(form._is_challenge_url(
            "https://www.amazon.com/gp/yourorders", original))

    def test_submit_waits_for_challenge_text_to_disappear(self):
        # GIVEN
        form = PlaywrightJSAuthForm(self.test_config)
        parsed = BeautifulSoup(self.js_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        original_url = "https://www.amazon.com/"
        last_response = MagicMock()
        last_response.url = original_url
        self.amazon_session.get = MagicMock(return_value="refetched")

        mock_sync_playwright, mock_page, _, _ = _make_mock_playwright(final_url=original_url)
        mock_page.evaluate.return_value = 120
        fake_module = _playwright_module(mock_sync_playwright)

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            result = form.submit(last_response)

        # THEN
        mock_page.wait_for_function.assert_called_once()
        _, kwargs = mock_page.wait_for_function.call_args
        self.assertEqual([form.regex, 120], kwargs["arg"])
        self.assertEqual(self.test_config.browser_timeout * 1000, kwargs["timeout"])
        self.assertEqual("refetched", result)
        self.amazon_session.get.assert_called_once_with(original_url, persist_cookies=True)

    def test_submit_timeout_when_challenge_text_persists(self):
        # GIVEN
        form = PlaywrightJSAuthForm(self.test_config)
        parsed = BeautifulSoup(self.js_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/"

        mock_sync_playwright, mock_page, _, mock_browser = _make_mock_playwright(
            final_url="https://www.amazon.com/")
        mock_page.wait_for_function.side_effect = _FakeTimeoutError("timed out")
        mock_page.context.browser = mock_browser
        fake_module = _playwright_module(mock_sync_playwright, timeout_error_cls=_FakeTimeoutError)

        # WHEN / THEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            with self.assertRaises(AmazonOrdersError):
                form.submit(last_response)
        mock_browser.close.assert_called_once()

    def test_submit_refetches_final_url(self):
        # GIVEN
        form = PlaywrightJSAuthForm(self.test_config)
        parsed = BeautifulSoup(self.js_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/ap/signin?openid.return_to=abc"
        self.amazon_session.get = MagicMock(return_value="refetched")

        final_url = "https://www.amazon.com/gp/yourorders"
        mock_sync_playwright, _, _, _ = _make_mock_playwright(final_url=final_url)
        fake_module = _playwright_module(mock_sync_playwright)

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            result = form.submit(last_response)

        # THEN
        self.assertEqual("refetched", result)
        self.amazon_session.get.assert_called_once_with(final_url, persist_cookies=True)


class TestPlaywrightManualWafForm(UnitTestCase):
    def setUp(self):
        super().setUp()
        self.amazon_session = AmazonSession("user", "pass", config=self.test_config)

        with open(os.path.join(self.RESOURCES_DIR, "auth", "waf-challenge.html"),
                  "r", encoding="utf-8") as f:
            self.waf_html = f.read()

    def test_select_form_detects_waf_challenge(self):
        # GIVEN
        form = PlaywrightManualWafForm(self.test_config)
        parsed = BeautifulSoup(self.waf_html, self.test_config.bs4_parser)

        # WHEN
        result = form.select_form(self.amazon_session, parsed)

        # THEN
        self.assertTrue(result)
        self.assertEqual(self.amazon_session, form.amazon_session)

    def test_select_form_returns_false_on_normal_page(self):
        # GIVEN
        form = PlaywrightManualWafForm(self.test_config)
        parsed = BeautifulSoup("<html><body>nothing special here</body></html>",
                               self.test_config.bs4_parser)

        # WHEN
        result = form.select_form(self.amazon_session, parsed)

        # THEN
        self.assertFalse(result)

    def test_select_form_returns_false_when_no_challenge_script(self):
        # GIVEN — gokuProps present but no awswaf.com script tag
        form = PlaywrightManualWafForm(self.test_config)
        parsed = BeautifulSoup(
            '<html><body><script>window.gokuProps = {"key":"k","iv":"i","context":"c"};</script>'
            "</body></html>",
            self.test_config.bs4_parser,
        )

        # WHEN
        result = form.select_form(self.amazon_session, parsed)

        # THEN
        self.assertFalse(result)

    def test_headless_is_false(self):
        # GIVEN / WHEN
        form = PlaywrightManualWafForm(self.test_config)

        # THEN
        self.assertFalse(form.headless)

    def test_submit_launches_chromium_non_headless(self):
        # GIVEN
        form = PlaywrightManualWafForm(self.test_config)
        parsed = BeautifulSoup(self.waf_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/errors/validateCaptcha"
        self.amazon_session.get = MagicMock(return_value="refetched")

        mock_sync_playwright, _, _, _ = _make_mock_playwright()
        fake_module = _playwright_module(mock_sync_playwright)

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            form.submit(last_response)

        # THEN
        launch_kwargs = mock_sync_playwright.return_value.__enter__.return_value.chromium.launch.call_args
        self.assertEqual(False, launch_kwargs.kwargs.get("headless"))

    def test_on_challenge_page_echoes_user_message(self):
        # GIVEN
        form = PlaywrightManualWafForm(self.test_config)
        parsed = BeautifulSoup(self.waf_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/errors/validateCaptcha"
        self.amazon_session.get = MagicMock(return_value="refetched")
        self.amazon_session.io = MagicMock()

        mock_sync_playwright, _, _, _ = _make_mock_playwright()
        fake_module = _playwright_module(mock_sync_playwright)

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            form.submit(last_response)

        # THEN — the user-facing prompt was echoed
        echoed = [call.args[0] for call in self.amazon_session.io.echo.call_args_list]
        self.assertTrue(any("browser window" in msg for msg in echoed))

    def test_is_challenge_url_matches_original_path(self):
        # GIVEN
        form = PlaywrightManualWafForm(self.test_config)
        original = "https://www.amazon.com/errors/validateCaptcha?foo=bar"

        # same path, different query → still on challenge
        self.assertTrue(form._is_challenge_url(
            "https://www.amazon.com/errors/validateCaptcha?other=1", original))

        # different path → challenge resolved
        self.assertFalse(form._is_challenge_url(
            "https://www.amazon.com/your-orders/orders", original))

    def test_submit_refetches_final_url(self):
        # GIVEN
        form = PlaywrightManualWafForm(self.test_config)
        parsed = BeautifulSoup(self.waf_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/errors/validateCaptcha"
        self.amazon_session.get = MagicMock(return_value="refetched")

        final_url = "https://www.amazon.com/your-orders/orders"
        mock_sync_playwright, _, _, _ = _make_mock_playwright(final_url=final_url)
        fake_module = _playwright_module(mock_sync_playwright)

        # WHEN
        with patch.dict(sys.modules, {"playwright": MagicMock(), "playwright.sync_api": fake_module}):
            result = form.submit(last_response)

        # THEN
        self.assertEqual("refetched", result)
        self.amazon_session.get.assert_called_once_with(final_url, persist_cookies=True)
