__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
import sys
import time

from amazonorders import conf
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.gift_cards import AmazonGiftCards
from amazonorders.orders import AmazonOrders
from amazonorders.session import AmazonSession
from amazonorders.transactions import AmazonTransactions
from tests.testcase import TestCase


class IntegrationTestCase(TestCase):
    """
    This test class will prompt for challenges (2FA, Captcha) as necessary. To run fully automated (assuming
    no Captcha prompts are encountered), set all authentication environment variables:

    - AMAZON_USERNAME
    - AMAZON_PASSWORD
    - AMAZON_OTP_SECRET_KEY (optional, if 2FA is enabled for the account)

    To run locally without signing in, set AMAZON_INTEGRATION_TEST_REUSE_SESSION=True to reuse the session saved by
    ``amazon-orders login --browser``. No sign-in form is submitted, so it can't be combined with
    AMAZON_INTEGRATION_TEST_AUTH=True.
    """

    amazon_session = None
    reuse_session = os.environ.get("AMAZON_INTEGRATION_TEST_REUSE_SESSION", "False") == "True"

    @classmethod
    def setUpClass(cls):
        cls.set_up_class_conf()

        cls.debug = os.environ.get("DEBUG", "False") == "True"
        cls.amazon_session = AmazonSession(debug=cls.debug,
                                           config=cls.test_config)
        if cls.reuse_session:
            cls.amazon_session.auth_forms = []
        cls.amazon_session.login()

        cls.amazon_orders = AmazonOrders(cls.amazon_session)
        cls.amazon_transactions = AmazonTransactions(cls.amazon_session)
        cls.amazon_gift_cards = AmazonGiftCards(cls.amazon_session)

    @classmethod
    def tearDownClass(cls):
        print(f"... sleeping {cls.teardown_sleep_time} seconds to slow down between integration suites ...")
        time.sleep(cls.teardown_sleep_time)

    @classmethod
    def set_up_class_conf(cls):
        cls.teardown_sleep_time = int(os.environ.get("AMAZON_INTEGRATION_TEST_TEARDOWN_SLEEP", 40))

        if cls.reuse_session:
            if os.environ.get("AMAZON_INTEGRATION_TEST_AUTH", "False") == "True":
                print("AMAZON_INTEGRATION_TEST_REUSE_SESSION can't be used with AMAZON_INTEGRATION_TEST_AUTH, "
                      "since auth tests sign in and out.")

                sys.exit(1)

            cls.test_config = AmazonOrdersConfig()
            if not AmazonSession(config=cls.test_config).auth_cookies_stored():
                print("AMAZON_INTEGRATION_TEST_REUSE_SESSION is set, but there's no saved session. Run "
                      "`amazon-orders login --browser` first.")

                sys.exit(1)

            return

        if not (os.environ.get("AMAZON_USERNAME") and os.environ.get("AMAZON_PASSWORD")):
            print("AMAZON_USERNAME and AMAZON_PASSWORD environment variables must be set to run integration tests")

            sys.exit(1)

        conf.DEFAULT_CONFIG_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), ".integration-config")
        test_output_dir = os.path.join(conf.DEFAULT_CONFIG_DIR, "output")
        test_cookie_jar_path = os.path.join(conf.DEFAULT_CONFIG_DIR, "cookies.json")
        cls.test_config = AmazonOrdersConfig(data={
            "output_dir": test_output_dir,
            "cookie_jar_path": test_cookie_jar_path
        })

        if os.path.exists(test_cookie_jar_path):
            os.remove(test_cookie_jar_path)

    def setUp(self):
        self.assertTrue(self.amazon_session.is_authenticated)
