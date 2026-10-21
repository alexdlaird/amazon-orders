__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import os

import responses
from responses.matchers import query_param_matcher

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.exception import AmazonOrdersAuthRedirectError, AmazonOrdersError
from amazonorders.orders import AmazonOrders
from amazonorders.session import AmazonSession
from tests.unittestcase import UnitTestCase

# Amazon's pagination, as the Order history renders it. The search pages read for these fixtures fit on one page,
# so a next page is given this markup.
NEXT_PAGE_HTML = """<ul class="a-pagination"><li class="a-last"><a href="{href}">Next<span class="a-letter-space">
</span><span class="a-letter-space"></span>&rarr;</a></li></ul>"""


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

    def given_search_page_exists(self, html, query="example", url=None):
        return responses.add(
            responses.GET,
            url or self.test_config.constants.ORDER_SEARCH_URL,
            body=html,
            status=200,
            match=[query_param_matcher({"search": query})] if query else [],
        )

    def with_next_page(self, html, href):
        return html.replace("</body>", f"{NEXT_PAGE_HTML.format(href=href)}\n</body>")

    def test_search_orders_unauthenticated(self):
        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_orders.search_orders("example")

        # THEN
        self.assertEqual("Call AmazonSession.login() to authenticate first.", str(cm.exception))

    def test_search_orders_empty_query(self):
        # GIVEN
        self.amazon_session.is_authenticated = True

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_orders.search_orders("  ")

        # THEN
        self.assertEqual("The search query must not be empty.", str(cm.exception))

    @responses.activate
    def test_search_orders(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        resp = self.given_search_page_exists(self.read_resource("orders", "order-search.html"))

        # WHEN
        results = self.amazon_orders.search_orders(" example ")

        # THEN
        self.assertEqual(1, resp.call_count)
        self.assertEqual(3, len(results))
        result = results[0]
        self.assertEqual("111-0000000-0000001", result.order_number)
        self.assertEqual(datetime.date(2026, 4, 22), result.order_placed_date)
        self.assertEqual("Example USB-C Cable, 2 m, Braided, Black", result.title)
        self.assertEqual("https://www.amazon.com/dp/B000000001?ref_=ppx_hzsearch_conn_dt_b_fed_asin_title_1",
                         result.link)
        self.assertEqual("B000000001", result.asin)
        self.assertEqual(1, result.quantity)
        self.assertEqual("https://www.amazon.com/gp/your-account/order-details?orderID=111-0000000-0000001",
                         result.order_details_link)
        self.assertEqual(["111-0000000-0000001", "111-0000000-0000002", "112-0000000-0000003"],
                         [r.order_number for r in results])
        self.assertEqual([datetime.date(2026, 4, 22), datetime.date(2025, 11, 3), datetime.date(2019, 6, 15)],
                         [r.order_placed_date for r in results])
        self.assertEqual([1, 1, 2], [r.quantity for r in results])

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
    def test_search_orders_follows_next_page(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        first_page = self.given_search_page_exists(
            self.with_next_page(self.read_resource("orders", "order-search.html"),
                                "/your-orders/search?search=example&amp;page=2"))
        second_page = responses.add(responses.GET, self.test_config.constants.ORDER_SEARCH_URL,
                                    body=self.read_resource("orders", "order-search-page-2.html"), status=200,
                                    match=[query_param_matcher({"search": "example", "page": "2"})])

        # WHEN
        results = self.amazon_orders.search_orders("example")

        # THEN
        self.assertEqual(1, first_page.call_count)
        self.assertEqual(1, second_page.call_count)
        self.assertEqual(["111-0000000-0000001", "111-0000000-0000002", "112-0000000-0000003",
                          "111-0000000-0000004"], [r.order_number for r in results])

    @responses.activate
    def test_search_orders_does_not_follow_next_page_off_site(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        self.given_search_page_exists(
            self.with_next_page(self.read_resource("orders", "order-search.html"),
                                "https://example.com/your-orders/search?search=example&amp;page=2"))

        # WHEN
        results = self.amazon_orders.search_orders("example")

        # THEN no request is made to the other host
        self.assertEqual(3, len(results))
        self.assertEqual(1, len(responses.calls))

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
                         results[0].link)
        self.assertEqual("https://www.amazon.de/gp/your-account/order-details?orderID=302-0000000-0000001",
                         results[0].order_details_link)

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
        results = AmazonOrders.parse_order_search(self.read_resource("orders", "order-search.html"),
                                                  self.test_config)

        # THEN
        self.assertEqual(3, len(results))
        self.assertEqual("Example AA Batteries, Pack of 24", results[1].title)

    def test_parse_order_search_language_package(self):
        # GIVEN a language package's own "Ordered on" text and dates
        config = AmazonOrdersConfig(config_path=self.test_config.config_path,
                                    data={"language_package": "tests.unit.example_language_package"})
        html = self.read_resource("orders", "order-search.html")
        html = html.replace("Ordered on April 22, 2026", "Nulla pariatur 22 amet 2026")

        # WHEN
        results = AmazonOrders.parse_order_search(html, config)

        # THEN
        self.assertEqual(datetime.date(2026, 4, 22), results[0].order_placed_date)

    def test_parse_order_search_unknown_page(self):
        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            AmazonOrders.parse_order_search("<html><body><p>Something else</p></body></html>", self.test_config)

        # THEN
        self.assertEqual("Could not parse Order search results. Check if Amazon changed the HTML.",
                         str(cm.exception))
