__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from amazonorders.util import to_type, cleanup_html_text
from tests.unittestcase import UnitTestCase


class TestUtil(UnitTestCase):
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
