__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
import sys

from amazonorders import conf
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.orders import AmazonOrders
from amazonorders.session import AmazonSession
from amazonorders.transactions import AmazonTransactions
from tests.testcase import TestCase


class IntegrationTestCase(TestCase):
    """
    If run from the Makefile, this test class will prompt for challenges (2FA, Captcha) as necessary.
    Additionally, for a more automated experience, the following environment variables can be setup for
    OTP prompts to be auto-solved:

    - OTP_SECRET_KEY
    """

    amazon_session = None

    @classmethod
    def setUpClass(cls):
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

        cls.amazon_session = AmazonSession(debug=os.environ.get("DEBUG", "False") == "True",
                                           config=cls.test_config)
        cls.amazon_session.login()

        cls.amazon_orders = AmazonOrders(cls.amazon_session)
        cls.amazon_transactions = AmazonTransactions(cls.amazon_session)

    def setUp(self):
        self.assertTrue(self.amazon_session.is_authenticated)
