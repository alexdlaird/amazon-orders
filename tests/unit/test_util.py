__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from datetime import date

from amazonorders.util import to_type, to_date, resolve_site_url, with_query_param
from tests.unittestcase import UnitTestCase


class TestUtil(UnitTestCase):
    def test_resolve_site_url_accepts_relative_and_www_variants(self):
        # GIVEN
        base_url = "https://www.amazon.com"

        # WHEN / THEN
        self.assertEqual("https://www.amazon.com/gc/balance?next=abc",
                         resolve_site_url("/gc/balance?next=abc", base_url))
        self.assertEqual("https://amazon.com/gc/balance?next=abc",
                         resolve_site_url("https://amazon.com/gc/balance?next=abc", base_url))
        self.assertEqual("https://www.amazon.com:443/gc/balance",
                         resolve_site_url("https://www.amazon.com:443/gc/balance", base_url))
        self.assertEqual("https://www.amazon.com/gc/balance",
                         resolve_site_url("https://www.amazon.com/gc/balance", "https://amazon.com"))

    def test_resolve_site_url_rejects_external_hosts_and_ports(self):
        # GIVEN
        base_url = "https://www.amazon.com"

        # WHEN / THEN
        self.assertIsNone(resolve_site_url("https://evil.example/gc/balance", base_url))
        self.assertIsNone(resolve_site_url("https://amazon.com.evil.example/gc/balance", base_url))
        self.assertIsNone(resolve_site_url("https://amazon.com:444/gc/balance", base_url))

    def test_resolve_site_url_rejects_malformed_urls_and_credentials(self):
        # GIVEN
        base_url = "https://www.amazon.com"
        invalid_urls = (
            "https://www.amazon.com:invalid/gc/balance",
            "https://user@www.amazon.com/gc/balance",
            "https://:password@www.amazon.com/gc/balance",
            "https://user:password@www.amazon.com/gc/balance",
            "mailto:orders@example.com",
            "https://www.amazon.com＠evil.example/gc/balance",
        )

        # WHEN / THEN
        for url in invalid_urls:
            with self.subTest(url=url):
                self.assertIsNone(resolve_site_url(url, base_url))

    def test_with_query_param(self):
        # GIVEN
        url = "https://www.amazon.com/your-orders/orders?timeFilter=year-2010&startIndex=10"

        # WHEN / THEN
        self.assertEqual(f"{url}&disableCsd=no-js", with_query_param(url, "disableCsd", "no-js"))
        self.assertEqual(f"{url}&disableCsd=no-js", with_query_param(f"{url}&disableCsd=x", "disableCsd", "no-js"))
        self.assertEqual(url, with_query_param(f"{url}&disableCsd=no-js", "disableCsd", None))
        self.assertEqual("https://www.amazon.com/your-orders/orders?ref_=a%2Cb",
                         with_query_param("https://www.amazon.com/your-orders/orders?ref_=a%2Cb", "disableCsd", None))

    def test_to_date_english(self):
        # WHEN / THEN
        self.assertEqual(to_date("August 23, 2024"), date(2024, 8, 23))
        self.assertEqual(to_date("2024/8/23"), date(2024, 8, 23))

    def test_to_date_japanese(self):
        # WHEN / THEN
        self.assertEqual(to_date("2024年8月23日"), date(2024, 8, 23))
        self.assertEqual(to_date("2024 年 8 月 23 日"), date(2024, 8, 23))
        self.assertEqual(to_date("2024年8月23日 に注文"), date(2024, 8, 23))

    def test_to_date_unparseable_returns_none(self):
        # WHEN / THEN
        self.assertIsNone(to_date(None))
        self.assertIsNone(to_date(""))
        self.assertIsNone(to_date("not a date"))
        self.assertIsNone(to_date("2024年13月40日"))

    def test_to_type(self):
        self.assertIsNone(to_type(None))

        self.assertEqual(to_type("0.0"), 0.0)
        self.assertEqual(to_type("0.1"), 0.1)
        self.assertEqual(to_type("0"), 0)
        self.assertEqual(to_type("1.0"), 1.0)
        self.assertEqual(to_type("1.1"), 1.1)
        self.assertEqual(to_type("1"), 1)

        self.assertEqual(to_type("True"), True)
        self.assertEqual(to_type("False"), False)

        self.assertIsNone(to_type(""))
        self.assertEqual(to_type(" "), " ")
        self.assertEqual(to_type("None"), "None")
