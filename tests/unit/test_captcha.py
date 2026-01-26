__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
import unittest
from unittest.mock import patch, MagicMock, Mock

import responses
from bs4 import BeautifulSoup

from amazonorders.captcha import CaptchaSolver, get_solver
from amazonorders.exception import AmazonOrdersError, AmazonOrdersAuthError
from amazonorders.forms import AmazonWafForm
from amazonorders.session import AmazonSession
from tests.unittestcase import UnitTestCase


class TestGetSolver(UnitTestCase):
    """Tests for the get_solver function."""

    @patch("amazonorders.captcha.twocaptcha.TWOCAPTCHA_AVAILABLE", True)
    @patch("amazonorders.captcha.twocaptcha.OfficialTwoCaptcha")
    def test_get_solver_twocaptcha(self, mock_twocaptcha_class):
        """Test that get_solver returns TwoCaptchaSolver for '2captcha'."""
        mock_twocaptcha_class.return_value = MagicMock()

        solver = get_solver("2captcha", "test-api-key")

        self.assertEqual(solver.api_key, "test-api-key")
        mock_twocaptcha_class.assert_called_once_with("test-api-key")

    def test_get_solver_invalid_service(self):
        """Test that get_solver raises ValueError for unknown service."""
        with self.assertRaises(ValueError) as cm:
            get_solver("unknown-service", "test-api-key")
        self.assertIn("Unsupported CAPTCHA solver", str(cm.exception))
        self.assertIn("unknown-service", str(cm.exception))

    def test_get_solver_rejects_twocaptcha_alias(self):
        """Test that 'twocaptcha' (without hyphen) is not accepted - must use '2captcha'."""
        with self.assertRaises(ValueError) as cm:
            get_solver("twocaptcha", "test-api-key")
        self.assertIn("Unsupported CAPTCHA solver", str(cm.exception))


class TestTwoCaptchaSolver(UnitTestCase):
    """Tests for TwoCaptchaSolver."""

    @patch("amazonorders.captcha.twocaptcha.TWOCAPTCHA_AVAILABLE", True)
    @patch("amazonorders.captcha.twocaptcha.OfficialTwoCaptcha")
    def test_solve_amazon_waf_success(self, mock_twocaptcha_class):
        """Test successful WAF CAPTCHA solving."""
        # Setup mock - 2captcha API returns token nested in JSON-encoded "code" field
        mock_solver_instance = MagicMock()
        mock_solver_instance.amazon_waf.return_value = {
            "code": '{"captcha_voucher": "voucher-value", "existing_token": "waf-token-value"}'
        }
        mock_twocaptcha_class.return_value = mock_solver_instance

        from amazonorders.captcha.twocaptcha import TwoCaptchaSolver
        solver = TwoCaptchaSolver("test-api-key")
        result = solver.solve_amazon_waf(
            sitekey="test-sitekey",
            iv="test-iv",
            context="test-context",
            page_url="https://www.amazon.com/test",
            challenge_script="https://example.com/challenge.js"
        )

        self.assertEqual(result["existing_token"], "waf-token-value")
        mock_solver_instance.amazon_waf.assert_called_once_with(
            sitekey="test-sitekey",
            iv="test-iv",
            context="test-context",
            url="https://www.amazon.com/test",
            challenge_script="https://example.com/challenge.js"
        )

    @patch("amazonorders.captcha.twocaptcha.TWOCAPTCHA_AVAILABLE", True)
    @patch("amazonorders.captcha.twocaptcha.OfficialTwoCaptcha")
    def test_solve_amazon_waf_failure(self, mock_twocaptcha_class):
        """Test handling of solving failure."""
        mock_solver_instance = MagicMock()
        mock_solver_instance.amazon_waf.side_effect = Exception("ERROR_KEY_DOES_NOT_EXIST")
        mock_twocaptcha_class.return_value = mock_solver_instance

        from amazonorders.captcha.twocaptcha import TwoCaptchaSolver
        solver = TwoCaptchaSolver("invalid-key")
        with self.assertRaises(AmazonOrdersError) as cm:
            solver.solve_amazon_waf(
                sitekey="test-sitekey",
                iv="test-iv",
                context="test-context",
                page_url="https://www.amazon.com/test"
            )
        self.assertIn("2captcha solving failed", str(cm.exception))


class TestAmazonSessionCaptchaIntegration(UnitTestCase):
    """Tests for AmazonSession captcha solver integration."""

    @patch("amazonorders.captcha.twocaptcha.TWOCAPTCHA_AVAILABLE", True)
    @patch("amazonorders.captcha.twocaptcha.OfficialTwoCaptcha")
    def test_session_with_captcha_solver_string(self, mock_twocaptcha_class):
        """Test that AmazonSession accepts captcha_solver as string."""
        mock_twocaptcha_class.return_value = MagicMock()

        session = AmazonSession(
            "test@example.com",
            "password",
            config=self.test_config,
            captcha_solver="2captcha",
            captcha_api_key="test-api-key"
        )

        # Verify AmazonWafForm was added to auth_forms
        from amazonorders.forms import AmazonWafForm
        waf_forms = [f for f in session.auth_forms if isinstance(f, AmazonWafForm)]
        self.assertEqual(len(waf_forms), 1)

    def test_session_without_captcha_solver(self):
        """Test that AmazonSession works without captcha_solver (backwards compatible)."""
        session = AmazonSession(
            "test@example.com",
            "password",
            config=self.test_config
        )

        # Verify AmazonWafForm was NOT added
        from amazonorders.forms import AmazonWafForm
        waf_forms = [f for f in session.auth_forms if isinstance(f, AmazonWafForm)]
        self.assertEqual(len(waf_forms), 0)

    def test_session_captcha_solver_string_without_api_key(self):
        """Test that AmazonSession raises error when captcha_solver string provided without api_key."""
        with self.assertRaises(AmazonOrdersError) as cm:
            AmazonSession(
                "test@example.com",
                "password",
                config=self.test_config,
                captcha_solver="2captcha"
                # Missing captcha_api_key
            )
        self.assertIn("captcha_api_key is required", str(cm.exception))

    def test_session_captcha_solver_invalid_type(self):
        """Test that AmazonSession raises error for invalid captcha_solver type."""
        with self.assertRaises(AmazonOrdersError) as cm:
            AmazonSession(
                "test@example.com",
                "password",
                config=self.test_config,
                captcha_solver=12345,  # type: ignore  # Invalid type - intentional for test
                captcha_api_key="test"
            )
        self.assertIn("must be a service name", str(cm.exception))

    @patch.dict(os.environ, {"AMAZON_CAPTCHA_SOLVER": "2captcha", "AMAZON_CAPTCHA_API_KEY": "env-api-key"})
    @patch("amazonorders.captcha.twocaptcha.TWOCAPTCHA_AVAILABLE", True)
    @patch("amazonorders.captcha.twocaptcha.OfficialTwoCaptcha")
    def test_session_captcha_from_environment(self, mock_twocaptcha_class):
        """Test that AmazonSession reads captcha config from environment variables."""
        mock_twocaptcha_class.return_value = MagicMock()

        session = AmazonSession(
            "test@example.com",
            "password",
            config=self.test_config
        )

        # Verify AmazonWafForm was added from env vars
        from amazonorders.forms import AmazonWafForm
        waf_forms = [f for f in session.auth_forms if isinstance(f, AmazonWafForm)]
        self.assertEqual(len(waf_forms), 1)

    @patch("amazonorders.captcha.twocaptcha.TWOCAPTCHA_AVAILABLE", True)
    @patch("amazonorders.captcha.twocaptcha.OfficialTwoCaptcha")
    def test_waf_form_inserted_before_js_blocker(self, mock_twocaptcha_class):
        """Test that AmazonWafForm is inserted before JSAuthBlocker."""
        mock_twocaptcha_class.return_value = MagicMock()

        session = AmazonSession(
            "test@example.com",
            "password",
            config=self.test_config,
            captcha_solver="2captcha",
            captcha_api_key="test-api-key"
        )

        from amazonorders.forms import AmazonWafForm, JSAuthBlocker

        # Find positions
        waf_index = None
        blocker_index = None
        for i, form in enumerate(session.auth_forms):
            if isinstance(form, AmazonWafForm):
                waf_index = i
            if isinstance(form, JSAuthBlocker):
                blocker_index = i

        self.assertIsNotNone(waf_index, "AmazonWafForm should be in auth_forms")
        self.assertIsNotNone(blocker_index, "JSAuthBlocker should be in auth_forms")
        self.assertLess(waf_index, blocker_index, "AmazonWafForm should come before JSAuthBlocker")


class TestAmazonWafForm(UnitTestCase):
    """Tests for AmazonWafForm detection, filling, submission, and clearing."""

    def setUp(self):
        super().setUp()
        self.amazon_session = AmazonSession(
            "test@example.com",
            "password",
            config=self.test_config
        )

    def test_select_form_detects_goku_props(self):
        """Test that AmazonWafForm correctly detects WAF challenge pages with gokuProps."""
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "auth", "waf-challenge.html"), "r", encoding="utf-8") as f:
            waf_html = f.read()

        parsed = BeautifulSoup(waf_html, "html.parser")
        mock_solver = MagicMock()
        waf_form = AmazonWafForm(self.test_config, solver=mock_solver)

        # WHEN
        result = waf_form.select_form(self.amazon_session, parsed)

        # THEN
        self.assertTrue(result)
        self.assertIsNotNone(waf_form._goku_props)
        self.assertIn("key", waf_form._goku_props)
        self.assertIn("iv", waf_form._goku_props)
        self.assertIn("context", waf_form._goku_props)
        self.assertIsNotNone(waf_form._challenge_script)
        self.assertIn("challenge.js", waf_form._challenge_script)

    def test_select_form_ignores_non_waf_pages(self):
        """Test that AmazonWafForm returns False for pages without gokuProps."""
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            regular_html = f.read()

        parsed = BeautifulSoup(regular_html, "html.parser")
        mock_solver = MagicMock()
        waf_form = AmazonWafForm(self.test_config, solver=mock_solver)

        # WHEN
        result = waf_form.select_form(self.amazon_session, parsed)

        # THEN
        self.assertFalse(result)
        self.assertIsNone(waf_form._goku_props)

    def test_select_form_rejects_incomplete_goku_props(self):
        """Test that AmazonWafForm returns False if gokuProps is incomplete (missing required keys)."""
        # GIVEN - HTML with incomplete gokuProps (missing 'context')
        incomplete_html = '''
        <html><script>
        window.gokuProps = {
            "key": "somekey",
            "iv": "someiv"
        };
        </script></html>
        '''
        parsed = BeautifulSoup(incomplete_html, "html.parser")
        mock_solver = MagicMock()
        waf_form = AmazonWafForm(self.test_config, solver=mock_solver)

        # WHEN
        result = waf_form.select_form(self.amazon_session, parsed)

        # THEN
        self.assertFalse(result)
        self.assertIsNone(waf_form._goku_props)

    def test_fill_form_populates_data(self):
        """Test that AmazonWafForm.fill_form() correctly populates form data."""
        # GIVEN - successful select_form
        with open(os.path.join(self.RESOURCES_DIR, "auth", "waf-challenge.html"), "r", encoding="utf-8") as f:
            waf_html = f.read()

        parsed = BeautifulSoup(waf_html, "html.parser")
        mock_solver = MagicMock()
        waf_form = AmazonWafForm(self.test_config, solver=mock_solver)
        waf_form.select_form(self.amazon_session, parsed)

        # WHEN
        waf_form.fill_form()

        # THEN
        self.assertIsNotNone(waf_form.data)
        self.assertIn("goku_props", waf_form.data)
        self.assertIn("challenge_script", waf_form.data)
        self.assertEqual(waf_form.data["goku_props"], waf_form._goku_props)
        self.assertEqual(waf_form.data["challenge_script"], waf_form._challenge_script)

    def test_fill_form_raises_without_select_form(self):
        """Test that fill_form() raises error if select_form() wasn't called first."""
        # GIVEN
        mock_solver = MagicMock()
        waf_form = AmazonWafForm(self.test_config, solver=mock_solver)

        # WHEN/THEN
        with self.assertRaises(AmazonOrdersError) as cm:
            waf_form.fill_form()
        self.assertIn("select_form", str(cm.exception))

    @responses.activate
    def test_submit_calls_solver_and_sets_cookie(self):
        """Test that AmazonWafForm.submit() calls solver and sets aws-waf-token cookie."""
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "auth", "waf-challenge.html"), "r", encoding="utf-8") as f:
            waf_html = f.read()

        parsed = BeautifulSoup(waf_html, "html.parser")
        mock_solver = MagicMock()
        mock_solver.solve_amazon_waf.return_value = {"existing_token": "test-waf-token-12345"}

        waf_form = AmazonWafForm(self.test_config, solver=mock_solver)
        waf_form.select_form(self.amazon_session, parsed)
        waf_form.fill_form()

        # Mock response for the retry request
        mock_last_response = Mock()
        mock_last_response.url = "https://www.amazon.com/some-page"

        with open(os.path.join(self.RESOURCES_DIR, "index.html"), "r", encoding="utf-8") as f:
            responses.add(
                responses.GET,
                "https://www.amazon.com/some-page",
                body=f.read(),
                status=200,
            )

        # WHEN
        waf_form.submit(mock_last_response)

        # THEN - verify solver was called with correct params
        mock_solver.solve_amazon_waf.assert_called_once()
        call_kwargs = mock_solver.solve_amazon_waf.call_args[1]
        self.assertEqual(call_kwargs["sitekey"], waf_form._goku_props["key"])
        self.assertEqual(call_kwargs["iv"], waf_form._goku_props["iv"])
        self.assertEqual(call_kwargs["context"], waf_form._goku_props["context"])
        self.assertEqual(call_kwargs["page_url"], "https://www.amazon.com/some-page")

        # Verify cookie was set on the session
        cookie_names = [c.name for c in self.amazon_session.session.cookies]
        self.assertIn("aws-waf-token", cookie_names)

    def test_submit_raises_on_missing_token(self):
        """Test that AmazonWafForm.submit() raises error if solver returns no existing_token."""
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "auth", "waf-challenge.html"), "r", encoding="utf-8") as f:
            waf_html = f.read()

        parsed = BeautifulSoup(waf_html, "html.parser")
        mock_solver = MagicMock()
        mock_solver.solve_amazon_waf.return_value = {}  # No existing_token!

        waf_form = AmazonWafForm(self.test_config, solver=mock_solver)
        waf_form.select_form(self.amazon_session, parsed)
        waf_form.fill_form()

        mock_last_response = Mock()
        mock_last_response.url = "https://www.amazon.com/test"

        # WHEN/THEN
        with self.assertRaises(AmazonOrdersAuthError) as cm:
            waf_form.submit(mock_last_response)
        self.assertIn("existing_token", str(cm.exception))

    def test_submit_raises_without_fill_form(self):
        """Test that submit() raises error if fill_form() wasn't called first."""
        # GIVEN
        mock_solver = MagicMock()
        waf_form = AmazonWafForm(self.test_config, solver=mock_solver)

        mock_last_response = Mock()
        mock_last_response.url = "https://www.amazon.com/test"

        # WHEN/THEN
        with self.assertRaises(AmazonOrdersError) as cm:
            waf_form.submit(mock_last_response)
        self.assertIn("fill_form", str(cm.exception))

    def test_clear_form_resets_state(self):
        """Test that clear_form() properly resets all WAF form state."""
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "auth", "waf-challenge.html"), "r", encoding="utf-8") as f:
            waf_html = f.read()

        parsed = BeautifulSoup(waf_html, "html.parser")
        mock_solver = MagicMock()
        waf_form = AmazonWafForm(self.test_config, solver=mock_solver)
        waf_form.select_form(self.amazon_session, parsed)
        waf_form.fill_form()

        # Verify state exists before clear
        self.assertIsNotNone(waf_form._html)
        self.assertIsNotNone(waf_form._goku_props)
        self.assertIsNotNone(waf_form._challenge_script)
        self.assertIsNotNone(waf_form.data)
        self.assertIsNotNone(waf_form.amazon_session)

        # WHEN
        waf_form.clear_form()

        # THEN
        self.assertIsNone(waf_form._html)
        self.assertIsNone(waf_form._goku_props)
        self.assertIsNone(waf_form._challenge_script)
        self.assertIsNone(waf_form.amazon_session)
        self.assertIsNone(waf_form.data)


class TestAmazonSessionWafLoginFlow(UnitTestCase):
    """Tests for AmazonSession login flow with WAF challenge (mocked)."""

    @responses.activate
    @patch("amazonorders.captcha.twocaptcha.TWOCAPTCHA_AVAILABLE", True)
    @patch("amazonorders.captcha.twocaptcha.OfficialTwoCaptcha")
    def test_login_with_waf_challenge_solved(self, mock_twocaptcha_class):
        """Test full login flow when WAF challenge is encountered and solved via 2captcha."""
        # GIVEN - mock the 2captcha solver
        mock_solver_instance = MagicMock()
        mock_solver_instance.amazon_waf.return_value = {
            "code": '{"captcha_voucher": "voucher", "existing_token": "solved-waf-token"}'
        }
        mock_twocaptcha_class.return_value = mock_solver_instance

        # Create session with captcha solver
        session = AmazonSession(
            "test@example.com",
            "password",
            config=self.test_config,
            captcha_solver="2captcha",
            captcha_api_key="test-api-key"
        )

        # Step 1: Initial home page (unauthenticated)
        with open(os.path.join(self.RESOURCES_DIR, "auth", "unauth-index.html"), "r", encoding="utf-8") as f:
            responses.add(
                responses.GET,
                self.test_config.constants.BASE_URL,
                body=f.read(),
                status=200,
            )

        # Step 2: Sign-in page returns WAF challenge
        with open(os.path.join(self.RESOURCES_DIR, "auth", "waf-challenge.html"), "r", encoding="utf-8") as f:
            responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )

        # Step 3: After WAF solved, retry returns normal sign-in page
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )

        # Step 4: Sign-in POST succeeds with authenticated page
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"), "r", encoding="utf-8") as f:
            responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )

        # WHEN
        session.login()

        # THEN
        self.assertTrue(session.is_authenticated)
        # Verify the solver was called
        mock_solver_instance.amazon_waf.assert_called_once()
        # Verify aws-waf-token cookie was set
        cookie_names = [c.name for c in session.session.cookies]
        self.assertIn("aws-waf-token", cookie_names)


if __name__ == "__main__":
    unittest.main()
