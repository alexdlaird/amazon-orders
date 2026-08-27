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

    def test_get_invoice_unauthenticated(self):
        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_orders.get_invoice("1234-fake-id")

        self.assertEqual("Call AmazonSession.login() to authenticate first.", str(cm.exception))

    @responses.activate
    def test_get_invoice(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        resp = self.given_any_invoice_exists("get-invoice.html")

        # WHEN
        invoice = self.amazon_orders.get_invoice("123-4567890-1234567")

        # THEN
        self.assertEqual(1, resp.call_count)
        self.assertIn("Grand Total", invoice.response.text)
        self.assertEqual("Order Details", invoice.parsed.find("title").text.strip())

    @responses.activate
    def test_get_invoice_session_expires(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        resp = self.given_authenticated_url_redirects_to_login()
        self.given_login_responses_success()

        # WHEN
        with self.assertRaises(AmazonOrdersAuthRedirectError) as cm:
            self.amazon_orders.get_invoice("1234-fake-id")

        self.assertIn("Amazon redirected to login.", str(cm.exception))
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertEqual(2, resp.call_count)

    @responses.activate
    def test_get_invoice_not_found(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        order_id = "123-4567890-1234567"
        # A redirect away from the invoice URL (not to login) simulates a not-found order
        resp1 = responses.add(
            responses.GET,
            f"{self.test_config.constants.ORDER_INVOICE_URL}?orderID={order_id}",
            status=302,
            headers={"Location": self.test_config.constants.ORDER_HISTORY_URL},
        )
        resp2 = responses.add(responses.GET, self.test_config.constants.ORDER_HISTORY_URL, status=200)

        # WHEN
        with self.assertRaises(AmazonOrdersNotFoundError) as cm:
            self.amazon_orders.get_invoice(order_id)
        self.assertIn("was not found", str(cm.exception))
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)

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
        self.assertFalse(order.is_whole_foods)
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
        self.assertFalse(order.is_whole_foods)
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
        self.assertTrue(order.is_whole_foods)
        self.assertEqual(62.92, order.grand_total)  # Whole Foods totals are shown on the history page
        self.assertEqual(10, order.item_count)
        self.assertIsNotNone(order.order_details_link)
        self.assertEqual(date(2024, 12, 12), order.order_placed_date)
        self.assertEqual(0, len(order.items))  # Per-item details require the Whole Foods receipt page

    def _get_order_history_full_details_wholefoods(self,
                                                   whole_foods_details="order-details-fopo-147-7999693-6862434.html"):
        # A catering history page with three FOPO orders and six standard orders, plus the details pages
        # each links to. Returns the fetched Orders and the mocked responses so callers can assert on them.
        self.amazon_session.is_authenticated = True
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-wholefoods-catering.html"), "r",
                  encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                self.test_config.constants.ORDER_HISTORY_URL,
                body=f.read(),
                status=200,
            )
        resp2 = self.given_any_order_details_exists("order-details-114-9460922-7737063.html")
        resp3 = self.given_any_whole_foods_details_exists(whole_foods_details)

        orders = self.amazon_orders.get_order_history(year=2024, keep_paging=False, full_details=True)
        return orders, resp1, resp2, resp3

    @responses.activate
    def test_get_order_history_full_details_wholefoods(self):
        # WHEN
        orders, resp1, resp2, resp3 = self._get_order_history_full_details_wholefoods()

        # THEN
        self.assertEqual(10, len(orders))
        self.assertEqual(1, resp1.call_count)
        # The six non-Whole Foods orders fetch the standard details page
        self.assertEqual(6, resp2.call_count)
        # The three Whole Foods orders that link to a FOPO details page fetch it for full details
        self.assertEqual(3, resp3.call_count)
        wfm_orders = [order for order in orders if order.is_whole_foods]
        self.assertEqual(4, len(wfm_orders))
        self.assertTrue(all(order.grand_total is not None for order in wfm_orders))

    @responses.activate
    def test_get_order_history_full_details_wholefoods_items(self):
        # GIVEN
        orders, *_ = self._get_order_history_full_details_wholefoods()

        # WHEN a FOPO order is enriched with per-item details and the receipt's subtotal/tax
        fopo_order = next(order for order in orders if order.order_number == "777-5719845-2377811")

        # THEN
        self.assertEqual(125.67, fopo_order.grand_total)  # from the history page
        self.assertEqual(64.15, fopo_order.subtotal)
        self.assertEqual(1.96, fopo_order.estimated_tax)
        self.assertEqual(10, len(fopo_order.items))
        items_by_title = {item.title: item for item in fopo_order.items}
        self.assertIn("Emmi, Raw Kaltbach Cave Aged Gruyere", items_by_title)
        gruyere = items_by_title["Emmi, Raw Kaltbach Cave Aged Gruyere"]
        self.assertEqual(7.75, gruyere.price)
        self.assertTrue(gruyere.link.endswith("/dp/B07887281X?ref_=wfmInStore_food_od_product_details"))
        self.assertIsNotNone(gruyere.image_link)
        self.assertIsNone(gruyere.quantity)  # sold by weight (Qty: 0.31 lb), so no whole-unit count
        croissants = next(item for item in fopo_order.items
                          if item.title.startswith("Whole Foods Market, Croissant"))
        self.assertEqual(1, croissants.quantity)

    @responses.activate
    def test_get_order_history_full_details_wholefoods_unparseable_details(self):
        # GIVEN a Whole Foods order whose FOPO details page returns no parseable order-details container
        orders, *_ = self._get_order_history_full_details_wholefoods("order-details-wholefoods-unparseable.html")

        # WHEN the FOPO details cannot be parsed
        fopo_order = next(order for order in orders if order.order_number == "777-5719845-2377811")

        # THEN the history-page grand_total is kept, but per-item details are left unpopulated
        self.assertTrue(fopo_order.is_whole_foods)
        self.assertIsNotNone(fopo_order.grand_total)
        self.assertEqual(0, len(fopo_order.items))

    @responses.activate
    def test_get_order_history_full_details_whole_foods_without_details_link(self):
        # GIVEN a Whole Foods order identified by its shipment text but with no linkable details page
        self.amazon_session.is_authenticated = True
        history = (
            "<html><body>"
            "<div class='order-card'>"
            "<div data-component='orderId'>111-2222222-3333333</div>"
            "<div class='yohtmlc-order-total'><span class='value'>$25.00</span></div>"
            "<div class='yohtmlc-shipment-status-primaryText'>Purchased at Whole Foods Market</div>"
            "</div>"
            "</body></html>"
        )
        responses.add(responses.GET, self.test_config.constants.ORDER_HISTORY_URL, body=history, status=200)

        # WHEN full details are requested but no FOPO/receipt link is present to fetch
        orders = self.amazon_orders.get_order_history(year=2024, keep_paging=False, full_details=True)

        # THEN the order is returned partially populated from the history page
        self.assertEqual(1, len(orders))
        order = orders[0]
        self.assertTrue(order.is_whole_foods)
        self.assertEqual(25.00, order.grand_total)
        self.assertEqual(0, len(order.items))

    @responses.activate
    def test_get_order_history_full_details_wholefoods_payment(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2024
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-wholefoods-catering.html"), "r",
                  encoding="utf-8") as f:
            responses.add(
                responses.GET,
                self.test_config.constants.ORDER_HISTORY_URL,
                body=f.read(),
                status=200,
            )
        self.given_any_order_details_exists("order-details-114-9460922-7737063.html")
        self.given_any_whole_foods_details_exists("order-details-fopo-113-4055495-4107437.html")

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year, keep_paging=False, full_details=True)

        # THEN
        fopo_order = next(order for order in orders if order.order_number == "777-5719845-2377811")
        # The receipt's first payment method maps onto the existing Order payment fields
        self.assertEqual("Visa", fopo_order.payment_method)
        self.assertEqual(9790, fopo_order.payment_method_last_4)
        self.assertEqual(27.96, fopo_order.subtotal)
        self.assertEqual(0.54, fopo_order.estimated_tax)
        # An ASINLESS line item (no Amazon detail page) still parses, with a title but no link
        self.assertEqual(3, len(fopo_order.items))
        grapes = next(item for item in fopo_order.items if item.title == "Moon Drop Grapes")
        self.assertIsNone(grapes.link)
        self.assertIsNone(grapes.quantity)  # sold by weight (Qty: 2.44 lb)
        self.assertIsNotNone(grapes.image_link)

    @responses.activate
    def test_get_order_history_full_details_unsupported_type(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2024
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-fresh.html"), "r",
                  encoding="utf-8") as f:
            responses.add(
                responses.GET,
                self.test_config.constants.ORDER_HISTORY_URL,
                body=f.read(),
                status=200,
            )
        self.given_any_order_details_exists("order-details-114-9460922-7737063.html")

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year, keep_paging=False, full_details=True)

        # THEN
        # An Amazon Fresh order is an unsupported type (not Whole Foods), so it stays partially populated
        fresh_order = next(order for order in orders if order.order_number == "111-2072777-8279433")
        self.assertFalse(fresh_order.is_whole_foods)
        self.assertIsNone(fresh_order.grand_total)
        self.assertEqual(0, len(fresh_order.items))

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
    def test_get_order_digital(self):
        # GIVEN - digital (D01-) order details pages label their charge summary "Total for this
        # Order", "Tax Collected", and "Gift Card" instead of "Grand Total", "Estimated tax",
        # and "Gift Card Amount"
        self.amazon_session.is_authenticated = True
        order_id = "D01-1000111-2000222"
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
        self.assertEqual(order_id, order.order_number)
        self.assertEqual(0.0, order.grand_total)
        self.assertEqual(2.73, order.subtotal)
        self.assertEqual(0.18, order.estimated_tax)
        self.assertEqual(-2.9, order.gift_card)
        self.assertEqual("Amazon Visa", order.payment_method)
        self.assertEqual(1, len(order.items))
        self.assertEqual("Digital Item 01", order.items[0].title)
        self.assertEqual(2.73, order.items[0].price)
        self.assertEqual(1, resp.call_count)

    @responses.activate
    def test_get_order_chargesummary_totals(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        order_id = "112-3456789-0123456"
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
        self.assertEqual(order_id, order.order_number)
        self.assertEqual(47.99, order.grand_total)
        self.assertEqual(47.99, order.subtotal)
        self.assertEqual(47.99, order.total_before_tax)
        self.assertEqual(0.0, order.estimated_tax)
        self.assertEqual(0.0, order.shipping_total)
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
    def test_get_order_whole_foods(self):
        # GIVEN ORDER_DETAILS_URL redirects to the dedicated FOPO details page, as Amazon does for
        # Whole Foods Market orders looked up directly (not via order history)
        self.amazon_session.is_authenticated = True
        order_id = "147-7999693-6862434"
        fopo_url = "https://www.amazon.com/fopo/order-details/ref=ppx_yo2ov_dt_b_fed_order_details" \
                   f"?ie=UTF8&orderID={order_id}"
        resp1 = responses.add(
            responses.GET,
            f"{self.test_config.constants.ORDER_DETAILS_URL}?orderID={order_id}",
            status=302,
            headers={"Location": fopo_url},
        )
        resp2 = self.given_any_whole_foods_details_exists("order-details-fopo-147-7999693-6862434.html")

        # WHEN
        order = self.amazon_orders.get_order(order_id)

        # THEN
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(order_id, order.order_number)
        self.assertTrue(order.is_whole_foods)
        self.assertEqual(62.95, order.grand_total)
        self.assertEqual(64.15, order.subtotal)
        self.assertEqual(1.96, order.estimated_tax)
        self.assertEqual(10, len(order.items))

    @responses.activate
    def test_get_order_whole_foods_unparseable_details(self):
        # GIVEN the FOPO details page returns no parseable order-details container
        self.amazon_session.is_authenticated = True
        order_id = "147-7999693-6862434"
        fopo_url = "https://www.amazon.com/fopo/order-details/ref=ppx_yo2ov_dt_b_fed_order_details" \
                   f"?ie=UTF8&orderID={order_id}"
        responses.add(
            responses.GET,
            f"{self.test_config.constants.ORDER_DETAILS_URL}?orderID={order_id}",
            status=302,
            headers={"Location": fopo_url},
        )
        self.given_any_whole_foods_details_exists("order-details-wholefoods-unparseable.html")

        # WHEN there is no clone to fall back to, so the FOPO page must parse to be usable at all
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_orders.get_order(order_id)

        self.assertIn("Could not parse Whole Foods Market details", str(cm.exception))

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

    @responses.activate
    def test_get_order_history_start_index_past_end(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2026
        start_index = 220
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2026-220.html"), "r",
                  encoding="utf-8") as f:
            resp = responses.add(
                responses.GET,
                f"{self.test_config.constants.ORDER_HISTORY_URL}?timeFilter=year-{year}&startIndex={start_index}",
                body=f.read(),
                status=200,
            )

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year, start_index=start_index)

        # THEN
        self.assertEqual(0, len(orders))
        self.assertEqual(1, resp.call_count)

    @responses.activate
    def test_get_order_history_empty_page_within_window(self):
        """
        The same page served for an index the count does not account for is a page that failed to render, not a
        spent window, and must not be reported as no Orders.
        """
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2026
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2026-220.html"), "r",
                  encoding="utf-8") as f:
            resp = responses.add(
                responses.GET,
                f"{self.test_config.constants.ORDER_HISTORY_URL}?timeFilter=year-{year}",
                body=f.read(),
                status=200,
            )

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_orders.get_order_history(year=year)

        # THEN
        self.assertEqual(1, resp.call_count)
        self.assertIn("Could not parse Order history.", str(cm.exception))

    @responses.activate
    def test_get_order_history_count_with_thousands_separator(self):
        # GIVEN - the same real past-the-end page, with the count rendered the way Amazon renders
        # four-digit counts ("1,213 orders"); the previous split()/int() parse raised ValueError on it
        self.amazon_session.is_authenticated = True
        year = 2026
        start_index = 1220
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-history-2026-220.html"), "r",
                  encoding="utf-8") as f:
            body = f.read().replace("<b>213 orders</b>", "<b>1,213 orders</b>")
        resp = responses.add(
            responses.GET,
            f"{self.test_config.constants.ORDER_HISTORY_URL}?timeFilter=year-{year}&startIndex={start_index}",
            body=body,
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

    @responses.activate
    def test_get_order_history_with_order_filter(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        year = 2018
        resp = self.given_any_order_history_exists("order-history-2018-0.html")

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year, order_filter="digital-orders", keep_paging=False)

        # THEN - URL must include both timeFilter and orderFilter
        self.assertEqual(1, resp.call_count)
        request_url = resp.calls[0].request.url
        self.assertIn(f"timeFilter=year-{year}", request_url)
        self.assertIn("orderFilter=digital-orders", request_url)
        self.assertEqual(10, len(orders))

    @responses.activate
    def test_get_order_history_digital_empty_window(self):
        # GIVEN - the digital Order history page renders its count (and no order cards) in the
        # time filter label, without the span.num-orders element regular Order history pages have
        self.amazon_session.is_authenticated = True
        year = 2005
        resp = self.given_any_order_history_exists("order-history-digital-2005-0.html")

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year, order_filter="digital")

        # THEN - an empty window returns an empty list rather than raising a parse error
        self.assertEqual(0, len(orders))
        self.assertEqual(1, resp.call_count)
        request_url = resp.calls[0].request.url
        self.assertIn(f"timeFilter=year-{year}", request_url)
        self.assertIn("orderFilter=digital", request_url)
