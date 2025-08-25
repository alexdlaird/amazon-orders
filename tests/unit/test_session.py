__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
from unittest.mock import patch

import responses
from responses.matchers import query_string_matcher

from amazonorders.exception import AmazonOrdersAuthError
from amazonorders.session import AmazonSession
from tests.unittestcase import UnitTestCase


class TestSession(UnitTestCase):
    def setUp(self):
        super().setUp()

        self.amazon_session = AmazonSession("some-username@gmail.com",
                                            "some-password",
                                            config=self.test_config)

    @responses.activate
    def test_login(self):
        # GIVEN
        self.given_login_responses_success()

        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)
        self.assert_login_responses_success()

    @responses.activate
    def test_login_claim(self):
        # GIVEN
        self.given_login_claim_responses_success()

        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)
        self.assert_login_responses_success()

    @responses.activate
    def test_logout(self):
        # GIVEN
        signout_response = self.given_logout_response_success()
        self.amazon_session.is_authenticated = True
        old_session = self.amazon_session.session

        # WHEN
        self.amazon_session.logout()

        # THEN
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertNotEqual(old_session, self.amazon_session.session)
        self.assertEqual(1, signout_response.call_count)

    @responses.activate
    def test_login_claim_invalid_username(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin-claim-username.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-intent.html"), "r",
                  encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_CLAIM_URL,
                body=f.read(),
                status=200,
            )

        # WHEN
        with self.assertRaises(AmazonOrdersAuthError) as cm:
            self.amazon_session.login()

        # THEN
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertIn("Error from Amazon: Looks like you're new to Amazon", str(cm.exception))
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)

    @responses.activate
    def test_login_invalid_username(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-invalid-email.html"), "r",
                  encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )

        # WHEN
        with self.assertRaises(AmazonOrdersAuthError) as cm:
            self.amazon_session.login()

        # THEN
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertIn("Error from Amazon: There was a problem. We cannot find an account with that "
                      "email address.", str(cm.exception))
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)

    @responses.activate
    def test_login_invalid_password(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-invalid-password.html"), "r",
                  encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )

        # WHEN
        with self.assertRaises(AmazonOrdersAuthError) as cm:
            self.amazon_session.login()

        # THEN
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertEqual("Error from Amazon: There was a problem. Your password is incorrect.", str(cm.exception))
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)

    @responses.activate
    @patch("builtins.input")
    def test_mfa(self, input_mock):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-mfa.html"), "r", encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"), "r", encoding="utf-8") as f:
            resp3 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )

        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)
        self.assertEqual(1, input_mock.call_count)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(1, resp3.call_count)

    @responses.activate
    @patch("builtins.input")
    def test_mfa_2(self, input_mock):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-mfa-2.html"),
                  "r", encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"),
                  "r", encoding="utf-8") as f:
            resp3 = responses.add(
                responses.POST,
                f"{self.test_config.constants.BASE_URL}/ap/cvf/approval/verifyOtp",
                body=f.read(),
                status=200,
            )

        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)
        self.assertEqual(1, input_mock.call_count)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(1, resp3.call_count)

    @responses.activate
    @patch("builtins.input")
    def test_new_otp(self, input_mock):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-new-otp.html"), "r", encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-mfa.html"), "r", encoding="utf-8") as f:
            resp3 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2018-0.html"), "r", encoding="utf-8") as f:
            resp4 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )

        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)
        self.assertEqual(2, input_mock.call_count)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(1, resp3.call_count)
        self.assertEqual(1, resp4.call_count)

    @responses.activate
    def test_amazon_blocks_auth(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        resp2 = responses.add(
            responses.POST,
            self.test_config.constants.SIGN_IN_URL,
            status=503
        )

        # WHEN
        with self.assertRaises(AmazonOrdersAuthError) as cm:
            self.amazon_session.login()

        # THEN
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertIn("The page https://www.amazon.com/ap/signin returned 503. Amazon had an issue on "
                      "their end, or may be temporarily blocking your requests.", str(cm.exception))

    @responses.activate
    def test_captcha_loop_retries_exhausted(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-captcha-field-keywords.html"), "r",
                  encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        resp3 = responses.add(
            responses.GET,
            f"{self.test_config.constants.BASE_URL}/errors/validateCaptcha",
            status=302,
            headers={"Location": f"{self.test_config.constants.BASE_URL}/"},
            match=[query_string_matcher(
                "amzn=JC7LJGBaJlGTFs1Ao3s3XA%3D%3D&amzn-r=%2F&field-keywords=CJYYPE")],
        )
        with open(os.path.join(self.RESOURCES_DIR, "index.html"), "r", encoding="utf-8") as f:
            resp4 = responses.add(
                responses.GET,
                f"{self.test_config.constants.BASE_URL}/",
                body=f.read(),
                status=200,
            )

        # WHEN
        with self.assertRaises(AmazonOrdersAuthError) as cm:
            self.amazon_session.login()

        # THEN
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertEqual(5, resp1.call_count)
        self.assertEqual(5, resp2.call_count)
        self.assertEqual(5, resp3.call_count)
        self.assertEqual(5, resp4.call_count)
        self.assertIn("Authentication attempts exhausted.", str(cm.exception))

    @responses.activate
    def test_captcha_fields_keywords(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-captcha-field-keywords.html"), "r",
                  encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200
            )
        resp3 = responses.add(
            responses.GET,
            f"{self.test_config.constants.BASE_URL}/errors/validateCaptcha",
            status=302,
            headers={"Location": f"{self.test_config.constants.BASE_URL}/"},
            match=[query_string_matcher(
                "amzn=JC7LJGBaJlGTFs1Ao3s3XA%3D%3D&amzn-r=%2F&field-keywords=CJYYPE")],
        )
        with open(os.path.join(self.RESOURCES_DIR, "index.html"), "r", encoding="utf-8") as f:
            resp4 = responses.add(
                responses.GET,
                f"{self.test_config.constants.BASE_URL}/",
                body=f.read(),
                status=200,
            )
        self.given_login_responses_success()

        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(1, resp3.call_count)
        self.assertEqual(1, resp4.call_count)

    @responses.activate
    def test_js_waf_login_blocker(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "auth", "signin.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "auth", "post-signin-js-bot-challenge.html"), "r",
                  encoding="utf-8") as f:
            resp2 = responses.add(
                responses.POST,
                self.test_config.constants.SIGN_IN_URL,
                body=f.read(),
                status=200,
            )

        # WHEN
        with self.assertRaises(AmazonOrdersAuthError) as cm:
            self.amazon_session.login()

        # THEN
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertIn("A JavaScript-based authentication challenge page has been found.", str(cm.exception))
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
