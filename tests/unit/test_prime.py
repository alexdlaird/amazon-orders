__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import os

import responses
from bs4 import BeautifulSoup

from amazonorders.exception import AmazonOrdersError, AmazonOrdersAuthRedirectError
from amazonorders.prime import AmazonPrime
from amazonorders.session import AmazonSession
from tests.unittestcase import UnitTestCase


class TestPrime(UnitTestCase):
    def setUp(self):
        super().setUp()

        self.amazon_session = AmazonSession("some-username@gmail.com",
                                            "some-password",
                                            config=self.test_config)

        self.amazon_prime = AmazonPrime(self.amazon_session)

    def given_prime_payments_page_exists(self, html):
        return responses.add(
            responses.GET,
            f"{self.test_config.constants.PRIME_PAYMENTS_URL}",
            body=html,
            status=200,
        )

    def read_resource(self, *path):
        with open(os.path.join(self.RESOURCES_DIR, *path), "r", encoding="utf-8") as f:
            return f.read()

    def test_get_prime_payments_unauthenticated(self):
        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_prime.get_prime_payments()

        # THEN
        self.assertEqual("Call AmazonSession.login() to authenticate first.", str(cm.exception))

    @responses.activate
    def test_get_prime_payments_session_expires(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        auth_redirect_response = self.given_prime_payments_page_exists(self.read_resource("auth", "signin.html"))
        signout_response = self.given_logout_response_success()

        # WHEN
        with self.assertRaises(AmazonOrdersAuthRedirectError) as cm:
            self.amazon_prime.get_prime_payments()

        # THEN
        self.assertIn("Amazon redirected to login.", str(cm.exception))
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertEqual(1, auth_redirect_response.call_count)
        self.assertEqual(1, signout_response.call_count)

    @responses.activate
    def test_get_prime_payments(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        resp = self.given_prime_payments_page_exists(self.read_resource("prime", "prime-payments.html"))

        # WHEN
        payments = self.amazon_prime.get_prime_payments()

        # THEN
        self.assertEqual(1, resp.call_count)
        self.assertEqual(8, len(payments))
        self.assertEqual([datetime.date(year, 11, 17) for year in range(2025, 2017, -1)],
                         [payment.payment_date for payment in payments])
        self.assertEqual([148.38, 148.38, 148.38, 148.38, 127.03, 128.82, 129.56, 127.78],
                         [payment.total for payment in payments])
        self.assertEqual([f"D01-{1000000 + i}-{2000000 + i}" for i in range(8, 0, -1)],
                         [payment.order_number for payment in payments])
        self.assertEqual("https://www.amazon.com/gp/your-account/order-details?orderID=D01-1000008-2000008",
                         payments[0].order_details_link)
        self.assertEqual("https://www.amazon.com/gp/digital/your-account/order-summary.html/ref=primecentral"
                         "?ie=UTF8&orderID=D01-1000008-2000008&print=1",
                         payments[0].receipt_link)

    @responses.activate
    def test_get_prime_payments_error_page(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        resp = self.given_prime_payments_page_exists(self.read_resource("prime", "prime-payments-error.html"))

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_prime.get_prime_payments()

        # THEN
        self.assertEqual(1, resp.call_count)
        self.assertEqual("Could not parse Prime payments. Check if Amazon changed the HTML.", str(cm.exception))

    def test_parse_prime_payments(self):
        # WHEN
        payments = AmazonPrime.parse_prime_payments(self.read_resource("prime", "prime-payments.html"),
                                                    self.test_config)

        # THEN
        self.assertEqual(8, len(payments))
        self.assertEqual(datetime.date(2018, 11, 17), payments[-1].payment_date)
        self.assertEqual(127.78, payments[-1].total)
        self.assertEqual("D01-1000001-2000001", payments[-1].order_number)

    def test_parse_prime_payments_no_payments(self):
        # GIVEN
        parsed = BeautifulSoup(self.read_resource("prime", "prime-payments.html"), self.test_config.bs4_parser)
        for card_tag in parsed.select(self.test_config.selectors.PRIME_PAYMENT_SELECTOR):
            card_tag.decompose()
        html = str(parsed)

        # WHEN
        payments = AmazonPrime.parse_prime_payments(html, self.test_config)

        # THEN
        self.assertEqual([], payments)

    def test_parse_prime_payments_not_prime_payments_page(self):
        for path in [("prime", "prime-payments-error.html"), ("auth", "signin.html"), ("500.html",)]:
            with self.subTest(path=path):
                # WHEN
                with self.assertRaises(AmazonOrdersError) as cm:
                    AmazonPrime.parse_prime_payments(self.read_resource(*path), self.test_config)

                # THEN
                self.assertEqual("Could not parse Prime payments. Check if Amazon changed the HTML.",
                                 str(cm.exception))
