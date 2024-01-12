import os
import unittest

import responses

from amazonorders.exception import AmazonOrdersAuthError
from amazonorders.session import AmazonSession, BASE_URL

from tests.testcase import UnitTestCase

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.4"


class TestSession(UnitTestCase):
    def setUp(self):
        self.amazon_session = AmazonSession("some-username",
                                            "some-password")

    @responses.activate
    def test_login(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "signin.html"), "r") as f:
            responses.add(
                responses.GET,
                "{}/gp/sign-in.html".format(BASE_URL),
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "orders.html"), "r") as f:
            orders_page = f.read()
            responses.add(
                responses.POST,
                "{}/ap/signin".format(BASE_URL),
                body=orders_page,
                status=200,
            )

        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)

    @responses.activate
    def test_login_invalid_username(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "signin.html"), "r") as f:
            responses.add(
                responses.GET,
                "{}/gp/sign-in.html".format(BASE_URL),
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "post-signin-invalid-email.html"), "r") as f:
            orders_page = f.read()
            responses.add(
                responses.POST,
                "{}/ap/signin".format(BASE_URL),
                body=orders_page,
                status=200,
            )

        # WHEN
        with self.assertRaises(AmazonOrdersAuthError):
            self.amazon_session.login()

        # THEN
        self.assertFalse(self.amazon_session.is_authenticated)

    @responses.activate
    def test_login_invalid_password(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "signin.html"), "r") as f:
            responses.add(
                responses.GET,
                "{}/gp/sign-in.html".format(BASE_URL),
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "post-signin-invalid-password.html"), "r") as f:
            orders_page = f.read()
            responses.add(
                responses.POST,
                "{}/ap/signin".format(BASE_URL),
                body=orders_page,
                status=200,
            )

        # WHEN
        with self.assertRaises(AmazonOrdersAuthError):
            self.amazon_session.login()

        # THEN
        self.assertFalse(self.amazon_session.is_authenticated)

    def test_mfa(self):
        pass
        # https://www.amazon.com/ap/mfa?ie=UTF8&arb=cdfb9d0a-adf4-4499-a75f-9a746a10a6b4&mfa.arb.value=cdfb9d0a-adf4-4499-a75f-9a746a10a6b4&mfa.arb.key=arb - 200

    def test_new_otp(self):
        pass
        # https://www.amazon.com/ap/mfa/new-otp?ie=UTF8&arb=9ba6b98b-c0a1-43b2-99f7-f3c3182ea127&mfa.arb.value=9ba6b98b-c0a1-43b2-99f7-f3c3182ea127&mfa.arb.key=arb&codeHasBeenSent=false - 200

    def test_captcha(self):
        pass
        # https://www.amazon.com/ap/cvf/request?arb=5892fc4a-2c9e-4a2d-86f3-a9ac4cef3ce0 - 200
