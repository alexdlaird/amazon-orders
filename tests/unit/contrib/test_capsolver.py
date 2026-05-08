__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
import sys
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

from amazonorders.contrib.waf.capsolver import CapSolverWafForm
from amazonorders.exception import AmazonOrdersError
from amazonorders.session import AmazonSession
from tests.unittestcase import UnitTestCase


class TestCapSolverWafForm(UnitTestCase):
    def setUp(self):
        super().setUp()
        self.amazon_session = AmazonSession("user", "pass", config=self.test_config)

        with open(os.path.join(self.RESOURCES_DIR, "auth", "waf-challenge.html"),
                  "r", encoding="utf-8") as f:
            self.waf_html = f.read()

    def test_init_missing_env_var_raises(self):
        # GIVEN
        prior = os.environ.pop("CAPSOLVER_API_KEY", None)
        try:
            # WHEN / THEN
            with self.assertRaises(AmazonOrdersError) as cm:
                CapSolverWafForm(self.test_config)
            self.assertIn("CAPSOLVER_API_KEY", str(cm.exception))
        finally:
            if prior is not None:
                os.environ["CAPSOLVER_API_KEY"] = prior

    @patch.dict(os.environ, {"CAPSOLVER_API_KEY": "test-api-key"})
    def test_init_with_env_var(self):
        # WHEN
        form = CapSolverWafForm(self.test_config)

        # THEN
        self.assertEqual("test-api-key", form.api_key)

    @patch.dict(os.environ, {"CAPSOLVER_API_KEY": "test-api-key"})
    def test_select_form_detects_waf_challenge(self):
        # GIVEN
        form = CapSolverWafForm(self.test_config)
        parsed = BeautifulSoup(self.waf_html, self.test_config.bs4_parser)

        # WHEN
        result = form.select_form(self.amazon_session, parsed)

        # THEN
        self.assertTrue(result)
        self.assertIsNotNone(form._goku)
        self.assertIn("key", form._goku)
        self.assertIn("iv", form._goku)
        self.assertIn("context", form._goku)
        self.assertIn("awswaf.com", form._challenge_script)

    @patch.dict(os.environ, {"CAPSOLVER_API_KEY": "test-api-key"})
    def test_select_form_returns_false_on_non_waf_page(self):
        # GIVEN
        form = CapSolverWafForm(self.test_config)
        parsed = BeautifulSoup("<html><body>just a normal page</body></html>",
                               self.test_config.bs4_parser)

        # WHEN
        result = form.select_form(self.amazon_session, parsed)

        # THEN
        self.assertFalse(result)

    @patch.dict(os.environ, {"CAPSOLVER_API_KEY": "test-api-key"})
    def test_solve_token_calls_capsolver_with_correct_task(self):
        # GIVEN
        fake_capsolver = MagicMock()
        fake_capsolver.solve.return_value = {"cookie": "waf-token-value"}

        form = CapSolverWafForm(self.test_config)
        form._goku = {"key": "k123", "iv": "i123", "context": "c123"}
        form._challenge_script = "https://example.token.awswaf.com/challenge.js"

        # WHEN
        with patch.dict(sys.modules, {"capsolver": fake_capsolver}):
            token = form._solve_token("https://www.amazon.com/login")

        # THEN
        self.assertEqual("waf-token-value", token)
        fake_capsolver.solve.assert_called_once()
        task = fake_capsolver.solve.call_args[0][0]
        self.assertEqual("AntiAwsWafTaskProxyLess", task["type"])
        self.assertEqual("https://www.amazon.com/login", task["websiteURL"])
        self.assertEqual("k123", task["awsKey"])
        self.assertEqual("i123", task["awsIv"])
        self.assertEqual("c123", task["awsContext"])
        self.assertEqual("https://example.token.awswaf.com/challenge.js", task["awsChallengeJS"])
        self.assertEqual("test-api-key", fake_capsolver.api_key)

    @patch.dict(os.environ, {"CAPSOLVER_API_KEY": "test-api-key"})
    def test_solve_token_missing_cookie_raises(self):
        # GIVEN
        fake_capsolver = MagicMock()
        fake_capsolver.solve.return_value = {"unexpected": "shape"}

        form = CapSolverWafForm(self.test_config)
        form._goku = {"key": "k", "iv": "i", "context": "c"}
        form._challenge_script = "https://example.token.awswaf.com/challenge.js"

        # WHEN / THEN
        with patch.dict(sys.modules, {"capsolver": fake_capsolver}):
            with self.assertRaises(AmazonOrdersError) as cm:
                form._solve_token("https://www.amazon.com/login")
        self.assertIn("cookie", str(cm.exception))

    @patch.dict(os.environ, {"CAPSOLVER_API_KEY": "test-api-key"})
    def test_submit_sets_cookie_and_refetches(self):
        # GIVEN
        fake_capsolver = MagicMock()
        fake_capsolver.solve.return_value = {"cookie": "waf-token-value"}

        form = CapSolverWafForm(self.test_config)
        parsed = BeautifulSoup(self.waf_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/login"

        self.amazon_session.get = MagicMock(return_value="refetched-response")

        # WHEN
        with patch.dict(sys.modules, {"capsolver": fake_capsolver}):
            result = form.submit(last_response)

        # THEN
        self.assertEqual("refetched-response", result)
        self.amazon_session.get.assert_called_once_with("https://www.amazon.com/login")

        cookies = list(self.amazon_session.session.cookies)
        waf_cookies = [c for c in cookies if c.name == "aws-waf-token"]
        self.assertEqual(1, len(waf_cookies))
        self.assertEqual("waf-token-value", waf_cookies[0].value)
        self.assertEqual("www.amazon.com", waf_cookies[0].domain)

    @patch.dict(os.environ, {"CAPSOLVER_API_KEY": "test-api-key"})
    def test_submit_emits_provider_used_message(self):
        # GIVEN
        fake_capsolver = MagicMock()
        fake_capsolver.solve.return_value = {"cookie": "waf-token-value"}

        form = CapSolverWafForm(self.test_config)
        parsed = BeautifulSoup(self.waf_html, self.test_config.bs4_parser)
        form.select_form(self.amazon_session, parsed)

        last_response = MagicMock()
        last_response.url = "https://www.amazon.com/login"

        self.amazon_session.get = MagicMock(return_value="refetched-response")
        self.amazon_session.io = MagicMock()

        # WHEN
        with patch.dict(sys.modules, {"capsolver": fake_capsolver}):
            with self.assertLogs("amazonorders.contrib.waf.base", level="INFO") as logs:
                form.submit(last_response)

        # THEN
        self.assertTrue(
            any("CapSolver" in m and "AWS WAF" in m for m in logs.output),
            f"Expected CapSolver/AWS WAF message in logs, got: {logs.output}",
        )
        self.amazon_session.io.echo.assert_called_once()
        echo_msg = self.amazon_session.io.echo.call_args[0][0]
        self.assertIn("CapSolver", echo_msg)
        self.assertIn("AWS WAF", echo_msg)

    @patch.dict(os.environ, {"CAPSOLVER_API_KEY": "test-api-key"})
    def test_solve_token_sdk_exception_wraps_as_amazon_orders_error(self):
        # GIVEN
        fake_capsolver = MagicMock()
        fake_capsolver.solve.side_effect = RuntimeError("ERROR_NO_FUNDS")

        form = CapSolverWafForm(self.test_config)
        form._goku = {"key": "k", "iv": "i", "context": "c"}
        form._challenge_script = "https://example.token.awswaf.com/challenge.js"

        # WHEN / THEN
        with patch.dict(sys.modules, {"capsolver": fake_capsolver}):
            with self.assertRaises(AmazonOrdersError) as cm:
                form._solve_token("https://www.amazon.com/login")
        self.assertIn("CapSolver", str(cm.exception))
        self.assertIn("ERROR_NO_FUNDS", str(cm.exception))

    @patch.dict(os.environ, {"CAPSOLVER_API_KEY": "test-api-key"})
    def test_solve_token_missing_capsolver_package_raises(self):
        # GIVEN
        form = CapSolverWafForm(self.test_config)
        form._goku = {"key": "k", "iv": "i", "context": "c"}
        form._challenge_script = "https://example.token.awswaf.com/challenge.js"

        # WHEN / THEN: simulate import failure by injecting None
        with patch.dict(sys.modules, {"capsolver": None}):
            with self.assertRaises(AmazonOrdersError) as cm:
                form._solve_token("https://www.amazon.com/login")
        self.assertIn("capsolver", str(cm.exception).lower())
