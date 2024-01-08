import unittest

from amazonorders.parser import get_orders

from amazonorders.auth import login

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.2"


class TestAuth(unittest.TestCase):
    def test_login(self):
        login()

        get_orders()

    def test_new_otp(self):
        pass
        # https://www.amazon.com/ap/mfa/new-otp?ie=UTF8&arb=9ba6b98b-c0a1-43b2-99f7-f3c3182ea127&mfa.arb.value=9ba6b98b-c0a1-43b2-99f7-f3c3182ea127&mfa.arb.key=arb&codeHasBeenSent=false - 200

    def test_captcha(self):
        pass
        #
