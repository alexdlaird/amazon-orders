__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import json
import os
import time
import unittest

from amazonorders.exception import AmazonOrdersAuthError, AmazonOrdersError, AmazonOrdersNotFoundError, \
    AmazonOrdersAuthRedirectError
from amazonorders.orders import AmazonOrders
from amazonorders.session import AmazonSession
from tests.integrationtestcase import IntegrationTestCase


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

    @unittest.skip("The manual process to make stale isn't working here, needs investigation")
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
        # Navigating to a non-existent Order when authenticated returns 404 (rather than redirecting to login), which
        # indicates we're successfully logged in
        with self.assertRaises(AmazonOrdersNotFoundError):
            amazon_orders.get_order(order_id="1234-fake-id")

        # WHEN
        time.sleep(1)
        with open(self.test_config.cookie_jar_path, "r") as f:
            cookies = json.loads(f.read())
        for cookie in self.test_config.constants.COOKIES_SET_WHEN_AUTHENTICATED:
            cookies[cookie] = "invalid-and-stale"
        with open(self.test_config.cookie_jar_path, "w") as f:
            f.write(json.dumps(cookies))
        amazon_session.session.cookies.update(cookies)

        # THEN
        # Trying to interact with a privileged resource will redirect us to login
        self.assertTrue(amazon_session.is_authenticated)
        with self.assertRaises(AmazonOrdersAuthRedirectError):
            amazon_orders.get_order(order_id="1234-fake-id")
        time.sleep(1)
        # And then we will find our session invalidated
        self.assertFalse(amazon_session.is_authenticated)
        self.assertFalse(amazon_session.auth_cookies_stored())
        with self.assertRaises(AmazonOrdersError) as cm:
            amazon_orders.get_order(order_id="1234-fake-id")
        self.assertIn("AmazonSession.login() to authenticate first", str(cm.exception))

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
        amazon_username = os.environ["AMAZON_USERNAME"]
        os.environ["AMAZON_USERNAME"] = "08511698-9ff5-fake@gmail.com"

        # GIVEN
        amazon_session = AmazonSession(debug=self.debug,
                                       config=self.test_config)

        # WHEN
        with self.assertRaises(AmazonOrdersAuthError) as cm:
            amazon_session.login()

        # THEN
        self.assertFalse(amazon_session.is_authenticated)
        self.assertIn("Looks like you're new to Amazon", str(cm.exception))

        os.environ["AMAZON_USERNAME"] = amazon_username

    @unittest.skipIf(not os.environ.get("AMAZON_INTEGRATION_TEST_AUTH_WRONG_PASSWORD", "False") == "True",
                     "Running this test too too frequently will trigger the Captcha flow instead (causing"
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
