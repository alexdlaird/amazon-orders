__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import re

from amazonorders import constants, selectors, transactions

_MONTHS = {"lorem": 1, "ipsum": 2, "dolor": 3, "amet": 4, "elit": 5, "magna": 6, "enim": 7, "minim": 8, "quis": 9,
           "nisi": 10, "duis": 11, "irure": 12}
_DATE_RE = re.compile(r"(\d{1,2})\s+(" + "|".join(_MONTHS) + r")\s+(\d{4})", re.IGNORECASE)


class Selectors(selectors.Selectors):
    FIELD_ITEM_WHOLE_FOODS_QUANTITY_REGEX = r"^Occaecat:\s*{count}$"
    FIELD_ITEM_CONDITION_PREFIX = "Excepteur:"
    FIELD_ITEM_SELLER_TEXT = "Ullamco:"
    FIELD_ITEM_RETURN_TEXT = "Commodo"
    FIELD_ORDER_GRAND_TOTAL_PREFIX = "Officia"
    FIELD_ORDER_PLACED_DATE_SUFFIX = "Deserunt"
    FIELD_ORDER_PAYMENT_METHOD_LAST_4_REGEX = r"(?:mollit anim\s+|^\s*)(\d+)"
    FIELD_ORDER_GRAND_TOTAL_LABELS = [re.compile(r"\bnostrud")]
    FIELD_ORDER_SUBTOTAL_LABELS = ["consectetur"]
    FIELD_ORDER_SHIPPING_TOTAL_LABELS = ["adipiscing"]
    FIELD_ORDER_FREE_SHIPPING_LABELS = ["eiusmod"]
    FIELD_ORDER_PROMOTION_APPLIED_LABELS = ["reprehenderit"]
    FIELD_ORDER_COUPON_SAVINGS_LABELS = ["tempor"]
    FIELD_ORDER_REWARD_POINTS_LABELS = ["veniam"]
    FIELD_ORDER_SUBSCRIPTION_DISCOUNT_LABELS = ["incididunt"]
    FIELD_ORDER_TOTAL_BEFORE_TAX_LABELS = ["labore"]
    FIELD_ORDER_ESTIMATED_TAX_LABELS = ["aliqua"]
    FIELD_ORDER_REFUND_TOTAL_LABELS = ["exercitation"]
    FIELD_ORDER_MULTIBUY_DISCOUNT_LABELS = ["voluptate"]
    FIELD_ORDER_AMAZON_DISCOUNT_LABELS = ["cillum"]
    FIELD_ORDER_GIFT_CARD_LABELS = ["fugiat"]
    FIELD_ORDER_GIFT_WRAP_LABELS = ["pariatur"]
    FIELD_ORDER_ITEM_COUNT_REGEX = r"{count}\s+cupidatat\s+proident"
    FIELD_SELLER_NAME_PREFIX = "Ullamco:"
    TRANSACTION_HISTORY_EMPTY_TEXT = "laborum"
    ORDER_PHYSICAL_STORE_TEXT = "Sint culpa"
    ORDER_WHOLE_FOODS_TEXT = "Anim id est"
    ORDER_CANCELLED_TEXT = "Velit"


class Constants(constants.Constants):
    SIGNED_OUT_TEXT = "Lorem, ipsum"
    JS_ROBOT_TEXT_REGEX = r"[.\s\S]*sed do robotus[.\s\S]*"
    CURRENCY_FREE_TEXT = "nulla"
    ORDER_NUMBER_REGEX = r"(?<![A-Z0-9-])(?:[A-Z0-9]{3}-\d{7}-\d{7}|\d{4}-\d{6}-\d{7}|\d{19})(?![A-Z0-9-])"

    def parse_currency(self, value):
        if isinstance(value, str) and value.strip().endswith("-"):
            value = "-" + value.strip()[:-1]
        return super().parse_currency(value)

    def parse_date(self, value, fuzzy=False):
        match = _DATE_RE.search(value or "")
        if not match:
            return None
        return datetime.date(int(match.group(3)), _MONTHS[match.group(2).lower()], int(match.group(1)))

    def parse_count(self, value, pattern=r"^\s*{count}"):
        return super().parse_count(value, pattern)

    def parse_order_number(self, value):
        return super().parse_order_number(value)


class TransactionsPage(transactions.TransactionsPage):
    def get_page(self, amazon_session, url, next_page_data=None):
        return super().get_page(amazon_session, url, next_page_data)

    def parse_page(self, parsed):
        return super().parse_page(parsed)
