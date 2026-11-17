import datetime

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.orders import AmazonOrders
from tests.unit import example_polish_language_package
from tests.unittestcase import UnitTestCase


class TestPolishLanguagePackage(UnitTestCase):
    def setUp(self):
        super().setUp()
        self.polish_config = AmazonOrdersConfig(data={
            "output_dir": self.test_output_dir,
            "cookie_jar_path": self.test_cookie_jar_path,
            "warn_on_missing_required_field": True,
            "language_package": "tests.unit.example_polish_language_package",
        })

    def test_parses_polish_month_names_and_rejects_ambiguous_dates(self):
        constants = example_polish_language_package.Constants()
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

        # The synthetic page has no Amazon ID, so supply only a non-ID fallback for the required field.
        order = AmazonOrders.parse_order(html, self.polish_config, order_number="synthetic-only")

        self.assertEqual(2222.22, order.grand_total)
        self.assertEqual(333.33, order.refund_total)

    def test_polish_cancellation_text_marks_the_order_cancelled(self):
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

        order = AmazonOrders.parse_order(html, self.polish_config, order_number="synthetic-only")

        self.assertTrue(order.cancelled)
        self.assertIsNone(order.grand_total)
