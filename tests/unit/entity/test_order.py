__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os

from bs4 import BeautifulSoup

from amazonorders.entity.order import Order
from tests.unittestcase import UnitTestCase


class TestOrder(UnitTestCase):
    def test_order_currency_stripped(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-currency-stripped-snippet.html"),
                  "r",
                  encoding="utf-8") as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)

        # WHEN
        order = Order(parsed, self.test_config, full_details=True)

        # THEN
        self.assertEqual(order.subtotal, 1111.99)
        self.assertEqual(order.shipping_total, 2222.99)
        self.assertEqual(order.total_before_tax, 3333.99)
        self.assertEqual(order.estimated_tax, 4444.99)
        self.assertIsNone(order.refund_total)
        self.assertIsNone(order.subscription_discount)
        self.assertEqual(order.grand_total, 7777.99)

    def test_order_promotion_applied(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-promotion-applied-snippet.html"),
                  "r",
                  encoding="utf-8") as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)

        # WHEN
        order = Order(parsed, self.test_config, full_details=True)

        # THEN
        self.assertEqual(order.promotion_applied, -0.05)

    def test_order_subscriptions_and_reward_points(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-subscriptions-and-reward-points-snippet.html"),
                  "r",
                  encoding="utf-8") as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)

        # WHEN
        order = Order(parsed, self.test_config, full_details=True)

        # THEN
        self.assertEqual(order.subscription_discount, -0.78)
        self.assertEqual(order.reward_points, -5.98)

    def test_order_coupon_savings(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-details-coupon-savings.html"),
                  "r",
                  encoding="utf-8") as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)

        # WHEN
        order = Order(parsed, self.test_config, full_details=True)

        # THEN
        self.assertEqual(order.coupon_savings, -3.89)

    def test_order_free_shipping(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-details-111-6778632-7354601.html"),
                  "r",
                  encoding="utf-8") as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)

        # WHEN
        order = Order(parsed, self.test_config, full_details=True)

        # THEN
        self.assertEqual(order.free_shipping, -2.99)

    def test_order_coupon_savings_multiple(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-details-coupon-savings-multiple.html"),
                  "r",
                  encoding="utf-8") as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)

        # WHEN
        order = Order(parsed, self.test_config, full_details=True)

        # THEN
        self.assertEqual(order.coupon_savings, -1.29)

    def test_order_amazon_discount(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-amazon-discount-snippet.html"),
                  "r",
                  encoding="utf-8") as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)

        # WHEN
        order = Order(parsed, self.test_config, full_details=True)

        # THEN
        self.assertEqual(order.amazon_discount, -1.62)

    def test_order_gift_wrap(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-details-gift-wrap-snippet.html"),
                  "r",
                  encoding="utf-8") as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)

        # WHEN
        order = Order(parsed, self.test_config, full_details=True)

        # THEN
        self.assertEqual(order.gift_wrap, 3.99)

    def test_order_multibuy_discount(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-multibuy-snippet.html"),
                  "r",
                  encoding="utf-8") as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)

        # WHEN
        order = Order(parsed, self.test_config, full_details=True)

        # THEN
        self.assertEqual(order.multibuy_discount, -3.74)

    def test_order_gift_card(self):
        # GIVEN
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-gift-card-snippet.html"),
                  "r",
                  encoding="utf-8") as f:
            parsed = BeautifulSoup(f.read(), self.test_config.bs4_parser)

        # WHEN
        order = Order(parsed, self.test_config, full_details=True)

        # THEN
        self.assertEqual(order.gift_card, -2.37)
