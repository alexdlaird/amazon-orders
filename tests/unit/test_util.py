__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from datetime import date

from amazonorders.util import to_type, to_date, cleanup_html_text
from tests.unittestcase import UnitTestCase


class TestUtil(UnitTestCase):
    def test_to_date(self):
        self.assertIsNone(to_date(None))
        self.assertIsNone(to_date(""))

        # English formats delegated to dateutil
        self.assertEqual(to_date("August 23, 2024"), date(2024, 8, 23))
        self.assertEqual(to_date("2024/8/23"), date(2024, 8, 23))

        # Japanese (amazon.co.jp) notation, which dateutil cannot parse
        self.assertEqual(to_date("2024年8月23日"), date(2024, 8, 23))
        self.assertEqual(to_date("2024 年 8 月 23 日"), date(2024, 8, 23))
        self.assertEqual(to_date("2024年8月23日 に注文"), date(2024, 8, 23))

        # Unparseable input returns None rather than raising or guessing
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
