__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from amazonorders.selectors import Selector, Selectors
from tests.unittestcase import UnitTestCase


class TestSelectors(UnitTestCase):
    def test_subclass_changing_text_rebuilds_selectors_built_from_it(self):
        # WHEN
        class LoremSelectors(Selectors):
            ORDER_CANCELLED_TEXT = "Lorem"
            ORDER_SHIPMENT_STATUS_SELECTOR = "h4.lorem-status"

        # THEN
        self.assertEqual(["Lorem", None], [selector.text for selector in LoremSelectors.ORDER_SKIP_TOTALS])
        self.assertEqual("Lorem", LoremSelectors.ORDER_SHIPMENT_CANCELLED_SELECTOR.text_contains)
        self.assertEqual("h4.lorem-status", LoremSelectors.ORDER_SHIPMENT_CANCELLED_SELECTOR.css_selector)
        self.assertIs(Selectors.ORDER_SKIP_ITEMS, LoremSelectors.ORDER_SKIP_ITEMS)
        self.assertEqual("Cancelled", Selectors.ORDER_SHIPMENT_CANCELLED_SELECTOR.text_contains)

    def test_subclass_not_changing_text_keeps_selectors(self):
        # WHEN
        class LoremSelectors(Selectors):
            ORDER_PHYSICAL_STORE_TEXT = "Lorem"

        # THEN
        self.assertIs(Selectors.ORDER_SKIP_TOTALS, LoremSelectors.ORDER_SKIP_TOTALS)
        self.assertIs(Selectors.ORDER_WHOLE_FOODS, LoremSelectors.ORDER_WHOLE_FOODS)
        self.assertIs(Selectors.ORDER_SHIPMENT_CANCELLED_SELECTOR, LoremSelectors.ORDER_SHIPMENT_CANCELLED_SELECTOR)

    def test_selector_set_explicitly_wins_over_text(self):
        # GIVEN
        explicit = [Selector("div.lorem", "Ipsum")]

        # WHEN
        class ExplicitSelectors(Selectors):
            ORDER_CANCELLED_TEXT = "Lorem"
            ORDER_SKIP_TOTALS = explicit

        class ChildSelectors(ExplicitSelectors):
            ORDER_CANCELLED_TEXT = "Dolor"

        # THEN
        self.assertIs(explicit, ExplicitSelectors.ORDER_SKIP_TOTALS)
        self.assertEqual("Lorem", ExplicitSelectors.ORDER_SHIPMENT_CANCELLED_SELECTOR.text_contains)
        self.assertIs(explicit, ChildSelectors.ORDER_SKIP_TOTALS)
        self.assertEqual("Dolor", ChildSelectors.ORDER_SHIPMENT_CANCELLED_SELECTOR.text_contains)
