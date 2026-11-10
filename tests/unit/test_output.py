__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from amazonorders.output import OutputFormatter
from tests.unittestcase import UnitTestCase


class TestOutput(UnitTestCase):
    def test_format_rejects_unknown_format(self):
        # GIVEN
        formatter = OutputFormatter(self.test_config)

        # WHEN / THEN
        with self.assertRaises(ValueError):
            formatter.format([], "xml")

    def test_format_empty_entities(self):
        # GIVEN
        formatter = OutputFormatter(self.test_config)

        # WHEN / THEN
        self.assertEqual(formatter.format([], "json"), "[]\n")
        self.assertEqual(formatter.format([], "csv"), "")
