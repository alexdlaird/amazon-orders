__copyright__ = "Copyright (c) 2024 Alex Laird"
__license__ = "MIT"

import os

from amazonorders.orders import AmazonOrders

from amazonorders.session import IODefault, AmazonSession

from tests.testcase import TestCase
from tests.util.smsprompt import IODefaultWithTextPrompt, start_tiny_server


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
        cls.credentials_found = os.environ.get("AMAZON_USERNAME") and os.environ.get("AMAZON_PASSWORD")

        to_phone_number = os.environ.get("TO_PHONE_NUMBER")
        if (os.environ.get("TWILIO_ACCOUNT_SID") and
                os.environ.get("TWILIO_AUTH_TOKEN") and
                os.environ.get("TWILIO_PHONE_NUMBER") and
                to_phone_number and
                os.environ.get("NGROK_AUTHTOKEN")):
            tiny_server = start_tiny_server()

            print(f"TinySMSServer initialized, prompts will be sent over text to {to_phone_number}")

            io = IODefaultWithTextPrompt(tiny_server, to_phone_number)
        else:
            io = IODefault()

        cls.amazon_session = AmazonSession(os.environ.get("AMAZON_USERNAME"),
                                           os.environ.get("AMAZON_PASSWORD"),
                                           io=io)
        cls.amazon_session.login()

        cls.amazon_orders = AmazonOrders(cls.amazon_session)

    def setUp(self):
        if not self.credentials_found:
            self.fail("AMAZON_USERNAME and AMAZON_PASSWORD environment variables not set")

        self.assertTrue(self.amazon_session.is_authenticated)