import os
import unittest
from datetime import date

from amazonorders.orders import AmazonOrders
from amazonorders.session import AmazonSession

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.3"


@unittest.skipIf(os.environ.get("INTEGRATION_TESTS", "False") != "True",
                 "Skipping, INTEGRATION_TESTS=True was not set in the environment")
class TestIntegration(unittest.TestCase):
    def setUp(self):
        if not (os.environ.get("AMAZON_USERNAME") and os.environ.get(
                "AMAZON_PASSWORD")):
            self.fail(
                "AMAZON_USERNAME and AMAZON_PASSWORD environment variables not set")

        self.amazon_session = AmazonSession(os.environ.get("AMAZON_USERNAME"),
                                            os.environ.get("AMAZON_PASSWORD"))
        self.amazon_session.login()

        self.amazon_orders = AmazonOrders(self.amazon_session)

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
        shipment = cat_food_order.shipments[0]
        self.assertEqual(str(cat_food_order.items), str(shipment.items))
        self.assertEqual(cat_food_order, shipment.order)
        self.assertIsNone(shipment.delivery_status)
        self.assertIsNone(shipment.tracking_link)
        self.assertEqual(1, len(cat_food_order.items))
        self.assertEqual(
            "Taste Of The Wild Rocky Mountain Grain-Free Dry Cat Food With Roasted Venison & Smoked Salmon 15Lb",
            cat_food_order.items[0].title)
        self.assertIsNotNone(cat_food_order.items[0].link)
        self.assertEqual(date(2019, 2, 2),
                         cat_food_order.items[0].return_eligible_date)
        self.assertFalse(cat_food_order.full_details)

    def test_get_orders_full_details(self):
        # GIVEN
        year = 2020
        start_index = 40

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year,
                                                      start_index=start_index,
                                                      full_details=True)

        # THEN
        self.assertEqual(10, len(orders))
        paper_towels_order = orders[3]
        self.assertEqual("35.90", paper_towels_order.grand_total)
        self.assertEqual("114-9460922-7737063", paper_towels_order.order_number)
        self.assertIsNotNone(paper_towels_order.order_details_link)
        self.assertEqual(date(2020, 10, 27), paper_towels_order.order_placed_date)
        self.assertEqual("Alex Laird", paper_towels_order.recipient.name)
        self.assertIsNotNone(paper_towels_order.recipient.address)
        self.assertEqual(1, len(paper_towels_order.shipments))
        shipment = paper_towels_order.shipments[0]
        self.assertEqual(str(paper_towels_order.items),
                         str(shipment.items))
        self.assertEqual(str(paper_towels_order),
                         str(shipment.order))
        self.assertIsNone(shipment.tracking_link)
        self.assertIsNone(shipment.delivery_status)
        self.assertEqual(1, len(paper_towels_order.items))
        self.assertEqual("Bounty Quick-Size Paper Towels, White, 16 Family Rolls = 40 Regular Rolls",
                         paper_towels_order.items[0].title)
        self.assertIsNotNone(paper_towels_order.items[0].link)
        self.assertIsNone(paper_towels_order.items[0].return_eligible_date)

        self.assertTrue(paper_towels_order.full_details)
        self.assertEqual("American Express", paper_towels_order.payment_method)
        self.assertEqual(4, len(paper_towels_order.payment_method_last_4))
        self.assertEqual("38.84", paper_towels_order.subtotal)
        self.assertEqual("0.00", paper_towels_order.shipping_total)
        self.assertEqual("-5.83", paper_towels_order.subscription_discount)
        self.assertEqual("33.01", paper_towels_order.total_before_tax)
        self.assertEqual("2.89", paper_towels_order.estimated_tax)
        self.assertEqual(date(2020, 10, 28), paper_towels_order.order_shipped_date)
        self.assertEqual("New", paper_towels_order.items[0].condition)
        self.assertEqual("38.84", paper_towels_order.items[0].price)
        self.assertEqual("Amazon.com Services, Inc",
                         paper_towels_order.items[0].seller.name)
        self.assertIsNone(paper_towels_order.items[0].seller.link)

    def test_get_orders_multiple_items(self):
        # GIVEN
        year = 2020
        start_index = 40

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year,
                                                      start_index=start_index,
                                                      full_details=True)

        # THEN
        multiple_items_order = orders[6]
        self.assertEqual(1, len(multiple_items_order.shipments))
        self.assertEqual(2, len(multiple_items_order.items))
        self.assertEqual(str(multiple_items_order.items),
                         str(multiple_items_order.shipments[0].items))
        self.assertEqual(str(multiple_items_order),
                         str(multiple_items_order.shipments[0].order))
        self.assertEqual(
            "AmazonBasics 36 Pack AAA High-Performance Alkaline Batteries, 10-Year Shelf Life, Easy to Open Value Pack",
            multiple_items_order.items[0].title)
        item = multiple_items_order.items[1]
        self.assertEqual(
            "AmazonBasics 48 Pack AA High-Performance Alkaline Batteries, 10-Year Shelf Life, Easy to Open Value Pack",
            item.title)
        self.assertIsNotNone(item.link)
        self.assertIsNone(item.return_eligible_date)
        self.assertEqual("New", item.condition)
        self.assertEqual("15.49", item.price)
        self.assertEqual("Amazon.com Services, Inc",
                         item.seller.name)
        self.assertIsNone(item.seller.link)

    def test_get_orders_return(self):
        # GIVEN
        year = 2020
        start_index = 50

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year,
                                                      start_index=start_index,
                                                      full_details=True)

        # THEN
        return_order = orders[1]
        self.assertEqual("76.11", return_order.grand_total)
        self.assertEqual("112-2961628-4757846", return_order.order_number)
        self.assertIsNotNone(return_order.order_details_link)
        self.assertEqual(date(2020, 10, 18), return_order.order_placed_date)
        self.assertEqual("Alex Laird", return_order.recipient.name)
        self.assertIsNotNone(return_order.recipient.address)
        self.assertEqual(1, len(return_order.shipments))
        shipment = return_order.shipments[0]
        self.assertEqual(str(return_order.items),
                         str(shipment.items))
        self.assertEqual(str(return_order),
                         str(shipment.order))
        self.assertIsNone(shipment.tracking_link)
        self.assertTrue("Return complete", shipment.delivery_status)
        self.assertEqual(1, len(return_order.items))
        self.assertEqual("Nintendo Switch Pro Controller",
                         return_order.items[0].title)
        self.assertIsNotNone(return_order.items[0].link)
        self.assertIsNone(return_order.items[0].return_eligible_date)

        self.assertTrue(return_order.full_details)
        self.assertEqual("American Express", return_order.payment_method)
        self.assertEqual(4, len(return_order.payment_method_last_4))
        self.assertEqual("69.99", return_order.subtotal)
        self.assertEqual("0.00", return_order.shipping_total)
        self.assertIsNone(return_order.subscription_discount)
        self.assertEqual("69.99", return_order.total_before_tax)
        self.assertEqual("6.12", return_order.estimated_tax)
        self.assertEqual("76.11", return_order.refund_total)
        self.assertEqual(date(2020, 10, 19), return_order.order_shipped_date)
        self.assertTrue(date(2020, 11, 2), return_order.refund_completed_date)
        self.assertEqual("New", return_order.items[0].condition)
        self.assertEqual("69.99", return_order.items[0].price)
        self.assertEqual("Amazon.com Services, Inc",
                         return_order.items[0].seller.name)
        self.assertIsNone(return_order.items[0].seller.link)

    def test_get_orders_multiple_shipments(self):
        # GIVEN
        year = 2023
        start_index = 10

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year,
                                                      start_index=start_index,
                                                      full_details=True)

        # THEN
        multiple_shipments_order = orders[3]
        self.assertEqual(2, len(multiple_shipments_order.shipments))
        self.assertEqual(2, len(multiple_shipments_order.items))
        self.assertEqual(str(multiple_shipments_order.items),
                         str(multiple_shipments_order.shipments[0].items + multiple_shipments_order.shipments[1].items))
        self.assertEqual(str(multiple_shipments_order),
                         str(multiple_shipments_order.shipments[0].order))
        seller = multiple_shipments_order.items[0]
        self.assertEqual("Amazon.com Services, Inc", seller.seller.name)
        self.assertIsNone(seller.seller.link)
        seller = multiple_shipments_order.items[1]
        self.assertEqual("Cadeya", seller.seller.name)
        self.assertIsNotNone(seller.seller.link)

    def test_get_order(self):
        # GIVEN
        order_id = "112-9685975-5907428"

        # WHEN
        order = self.amazon_orders.get_order(order_id)

        # THEN
        self.assertEqual("46.61", order.grand_total)
        self.assertEqual(order_id, order.order_number)
        self.assertIsNone(order.order_details_link)
        self.assertEqual(date(2023, 12, 7), order.order_placed_date)
        self.assertEqual("Alex Laird", order.recipient.name)
        self.assertIsNotNone(order.recipient.address)
        self.assertEqual(2, len(order.shipments))
        shipment = order.shipments[0]
        self.assertEqual(1, len(shipment.items))
        self.assertEqual(str(order.items[0]),
                         str(shipment.items[0]))
        self.assertEqual(str(order),
                         str(shipment.order))
        self.assertIsNotNone(shipment.tracking_link)
        self.assertEqual("Delivered Dec 9, 2023", shipment.delivery_status)
        self.assertEqual(2, len(order.items))
        self.assertEqual(
            "Cadeya Egg Cleaning Brush Silicone, Egg Scrubber for Fresh Eggs, Reusable Cleaning Tools for Egg Washer (Pink)",
            order.items[0].title)
        self.assertIsNotNone(order.items[0].link)
        self.assertEqual(date(2024, 1, 31), order.items[0].return_eligible_date)
        self.assertEqual(
            "Swiffer WetJet Hardwood and Floor Spray Mop Cleaner Starter Kit, Includes: 1 Power Mop, 10 Pads, Cleaning Solution, Batteries",
            order.items[1].title)
        self.assertIsNotNone(order.items[1].link)
        self.assertEqual(date(2024, 1, 31), order.items[1].return_eligible_date)

        self.assertTrue(order.full_details)
        self.assertEqual("American Express", order.payment_method)
        self.assertEqual(4, len(order.payment_method_last_4))
        self.assertEqual("43.23", order.subtotal)
        self.assertEqual("0.00", order.shipping_total)
        self.assertIsNone(order.subscription_discount)
        self.assertEqual("43.23", order.total_before_tax)
        self.assertEqual("3.38", order.estimated_tax)
        self.assertEqual(date(2023, 12, 7), order.order_shipped_date)
        self.assertEqual("New", order.items[0].condition)
        self.assertEqual("14.99", order.items[0].price)
        self.assertEqual("New", order.items[1].condition)
        self.assertEqual("28.24", order.items[1].price)
        seller = order.items[0].seller
        self.assertEqual("Cadeya", seller.name)
        self.assertIsNotNone(seller.link)
        seller = order.items[1].seller
        self.assertEqual("Amazon.com Services, Inc",
                         seller.name)
        self.assertIsNone(seller.link)
