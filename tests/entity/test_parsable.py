__copyright__ = "Copyright (c) 2024 Jeff Sawatzky"
__license__ = "MIT"

from bs4 import BeautifulSoup

from amazonorders.entity.parsable import Parsable
from tests.unittestcase import UnitTestCase


class TestItem(UnitTestCase):
    def test_to_currency(self):
        # GIVEN
        html = "<html />"
        parsed = BeautifulSoup(html, "html.parser")

        # WHEN
        parsable = Parsable(parsed, self.test_config)

        # THEN
        self.assertEqual(parsable.to_currency(None), None)
        self.assertEqual(parsable.to_currency(""), None)
        self.assertEqual(parsable.to_currency(1234.99), 1234.99)
        self.assertEqual(parsable.to_currency(1234), 1234)
        self.assertEqual(parsable.to_currency("1,234.99"), 1234.99)
        self.assertEqual(parsable.to_currency("$1,234.99"), 1234.99)
        self.assertEqual(parsable.to_currency("not currency"), None)