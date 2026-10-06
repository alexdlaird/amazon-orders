__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

from amazonorders.selectors import Selectors
from amazonorders.transactions import TransactionsPage


class LoremSelectors(Selectors):
    FIELD_ITEM_SELLER_TEXT = "Ullamco:"


class LoremTransactionsPage(TransactionsPage):
    pass


class Constants:
    pass
