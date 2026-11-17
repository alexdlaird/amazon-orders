import datetime
import os
import tempfile
import unittest

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.orders import AmazonOrders
from amazon_orders_pl_language import Constants, Selectors


class TestPolishLanguagePackage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.config = AmazonOrdersConfig(
            config_path=os.path.join(self.temp_dir.name, "config.yml"),
            data={
                "output_dir": self.temp_dir.name,
                "cookie_jar_path": os.path.join(self.temp_dir.name, "cookies.json"),
                "warn_on_missing_required_field": True,
                "language_package": "amazon_orders_pl_language",
            })

    def test_parses_polish_month_names_and_rejects_ambiguous_dates(self):
        constants = Constants()
        months = (
            ("stycznia", 1), ("lutego", 2), ("marca", 3), ("kwietnia", 4),
            ("maja", 5), ("czerwca", 6), ("lipca", 7), ("sierpnia", 8),
            ("września", 9), ("października", 10), ("listopada", 11), ("grudnia", 12),
        )

        for month_name, month in months:
            with self.subTest(month=month_name):
                self.assertEqual(datetime.date(2025, month, 18), constants.parse_date(f"18 {month_name} 2025"))

        self.assertEqual(datetime.date(2025, 3, 18), constants.parse_date("Dostawa: 18 marca 2025", fuzzy=True))
        self.assertIsNone(constants.parse_date("18 marca 2025 i 19 marca 2025", fuzzy=True))
        self.assertIsNone(constants.parse_date("31 lutego 2025"))

    def test_formats_and_parses_synthetic_polish_currency(self):
        constants = Constants()

        self.assertEqual("1.111,11 zł", constants.format_currency(1111.11))
        self.assertEqual("-1.111,11 zł", constants.format_currency(-1111.11))
        self.assertEqual(1111.11, constants.parse_currency("1.111,11 zł"))

    def test_polish_subtotal_labels_match_synthetic_rows(self):
        labels = (
            (Selectors.FIELD_ORDER_GRAND_TOTAL_LABELS, "łączna kwota:"),
            (Selectors.FIELD_ORDER_SUBTOTAL_LABELS, "produkty:"),
            (Selectors.FIELD_ORDER_SHIPPING_TOTAL_LABELS, "pakowanie i wysyłka:"),
            (Selectors.FIELD_ORDER_FREE_SHIPPING_LABELS, "darmowa dostawa:"),
            (Selectors.FIELD_ORDER_REFUND_TOTAL_LABELS, "łączna kwota zwrotu: 1,11 zł"),
        )

        for patterns, row in labels:
            with self.subTest(row=row):
                self.assertIsNotNone(patterns[0].search(row))

    def test_parses_synthetic_polish_order_and_refund_totals_separately(self):
        html = """
        <div id="orderDetails">
          <div data-component="orderSubtotals">
            <div class="a-row">
              <span>Łączna kwota:</span>
              <div class="a-span-last">2.222,22 zł</div>
            </div>
            <div class="a-row">
              <span>Łączna kwota zwrotu:</span>
              <div class="a-span-last">333,33 zł</div>
            </div>
          </div>
        </div>
        """

        order = AmazonOrders.parse_order(html, self.config, order_number="synthetic-only")

        self.assertEqual(2222.22, order.grand_total)
        self.assertEqual(333.33, order.refund_total)

    def test_polish_cancellation_text_marks_order_cancelled(self):
        html = """
        <div id="orderDetails">
          <h4 class="od-status-message">Anulowane</h4>
          <div data-component="orderSubtotals">
            <div class="a-row">
              <span>Łączna kwota:</span>
              <div class="a-span-last">2.222,22 zł</div>
            </div>
          </div>
        </div>
        """

        order = AmazonOrders.parse_order(html, self.config, order_number="synthetic-only")

        self.assertTrue(order.cancelled)
        self.assertIsNone(order.grand_total)
