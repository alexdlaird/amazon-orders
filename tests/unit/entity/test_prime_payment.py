__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
from datetime import date

from bs4 import BeautifulSoup

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.prime_payment import PrimePayment
from amazonorders.exception import AmazonOrdersError
from tests.unittestcase import UnitTestCase


class TestPrimePayment(UnitTestCase):
    def given_first_card(self, html=None):
        if html is None:
            with open(os.path.join(self.RESOURCES_DIR, "prime", "prime-payments.html"), "r",
                      encoding="utf-8") as f:
                html = f.read()

        parsed = BeautifulSoup(html, self.test_config.bs4_parser)

        return parsed.select(self.test_config.selectors.PRIME_PAYMENT_SELECTOR)[0]

    def test_parse(self):
        # GIVEN
        card_tag = self.given_first_card()

        # WHEN
        payment = PrimePayment(card_tag, self.test_config)

        # THEN
        self.assertEqual(date(2025, 11, 17), payment.payment_date)
        self.assertEqual(148.38, payment.total)
        self.assertEqual("D01-1000008-2000008", payment.order_number)
        self.assertEqual("https://www.amazon.com/gp/your-account/order-details?orderID=D01-1000008-2000008",
                         payment.order_details_link)
        self.assertEqual("https://www.amazon.com/gp/digital/your-account/order-summary.html/ref=primecentral"
                         "?ie=UTF8&orderID=D01-1000008-2000008&print=1",
                         payment.receipt_link)
        self.assertEqual("<PrimePayment 2025-11-17: \"Order #D01-1000008-2000008, Total: 148.38\">",
                         repr(payment))
        self.assertEqual("PrimePayment 2025-11-17: Order #D01-1000008-2000008, Total: 148.38", str(payment))

    def test_parse_labeled_rows_in_any_order(self):
        # GIVEN
        card_tag = self.given_first_card("""
        <div class="a-cardui">
          <div class="a-cardui-header"><h3>March 3, 2026</h3></div>
          <div class="a-cardui-body"><ul>
            <li><div><span class="a-color-tertiary">Order Number</span><p>D01-1234567-7654321</p></div></li>
            <li><div><span class="a-color-tertiary">Subtotal</span><p>$14.99</p></div></li>
            <li><div><span class="a-color-tertiary">Total</span><p>$15.94</p></div></li>
          </ul></div>
        </div>
        """)

        # WHEN
        payment = PrimePayment(card_tag, self.test_config)

        # THEN
        self.assertEqual(date(2026, 3, 3), payment.payment_date)
        self.assertEqual(15.94, payment.total)
        self.assertEqual("D01-1234567-7654321", payment.order_number)
        self.assertIsNone(payment.receipt_link)

    def test_parse_order_number_required(self):
        # GIVEN
        card_tag = self.given_first_card()
        card_tag.select_one("p:-soup-contains('D01-1000008-2000008')").string = "pending"

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            PrimePayment(card_tag, self.test_config)

        # THEN
        self.assertIn("PrimePayment.order_number could not be parsed, but it's required.", str(cm.exception))

    def test_parse_order_number_required_warn(self):
        # GIVEN
        config = AmazonOrdersConfig(data={"output_dir": self.test_output_dir,
                                          "cookie_jar_path": self.test_cookie_jar_path,
                                          "warn_on_missing_required_field": True})
        card_tag = self.given_first_card()
        card_tag.select_one("p:-soup-contains('D01-1000008-2000008')").string = "pending"

        # WHEN
        with self.assertLogs("amazonorders.entity.prime_payment", level="WARNING") as cm:
            payment = PrimePayment(card_tag, config)

        # THEN
        self.assertIsNone(payment.order_number)
        self.assertIsNone(payment.order_details_link)
        self.assertEqual(148.38, payment.total)
        self.assertIn("PrimePayment.order_number could not be parsed", cm.output[0])

    def test_parse_total_required(self):
        # GIVEN
        card_tag = self.given_first_card()
        card_tag.select_one("p:-soup-contains('$148.38')").string = ""

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            PrimePayment(card_tag, self.test_config)

        # THEN
        self.assertIn("PrimePayment.total could not be parsed, but it's required.", str(cm.exception))

    def test_parse_total_required_warn(self):
        # GIVEN
        config = AmazonOrdersConfig(data={"output_dir": self.test_output_dir,
                                          "cookie_jar_path": self.test_cookie_jar_path,
                                          "warn_on_missing_required_field": True})
        card_tag = self.given_first_card()
        card_tag.select_one("p:-soup-contains('$148.38')").string = ""

        # WHEN
        with self.assertLogs("amazonorders.entity.prime_payment", level="WARNING") as cm:
            payment = PrimePayment(card_tag, config)

        # THEN
        self.assertIsNone(payment.total)
        self.assertEqual("D01-1000008-2000008", payment.order_number)
        self.assertIn("PrimePayment.total could not be parsed", cm.output[0])
