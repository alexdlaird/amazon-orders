__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
import sys
from datetime import date
from unittest.mock import patch

from bs4 import BeautifulSoup

from amazonorders.selectors import Selector
from amazonorders.util import to_type, to_date, cleanup_html_text, has_display, resolve_site_url, select, select_one, \
    with_query_param
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

    def test_cleanup_html_text(self):
        self.assertEqual(cleanup_html_text("""This is a paragraph.
        
        
        So much space. More space.
        This sentence will have period added
        So will this one with two spaces
        
        And then some more.
        
        And that's all"""  # noqa: W293
                                           ),
                         "This is a paragraph. So much space. More space. This sentence will have period "
                         "added. So will this one with two spaces. And then some more. And that's all.")
        self.assertEqual(cleanup_html_text(""" There was a problem
        
        The One Time Password (OTP) you entered is not valid.
        
        Please try again
        
        """  # noqa: W293
                                           ),
                         "There was a problem. The One Time Password (OTP) you entered is not valid. "
                         "Please try again.")
        self.assertEqual(cleanup_html_text("""
        
        This has leading newlines.
        
        They should be removed
        
        """  # noqa: W293
                                           ), "This has leading newlines. They should be removed.")

    def test_select_with_text_selector_returns_matched_tags(self):
        # GIVEN
        parsed = BeautifulSoup("<div><span>Rewards balance</span><span>Other</span>"
                               "<p><b>Rewards balance</b></p><i>Rewards balance</i></div>",
                               self.test_config.bs4_parser)

        # WHEN
        tags = select(parsed, Selector("span, b", text="Rewards balance"))

        # THEN
        self.assertEqual(["span", "b"], [t.name for t in tags])
        self.assertEqual(["Rewards balance", "Rewards balance"], [t.text for t in tags])

    def test_select_with_text_selector_returns_tag_not_children(self):
        # GIVEN
        parsed = BeautifulSoup("<div><span class=\"s\"><b>Rewards balance</b> <i>(updated today)</i></span>"
                               "<span class=\"s\">Other</span></div>",
                               self.test_config.bs4_parser)

        # WHEN
        tags = select(parsed, Selector("span.s", text_contains="Rewards balance"))

        # THEN
        self.assertEqual(1, len(tags))
        self.assertEqual("span", tags[0].name)

    def test_select_one_with_text_selector_returns_first_matched_tag(self):
        # GIVEN
        parsed = BeautifulSoup("<ul><li><span class=\"label\">Total</span><p>$1.00</p></li>"
                               "<li><span class=\"label\">Order Number</span><p>123-1234567-1234567</p></li>"
                               "<li><span class=\"label\">Receipts</span><p>n/a</p></li></ul>",
                               self.test_config.bs4_parser)

        # WHEN
        tag = select_one(parsed, Selector("span.label", text="Order Number"))

        # THEN
        self.assertIsNotNone(tag)
        self.assertEqual("Order Number", tag.text)
        self.assertEqual("123-1234567-1234567", tag.find_next_sibling("p").text)

    def test_select_one_with_text_selector_returns_none_when_no_text_matches(self):
        # GIVEN
        parsed = BeautifulSoup("<ul><li><span class=\"label\">Total</span></li>"
                               "<li><span class=\"label\">Order Number</span></li></ul>",
                               self.test_config.bs4_parser)

        # WHEN
        tag = select_one(parsed, Selector("span.label", text="Subtotal"))

        # THEN
        self.assertIsNone(tag)

    @patch.object(sys, "platform", "linux")
    def test_has_display_linux_without_display(self):
        # GIVEN
        with patch.dict(os.environ):
            os.environ.pop("DISPLAY", None)
            os.environ.pop("WAYLAND_DISPLAY", None)

            # WHEN / THEN
            self.assertFalse(has_display())

    @patch.object(sys, "platform", "linux")
    def test_has_display_linux_with_display(self):
        # GIVEN
        for name, value in (("DISPLAY", ":0"), ("WAYLAND_DISPLAY", "wayland-0")):
            with self.subTest(name=name), patch.dict(os.environ, {name: value}):
                os.environ.pop("WAYLAND_DISPLAY" if name == "DISPLAY" else "DISPLAY", None)

                # WHEN / THEN
                self.assertTrue(has_display())

    @patch.object(sys, "platform", "darwin")
    def test_has_display_assumed_off_linux(self):
        # GIVEN
        with patch.dict(os.environ):
            os.environ.pop("DISPLAY", None)
            os.environ.pop("WAYLAND_DISPLAY", None)

            # WHEN / THEN
            self.assertTrue(has_display())
