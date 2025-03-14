__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
import sys

from amazonorders import conf
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.orders import AmazonOrders
from amazonorders.session import AmazonSession, IODefault
from amazonorders.transactions import AmazonTransactions
from tests.testcase import TestCase
from tests.util.smsprompt import IODefaultWithTextPrompt
from tests.util.tinyserver import get_tiny_server


class IntegrationTestCase(TestCase):
    """
    If run from the Makefile, this test class will prompt for challenges (2FA, Captcha) as necessary.
    Additionally, for a slightly more async and automated experience, the following environment variables
    can be setup for prompts to be texted to a phone number to answer challenge responses:

    - TWILIO_ACCOUNT_SID
    - TWILIO_AUTH_TOKEN
    - TWILIO_PHONE_NUMBER
    - TO_PHONE_NUMBER
    - NGROK_AUTHTOKEN
    """

    amazon_session = None
    tiny_server = None

    @classmethod
    def setUpClass(cls):
        if not (os.environ.get("AMAZON_USERNAME") and os.environ.get("AMAZON_PASSWORD")):
            print("AMAZON_USERNAME and AMAZON_PASSWORD environment variables must be set to run integration tests")

            sys.exit(1)

        twilio_account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        twilio_auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        twilio_phone_number = os.environ.get("TWILIO_PHONE_NUMBER")
        to_phone_number = os.environ.get("TO_PHONE_NUMBER")
        if (os.environ.get("USE_TINY_SERVER", "False") == "True" and
                os.environ.get("NGROK_AUTHTOKEN") and twilio_account_sid and twilio_auth_token and
                twilio_phone_number and to_phone_number):
            cls.tiny_server = get_tiny_server(twilio_account_sid, twilio_auth_token, twilio_phone_number)

            io = IODefaultWithTextPrompt(cls.tiny_server, to_phone_number)
        else:
            io = IODefault()

        conf.DEFAULT_CONFIG_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), ".integration-config")
        test_output_dir = os.path.join(conf.DEFAULT_CONFIG_DIR, "output")
        test_cookie_jar_path = os.path.join(conf.DEFAULT_CONFIG_DIR, "cookies.json")
        cls.test_config = AmazonOrdersConfig(data={
            "output_dir": test_output_dir,
            "cookie_jar_path": test_cookie_jar_path
        })

        cls.amazon_session = AmazonSession(os.environ.get("AMAZON_USERNAME"),
                                           os.environ.get("AMAZON_PASSWORD"),
                                           os.environ.get("DEBUG", "False") == "True",
                                           io=io,
                                           config=cls.test_config)
        cls.amazon_session.login()

        cls.amazon_orders = AmazonOrders(cls.amazon_session)
        cls.amazon_transactions = AmazonTransactions(cls.amazon_session)

    def setUp(self):
        self.assertTrue(self.amazon_session.is_authenticated)
