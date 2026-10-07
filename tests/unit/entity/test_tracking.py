__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os

from bs4 import BeautifulSoup

from amazonorders.entity.tracking import Tracking
from amazonorders.exception import AmazonOrdersError
from amazonorders.orders import AmazonOrders
from tests.unittestcase import UnitTestCase


class TestTracking(UnitTestCase):
    def _read(self, filename):
        with open(os.path.join(self.RESOURCES_DIR, "tracking", filename), "r", encoding="utf-8") as f:
            return f.read()

    def test_parse_tracking_carrier(self):
        # WHEN
        tracking = AmazonOrders.parse_tracking(self._read("progress-tracker-ups.html"), self.test_config)

        # THEN
        self.assertEqual("UPS", tracking.carrier)
        self.assertEqual("1Z999AA10123456784", tracking.tracking_number)

    def test_parse_tracking_amazon_delivery(self):
        # WHEN
        tracking = AmazonOrders.parse_tracking(self._read("progress-tracker-amazon.html"), self.test_config)

        # THEN
        self.assertEqual("Amazon", tracking.carrier)
        self.assertEqual("TBA000000000000", tracking.tracking_number)

    def test_parse_tracking_status_only_page(self):
        # GIVEN the layout that only shows the delivery milestones (no carrier tracking)

        # WHEN
        tracking = AmazonOrders.parse_tracking(self._read("progress-tracker-status-only.html"), self.test_config)

        # THEN
        self.assertIsNone(tracking.carrier)
        self.assertIsNone(tracking.tracking_number)

    def test_parse_tracking_to_dict(self):
        # WHEN
        tracking = AmazonOrders.parse_tracking(self._read("progress-tracker-ups.html"), self.test_config)

        # THEN
        self.assertEqual({"carrier": "UPS", "tracking_number": "1Z999AA10123456784"}, tracking.to_dict())

    def test_tracking_number_all_digits_stays_text(self):
        # GIVEN a USPS-style number: all digits, with leading zeros
        html = self._read("progress-tracker-ups.html").replace("1Z999AA10123456784", "0094001118992231000000")

        # WHEN
        tracking = AmazonOrders.parse_tracking(html, self.test_config)

        # THEN
        self.assertEqual("0094001118992231000000", tracking.tracking_number)
        self.assertIsInstance(tracking.tracking_number, str)

    def test_tracking_fields_missing(self):
        # GIVEN
        parsed = BeautifulSoup("<div class=\"a-row pt-main-container\"></div>", self.test_config.bs4_parser)

        # WHEN
        tracking = Tracking(parsed, self.test_config)

        # THEN
        self.assertIsNone(tracking.carrier)
        self.assertIsNone(tracking.tracking_number)

    def test_parse_tracking_not_a_tracking_page(self):
        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            AmazonOrders.parse_tracking("<html><body><p>Something else</p></body></html>", self.test_config)

        # THEN
        self.assertIn("Could not parse package tracking", str(cm.exception))
