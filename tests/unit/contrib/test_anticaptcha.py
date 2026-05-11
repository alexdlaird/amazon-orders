__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
import sys
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.contrib.waf.anticaptcha import AntiCaptchaWafForm
from amazonorders.exception import AmazonOrdersError
from amazonorders.session import AmazonSession
from tests.unittestcase import UnitTestCase


class TestAntiCaptchaWafForm(UnitTestCase):
    def setUp(self):
        super().setUp()
        self.amazon_session = AmazonSession("user", "pass", config=self.test_config)

        with open(os.path.join(self.RESOURCES_DIR, "auth", "waf-challenge.html"),
                  "r", encoding="utf-8") as f:
            self.waf_html = f.read()

    def test_init_missing_env_var_raises(self):
        with patch.dict(os.environ):
            # GIVEN
            os.environ.pop("ANTICAPTCHA_API_KEY", None)

            # WHEN / THEN
            with self.assertRaises(AmazonOrdersError) as cm:
                AntiCaptchaWafForm(self.test_config)
            self.assertIn("ANTICAPTCHA_API_KEY", str(cm.exception))

    @patch.dict(os.environ, {"ANTICAPTCHA_API_KEY": "test-api-key"})
    def test_init_with_env_var(self):
        # WHEN
        form = AntiCaptchaWafForm(self.test_config)

        # THEN
        self.assertEqual("test-api-key", form.api_key)

    def test_init_with_config_key(self):
        with patch.dict(os.environ):
            # GIVEN
            os.environ.pop("ANTICAPTCHA_API_KEY", None)
            config = AmazonOrdersConfig(data={
                "output_dir": self.test_output_dir,
                "cookie_jar_path": self.test_cookie_jar_path,
                "anticaptcha_api_key": "config-api-key"
            })

            # WHEN
            form = AntiCaptchaWafForm(config)

            # THEN
            self.assertEqual("config-api-key", form.api_key)

    @patch.dict(os.environ, {"ANTICAPTCHA_API_KEY": "env-api-key"})
    def test_init_env_var_takes_precedence_over_config(self):
        # GIVEN
        config = AmazonOrdersConfig(data={
            "output_dir": self.test_output_dir,
            "cookie_jar_path": self.test_cookie_jar_path,
            "anticaptcha_api_key": "config-api-key"
        })

        # WHEN
        form = AntiCaptchaWafForm(config)

        # THEN
        self.assertEqual("env-api-key", form.api_key)

    @patch.dict(os.environ, {"ANTICAPTCHA_API_KEY": "test-api-key"})
    def test_select_form_detects_waf_challenge(self):
        # GIVEN
        form = AntiCaptchaWafForm(self.test_config)
        parsed = BeautifulSoup(self.waf_html, self.test_config.bs4_parser)

        # WHEN
        result = form.select_form(self.amazon_session, parsed)

        # THEN
        self.assertTrue(result)
        self.assertIn("key", form._goku)
        self.assertIn("awswaf.com", form._challenge_script)

    @patch.dict(os.environ, {"ANTICAPTCHA_API_KEY": "test-api-key"})
    def test_solve_token_calls_anticaptcha_with_correct_setters(self):
        # GIVEN
        fake_solver_instance = MagicMock()
        fake_solver_instance.solve_and_return_solution.return_value = "waf-token-value"

        fake_module = MagicMock()
        fake_module.amazonProxyless = MagicMock(return_value=fake_solver_instance)

        form = AntiCaptchaWafForm(self.test_config)
        goku = {"key": "k123", "iv": "i123", "context": "c123"}
        challenge_script = "https://example.token.awswaf.com/challenge.js"

        # WHEN
        with patch.dict(sys.modules, {
            "anticaptchaofficial": MagicMock(),
            "anticaptchaofficial.amazonproxyless": fake_module,
        }):
            token = form._solve_token("https://www.amazon.com/login", goku, challenge_script)

        # THEN
        self.assertEqual("waf-token-value", token)
        fake_solver_instance.set_key.assert_called_once_with("test-api-key")
        fake_solver_instance.set_website_url.assert_called_once_with("https://www.amazon.com/login")
        fake_solver_instance.set_website_key.assert_called_once_with("k123")
        fake_solver_instance.set_iv.assert_called_once_with("i123")
        fake_solver_instance.set_context.assert_called_once_with("c123")
        fake_solver_instance.set_challenge_script.assert_called_once_with(
            "https://example.token.awswaf.com/challenge.js")

    @patch.dict(os.environ, {"ANTICAPTCHA_API_KEY": "test-api-key"})
    def test_solve_token_zero_response_raises(self):
        # GIVEN
        fake_solver_instance = MagicMock()
        fake_solver_instance.solve_and_return_solution.return_value = 0
        fake_solver_instance.error_code = "ERROR_NO_SLOT_AVAILABLE"

        fake_module = MagicMock()
        fake_module.amazonProxyless = MagicMock(return_value=fake_solver_instance)

        form = AntiCaptchaWafForm(self.test_config)
        goku = {"key": "k", "iv": "i", "context": "c"}
        challenge_script = "https://example.token.awswaf.com/challenge.js"

        # WHEN / THEN
        with patch.dict(sys.modules, {
            "anticaptchaofficial": MagicMock(),
            "anticaptchaofficial.amazonproxyless": fake_module,
        }):
            with self.assertRaises(AmazonOrdersError) as cm:
                form._solve_token("https://www.amazon.com/login", goku, challenge_script)
        self.assertIn("Anti-Captcha", str(cm.exception))
        self.assertIn("ERROR_NO_SLOT_AVAILABLE", str(cm.exception))

    @patch.dict(os.environ, {"ANTICAPTCHA_API_KEY": "test-api-key"})
    def test_solve_token_sdk_exception_wraps_as_amazon_orders_error(self):
        # GIVEN
        fake_solver_instance = MagicMock()
        fake_solver_instance.solve_and_return_solution.side_effect = RuntimeError(
            "Network unreachable")

        fake_module = MagicMock()
        fake_module.amazonProxyless = MagicMock(return_value=fake_solver_instance)

        form = AntiCaptchaWafForm(self.test_config)
        goku = {"key": "k", "iv": "i", "context": "c"}
        challenge_script = "https://example.token.awswaf.com/challenge.js"

        # WHEN / THEN
        with patch.dict(sys.modules, {
            "anticaptchaofficial": MagicMock(),
            "anticaptchaofficial.amazonproxyless": fake_module,
        }):
            with self.assertRaises(AmazonOrdersError) as cm:
                form._solve_token("https://www.amazon.com/login", goku, challenge_script)
        self.assertIn("Anti-Captcha", str(cm.exception))
        self.assertIn("Network unreachable", str(cm.exception))

    @patch.dict(os.environ, {"ANTICAPTCHA_API_KEY": "test-api-key"})
    def test_solve_token_missing_anticaptcha_package_raises(self):
        # GIVEN
        form = AntiCaptchaWafForm(self.test_config)
        goku = {"key": "k", "iv": "i", "context": "c"}
        challenge_script = "https://example.token.awswaf.com/challenge.js"

        # WHEN / THEN: simulate import failure
        with patch.dict(sys.modules, {"anticaptchaofficial.amazonproxyless": None}):
            with self.assertRaises(AmazonOrdersError) as cm:
                form._solve_token("https://www.amazon.com/login", goku, challenge_script)
        self.assertIn("anticaptchaofficial", str(cm.exception).lower())
