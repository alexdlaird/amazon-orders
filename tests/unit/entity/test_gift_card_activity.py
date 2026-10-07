__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from datetime import date

from bs4 import BeautifulSoup

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.gift_card_activity import GiftCardActivity
from amazonorders.exception import AmazonOrdersError
from tests.unittestcase import UnitTestCase


class TestGiftCardActivity(UnitTestCase):
    ORDER_CELL = ('<span>Gift Card applied to Amazon.com order</span> '
                  '<a class="a-link-normal" href="/gp/your-account/order-details?orderID=111-5500901-2478601">'
                  '<span>111-5500901-2478601</span></a>')

    def given_row(self, activity_date="May 12, 2026", description=ORDER_CELL, amount="-$19.48",
                  closing_balance="$0.00"):
        html = (f"<table><tr><td>{activity_date}</td><td>{description}</td><td>{amount}</td>"
                f"<td>{closing_balance}</td></tr></table>")
        return BeautifulSoup(html, self.test_config.bs4_parser).select_one("tr")

    def given_lenient_config(self):
        return AmazonOrdersConfig(data={
            "output_dir": self.test_output_dir,
            "cookie_jar_path": self.test_cookie_jar_path,
            "warn_on_missing_required_field": True
        })

    def test_parse(self):
        # GIVEN
        parsed = self.given_row()

        # WHEN
        activity = GiftCardActivity(parsed, self.test_config)

        # THEN
        self.assertEqual(date(2026, 5, 12), activity.activity_date)
        self.assertEqual("Gift Card applied to Amazon.com order", activity.description)
        self.assertEqual(-19.48, activity.amount)
        self.assertFalse(activity.is_credit)
        self.assertEqual(0.00, activity.closing_balance)
        self.assertEqual("111-5500901-2478601", activity.order_number)
        self.assertEqual("https://www.amazon.com/gp/your-account/order-details?orderID=111-5500901-2478601",
                         activity.order_details_link)
        self.assertEqual('<GiftCardActivity 2026-05-12: "Gift Card applied to Amazon.com order, Amount: -19.48">',
                         repr(activity))

    def test_parse_order_link_text_not_an_order_number(self):
        # GIVEN
        parsed = self.given_row(description='<span>Gift Card applied to Amazon.com order</span> '
                                            '<a class="a-link-normal" href="/gp/x"><span>pending</span></a>')

        # WHEN
        with self.assertLogs("amazonorders.entity.gift_card_activity", level="WARNING") as cm:
            activity = GiftCardActivity(parsed, self.test_config)

        # THEN
        self.assertIsNone(activity.order_number)
        self.assertIsNone(activity.order_details_link)
        self.assertIn("not an Order number: 'pending'", cm.output[0])

    def test_parse_unparseable_date_raises(self):
        # GIVEN
        parsed = self.given_row(activity_date="Not a date")

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            GiftCardActivity(parsed, self.test_config)

        # THEN
        self.assertIn("GiftCardActivity.activity_date could not be parsed", str(cm.exception))

    def test_parse_unparseable_date_warns_when_configured(self):
        # GIVEN
        parsed = self.given_row(activity_date="Not a date")

        # WHEN
        with self.assertLogs("amazonorders.entity.gift_card_activity", level="WARNING") as cm:
            activity = GiftCardActivity(parsed, self.given_lenient_config())

        # THEN
        self.assertIsNone(activity.activity_date)
        self.assertEqual(-19.48, activity.amount)
        self.assertIn("GiftCardActivity.activity_date could not be parsed", cm.output[0])

    def test_parse_unparseable_amount_raises(self):
        # GIVEN
        parsed = self.given_row(amount="")

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            GiftCardActivity(parsed, self.test_config)

        # THEN
        self.assertIn("GiftCardActivity.amount could not be parsed", str(cm.exception))

    def test_parse_unparseable_amount_warns_when_configured(self):
        # GIVEN
        parsed = self.given_row(amount="")

        # WHEN
        with self.assertLogs("amazonorders.entity.gift_card_activity", level="WARNING") as cm:
            activity = GiftCardActivity(parsed, self.given_lenient_config())

        # THEN
        self.assertIsNone(activity.amount)
        self.assertFalse(activity.is_credit)
        self.assertIn("GiftCardActivity.amount could not be parsed", cm.output[0])
