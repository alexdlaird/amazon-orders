__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import unittest
from datetime import date


class TestCase(unittest.TestCase):
    def assert_order_112_0399923_3070642(self, order, full_details):
        self.assertEqual("112-0399923-3070642", order.order_number)
        self.assertEqual(34.01, order.grand_total)
        self.assertIsNotNone(order.order_details_link)
        self.assertEqual(date(2018, 12, 21), order.order_placed_date)
        self.assertEqual("Alex Laird", order.recipient.name)
        self.assertIsNotNone(order.recipient.address)
        self.assertEqual(1, len(order.shipments))
        self.assertEqual(str(order.items), str(order.shipments[0].items))
        self.assertIsNone(order.shipments[0].delivery_status)
        self.assertIsNone(order.shipments[0].tracking_link)
        self.assertEqual(1, len(order.items))
        self.assertEqual(
            "Taste Of The Wild Rocky Mountain Grain-Free Dry Cat Food With Roasted Venison & Smoked Salmon 15Lb",
            order.items[0].title)
        self.assertIsNotNone(order.items[0].link)
        self.assertEqual(date(2019, 2, 2),
                         order.items[0].return_eligible_date)
        self.assertIsNotNone(order.items[0].image_link)

        self.assertEqual(order.full_details, full_details)

        if full_details:
            self.assertEqual("American Express", order.payment_method)
            self.assertEqual(4, len(str(order.payment_method_last_4)))
            self.assertEqual(30.99, order.subtotal)
            self.assertEqual(0.00, order.shipping_total)
            self.assertIsNone(order.subscription_discount)
            self.assertEqual(30.99, order.total_before_tax)
            self.assertEqual(3.02, order.estimated_tax)
            self.assertEqual(30.99, order.items[0].price)
            self.assertEqual("Amazon.com Services, Inc",
                             order.items[0].seller.name)
            self.assertIsNone(order.items[0].seller.link)

    def assert_order_114_9460922_7737063(self, order, full_details):
        self.assertEqual("114-9460922-7737063", order.order_number)
        self.assertEqual(35.90, order.grand_total)
        self.assertIsNotNone(order.order_details_link)
        self.assertEqual(date(2020, 10, 27), order.order_placed_date)
        self.assertEqual("Alex Laird", order.recipient.name)
        self.assertIsNotNone(order.recipient.address)
        self.assertEqual(1, len(order.shipments))
        self.assertEqual(str(order.items),
                         str(order.shipments[0].items))
        self.assertIsNone(order.shipments[0].tracking_link)
        self.assertIsNone(order.shipments[0].delivery_status)
        self.assertEqual(1, len(order.items))
        self.assertEqual("Bounty Quick-Size Paper Towels, White, 16 Family Rolls = 40 Regular Rolls",
                         order.items[0].title)
        self.assertIsNotNone(order.items[0].link)
        self.assertIsNotNone(order.items[0].image_link)
        self.assertIsNone(order.items[0].return_eligible_date)

        self.assertEqual(order.full_details, full_details)

        if full_details:
            self.assertEqual("American Express", order.payment_method)
            self.assertEqual(4, len(str(order.payment_method_last_4)))
            self.assertEqual(38.84, order.subtotal)
            self.assertEqual(0.00, order.shipping_total)
            self.assertEqual(-5.83, order.subscription_discount)
            self.assertEqual(33.01, order.total_before_tax)
            self.assertEqual(2.89, order.estimated_tax)
            self.assertEqual(38.84, order.items[0].price)
            self.assertEqual("Amazon.com Services, Inc",
                             order.items[0].seller.name)
            self.assertIsNone(order.items[0].seller.link)

    def assert_order_112_2961628_4757846_return(self, order, full_details):
        self.assertEqual("112-2961628-4757846", order.order_number)
        self.assertEqual(76.11, order.grand_total)
        self.assertIsNotNone(order.order_details_link)
        self.assertEqual(date(2020, 10, 18), order.order_placed_date)
        self.assertEqual("Alex Laird", order.recipient.name)
        self.assertIsNotNone(order.recipient.address)
        self.assertEqual(1, len(order.shipments))
        self.assertEqual(str(order.items),
                         str(order.shipments[0].items))
        self.assertIsNone(order.shipments[0].tracking_link)
        self.assertTrue("Return complete", order.shipments[0].delivery_status)
        self.assertEqual(1, len(order.items))
        self.assertEqual("Nintendo Switch Pro Controller",
                         order.items[0].title)
        self.assertIsNotNone(order.items[0].link)
        self.assertIsNotNone(order.items[0].image_link)
        self.assertIsNone(order.items[0].return_eligible_date)

        self.assertEqual(order.full_details, full_details)

        if full_details:
            self.assertEqual("American Express", order.payment_method)
            self.assertEqual(4, len(str(order.payment_method_last_4)))
            self.assertEqual(69.99, order.subtotal)
            self.assertEqual(0.00, order.shipping_total)
            self.assertIsNone(order.subscription_discount)
            self.assertEqual(69.99, order.total_before_tax)
            self.assertEqual(6.12, order.estimated_tax)
            self.assertEqual(76.11, order.refund_total)
            self.assertEqual(69.99, order.items[0].price)
            self.assertEqual("Amazon.com Services, Inc",
                             order.items[0].seller.name)
            self.assertIsNone(order.items[0].seller.link)

    def assert_order_112_8888666_5244209_quantity(self, order):
        self.assertEqual("112-8888666-5244209", order.order_number)
        self.assertEqual(2, order.items[0].quantity)

    def assert_order_112_9685975_5907428_multiple_items_shipments_sellers(self, order, full_details):
        self.assertEqual("112-9685975-5907428", order.order_number)
        self.assertEqual(46.61, order.grand_total)
        self.assertIsNotNone(order.order_details_link)
        self.assertEqual(date(2023, 12, 7), order.order_placed_date)
        self.assertEqual("Alex Laird", order.recipient.name)
        self.assertIsNotNone(order.recipient.address)
        self.assertEqual(2, len(order.shipments))
        found_cadeya = False
        found_amazon = False
        for shipment in order.shipments:
            self.assertEqual(1, len(shipment.items))
            order_item = next(filter(lambda i: i.title == shipment.items[0].title, order.items))
            self.assertEqual(str(order_item),
                             str(shipment.items[0]))
            if "TestIntegration" not in self.__class__.__name__:
                self.assertIsNotNone(shipment.tracking_link)
            if "Cadeya" in shipment.items[0].title:
                found_cadeya = True
                self.assertEqual("Delivered Dec 9, 2023", shipment.delivery_status)
            else:
                found_amazon = True
                self.assertEqual("Delivered Dec 8, 2023", shipment.delivery_status)
        self.assertTrue(found_cadeya)
        self.assertTrue(found_amazon)
        self.assertEqual(str(order.items),
                         str(order.shipments[1].items + order.shipments[0].items))
        self.assertEqual(2, len(order.items))
        found_cadeya = False
        found_amazon = False
        for order_item in order.items:
            if "Cadeya" in order_item.title:
                found_cadeya = True
                self.assertEqual(
                    "Cadeya Egg Cleaning Brush Silicone, Egg Scrubber for Fresh Eggs, Reusable Cleaning Tools "
                    "for Egg Washer (Pink)",
                    order_item.title)
                self.assertIsNotNone(order_item.link)
                self.assertEqual(date(2024, 1, 31), order_item.return_eligible_date)
            else:
                found_amazon = True
                self.assertEqual(
                    "Swiffer WetJet Hardwood and Floor Spray Mop Cleaner Starter Kit, Includes: 1 Power Mop, "
                    "10 Pads, Cleaning Solution, Batteries",
                    order_item.title)
                self.assertIsNotNone(order_item.link)
                self.assertEqual(date(2024, 1, 31), order_item.return_eligible_date)
        self.assertTrue(found_cadeya)
        self.assertTrue(found_amazon)

        self.assertEqual(order.full_details, full_details)

        if full_details:
            self.assertEqual("American Express", order.payment_method)
            self.assertEqual(4, len(str(order.payment_method_last_4)))
            self.assertEqual(43.23, order.subtotal)
            self.assertEqual(0.00, order.shipping_total)
            self.assertIsNone(order.subscription_discount)
            self.assertEqual(43.23, order.total_before_tax)
            self.assertEqual(3.38, order.estimated_tax)
            self.assertEqual(14.99, order.items[0].price)
            self.assertEqual(28.24, order.items[1].price)
            found_cadeya = False
            found_amazon = False
            for order_item in order.items:
                seller = order_item.seller
                if "Cadeya" in seller.name:
                    found_cadeya = True
                    self.assertEqual("Cadeya", seller.name)
                    self.assertIsNotNone(seller.link)
                else:
                    found_amazon = True
                    self.assertEqual("Amazon.com Services, Inc",
                                     seller.name)
                    self.assertIsNone(seller.link)
            self.assertTrue(found_cadeya)
            self.assertTrue(found_amazon)

    def assert_order_112_6539663_7312263_multiple_items_shipments_sellers(self, order, full_details):
        self.assertEqual("112-6539663-7312263", order.order_number)
        self.assertEqual(45.25, order.grand_total)
        self.assertIsNotNone(order.order_details_link)
        self.assertEqual(date(2024, 5, 12), order.order_placed_date)
        self.assertEqual("Alex Laird", order.recipient.name)
        self.assertIsNotNone(order.recipient.address)
        self.assertEqual(2, len(order.shipments))
        found_kimoe = False
        found_amazon = False
        for shipment in order.shipments:
            self.assertEqual(1, len(shipment.items))
            order_item = next(filter(lambda i: i.title == shipment.items[0].title, order.items))
            self.assertEqual(str(order_item),
                             str(shipment.items[0]))
            if "TestIntegration" not in self.__class__.__name__:
                self.assertIsNotNone(shipment.tracking_link)
            if "kimoe" in shipment.items[0].title:
                found_kimoe = True
                self.assertIn("Delivered May 18", shipment.delivery_status)
            else:
                found_amazon = True
                self.assertIn("Delivered May 13", shipment.delivery_status)
        self.assertTrue(found_kimoe)
        self.assertTrue(found_amazon)
        self.assertEqual(str(order.items.sort()),
                         str((order.shipments[0].items + order.shipments[1].items).sort()))
        self.assertEqual(2, len(order.items))
        found_kimoe = False
        found_amazon = False
        for order_item in order.items:
            if "kimoe" in order_item.title:
                found_kimoe = True
                self.assertEqual(
                    "kimoe 5LB 100% Natural Non-GMO Dried mealworms-High-Protein for Birds, Chicken，Ducks",
                    order_item.title)
                self.assertIsNotNone(order_item.link)
                self.assertIsNone(order_item.return_eligible_date)
            else:
                found_amazon = True
                self.assertEqual(
                    "Go Green Power Inc. GG-13725BK 16/3 Heavy Duty Extension Cord, Outdoor Extension Cord, "
                    "Black, 25 ft",
                    order_item.title)
                self.assertIsNotNone(order_item.link)
                self.assertEqual(date(2024, 6, 12), order_item.return_eligible_date)
        self.assertTrue(found_kimoe)
        self.assertTrue(found_amazon)

        self.assertEqual(order.full_details, full_details)

        if full_details:
            self.assertEqual("American Express", order.payment_method)
            self.assertEqual(4, len(str(order.payment_method_last_4)))
            self.assertEqual(42.29, order.subtotal)
            self.assertEqual(0.00, order.shipping_total)
            self.assertIsNone(order.subscription_discount)
            self.assertEqual(42.29, order.total_before_tax)
            self.assertEqual(2.96, order.estimated_tax)
            self.assertEqual(12.30, order.items[0].price)
            self.assertEqual(29.99, order.items[1].price)
            found_kimoe = False
            found_amazon = False
            for order_item in order.items:
                seller = order_item.seller
                if "kimoe" in seller.name:
                    found_kimoe = True
                    self.assertEqual("kimoe store", seller.name)
                    self.assertIsNotNone(seller.link)
                else:
                    found_amazon = True
                    self.assertEqual("Amazon.com Services, Inc",
                                     seller.name)
                    self.assertIsNone(seller.link)
            self.assertTrue(found_kimoe)
            self.assertTrue(found_amazon)

    def assert_order_113_1625648_3437067_multiple_items(self, order, full_details):
        self.assertEqual("113-1625648-3437067", order.order_number)
        self.assertEqual(28.80, order.grand_total)
        self.assertEqual(1, len(order.shipments))
        self.assertEqual(2, len(order.items))
        self.assertEqual(str(order.items),
                         str(order.shipments[0].items))
        found_aaa = False
        found_aa = False
        for item in order.items:
            if "AAA" in item.title:
                found_aaa = True
                self.assertEqual(
                    "AmazonBasics 36 Pack AAA High-Performance Alkaline Batteries, 10-Year Shelf Life, Easy to "
                    "Open Value Pack",
                    item.title)
                self.assertIsNotNone(item.link)
                # TODO: this actually is shown on the page, it's just collapsed, find a way to parse it
                self.assertIsNone(item.return_eligible_date)
            else:
                found_aa = True
                self.assertEqual(
                    "AmazonBasics 48 Pack AA High-Performance Alkaline Batteries, 10-Year Shelf Life, Easy to "
                    "Open Value Pack",
                    item.title)
                self.assertIsNotNone(item.link)
                # TODO: this actually is shown on the page, it's just collapsed, find a way to parse it
                self.assertIsNone(item.return_eligible_date)
        self.assertTrue(found_aaa)
        self.assertTrue(found_aa)

        self.assertEqual(order.full_details, full_details)

        if full_details:
            self.assertEqual("American Express", order.payment_method)
            self.assertEqual(4, len(str(order.payment_method_last_4)))
            self.assertEqual(26.48, order.subtotal)
            self.assertEqual(0.00, order.shipping_total)
            self.assertIsNone(order.subscription_discount)
            self.assertEqual(26.48, order.total_before_tax)
            self.assertEqual(2.32, order.estimated_tax)
            found_aa = False
            found_aaa = False
            for item in order.items:
                if "AAA" in item.title:
                    found_aa = True
                    self.assertEqual(10.99, item.price)
                    self.assertEqual("Amazon.com Services, Inc",
                                     item.seller.name)
                    self.assertIsNone(item.seller.link)
                else:
                    found_aaa = True
                    self.assertEqual(15.49, item.price)
                    self.assertEqual("Amazon.com Services, Inc",
                                     item.seller.name)
                    self.assertIsNone(item.seller.link)
            self.assertTrue(found_aa)
            self.assertTrue(found_aaa)

    def assert_order_112_5939971_8962610_data_component(self, order, full_details=False):
        self.assertEqual("112-5939971-8962610", order.order_number)
        self.assertEqual(28.50, order.grand_total)
        self.assertIsNotNone(order.order_details_link)
        self.assertEqual(date(2024, 11, 1), order.order_placed_date)
        self.assertEqual("Alex Laird", order.recipient.name)
        self.assertIn("555 My Road", order.recipient.address)
        self.assertEqual(1, len(order.shipments))
        self.assertEqual(str(order.items),
                         str(order.shipments[0].items))
        self.assertIsNotNone(order.shipments[0].tracking_link)
        self.assertEqual("Delivered November 2", order.shipments[0].delivery_status)
        self.assertEqual(1, len(order.items))
        self.assertEqual("2 Set Replacement Parts Roller Brushes Compatible for iRobot Roomba E I and J Series, "
                         "Brush Replacement for iRobot Roomba i3 i3+ i6 i6+ i7 i7+ i8 i8+Plus E5 E6 E7 j7 j7+ evo "
                         "Vacuum Cleaner Accessories",
                         order.items[0].title)
        self.assertEqual(2, order.items[0].quantity)
        self.assertIsNotNone(order.items[0].link)
        self.assertIsNotNone(order.items[0].image_link)

        self.assertEqual(order.full_details, full_details)

        if full_details:
            self.assertEqual(date(2025, 1, 31), order.items[0].return_eligible_date)
            self.assertEqual("American Express", order.payment_method)
            self.assertEqual(1234, order.payment_method_last_4)
            self.assertEqual(27.98, order.subtotal)
            self.assertEqual(0.00, order.shipping_total)
            self.assertEqual(26.58, order.total_before_tax)
            self.assertEqual(1.92, order.estimated_tax)
            self.assertEqual(13.99, order.items[0].price)
            self.assertEqual("xianbaikeshang",
                             order.items[0].seller.name)
            self.assertIsNotNone(order.items[0].seller.link)

    def assert_order_112_4482432_2955442_gift_card(self, order, full_details=False):
        self.assertEqual("112-4482432-2955442", order.order_number)
        self.assertEqual(10.00, order.grand_total)
        self.assertIsNotNone(order.order_details_link)
        self.assertEqual(date(2024, 10, 30), order.order_placed_date)
        self.assertIsNone(order.recipient)
        self.assertEqual(0, len(order.shipments))
        self.assertEqual(1, len(order.items))
        self.assertEqual("Amazon eGift Card - Amazon Logo (Animated)",
                         order.items[0].title)
        self.assertIsNotNone(order.items[0].link)
        self.assertIsNotNone(order.items[0].image_link)

        self.assertEqual(order.full_details, full_details)

        if full_details:
            self.assertEqual("American Express", order.payment_method)
            self.assertEqual(1234, order.payment_method_last_4)
            self.assertEqual(10.00, order.subtotal)
            self.assertEqual(10.00, order.total_before_tax)
            self.assertEqual(0.00, order.estimated_tax)

    def assert_order_112_9087159_1657009_digital_order_legacy(self, order, full_details=False):
        if full_details:
            self.assertEqual(order.order_number, "D01-8711688-7680252")
        else:
            self.assertEqual(order.order_number, "112-9087159-1657009")
        self.assertEqual(10.00, order.grand_total)
        self.assertIsNotNone(order.order_details_link)
        self.assertEqual(date(2024, 10, 30), order.order_placed_date)
        self.assertEqual(0, len(order.shipments))
        self.assertEqual(1, len(order.items))
        self.assertEqual("$10 -PlayStation Store Gift Card [Digital Code]",
                         order.items[0].title)
        self.assertIsNotNone(order.items[0].link)
        self.assertIsNotNone(order.items[0].image_link)

        self.assertEqual(order.full_details, full_details)

        # We cannot parse full details for digital orders, so nothing to assert

    def assert_order_114_8722141_6545058_data_component_subscription(self, order, full_details=False):
        self.assertEqual("114-8722141-6545058", order.order_number)
        self.assertEqual(44.46, order.grand_total)
        self.assertIsNotNone(order.order_details_link)
        self.assertEqual(date(2024, 10, 23), order.order_placed_date)
        self.assertEqual("Alex Laird", order.recipient.name)
        self.assertIn("555 My Road", order.recipient.address)
        self.assertEqual(1, len(order.shipments))
        self.assertEqual(str(order.items),
                         str(order.shipments[0].items))
        self.assertIsNotNone(order.shipments[0].tracking_link)
        self.assertEqual("Delivered October 26", order.shipments[0].delivery_status)
        self.assertEqual(1, len(order.items))
        self.assertEqual("Bounty Paper Towels Quick Size, White, 16 Family Rolls = 40 Regular Rolls",
                         order.items[0].title)
        self.assertIsNotNone(order.items[0].link)
        self.assertIsNotNone(order.items[0].image_link)

        self.assertEqual(order.full_details, full_details)

        if full_details:
            self.assertEqual(date(2024, 11, 25), order.items[0].return_eligible_date)
            self.assertEqual("American Express", order.payment_method)
            self.assertEqual(1234, order.payment_method_last_4)
            self.assertEqual(43.49, order.subtotal)
            self.assertEqual(0.00, order.shipping_total)
            self.assertEqual(-2.17, order.subscription_discount)
            self.assertEqual(41.32, order.total_before_tax)
            self.assertEqual(3.14, order.estimated_tax)
            self.assertEqual(43.49, order.items[0].price)
            self.assertEqual("Amazon.com",
                             order.items[0].seller.name)
            self.assertIsNone(order.items[0].seller.link)

    def assert_order_111_6778632_7354601_data_component_subscription(self, order, full_details=False):
        self.assertEqual("111-6778632-7354601", order.order_number)
        self.assertEqual(60.88, order.grand_total)
        self.assertIsNotNone(order.order_details_link)
        self.assertEqual(date(2024, 9, 8), order.order_placed_date)
        self.assertEqual("Name1 & Name2", order.recipient.name)
        self.assertIn("Address2", order.recipient.address)
        self.assertEqual(2, len(order.shipments))
        self.assertEqual(str(order.items.sort()),
                         str((order.shipments[0].items + order.shipments[1].items).sort()))
        self.assertEqual(3, len(order.shipments[0].items))
        self.assertEqual(1, len(order.shipments[1].items))
        self.assertEqual("Delivered September 9", order.shipments[0].delivery_status)
        self.assertEqual("Delivered September 9", order.shipments[1].delivery_status)
        self.assertEqual(4, len(order.items))
        self.assertEqual(
            "Dxhycc Satin Pirate Sash Pirate Medieval Renaissance Large Sash Halloween Costume Waist "
            "Sash Belt, Red",
            order.items[0].title)
        self.assertEqual("Ziploc Paper Sandwich and Snack Bags, Recyclable & Sealable with Fun Designs, "
                         "150 Total Bags",
                         order.items[3].title)
        self.assertIsNotNone(order.items[0].link)
        self.assertIsNotNone(order.items[0].image_link)
        self.assertIsNotNone(order.items[3].link)
        self.assertIsNotNone(order.items[3].image_link)

        self.assertEqual(order.full_details, full_details)

        if full_details:
            self.assertEqual("Prime Visa", order.payment_method)
            self.assertEqual(1111, order.payment_method_last_4)
            self.assertEqual(57.69, order.subtotal)
            self.assertEqual(2.99, order.shipping_total)
            self.assertEqual(57.69, order.total_before_tax)
            self.assertEqual(3.19, order.estimated_tax)
            self.assertEqual(date(2024, 10, 9), order.items[0].return_eligible_date)
            self.assertEqual(date(2024, 10, 9), order.items[1].return_eligible_date)
            self.assertEqual(date(2024, 10, 9), order.items[2].return_eligible_date)
            self.assertEqual(date(2024, 10, 9), order.items[3].return_eligible_date)
            self.assertEqual(7.49, order.items[0].price)
            self.assertEqual(18.95, order.items[1].price)
            self.assertEqual(9.98, order.items[2].price)
            self.assertEqual(21.27, order.items[3].price)

    def assert_populated_generic(self, order, full_details):
        self.assertIsNotNone(order.order_number)
        self.assertIsNotNone(order.grand_total)
        self.assertIsNotNone(order.order_details_link)
        self.assertIsNotNone(order.order_placed_date)
        if order.recipient:
            self.assertIsNotNone(order.recipient.name)
            self.assertIsNotNone(order.recipient.address)
            self.assertGreaterEqual(len(order.shipments), 1)
            shipment_items = []
            for shipment in order.shipments:
                shipment_items += shipment.items
                self.assertGreaterEqual(len(shipment.items), 1)
                self.assertIsNotNone(shipment.delivery_status)
            self.assertEqual(str(order.items.sort()), str(shipment_items.sort()))
        self.assertGreaterEqual(len(order.items), 1)
        for item in order.items:
            self.assertIsNotNone(item.title)
            self.assertIsNotNone(item.link)

        self.assertEqual(order.full_details, full_details)

        if full_details:
            self.assertIsNotNone(order.payment_method)
            self.assertEqual(4, len(str(order.payment_method_last_4)))
            self.assertIsNotNone(order.subtotal)
            if order.recipient:
                self.assertIsNotNone(order.shipping_total)
            self.assertIsNotNone(order.total_before_tax)
            self.assertIsNotNone(order.estimated_tax)
            if order.recipient:
                for item in order.items:
                    self.assertIsNotNone(item.price)
                    self.assertIsNotNone(item.seller.name)
