__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import json
import os
import sys
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

from amazonorders.contrib.waf.twocaptcha import TwoCaptchaWafForm
from amazonorders.exception import AmazonOrdersError
from amazonorders.session import AmazonSession
from tests.unittestcase import UnitTestCase


class TestTwoCaptchaWafForm(UnitTestCase):
    def setUp(self):
        super().setUp()
        self.amazon_session = AmazonSession("user", "pass", config=self.test_config)

        with open(os.path.join(self.RESOURCES_DIR, "auth", "waf-challenge.html"),
                  "r", encoding="utf-8") as f:
            self.waf_html = f.read()

    def test_init_missing_env_var_raises(self):
        # GIVEN
        prior = os.environ.pop("TWOCAPTCHA_API_KEY", None)
        try:
            # WHEN / THEN
            with self.assertRaises(AmazonOrdersError) as cm:
                TwoCaptchaWafForm(self.test_config)
            self.assertIn("TWOCAPTCHA_API_KEY", str(cm.exception))
        finally:
            if prior is not None:
                os.environ["TWOCAPTCHA_API_KEY"] = prior

    @patch.dict(os.environ, {"TWOCAPTCHA_API_KEY": "test-api-key"})
    def test_init_with_env_var(self):
        # WHEN
        form = TwoCaptchaWafForm(self.test_config)

        # THEN
        self.assertEqual("test-api-key", form.api_key)

    @patch.dict(os.environ, {"TWOCAPTCHA_API_KEY": "test-api-key"})
    def test_select_form_detects_waf_challenge(self):
        # GIVEN
        form = TwoCaptchaWafForm(self.test_config)
        parsed = BeautifulSoup(self.waf_html, self.test_config.bs4_parser)

        # WHEN
        result = form.select_form(self.amazon_session, parsed)

        # THEN
        self.assertTrue(result)
        self.assertIn("key", form._goku)
        self.assertIn("awswaf.com", form._challenge_script)

    @patch.dict(os.environ, {"TWOCAPTCHA_API_KEY": "test-api-key"})
    def test_solve_token_calls_amazon_waf_with_correct_kwargs(self):
        # GIVEN
        fake_solver_instance = MagicMock()
        fake_solver_instance.amazon_waf.return_value = {
            "captchaId": "abc123",
            "code": json.dumps({
                "captcha_voucher": "voucher-value",
                "existing_token": "waf-token-value",
            }),
        }

        fake_module = MagicMock()
        fake_module.TwoCaptcha = MagicMock(return_value=fake_solver_instance)

        form = TwoCaptchaWafForm(self.test_config)
        goku = {"key": "k123", "iv": "i123", "context": "c123"}
        challenge_script = "https://example.token.awswaf.com/challenge.js"

        # WHEN
        with patch.dict(sys.modules, {"twocaptcha": fake_module}):
            token = form._solve_token("https://www.amazon.com/login", goku, challenge_script)

        # THEN
        self.assertEqual("waf-token-value", token)
        fake_module.TwoCaptcha.assert_called_once_with("test-api-key")
        fake_solver_instance.amazon_waf.assert_called_once_with(
            sitekey="k123",
            iv="i123",
            context="c123",
            url="https://www.amazon.com/login",
            challenge_script="https://example.token.awswaf.com/challenge.js",
        )

    @patch.dict(os.environ, {"TWOCAPTCHA_API_KEY": "test-api-key"})
    def test_solve_token_malformed_response_raises(self):
        # GIVEN
        fake_solver_instance = MagicMock()
        fake_solver_instance.amazon_waf.return_value = {"code": "not-json"}

        fake_module = MagicMock()
        fake_module.TwoCaptcha = MagicMock(return_value=fake_solver_instance)

        form = TwoCaptchaWafForm(self.test_config)
        goku = {"key": "k", "iv": "i", "context": "c"}
        challenge_script = "https://example.token.awswaf.com/challenge.js"

        # WHEN / THEN
        with patch.dict(sys.modules, {"twocaptcha": fake_module}):
            with self.assertRaises(AmazonOrdersError) as cm:
                form._solve_token("https://www.amazon.com/login", goku, challenge_script)
        self.assertIn("existing_token", str(cm.exception))

    @patch.dict(os.environ, {"TWOCAPTCHA_API_KEY": "test-api-key"})
    def test_solve_token_missing_existing_token_raises(self):
        # GIVEN
        fake_solver_instance = MagicMock()
        fake_solver_instance.amazon_waf.return_value = {
            "code": json.dumps({"captcha_voucher": "v", "other_key": "x"}),
        }

        fake_module = MagicMock()
        fake_module.TwoCaptcha = MagicMock(return_value=fake_solver_instance)

        form = TwoCaptchaWafForm(self.test_config)
        goku = {"key": "k", "iv": "i", "context": "c"}
        challenge_script = "https://example.token.awswaf.com/challenge.js"

        # WHEN / THEN
        with patch.dict(sys.modules, {"twocaptcha": fake_module}):
            with self.assertRaises(AmazonOrdersError) as cm:
                form._solve_token("https://www.amazon.com/login", goku, challenge_script)
        self.assertIn("existing_token", str(cm.exception))

    @patch.dict(os.environ, {"TWOCAPTCHA_API_KEY": "test-api-key"})
    def test_solve_token_sdk_exception_wraps_as_amazon_orders_error(self):
        # GIVEN
        fake_solver_instance = MagicMock()
        fake_solver_instance.amazon_waf.side_effect = RuntimeError("ERROR_ZERO_BALANCE")

        fake_module = MagicMock()
        fake_module.TwoCaptcha = MagicMock(return_value=fake_solver_instance)

        form = TwoCaptchaWafForm(self.test_config)
        goku = {"key": "k", "iv": "i", "context": "c"}
        challenge_script = "https://example.token.awswaf.com/challenge.js"

        # WHEN / THEN
        with patch.dict(sys.modules, {"twocaptcha": fake_module}):
            with self.assertRaises(AmazonOrdersError) as cm:
                form._solve_token("https://www.amazon.com/login", goku, challenge_script)
        self.assertIn("2Captcha", str(cm.exception))
        self.assertIn("ERROR_ZERO_BALANCE", str(cm.exception))

    @patch.dict(os.environ, {"TWOCAPTCHA_API_KEY": "test-api-key"})
    def test_solve_token_missing_twocaptcha_package_raises(self):
        # GIVEN
        form = TwoCaptchaWafForm(self.test_config)
        goku = {"key": "k", "iv": "i", "context": "c"}
        challenge_script = "https://example.token.awswaf.com/challenge.js"

        # WHEN / THEN
        with patch.dict(sys.modules, {"twocaptcha": None}):
            with self.assertRaises(AmazonOrdersError) as cm:
                form._solve_token("https://www.amazon.com/login", goku, challenge_script)
        self.assertIn("2captcha-python", str(cm.exception))
