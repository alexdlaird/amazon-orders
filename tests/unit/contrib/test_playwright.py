__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
import sys
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.contrib.browser.playwright import PlaywrightAcicForm, PlaywrightJSAuthForm, PlaywrightManualWafForm
from amazonorders.contrib.waf.base import AwsWafForm
from amazonorders.exception import AmazonOrdersError
from amazonorders.session import AmazonSession
from tests.unittestcase import UnitTestCase


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
    mock_pw_instance.chromium.launch.return_value = mock_browser
    mock_pw_instance.firefox.launch.return_value = mock_browser

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
    return fake


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

    def test_is_challenge_url_matches_original_path(self):
        # GIVEN
        form = PlaywrightJSAuthForm(self.test_config)
        original = "https://www.amazon.com/ap/signin?openid.return_to=abc"

        # same path, different query → still on challenge
        self.assertTrue(form._is_challenge_url(
            "https://www.amazon.com/ap/signin?other_param=123", original))

        # different path → challenge resolved
        self.assertFalse(form._is_challenge_url(
            "https://www.amazon.com/gp/yourorders", original))

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
