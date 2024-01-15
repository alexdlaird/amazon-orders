import os

import responses

from amazonorders.exception import AmazonOrdersError
from amazonorders.orders import AmazonOrders

from amazonorders.session import AmazonSession, BASE_URL

from tests.unittestcase import UnitTestCase

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.5"


class TestOrderHistory(UnitTestCase):
    def setUp(self):
        self.amazon_session = AmazonSession("some-username", "some-password")

        self.amazon_orders = AmazonOrders(self.amazon_session)

    def test_get_orders_unauthenticated(self):
        # WHEN
        with self.assertRaises(AmazonOrdersError):
            self.amazon_orders.get_order_history()

    @responses.activate
    def test_get_order_history(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2023
        with open(os.path.join(self.RESOURCES_DIR, "orders.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                "{}/your-orders/orders?timeFilter=year-{}".format(BASE_URL,
                                                                  year),
                body=f.read(),
                status=200,
            )

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year)

        # THEN
        self.assertEqual(3, len(orders))
        self.assertEqual(1, resp1.call_count)
        # TODO: assert on this, but first get a better resource HTML file

    @responses.activate
    def test_get_order_history_paginated(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2023
        with open(os.path.join(self.RESOURCES_DIR, "orders-pagination-1.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                "{}/your-orders/orders?timeFilter=year-{}".format(BASE_URL,
                                                                  year),
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "orders-pagination-2.html"), "r", encoding="utf-8") as f:
            resp2 = responses.add(
                responses.GET,
                "{}/your-orders/orders?_encoding=UTF8&timeFilter=year-{}&startIndex=3&ref_=ppx_yo2ov_dt_b_pagination_1_2".format(
                    BASE_URL, year),
                body=f.read(),
                status=200,
            )

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year)

        # THEN
        self.assertEqual(3, len(orders))
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        # TODO: assert on this, but first get a better resource HTML file

    @responses.activate
    def test_get_order_history_page_full_details(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2023
        start_index = 3
        with open(os.path.join(self.RESOURCES_DIR, "orders-pagination-2.html"), "r", encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                "{}/your-orders/orders?timeFilter=year-{}&startIndex={}".format(BASE_URL,
                                                                                year, start_index),
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "order-details.html"), "r", encoding="utf-8") as f:
            resp2 = responses.add(
                responses.GET,
                "{}/gp/your-account/order-details/ref=ppx_yo_dt_b_order_details_o02?ie=UTF8&orderID=123-4567890-1234561".format(
                    BASE_URL),
                body=f.read(),
                status=200,
            )

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year, start_index=start_index, full_details=True)

        # THEN
        self.assertEqual(1, len(orders))
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        # TODO: assert on this, but first get a better resource HTML file
