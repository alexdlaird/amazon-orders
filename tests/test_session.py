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

    @unittest.skip("These tests require input, we need to mock that")
    @responses.activate
    def test_mfa(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "signin.html"), "r") as f:
            responses.add(
                responses.GET,
                "{}/gp/sign-in.html".format(BASE_URL),
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "post-signin-mfa.html"), "r") as f:
            orders_page = f.read()
            responses.add(
                responses.POST,
                "{}/ap/signin".format(BASE_URL),
                body=orders_page,
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

    @unittest.skip("These tests require input, we need to mock that")
    @responses.activate
    def test_new_otp(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "signin.html"), "r") as f:
            responses.add(
                responses.GET,
                "{}/gp/sign-in.html".format(BASE_URL),
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "post-signin-new-otp.html"), "r") as f:
            orders_page = f.read()
            responses.add(
                responses.POST,
                "{}/ap/signin".format(BASE_URL),
                body=orders_page,
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "post-signin-mfa.html"), "r") as f:
            orders_page = f.read()
            responses.add(
                responses.POST,
                "{}/ap/signin".format(BASE_URL),
                body=orders_page,
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

    @unittest.skip("These tests require input, we need to mock that")
    @responses.activate
    def test_captcha(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "signin.html"), "r") as f:
            responses.add(
                responses.GET,
                "{}/gp/sign-in.html".format(BASE_URL),
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "post-signin-captcha.html"), "r") as f:
            orders_page = f.read()
            responses.add(
                responses.POST,
                "{}/ap/signin".format(BASE_URL),
                body=orders_page,
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "orders.html"), "r") as f:
            orders_page = f.read()
            responses.add(
                responses.POST,
                "{}/ap/verify".format(BASE_URL),
                body=orders_page,
                status=200,
            )
        # Simulate the Captcha response
        with open(os.path.join(self.RESOURCES_DIR, "captcha.jpg"), "rb") as f:
            responses.add(
                responses.GET,
                "https://opfcaptcha-prod.s3.amazonaws.com/d32ff4fa043d4f969a1693adfb5d663a.jpg",
                body=f.read(),
                status=200,
            )

        # WHEN
        self.amazon_session.login()

        # THEN
        self.assertTrue(self.amazon_session.is_authenticated)
