__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import os
import re

import responses
from bs4 import BeautifulSoup
from responses.matchers import query_param_matcher

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.item import Item
from amazonorders.exception import AmazonOrdersAuthRedirectError, AmazonOrdersError
from amazonorders.orders import AmazonOrders
from amazonorders.session import AmazonSession
from tests.unittestcase import UnitTestCase

# The next page link order-search.html serves, and the "Next" of order-search-page-2.html, the last page, which has
# no link.
PAGE_2_HREF = "/your-orders/search?page=2&amp;search=example&amp;ref_=ppx_hzsearch_pagination_dt_b_pg_1"
LAST_PAGE_NEXT_HTML = ('<li class="a-disabled a-last">Next<span class="a-letter-space"></span>'
                       '<span class="a-letter-space"></span><span class="larr">→</span></li>')


class SearchItem(Item):
    pass


class TestOrderSearch(UnitTestCase):
    def setUp(self):
        super().setUp()

        self.amazon_session = AmazonSession("some-username@gmail.com",
                                            "some-password",
                                            config=self.test_config)

        self.amazon_orders = AmazonOrders(self.amazon_session)

    def read_resource(self, *path):
        with open(os.path.join(self.RESOURCES_DIR, *path), "r", encoding="utf-8") as f:
            return f.read()

    def given_search_page_exists(self, html=None, rsps=responses):
        return rsps.add(responses.GET, self.test_config.constants.ORDER_SEARCH_URL,
                        body=html or self.read_resource("orders", "order-search.html"), status=200,
                        match=[query_param_matcher({"search": "example"})])

    def given_search_page_2_exists(self, html=None, rsps=responses):
        return rsps.add(responses.GET, self.test_config.constants.ORDER_SEARCH_URL,
                        body=html or self.read_resource("orders", "order-search-page-2.html"), status=200,
                        match=[query_param_matcher({"page": "2", "search": "example",
                                                    "ref_": "ppx_hzsearch_pagination_dt_b_pg_1"})])

    def test_search_orders_unauthenticated(self):
        for search in [lambda: self.amazon_orders.search_orders("example"),
                       lambda: self.amazon_orders.search_orders_page("example")]:
            with self.subTest(search=search):
                # WHEN
                with self.assertRaises(AmazonOrdersError) as cm:
                    search()

                # THEN
                self.assertEqual("Call AmazonSession.login() to authenticate first.", str(cm.exception))

    def test_search_orders_empty_query(self):
        # GIVEN
        self.amazon_session.is_authenticated = True

        for search in [lambda: self.amazon_orders.search_orders("  "),
                       lambda: self.amazon_orders.search_orders_page()]:
            with self.subTest(search=search):
                # WHEN
                with self.assertRaises(AmazonOrdersError) as cm:
                    search()

                # THEN
                self.assertEqual("The search query must not be empty.", str(cm.exception))

    @responses.activate
    def test_search_orders(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        first_page = self.given_search_page_exists()
        second_page = self.given_search_page_2_exists()
        progress_calls = []

        # WHEN
        results = self.amazon_orders.search_orders(" example ", progress=progress_calls.append)

        # THEN the next link Amazon serves is followed to the last page
        self.assertEqual(1, first_page.call_count)
        self.assertEqual(1, second_page.call_count)
        self.assertEqual([10, 17], progress_calls)
        self.assertEqual(17, len(results))
        result = results[0]
        self.assertEqual("111-0000000-0000001", result.order_number)
        self.assertEqual("https://www.amazon.com/your-orders/order-details?orderID=111-0000000-0000001"
                         "&ref_=ppx_hzsearch_conn_dt_b_fed_order_details_1", result.order_details_link)
        self.assertEqual(datetime.date(2025, 9, 18), result.order_placed_date)
        self.assertIsInstance(result.item, Item)
        self.assertEqual("Example Garden Trowel", result.item.title)
        self.assertEqual("https://www.amazon.com/dp/B000000001?ref_=ppx_hzsearch_conn_dt_b_fed_asin_title_1",
                         result.item.link)
        self.assertEqual("B000000001", result.item.asin)
        self.assertEqual("https://m.media-amazon.com/images/I/01TESTIMG0L._SS90_.jpg", result.item.image_link)
        self.assertIsNone(result.item.quantity)
        self.assertIsNone(result.item.price)
        # One result per matching Item, so an Order with several shows up once for each
        self.assertEqual(["111-0000000-0000001", "111-0000000-0000001", "112-0000000-0000002",
                          "113-0000000-0000003", "111-0000000-0000004", "111-0000000-0000005",
                          "111-0000000-0000006", "111-0000000-0000007", "111-0000000-0000007",
                          "111-0000000-0000007", "111-0000000-0000008", "111-0000000-0000008",
                          "111-0000000-0000008", "111-0000000-0000008", "113-0000000-0000009",
                          "113-0000000-0000010", "113-0000000-0000011"], [r.order_number for r in results])
        self.assertEqual(datetime.date(2025, 4, 9), results[-1].order_placed_date)
        self.assertEqual("Example Chess Set, Wooden", results[-1].item.title)
        # Amazon shows a quantity only when more than one was ordered
        self.assertEqual([4, 11], [i for i, r in enumerate(results) if r.item.quantity])
        self.assertEqual([2, 2], [r.item.quantity for r in results if r.item.quantity])

    @responses.activate
    def test_search_orders_single_page(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        first_page = self.given_search_page_exists()
        progress_calls = []

        # WHEN
        results = self.amazon_orders.search_orders("example", keep_paging=False, progress=progress_calls.append)

        # THEN
        self.assertEqual(1, first_page.call_count)
        self.assertEqual(1, len(responses.calls))
        self.assertEqual(10, len(results))
        self.assertEqual([10], progress_calls)

    @responses.activate
    def test_search_orders_no_results(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        self.given_search_page_exists(self.read_resource("orders", "order-search-no-results.html"))

        # WHEN
        results = self.amazon_orders.search_orders("example")

        # THEN
        self.assertEqual([], results)

    @responses.activate
    def test_search_orders_stops_on_page_with_no_results(self):
        # GIVEN a first page with a next link, but no results
        self.amazon_session.is_authenticated = True
        parsed = BeautifulSoup(self.read_resource("orders", "order-search.html"), "html.parser")
        for tag in parsed.select("div.a-fixed-left-grid"):
            tag.decompose()
        first_page = self.given_search_page_exists(str(parsed))
        second_page = self.given_search_page_2_exists()

        # WHEN
        results = self.amazon_orders.search_orders("example")

        # THEN
        self.assertEqual([], results)
        self.assertEqual(1, first_page.call_count)
        self.assertEqual(0, second_page.call_count)

    def test_search_orders_stops_at_page_already_fetched(self):
        for page in ["1", "2"]:
            with self.subTest(page=page), responses.RequestsMock() as rsps:
                # GIVEN the last page's next link goes back to a page already fetched
                self.amazon_session.is_authenticated = True
                first_page = self.given_search_page_exists(rsps=rsps)
                next_html = (f'<li class="a-last"><a href="/your-orders/search?page={page}&amp;search=example&amp;'
                             f'ref_=ppx_hzsearch_pagination_dt_b_pg_2">Next</a></li>')
                second_page = self.given_search_page_2_exists(
                    self.read_resource("orders", "order-search-page-2.html").replace(LAST_PAGE_NEXT_HTML, next_html),
                    rsps)

                # WHEN
                with self.assertLogs("amazonorders.orders", level="WARNING") as cm:
                    results = self.amazon_orders.search_orders("example")

                # THEN
                self.assertEqual(17, len(results))
                self.assertEqual(1, first_page.call_count)
                self.assertEqual(1, second_page.call_count)
                self.assertIn("Ignoring a next link to an Order search page already fetched", cm.output[0])

    def test_search_orders_does_not_follow_next_page_off_site(self):
        for href in ["https://example.com/your-orders/search?search=example&amp;page=2",
                     "https://www.amazon.com.example.com/your-orders/search?page=2",
                     "https://user:secret@www.amazon.com/your-orders/search?page=2"]:
            with self.subTest(href=href), responses.RequestsMock() as rsps:
                # GIVEN
                self.amazon_session.is_authenticated = True
                self.given_search_page_exists(self.read_resource("orders", "order-search.html")
                                              .replace(f'<li class="a-last"><a href="{PAGE_2_HREF}">',
                                                       f'<li class="a-last"><a href="{href}">'), rsps)

                # WHEN
                with self.assertLogs("amazonorders.util", level="WARNING"):
                    results = self.amazon_orders.search_orders("example")

                # THEN no request is made to the other site
                self.assertEqual(10, len(results))
                self.assertEqual(1, len(rsps.calls))

    @responses.activate
    def test_search_orders_page(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        first_page = self.given_search_page_exists()
        second_page = self.given_search_page_2_exists()
        progress_calls = []

        # WHEN
        batch = self.amazon_orders.search_orders_page("example", limit=5, progress=progress_calls.append)

        # THEN whole pages are fetched, and the cursor is the next one
        self.assertEqual(1, first_page.call_count)
        self.assertEqual(0, second_page.call_count)
        self.assertEqual(10, len(batch.items))
        self.assertEqual([10], progress_calls)
        self.assertTrue(batch.has_more)
        self.assertEqual({"next_page": "https://www.amazon.com/your-orders/search?page=2&search=example"
                                       "&ref_=ppx_hzsearch_pagination_dt_b_pg_1"}, batch.cursor)

        # WHEN
        next_batch = self.amazon_orders.search_orders_page(limit=5, cursor=batch.cursor)

        # THEN
        self.assertEqual(1, first_page.call_count)
        self.assertEqual(1, second_page.call_count)
        self.assertEqual(7, len(next_batch.items))
        self.assertEqual("111-0000000-0000008", next_batch.items[0].order_number)
        self.assertFalse(next_batch.has_more)
        self.assertIsNone(next_batch.cursor)
        self.assertEqual(7, len(next_batch.to_dict()["items"]))

    @responses.activate
    def test_search_orders_page_without_limit(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        self.given_search_page_exists()
        self.given_search_page_2_exists()

        # WHEN
        batch = self.amazon_orders.search_orders_page("example")

        # THEN
        self.assertEqual(17, len(batch.items))
        self.assertIsNone(batch.cursor)

    def test_search_orders_page_cursor_off_site(self):
        # GIVEN
        self.amazon_session.is_authenticated = True

        # WHEN
        with self.assertLogs("amazonorders.util", level="WARNING"), self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_orders.search_orders_page(cursor={"next_page": "https://example.com/your-orders/search"})

        # THEN
        self.assertEqual("The cursor's next page is not on this Amazon site.", str(cm.exception))

    @responses.activate
    def test_search_orders_amazon_de(self):
        # GIVEN
        config = AmazonOrdersConfig(config_path=self.test_config.config_path,
                                    data={"domain": "amazon.de", "output_dir": self.test_output_dir})
        amazon_session = AmazonSession("some-username@gmail.com", "some-password", config=config)
        amazon_session.is_authenticated = True
        resp = responses.add(responses.GET, "https://www.amazon.de/your-orders/search",
                             body=self.read_resource("orders", "de", "order-search.html"), status=200,
                             match=[query_param_matcher({"search": "example"})])

        # WHEN
        results = AmazonOrders(amazon_session).search_orders("example")

        # THEN
        self.assertEqual(1, resp.call_count)
        self.assertEqual(["302-0000000-0000001", "028-0000000-0000002"], [r.order_number for r in results])
        self.assertEqual([datetime.date(2026, 8, 12), datetime.date(2025, 2, 28)],
                         [r.order_placed_date for r in results])
        self.assertEqual("https://www.amazon.de/dp/B000000001?ref_=ppx_hzsearch_conn_dt_b_fed_asin_title_1",
                         results[0].item.link)
        self.assertEqual("https://www.amazon.de/your-orders/order-details?orderID=302-0000000-0000001"
                         "&ref_=ppx_hzsearch_conn_dt_b_fed_order_details_1", results[0].order_details_link)

    @responses.activate
    def test_search_orders_session_expires(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        self.given_search_page_exists(self.read_resource("auth", "signin.html"))
        self.given_logout_response_success()

        # WHEN
        with self.assertRaises(AmazonOrdersAuthRedirectError) as cm:
            self.amazon_orders.search_orders("example")

        # THEN
        self.assertIn("Amazon redirected to login.", str(cm.exception))

    def test_parse_order_search(self):
        # WHEN
        results = AmazonOrders.parse_order_search(self.read_resource("orders", "order-search-page-2.html"),
                                                  self.test_config)

        # THEN
        self.assertEqual(7, len(results))
        self.assertEqual("Example Plant Pot, 14 cm", results[1].item.title)
        self.assertEqual(2, results[1].item.quantity)

    def test_parse_order_search_item_class(self):
        # GIVEN
        self.test_config.item_cls = SearchItem

        # WHEN
        results = AmazonOrders.parse_order_search(self.read_resource("orders", "order-search.html"),
                                                  self.test_config)

        # THEN
        self.assertIsInstance(results[0].item, SearchItem)
        self.assertEqual("Example Garden Trowel", results[0].item.title)

    def test_parse_order_search_language_package(self):
        # GIVEN a language package's own "Ordered on" text and dates
        config = AmazonOrdersConfig(config_path=self.test_config.config_path,
                                    data={"language_package": "tests.unit.example_language_package"})
        html = self.read_resource("orders", "order-search.html")
        html = html.replace("Ordered on September 18, 2025", "Nulla pariatur 18 quis 2025")

        # WHEN
        results = AmazonOrders.parse_order_search(html, config)

        # THEN
        self.assertEqual(datetime.date(2025, 9, 18), results[0].order_placed_date)

    def test_parse_order_search_result_without_order_number(self):
        # GIVEN a result whose Order details link is gone
        html = re.sub(r'<a [^>]*href="/your-orders/order-details\?orderID=112-0000000-0000002[^"]*"[^>]*>',
                      '<a class="a-link-normal" href="/your-orders/orders">',
                      self.read_resource("orders", "order-search.html"))

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            AmazonOrders.parse_order_search(html, self.test_config)

        # THEN
        self.assertIn("OrderSearchResult.order_number could not be parsed, but it's required.", str(cm.exception))

        # GIVEN
        self.test_config.update_config("warn_on_missing_required_field", True, save=False)

        # WHEN
        with self.assertLogs("amazonorders.entity.order_search_result", level="WARNING"):
            results = AmazonOrders.parse_order_search(html, self.test_config)

        # THEN
        self.assertIsNone(results[2].order_number)
        self.assertIsNone(results[2].order_details_link)
        self.assertEqual("Example Yoga Mat, 6 mm", results[2].item.title)
        self.assertEqual("113-0000000-0000003", results[3].order_number)

    def test_parse_order_search_result_without_product_page(self):
        # GIVEN a result whose Item has no product page
        html = self.read_resource("orders", "order-search.html").replace("/dp/B000000003?", "/your-orders/orders?")

        # WHEN
        results = AmazonOrders.parse_order_search(html, self.test_config)

        # THEN
        self.assertEqual("Example Yoga Mat, 6 mm", results[2].item.title)
        self.assertEqual("https://www.amazon.com/your-orders/orders?ref_=ppx_hzsearch_conn_dt_b_fed_asin_title_2",
                         results[2].item.link)
        self.assertIsNone(results[2].item.asin)
        self.assertEqual("B000000004", results[3].item.asin)

    def test_parse_order_search_unknown_page(self):
        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            AmazonOrders.parse_order_search("<html><body><p>Something else</p></body></html>", self.test_config)

        # THEN
        self.assertEqual("Could not parse Order search results. Check if Amazon changed the HTML.",
                         str(cm.exception))
