__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
import unittest
from datetime import date

import responses

from amazonorders.exception import AmazonOrdersError, AmazonOrdersNotFoundError, AmazonOrdersAuthRedirectError
from amazonorders.orders import AmazonOrders
from amazonorders.session import AmazonSession
from tests.unittestcase import UnitTestCase


class TestOrders(UnitTestCase):
    temp_order_history_file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "output",
                                                "temp-order-history.html")
    temp_order_details_file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "output",
                                                "temp-order-details.html")

    def setUp(self):
        super().setUp()

        self.amazon_session = AmazonSession("some-username@gmail.com",
                                            "some-password",
                                            config=self.test_config)

        self.amazon_orders = AmazonOrders(self.amazon_session)

    def test_get_order_unauthenticated(self):
        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_orders.get_order("1234-fake-id")

        self.assertEqual("Call AmazonSession.login() to authenticate first.", str(cm.exception))

    def test_get_order_history_unauthenticated(self):
        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_orders.get_order_history()

        self.assertEqual("Call AmazonSession.login() to authenticate first.", str(cm.exception))

    @responses.activate
    def test_get_order_session_expires(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        resp = self.given_authenticated_url_redirects_to_login()
        self.given_login_responses_success()

        # WHEN
        with self.assertRaises(AmazonOrdersAuthRedirectError) as cm:
            self.amazon_orders.get_order("1234-fake-id")

        self.assertIn("Amazon redirected to login.", str(cm.exception))
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertEqual(2, resp.call_count)

    @responses.activate
    def test_get_order_history_session_expires(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        resp = self.given_authenticated_url_redirects_to_login()
        self.given_login_responses_success()

        # WHEN
        with self.assertRaises(AmazonOrdersAuthRedirectError) as cm:
            self.amazon_orders.get_order_history()

        self.assertIn("Amazon redirected to login.", str(cm.exception))
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertEqual(2, resp.call_count)

    @responses.activate
    def test_get_order_history(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2018
        resp = self.given_order_history_exists(year)

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year, keep_paging=False)

        # THEN
        self.assertEqual(10, len(orders))
        self.assert_order_112_0399923_3070642(orders[3], False)
        self.assertEqual(3, orders[3].index)
        self.assert_orders_list_index(orders)
        self.assertEqual(1, resp.call_count)

    @responses.activate
    def test_get_order_history_errors_with_meta(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2020
        start_index = 40
        resp = responses.add(
            responses.GET,
            f"{self.test_config.constants.ORDER_HISTORY_URL}?timeFilter=year-{year}&startIndex={start_index}",
            status=503,
        )

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_orders.get_order_history(year=year,
                                                 start_index=start_index)

        # THEN
        self.assertEqual(1, resp.call_count)
        self.assertEqual(cm.exception.meta["index"], start_index)

    @responses.activate
    def test_get_order_history_invalid_page(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2020
        start_index = 40
        with open(os.path.join(self.RESOURCES_DIR, "500.html"), "r",
                  encoding="utf-8") as f:
            resp = responses.add(
                responses.GET,
                f"{self.test_config.constants.ORDER_HISTORY_URL}?timeFilter=year-{year}&startIndex={start_index}",
                body=f.read(),
                status=200,
            )

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_orders.get_order_history(year=year,
                                                 start_index=start_index)

        # THEN
        self.assertEqual(1, resp.call_count)
        self.assertIn("Could not parse Order history.", str(cm.exception))

    @responses.activate
    def test_get_order_history_2024_data_component(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2024
        resp = self.given_order_history_exists(year)

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year, keep_paging=False)

        # THEN
        self.assertEqual(10, len(orders))
        # Regular order with new `data-component` fields
        self.assert_order_112_5939971_8962610_data_component(orders[0], False)
        # Gift card order
        self.assert_order_112_4482432_2955442_gift_card(orders[2], False)
        # Digital order (legacy)
        self.assert_order_112_9087159_1657009_digital_order_legacy(orders[3], False)
        # Subscription order
        self.assert_order_114_8722141_6545058_data_component_subscription(orders[6], False)
        self.assertEqual(1, resp.call_count)

    @responses.activate
    def test_get_order_history_2025_gift_card(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2024
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-egift.html"), "r",
                  encoding="utf-8") as f:
            resp = responses.add(
                responses.GET,
                self.test_config.constants.ORDER_HISTORY_URL,
                body=f.read(),
                status=200,
            )

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year, keep_paging=False)

        # THEN
        self.assertEqual(10, len(orders))
        self.assertEqual(1, resp.call_count)
        order = orders[5]
        self.assertEqual("112-8022032-9113020", order.order_number)
        self.assertEqual(150.00, order.grand_total)
        self.assertIsNotNone(order.order_details_link)
        self.assertEqual(date(2024, 10, 28), order.order_placed_date)
        self.assertEqual(1, len(order.items))
        self.assertEqual("Amazon eGift Card - Birthday Candles (Animated)",
                         order.items[0].title)
        self.assertIsNotNone(order.items[0].link)
        self.assertIsNotNone(order.items[0].image_link)

    @responses.activate
    def test_get_order_history_2025_canceled(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2025
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-canceled-order.html"), "r",
                  encoding="utf-8") as f:
            resp = responses.add(
                responses.GET,
                self.test_config.constants.ORDER_HISTORY_URL,
                body=f.read(),
                status=200,
            )

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year, keep_paging=False)

        # THEN
        self.assertEqual(10, len(orders))
        self.assertEqual(1, resp.call_count)
        order = orders[0]
        self.assertEqual("111-9642662-1037012", order.order_number)
        self.assertIsNone(order.grand_total)
        self.assertIsNotNone(order.order_details_link)
        self.assertEqual(date(2025, 7, 15), order.order_placed_date)
        self.assertEqual(1, len(order.items))
        self.assertEqual("CarlinKit 5.0 Wireless CarPlay/Android Auto Adapter USB for Factory Wired CarPlay Cars "
                         "(Model Year: 2015 to 2025), Wireless CarPlay/Android Auto Dongle Convert Wired to Wireless,"
                         "Fit In-Dash Navigation",
                         order.items[0].title)
        self.assertIsNotNone(order.items[0].link)
        self.assertIsNotNone(order.items[0].image_link)

    @responses.activate
    def test_get_order_history_2025_amazon_store(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2024
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-amazon-store.html"), "r",
                  encoding="utf-8") as f:
            resp = responses.add(
                responses.GET,
                self.test_config.constants.ORDER_HISTORY_URL,
                body=f.read(),
                status=200,
            )

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year, keep_paging=False)

        # THEN
        self.assertEqual(10, len(orders))
        self.assertEqual(1, resp.call_count)
        order = orders[9]
        self.assertEqual("113-9085096-9353021", order.order_number)
        self.assertIsNone(order.grand_total)  # Amazon Store orders are unsupported order types
        self.assertIsNotNone(order.order_details_link)
        self.assertEqual(date(2025, 2, 28), order.order_placed_date)
        self.assertEqual(0, len(order.items))

    @responses.activate
    def test_get_order_history_paginated(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2010
        resp1 = self.given_order_history_exists(year, start_index=0)
        with open(os.path.join(self.RESOURCES_DIR, "orders", f"order-history-{year}-10.html"), "r",
                  encoding="utf-8") as f:
            resp2 = responses.add(
                responses.GET,
                f"{self.test_config.constants.ORDER_HISTORY_URL}?timeFilter=year-{year}"
                "&startIndex=10&ref_=ppx_yo2ov_dt_b_pagination_1_2",
                body=f.read(),
                status=200,
            )

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year)

        # THEN
        self.assertEqual(12, len(orders))
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)

    @responses.activate
    def test_get_order_history_fresh(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2024
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-fresh.html"), "r",
                  encoding="utf-8") as f:
            resp = responses.add(
                responses.GET,
                self.test_config.constants.ORDER_HISTORY_URL,
                body=f.read(),
                status=200,
            )

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year, keep_paging=False)

        # THEN
        self.assertEqual(10, len(orders))
        self.assertEqual(1, resp.call_count)
        order = orders[4]
        self.assertEqual("111-2072777-8279433", order.order_number)
        self.assertEqual(4, order.index)
        self.assertIsNone(order.grand_total)  # Amazon Fresh orders are unsupported order types
        self.assertIsNotNone(order.order_details_link)
        self.assertEqual(date(2025, 1, 3), order.order_placed_date)
        self.assertEqual(0, len(order.items))

    @responses.activate
    def test_get_order_history_wholefoods(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2024
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-wholefoods.html"), "r",
                  encoding="utf-8") as f:
            resp = responses.add(
                responses.GET,
                self.test_config.constants.ORDER_HISTORY_URL,
                body=f.read(),
                status=200,
            )

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year, keep_paging=False)

        # THEN
        self.assertEqual(10, len(orders))
        self.assertEqual(1, resp.call_count)
        order = orders[7]
        self.assertEqual("113-6307059-7336242", order.order_number)
        self.assertIsNone(order.grand_total)  # Whole Foods orders are unsupported order types
        self.assertIsNotNone(order.order_details_link)
        self.assertEqual(date(2024, 12, 12), order.order_placed_date)
        self.assertEqual(0, len(order.items))

    @responses.activate
    def test_get_order_history_full_details_wholefood_skip(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2024
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-wholefoods-catering.html"), "r",
                  encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.ORDER_HISTORY_URL,
                body=f.read(),
                status=200,
            )
        resp2 = self.given_any_order_details_exists("order-details-114-9460922-7737063.html")

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year, keep_paging=False, full_details=True)

        # THEN
        self.assertEqual(10, len(orders))
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(6, resp2.call_count)

    @responses.activate
    def test_get_order_history_full_details(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2020
        start_index = 40
        resp1 = self.given_order_history_exists(year, start_index)
        resp2 = self.given_any_order_details_exists("order-details-114-9460922-7737063.html")

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year,
                                                      start_index=start_index,
                                                      keep_paging=False,
                                                      full_details=True)

        # THEN
        self.assertEqual(10, len(orders))
        self.assert_order_114_9460922_7737063(orders[3], True)
        self.assertEqual(43, orders[3].index)
        self.assert_orders_list_index(orders)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(10, resp2.call_count)

    @responses.activate
    def test_get_order_history_multiple_items(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2020
        start_index = 40
        resp1 = self.given_order_history_exists(year, start_index)
        resp2 = self.given_any_order_details_exists("order-details-113-1625648-3437067.html")

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year,
                                                      start_index=start_index,
                                                      keep_paging=False,
                                                      full_details=True)

        # THEN
        self.assertEqual(10, len(orders))
        self.assert_order_113_1625648_3437067_multiple_items(orders[6], True)
        self.assertEqual(43, orders[3].index)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(10, resp2.call_count)

    @responses.activate
    def test_get_order_history_return(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2020
        start_index = 50
        resp1 = self.given_order_history_exists(year, start_index)
        resp2 = self.given_any_order_details_exists("order-details-112-2961628-4757846.html")

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year,
                                                      start_index=start_index,
                                                      keep_paging=False,
                                                      full_details=True)

        # THEN
        self.assertEqual(10, len(orders))
        self.assert_order_112_2961628_4757846_return(orders[1], True)
        self.assertEqual(53, orders[3].index)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(10, resp2.call_count)

    @responses.activate
    def test_get_order_history_quantity(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2020
        start_index = 50
        resp = self.given_order_history_exists(year, start_index)

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year,
                                                      start_index=start_index,
                                                      keep_paging=False)

        # THEN
        self.assertEqual(10, len(orders))
        self.assert_order_112_8888666_5244209_quantity(orders[7])
        self.assertEqual(53, orders[3].index)
        self.assertEqual(1, resp.call_count)

    @responses.activate
    def test_get_order_history_multiple_items_shipments_sellers(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2023
        start_index = 10
        resp1 = self.given_order_history_exists(year, start_index)
        resp2 = self.given_any_order_details_exists("order-details-112-9685975-5907428.html")

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year,
                                                      start_index=start_index,
                                                      keep_paging=False,
                                                      full_details=True)

        # THEN
        self.assertEqual(10, len(orders))
        self.assert_order_112_9685975_5907428_multiple_items_shipments_sellers(orders[3], True)
        self.assertEqual(13, orders[3].index)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(10, resp2.call_count)

    @responses.activate
    def test_get_order(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        order_id = "112-9685975-5907428"
        with open(os.path.join(self.RESOURCES_DIR, "orders", f"order-details-{order_id}.html"), "r",
                  encoding="utf-8") as f:
            resp = responses.add(
                responses.GET,
                f"{self.test_config.constants.ORDER_DETAILS_URL}?orderID={order_id}",
                body=f.read(),
                status=200,
            )

        # WHEN
        order = self.amazon_orders.get_order(order_id)

        # THEN
        self.assert_order_112_9685975_5907428_multiple_items_shipments_sellers(order, True)
        self.assertIsNone(order.index)
        self.assertEqual(1, resp.call_count)

    @responses.activate
    def test_get_order_not_found_errors_with_meta(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        order_id = "112-9685975-5907428"
        index = 42
        # The first time we fetch it will succeed
        with open(os.path.join(self.RESOURCES_DIR, "orders", f"order-details-{order_id}.html"), "r",
                  encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                f"{self.test_config.constants.ORDER_DETAILS_URL}?orderID={order_id}",
                body=f.read(),
                status=200,
            )
        # The second time it will redirect, simulating a not found
        with open(os.path.join(self.RESOURCES_DIR, "orders", f"order-details-{order_id}.html"), "r",
                  encoding="utf-8") as f:
            resp2 = responses.add(
                responses.GET,
                f"{self.test_config.constants.ORDER_DETAILS_URL}?orderID={order_id}",
                status=302,
                headers={"Location": self.test_config.constants.ORDER_HISTORY_URL}
            )
        resp3 = responses.add(
            responses.GET,
            self.test_config.constants.ORDER_HISTORY_URL,
            status=200
        )

        # WHEN
        order = self.amazon_orders.get_order(order_id)
        # Set the index, simulating that we fetched this order from a history query
        order.index = index
        with self.assertRaises(AmazonOrdersNotFoundError) as cm:
            self.amazon_orders.get_order(order_id, clone=order)

        # THEN
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(1, resp3.call_count)
        self.assertEqual(cm.exception.meta["index"], index)

    @responses.activate
    def test_get_order_invalid_page(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        order_id = "112-9685975-5907428"
        with open(os.path.join(self.RESOURCES_DIR, "500.html"), "r",
                  encoding="utf-8") as f:
            resp = responses.add(
                responses.GET,
                f"{self.test_config.constants.ORDER_DETAILS_URL}?orderID={order_id}",
                body=f.read(),
                status=200,
            )

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_orders.get_order(order_id)

        # THEN
        self.assertEqual(1, resp.call_count)
        self.assertIn("Could not parse details for Order", str(cm.exception))

    @responses.activate
    def test_get_order_2024_data_component(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        order_id = "112-5939971-8962610"
        with open(os.path.join(self.RESOURCES_DIR, "orders", f"order-details-{order_id}.html"), "r",
                  encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                f"{self.test_config.constants.ORDER_DETAILS_URL}?orderID={order_id}",
                body=f.read(),
                status=200,
            )

        # WHEN
        order = self.amazon_orders.get_order(order_id)

        # THEN
        self.assert_order_112_5939971_8962610_data_component(order, True)
        self.assertIsNone(order.index)
        self.assertEqual(1, resp1.call_count)

    @responses.activate
    def test_get_order_2024_gift_card(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        order_id = "112-4482432-2955442"
        with open(os.path.join(self.RESOURCES_DIR, "orders", f"order-details-{order_id}.html"), "r",
                  encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                f"{self.test_config.constants.ORDER_DETAILS_URL}?orderID={order_id}",
                body=f.read(),
                status=200,
            )

        # WHEN
        order = self.amazon_orders.get_order(order_id)

        # THEN
        self.assert_order_112_4482432_2955442_gift_card(order, True)
        self.assertIsNone(order.index)
        self.assertEqual(1, resp1.call_count)

    @responses.activate
    def test_get_order_2024_digital_order_legacy(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        order_id = "112-9087159-1657009"
        with open(os.path.join(self.RESOURCES_DIR, "orders", f"order-details-{order_id}.html"), "r",
                  encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                f"{self.test_config.constants.ORDER_DETAILS_URL}?orderID={order_id}",
                body=f.read(),
                status=200,
            )

        # WHEN
        order = self.amazon_orders.get_order(order_id)

        # THEN
        self.assert_order_112_9087159_1657009_digital_order_legacy(order, True)
        self.assertIsNone(order.index)
        self.assertEqual(1, resp1.call_count)

    @responses.activate
    def test_get_order_2024_data_component_subscription(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        order_id = "114-8722141-6545058"
        with open(os.path.join(self.RESOURCES_DIR, "orders", f"order-details-{order_id}.html"), "r",
                  encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                f"{self.test_config.constants.ORDER_DETAILS_URL}?orderID={order_id}",
                body=f.read(),
                status=200,
            )

        # WHEN
        order = self.amazon_orders.get_order(order_id)

        # THEN
        self.assert_order_114_8722141_6545058_data_component_subscription(order, True)
        self.assertIsNone(order.index)
        self.assertEqual(1, resp1.call_count)

    @responses.activate
    def test_get_order_2024_data_component_multiple_shipments(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        order_id = "111-6778632-7354601"
        with open(os.path.join(self.RESOURCES_DIR, "orders", f"order-details-{order_id}.html"), "r",
                  encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                f"{self.test_config.constants.ORDER_DETAILS_URL}?orderID={order_id}",
                body=f.read(),
                status=200,
            )

        # WHEN
        order = self.amazon_orders.get_order(order_id)

        # THEN
        self.assert_order_111_6778632_7354601_data_component_subscription(order, True)
        self.assertIsNone(order.index)
        self.assertEqual(1, resp1.call_count)

    @responses.activate
    def test_get_order_history_zero_orders(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2023
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2023-zero-orders.html"), "r",
                  encoding="utf-8") as f:
            resp = responses.add(
                responses.GET,
                self.test_config.constants.ORDER_HISTORY_URL,
                body=f.read(),
                status=200,
            )

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year)

        # THEN
        self.assertEqual(0, len(orders))
        self.assertEqual(1, resp.call_count)

    def test_get_order_history_start_index_equal_orders_count(self):
        for start_index in [10, 20]:
            year = 2023
            uri = f"{self.test_config.constants.ORDER_HISTORY_URL}?timeFilter=year-{year}&startIndex={start_index}"
            with self.subTest(start_index=start_index):
                with responses.RequestsMock() as rsps:
                    # GIVEN
                    self.amazon_session.is_authenticated = True
                    with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2023-10-ten-orders.html"), "r",
                              encoding="utf-8") as f:
                        resp = rsps.add(
                            responses.GET,
                            uri,
                            body=f.read(),
                            status=200,
                        )

                    # WHEN
                    orders = self.amazon_orders.get_order_history(year=year, start_index=start_index)

                    # THEN
                    self.assertEqual(0, len(orders))
                    self.assertEqual(1, resp.call_count)

    @unittest.skipIf(not os.path.exists(temp_order_history_file_path),
                     reason="Skipped, to debug an order history page, "
                            "place it at tests/output/temp-order-history.html")
    @responses.activate
    def test_temp_order_history_file(self):
        """
        This test can be used to drop in an order history page at tests/output/temp-order-history.html to easily
        run a test against it for debugging purposes.
        """
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2024
        with open(self.temp_order_history_file_path, "r", encoding="utf-8") as f:
            responses.add(
                responses.GET,
                "{url}?timeFilter=year-{year}".format(url=self.test_config.constants.ORDER_HISTORY_URL,
                                                      year=year),
                body=f.read(),
                status=200,
            )

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year,
                                                      keep_paging=False)

        # THEN, assert the primary fields are populated without regression
        for order in orders:
            self.assert_populated_generic(order, full_details=False)
            self.assertIsNotNone(order.index)

    @unittest.skipIf(not os.path.exists(temp_order_details_file_path),
                     reason="Skipped, to debug an order details page, "
                            "place it at tests/output/temp-order-details.html")
    @responses.activate
    def test_temp_order_details_file(self):
        """
        This test can be used to drop in an order details page at tests/output/temp-order-details.html to easily
        run a test against it for debugging purposes.
        """
        # GIVEN
        self.amazon_session.is_authenticated = True
        order_id = "temp-1234"
        with open(self.temp_order_details_file_path, "r", encoding="utf-8") as f:
            responses.add(
                responses.GET,
                f"{self.test_config.constants.ORDER_DETAILS_URL}?orderID={order_id}",
                body=f.read(),
                status=200,
            )

        # WHEN
        order = self.amazon_orders.get_order(order_id)

        # THEN, assert the primary fields are populated without regression
        self.assert_populated_generic(order, full_details=False)
        self.assertIsNone(order.index)

    @responses.activate
    def test_get_order_history_last30(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        resp = self.given_order_history_exists_for_time_filter("last30", "order-history-2024-0.html")

        # WHEN
        orders = self.amazon_orders.get_order_history(time_filter="last30", keep_paging=False)

        # THEN
        self.assertEqual(10, len(orders))
        self.assertEqual(1, resp.call_count)

    @responses.activate
    def test_get_order_history_months_3(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        resp = self.given_order_history_exists_for_time_filter("months-3", "order-history-2024-0.html")

        # WHEN
        orders = self.amazon_orders.get_order_history(time_filter="months-3", keep_paging=False)

        # THEN
        self.assertEqual(10, len(orders))
        self.assertEqual(1, resp.call_count)

    @responses.activate
    def test_get_order_history_time_filter_and_year_raises_error(self):
        with self.assertRaises(AmazonOrdersError):
            self.amazon_orders.get_order_history(year=2020, time_filter="last30", keep_paging=False)

    @responses.activate
    def test_get_order_history_default_year_when_no_params(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        current_year = date.today().year
        resp = self.given_order_history_exists_for_time_filter(f"year-{current_year}", "order-history-2024-0.html")

        # WHEN - no year or time_filter provided
        orders = self.amazon_orders.get_order_history(keep_paging=False)

        # THEN - should default to current year
        self.assertEqual(10, len(orders))
        self.assertEqual(1, resp.call_count)

    def test_get_order_history_invalid_time_filter(self):
        # GIVEN
        self.amazon_session.is_authenticated = True

        # WHEN/THEN - invalid time_filter should raise an error
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_orders.get_order_history(time_filter="last90")

        self.assertIn("Invalid time_filter 'last90'", str(cm.exception))
        self.assertIn("Valid values are 'last30', 'months-3', or 'year-YYYY'", str(cm.exception))
