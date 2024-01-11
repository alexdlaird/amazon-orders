import os
import unittest
from datetime import date

from amazonorders.exception import AmazonOrdersError
from amazonorders.orders import AmazonOrders

from amazonorders.session import AmazonSession

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.3"


class TestOrderHistory(unittest.TestCase):
    def setUp(self):
        self.amazon_session = AmazonSession(os.environ.get("AMAZON_USERNAME"), os.environ.get("AMAZON_PASSWORD"))
        self.amazon_session.login()

        self.amazon_orders = AmazonOrders(self.amazon_session)

    def test_get_orders_unauthenticated(self):
        # GIVEN
        amazon_session = AmazonSession(None, None)
        amazon_orders = AmazonOrders(amazon_session)

        # WHEN
        with self.assertRaises(AmazonOrdersError):
            amazon_orders.get_order_history()

    @unittest.skipIf(not (os.environ.get("AMAZON_USERNAME") and os.environ.get("AMAZON_PASSWORD")),
                     "AMAZON_USERNAME and AMAZON_PASSWORD environment variables not set")
    def test_get_orders(self):
        # GIVEN
        year = 2018

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year)

        # THEN
        self.assertEqual(85, len(orders))
        cat_food_order = orders[3]
        self.assertEqual("34.01", cat_food_order.grand_total)
        self.assertEqual("112-0399923-3070642", cat_food_order.order_number)
        self.assertIsNotNone(cat_food_order.order_details_link)
        self.assertEqual(date(2018, 12, 21), cat_food_order.order_placed_date)
        self.assertEqual("Alex Laird", cat_food_order.recipient.name)
        self.assertIsNotNone(cat_food_order.recipient.address)
        self.assertEqual(1, len(cat_food_order.shipments))
        # TODO: why aren't these equal?
        # self.assertEqual(cat_food_order.items, cat_food_order.shipments[0].items)
        self.assertEqual(cat_food_order, cat_food_order.shipments[0].order)
        self.assertEqual(1, len(cat_food_order.items))
        self.assertEqual(
            "Taste Of The Wild Rocky Mountain Grain-Free Dry Cat Food With Roasted Venison & Smoked Salmon 15Lb",
            cat_food_order.items[0].title)
        self.assertIsNotNone(cat_food_order.items[0].link)
        self.assertEqual(date(2019, 2, 2), cat_food_order.items[0].return_eligible_date)
        self.assertFalse(cat_food_order.full_details)

    @unittest.skipIf(not (os.environ.get("AMAZON_USERNAME") and os.environ.get("AMAZON_PASSWORD")),
                     "AMAZON_USERNAME and AMAZON_PASSWORD environment variables not set")
    def test_get_orders_full_details(self):
        # GIVEN
        year = 2018

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year,
                                                      full_details=True)

        # THEN
        self.assertEqual(85, len(orders))
        cat_food_order = orders[3]
        self.assertEqual("34.01", cat_food_order.grand_total)
        self.assertEqual("112-0399923-3070642", cat_food_order.order_number)
        self.assertIsNotNone(cat_food_order.order_details_link)
        self.assertEqual(date(2018, 12, 21), cat_food_order.order_placed_date)
        self.assertEqual("Alex Laird", cat_food_order.recipient.name)
        self.assertIsNotNone(cat_food_order.recipient.address)
        self.assertEqual(1, len(cat_food_order.shipments))
        self.assertEqual(str(cat_food_order.items), str(cat_food_order.shipments[0].items))
        self.assertEqual(str(cat_food_order), str(cat_food_order.shipments[0].order))
        self.assertEqual(1, len(cat_food_order.items))
        self.assertEqual(
            "Taste Of The Wild Rocky Mountain Grain-Free Dry Cat Food With Roasted Venison & Smoked Salmon 15Lb",
            cat_food_order.items[0].title)
        self.assertIsNotNone(cat_food_order.items[0].link)
        self.assertEqual(date(2019, 2, 2), cat_food_order.items[0].return_eligible_date)

        self.assertTrue(cat_food_order.full_details)
        self.assertEqual("American Express", cat_food_order.payment_method)
        self.assertIsNotNone(cat_food_order.payment_method_last_4)
        self.assertEqual("30.99", cat_food_order.subtotal)
        self.assertEqual("0.00", cat_food_order.shipping_total)
        # TODO: we should fetch an item and assert on a subscription discount too
        self.assertIsNone(cat_food_order.subscription_discount)
        self.assertEqual("30.99", cat_food_order.total_before_tax)
        self.assertEqual("3.02", cat_food_order.estimated_tax)
        self.assertEqual(date(2018, 12, 28), cat_food_order.order_shipped_date)
        # TODO: we should fetch an item and assert on a tracking with a link too
        self.assertIsNone(cat_food_order.tracking_link)
        # TODO: we should fetch an item that can parse this
        # self.assertTrue(cat_food_order.delivered)
        self.assertEqual("New", cat_food_order.items[0].condition)
        self.assertEqual("30.99", cat_food_order.items[0].price)
        self.assertEqual("Amazon.com Services, Inc", cat_food_order.items[0].seller.name)
        # TODO: we should fetch an item and assert on a seller with a link too
        self.assertIsNone(cat_food_order.items[0].seller.link)
