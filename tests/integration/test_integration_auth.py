__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import json
import os
import time
import unittest

from amazonorders.exception import AmazonOrdersAuthError, AmazonOrdersNotFoundError, AmazonOrdersError
from amazonorders.orders import AmazonOrders
from amazonorders.session import AmazonSession
from tests.integrationtestcase import IntegrationTestCase


@unittest.skipIf(not os.environ.get("AMAZON_INTEGRATION_TEST_AUTH", "False") == "True",
                 "Running auth tests may lock your account. Set AMAZON_INTEGRATION_TEST_AUTH=True explicitly "
                 "to run.")
class TestIntegrationAuth(IntegrationTestCase):
    """
    These integration tests run generically against any Amazon account to validate authentication.
    """

    @classmethod
    def setUpClass(cls):
        super().set_up_class_conf()

    def setUp(self):
        # An OTP is only valid for one login, so when an account is using 2FA, ensure extra sleep test to ensure the
        # next token has been generated
        self.reauth_sleep_time = 3 if "AMAZON_OTP_SECRET_KEY" not in os.environ else 61

        if os.path.exists(self.test_config.cookie_jar_path):
            os.remove(self.test_config.cookie_jar_path)

    def tearDown(self):
        # Slow down auth tests to ensure we don't trigger Amazon to throttle or lock the account
        time.sleep(self.reauth_sleep_time)

    def test_login(self):
        # GIVEN
        amazon_session = AmazonSession(debug=self.debug,
                                       config=self.test_config)
        amazon_orders = AmazonOrders(amazon_session)

        # WHEN
        amazon_session.login()
        time.sleep(1)
        # with open(self.test_config.cookie_jar_path, "r") as f:
        #     persisted_cookies = json.loads(f.read())

        # THEN
        self.assertTrue(amazon_session.is_authenticated)
        # TODO: possibly due to some race race, but this assertion is flaky, so commenting out for now to not bog down
        #  the nightly run
        # for cookie in self.test_config.constants.COOKIES_SET_WHEN_AUTHENTICATED:
        #     self.assertIn(cookie, amazon_session.session.cookies)
        #     self.assertIn(cookie, persisted_cookies)
        with self.assertRaises(AmazonOrdersNotFoundError):
            amazon_orders.get_order(order_id="1234-fake-id")

    def test_logout(self):
        # GIVEN
        amazon_session = AmazonSession(debug=self.debug,
                                       config=self.test_config)
        amazon_session.login()
        old_session = amazon_session.session
        time.sleep(1)

        # WHEN
        amazon_session.logout()
        time.sleep(1)
        # with open(self.test_config.cookie_jar_path, "r") as f:
        #     persisted_cookies = json.loads(f.read())

        # THEN
        self.assertFalse(amazon_session.is_authenticated)
        self.assertNotEqual(old_session, amazon_session.session)
        # TODO: possibly due to some race race, but this assertion is flaky, so commenting out for now to not bog down
        #  the nightly run
        # for cookie in self.test_config.constants.COOKIES_SET_WHEN_AUTHENTICATED:
        #     self.assertNotIn(cookie, amazon_session.session.cookies)
        #     self.assertNotIn(cookie, persisted_cookies)

    def test_login_no_account(self):
        amazon_username = os.environ["AMAZON_USERNAME"]
        os.environ["AMAZON_USERNAME"] = "invalid-username"

        # GIVEN
        amazon_session = AmazonSession(debug=self.debug,
                                       config=self.test_config)

        # WHEN
        with self.assertRaises(AmazonOrdersAuthError) as cm:
            amazon_session.login()

        # THEN
        self.assertFalse(amazon_session.is_authenticated)
        self.assertIn("cannot find an account", str(cm.exception))

        os.environ["AMAZON_USERNAME"] = amazon_username

    def test_persisted_session_expired(self):
        amazon_session = AmazonSession(debug=self.debug,
                                       config=self.test_config)
        amazon_session.login()
        time.sleep(1)
        amazon_orders = AmazonOrders(amazon_session)

        # WHEN
        with open(self.test_config.cookie_jar_path, "r") as f:
            cookies = json.loads(f.read())
        for cookie in self.test_config.constants.COOKIES_SET_WHEN_AUTHENTICATED:
            cookies[cookie] = "invalid-token"
        with open(self.test_config.cookie_jar_path, "w") as f:
            f.write(json.dumps(cookies))
        amazon_session.session.cookies.update(cookies)

        # THEN
        # Trying to interact with a privilege resources will invalidate the session
        self.assertTrue(amazon_session.is_authenticated)
        with self.assertRaises(AmazonOrdersAuthError):
            amazon_orders.get_order_history()
        self.assertFalse(amazon_session.is_authenticated)
        with self.assertRaises(AmazonOrdersError) as cm:
            amazon_orders.get_order_history()
        self.assertIn("AmazonSession.login() to authenticate first", str(cm.exception))

        # WHEN
        # Validate reauthentication after a session is expired
        time.sleep(self.reauth_sleep_time)
        amazon_session.login()

        # THEN
        self.assertTrue(amazon_session.is_authenticated)

    @unittest.skipIf(not os.environ.get("AMAZON_INTEGRATION_TEST_AUTH_WRONG_PASSWORD", "False") == "True",
                     "Running this test too many times in a row will trigger the Captcha flow instead (causing"
                     "the test to fail), and also may lock the Amazon account. Set "
                     "AMAZON_INTEGRATION_TEST_AUTH_WRONG_PASSWORD=True explicitly to run.")
    def test_login_wrong_password(self):
        amazon_password = os.environ["AMAZON_PASSWORD"]
        os.environ["AMAZON_PASSWORD"] = "invalid-password"

        # GIVEN
        amazon_session = AmazonSession(debug=self.debug,
                                       config=self.test_config)

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            amazon_session.login()

        # THEN
        self.assertFalse(amazon_session.is_authenticated)
        if isinstance(cm.exception, AmazonOrdersAuthError):
            self.assertIn("Error from Amazon:", str(cm.exception))
            self.assertIn("password", str(cm.exception))
        else:
            self.assertIn("CaptchaForm", str(cm.exception))

        os.environ["AMAZON_PASSWORD"] = amazon_password

    @unittest.skipIf(not os.environ.get("AMAZON_OTP_SECRET_KEY"),
                     "AMAZON_OTP_SECRET_KEY environment variable must be set")
    @unittest.skip("Even though the form submissions suggest that Amazon should not re-prompt for OTP, it often does. "
                   "Further investigation needs to be done—perhaps in to deviceId, or if we should go down the "
                   "/ax/claim auth flow instead—for this test to pass.")
    def test_login_logout_login_no_otp_reprompt(self):
        # GIVEN
        amazon_session = AmazonSession(debug=self.debug,
                                       config=self.test_config)
        amazon_session.login()
        time.sleep(1)

        # WHEN
        amazon_session.logout()

        # THEN
        self.assertFalse(amazon_session.is_authenticated)

        # GIVEN
        amazon_session.otp_secret_key = None
        time.sleep(1)

        # WHEN
        # If the test is not automated (ie. prompts for OTP here), consider that a failure
        amazon_session.login()

        # THEN
        self.assertTrue(amazon_session.is_authenticated)
