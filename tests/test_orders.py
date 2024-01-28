import os

import responses

from amazonorders.constants import ORDER_HISTORY_URL, ORDER_DETAILS_URL
from amazonorders.exception import AmazonOrdersError
from amazonorders.orders import AmazonOrders
from amazonorders.session import AmazonSession
from tests.unittestcase import UnitTestCase

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.7"


class TestOrders(UnitTestCase):
    def setUp(self):
        super().setUp()

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
        year = 2018
        start_index = 0
        resp1 = self.given_order_history_landing_exists()
        resp2 = self.given_order_history_exists(year, start_index)

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year, start_index=start_index)

        # THEN
        # Giving start_index=0 means we only got the first page, so just 10 results
        self.assertEqual(10, len(orders))
        self.assert_order_112_0399923_3070642(orders[3], False)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)

    @responses.activate
    def test_get_order_history_paginated(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2010
        resp1 = self.given_order_history_landing_exists()
        resp2 = self.given_order_history_exists(year, 0)
        with open(os.path.join(self.RESOURCES_DIR, "order-history-{}-10.html".format(year)), "r",
                  encoding="utf-8") as f:
            resp3 = responses.add(
                responses.GET,
                "{}?timeFilter=year-2010&startIndex=10&ref_=ppx_yo2ov_dt_b_pagination_1_2".format(
                    ORDER_HISTORY_URL, year),
                body=f.read(),
                status=200,
            )

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year)

        # THEN
        self.assertEqual(12, len(orders))
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(1, resp3.call_count)

    @responses.activate
    def test_get_order_history_full_details(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2020
        start_index = 40
        resp1 = self.given_order_history_landing_exists()
        resp2 = self.given_order_history_exists(year, start_index)
        resp3 = self.given_any_order_details_exists("order-details-114-9460922-7737063.html")

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year, start_index=start_index, full_details=True)

        # THEN
        self.assertEqual(10, len(orders))
        self.assert_order_114_9460922_7737063(orders[3], True)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(10, resp3.call_count)

    @responses.activate
    def test_get_order_history_multiple_items(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2020
        start_index = 40
        resp1 = self.given_order_history_landing_exists()
        resp2 = self.given_order_history_exists(year, start_index)
        resp3 = self.given_any_order_details_exists("order-details-113-1625648-3437067.html")

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year,
                                                      start_index=start_index,
                                                      full_details=True)

        # THEN
        self.assertEqual(10, len(orders))
        self.assert_order_113_1625648_3437067_multiple_items(orders[6], True)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(10, resp3.call_count)

    @responses.activate
    def test_get_order_history_return(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2020
        start_index = 50
        resp1 = self.given_order_history_landing_exists()
        resp2 = self.given_order_history_exists(year, start_index)
        resp3 = self.given_any_order_details_exists("order-details-112-2961628-4757846.html")

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year, start_index=start_index, full_details=True)

        # THEN
        self.assertEqual(10, len(orders))
        self.assert_order_112_2961628_4757846_return(orders[1], True)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(10, resp3.call_count)

    @responses.activate
    def test_get_order_history_quantity(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2020
        start_index = 50
        resp1 = self.given_order_history_landing_exists()
        resp2 = self.given_order_history_exists(year, start_index)

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year, start_index=start_index)

        # THEN
        self.assertEqual(10, len(orders))
        self.assert_order_112_8888666_5244209_quantity(orders[7])
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)

    @responses.activate
    def test_get_order_history_multiple_items_shipments_sellers(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2023
        start_index = 10
        resp1 = self.given_order_history_landing_exists()
        resp2 = self.given_order_history_exists(year, start_index)
        resp3 = self.given_any_order_details_exists("order-details-112-9685975-5907428.html")

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year, start_index=start_index, full_details=True)

        # THEN
        self.assertEqual(10, len(orders))
        self.assert_order_112_9685975_5907428_multiple_items_shipments_sellers(orders[3], True)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(10, resp3.call_count)

    @responses.activate
    def test_get_order(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        order_id = "112-9685975-5907428"
        with open(os.path.join(self.RESOURCES_DIR, "order-details-{}.html".format(order_id)), "r",
                  encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                "{}?orderID={}".format(ORDER_DETAILS_URL, order_id),
                body=f.read(),
                status=200,
            )

        # WHEN
        order = self.amazon_orders.get_order(order_id)

        # THEN
        self.assert_order_112_9685975_5907428_multiple_items_shipments_sellers(order, True)
        self.assertEqual(1, resp1.call_count)
