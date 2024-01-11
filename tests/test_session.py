import os
import unittest

from amazonorders.exception import AmazonOrdersAuthError
from amazonorders.session import AmazonSession

from tests.testcase import UnitTestCase

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.3"


class TestSession(UnitTestCase):
    def setUp(self):
        self.amazon_session = AmazonSession(os.environ.get("AMAZON_USERNAME"),
                                            os.environ.get("AMAZON_PASSWORD"))

    @unittest.skip("This test needs to be mocked against the resource files to work")
    def test_login(self):
        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)

    def test_login_invalid_username(self):
        # GIVEN
        amazon_session = AmazonSession("bad-username", "fake-password")

        # WHEN
        with self.assertRaises(AmazonOrdersAuthError):
            amazon_session.login()

        # THEN
        self.assertFalse(amazon_session.is_authenticated)

    @unittest.skip("This test needs to be mocked against the resource files to work")
    def test_login_invalid_password(self):
        # GIVEN
        amazon_session = AmazonSession(os.environ.get("AMAZON_USERNAME"),
                                       "fake-password")

        # WHEN
        amazon_session.login()

        # THEN
        self.assertFalse(amazon_session.is_authenticated)

    def test_mfa(self):
        pass
        # https://www.amazon.com/ap/mfa?ie=UTF8&arb=cdfb9d0a-adf4-4499-a75f-9a746a10a6b4&mfa.arb.value=cdfb9d0a-adf4-4499-a75f-9a746a10a6b4&mfa.arb.key=arb - 200

    def test_new_otp(self):
        pass
        # https://www.amazon.com/ap/mfa/new-otp?ie=UTF8&arb=9ba6b98b-c0a1-43b2-99f7-f3c3182ea127&mfa.arb.value=9ba6b98b-c0a1-43b2-99f7-f3c3182ea127&mfa.arb.key=arb&codeHasBeenSent=false - 200

    def test_captcha(self):
        pass
        # https://www.amazon.com/ap/cvf/request?arb=5892fc4a-2c9e-4a2d-86f3-a9ac4cef3ce0 - 200
