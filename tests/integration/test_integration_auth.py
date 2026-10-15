__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
import time
import unittest
from unittest import mock

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.exception import AmazonOrdersAuthError, AmazonOrdersError, AmazonOrdersNotFoundError, \
    AmazonOrdersAuthRedirectError
from amazonorders.orders import AmazonOrders
from amazonorders.session import AmazonSession
from tests.integrationtestcase import IntegrationTestCase


skip_unless_lockout_risk_allowed = unittest.skipIf(
    not os.environ.get("AMAZON_INTEGRATION_TEST_AUTH_LOCKOUT_RISK", "False") == "True",
    "These tests sign in extra times or submit bad credentials, which raises the risk of Captcha challenges or "
    "locking the account, so they stay off CI. Set AMAZON_INTEGRATION_TEST_AUTH_LOCKOUT_RISK=True explicitly to run.")


@unittest.skipIf(not os.environ.get("AMAZON_INTEGRATION_TEST_AUTH", "False") == "True",
                 "Running auth tests too frequently may lock the account. Set "
                 "AMAZON_INTEGRATION_TEST_AUTH=True explicitly to run.")
class TestIntegrationAuth(IntegrationTestCase):
    """
    These integration tests run generically against any Amazon account to validate authentication.
    """

    @classmethod
    def setUpClass(cls):
        super().set_up_class_conf()

    def setUp(self):
        if os.path.exists(self.test_config.cookie_jar_path):
            os.remove(self.test_config.cookie_jar_path)

    def tearDown(self):
        print(f"... sleeping {self.teardown_sleep_time} seconds to slow down between auth tests ...")
        time.sleep(self.teardown_sleep_time)

    def given_config_reading_environment(self):
        return AmazonOrdersConfig(data={
            "output_dir": self.test_config.output_dir,
            "cookie_jar_path": self.test_config.cookie_jar_path
        })

    def given_stale_auth_cookies(self, amazon_session):
        stale_cookie_names = set()
        for auth_cookie in self.test_config.constants.COOKIES_SET_WHEN_AUTHENTICATED:
            suffix = auth_cookie.removeprefix("x-")
            stale_cookie_names.update({auth_cookie, f"at-{suffix}", f"sess-at-{suffix}"})
        for cookie in amazon_session.session.cookies:
            if cookie.name in stale_cookie_names:
                cookie.value = "invalid-and-stale"

    @skip_unless_lockout_risk_allowed
    def test_login_then_expire_persisted_session(self):
        # GIVEN
        amazon_session = AmazonSession(debug=self.debug,
                                       config=self.test_config)
        amazon_orders = AmazonOrders(amazon_session)

        # WHEN
        amazon_session.login()

        # THEN
        self.assertTrue(amazon_session.is_authenticated)
        self.assertTrue(amazon_session.auth_cookies_stored())
        # When authenticated, Amazon redirects a non-existent Order somewhere other than sign-in, so get_order() raises
        # AmazonOrdersNotFoundError rather than an auth error, which indicates we're successfully logged in
        with self.assertRaises(AmazonOrdersNotFoundError):
            amazon_orders.get_order(order_id="1234-fake-id")

        # WHEN
        self.given_stale_auth_cookies(amazon_session)

        # THEN
        with self.assertRaises(AmazonOrdersAuthRedirectError) as cm:
            amazon_orders.get_order(order_id="1234-fake-id")
        self.assertIn("redirect_url", cm.exception.meta)
        self.assertTrue(amazon_session.is_authenticated,
                        "A sign-in redirect should keep the session, so other pages keep working")

        # WHEN
        time.sleep(1)
        amazon_session.login()

        # THEN
        self.assertTrue(amazon_session.is_authenticated)
        self.assertTrue(amazon_session.auth_cookies_stored())
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

        # THEN
        self.assertFalse(amazon_session.is_authenticated)
        self.assertFalse(amazon_session.auth_cookies_stored())
        self.assertNotEqual(old_session, amazon_session.session)

    def test_login_no_account(self):
        with mock.patch.dict(os.environ, {"AMAZON_USERNAME": "08511698-9ff5-fake@gmail.com"}):
            # GIVEN
            amazon_session = AmazonSession(debug=self.debug,
                                           config=self.given_config_reading_environment())

            # WHEN
            with self.assertRaises(AmazonOrdersAuthError) as cm:
                amazon_session.login()

            # THEN
            self.assertFalse(amazon_session.is_authenticated)
            self.assertIn("Looks like you're new to Amazon", str(cm.exception))

    @skip_unless_lockout_risk_allowed
    def test_login_wrong_password(self):
        with mock.patch.dict(os.environ, {"AMAZON_PASSWORD": "invalid-password"}):
            # GIVEN
            amazon_session = AmazonSession(debug=self.debug,
                                           config=self.given_config_reading_environment())

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
