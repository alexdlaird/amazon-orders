__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from datetime import date

from bs4 import BeautifulSoup

from amazonorders.selectors import Selector
from amazonorders.util import to_type, to_date, cleanup_html_text, select, select_one
from tests.unittestcase import UnitTestCase


class TestUtil(UnitTestCase):
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
