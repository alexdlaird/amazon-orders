__copyright__ = "Copyright (c) 2024 Jeff Sawatzky"
__license__ = "MIT"

import datetime
from typing import Dict, List, Optional, Tuple

from bs4 import Tag

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.transaction import Transaction


def parse_transaction_form_tag(
    form_tag: Tag, config: AmazonOrdersConfig
) -> Tuple[List[Transaction], Optional[str], Optional[Dict[str, str]]]:
    transactions = []
    date_container_tags = form_tag.select(
        config.selectors.TRANSACTION_DATE_CONTAINERS_SELECTOR
    )
    for date_container_tag in date_container_tags:
        date_tag = date_container_tag.select_one(
            config.selectors.FIELD_TRANSACTION_COMPLETED_DATE_SELECTOR
        )
        assert date_tag is not None

        date_str = date_tag.text
        date = datetime.datetime.strptime(
            date_str, config.constants.TRANSACTION_DATE_FORMAT
        ).date()

        transactions_container_tag = date_container_tag.find_next_sibling(
            config.selectors.TRANSACTIONS_CONTAINER_SELECTOR
        )
        assert isinstance(transactions_container_tag, Tag)

        transaction_tags = transactions_container_tag.select(
            config.selectors.TRANSACTIONS_SELECTOR
        )
        for transaction_tag in transaction_tags:
            transaction = Transaction(transaction_tag, config, date)
            transactions.append(transaction)

    form_state_input = form_tag.select_one(
        config.selectors.TRANSACTIONS_NEXT_PAGE_INPUT_STATE_SELECTOR
    )
    form_ie_input = form_tag.select_one(
        config.selectors.TRANSACTIONS_NEXT_PAGE_INPUT_IE_SELECTOR
    )
    next_page_input = form_tag.select_one(
        config.selectors.TRANSACTIONS_NEXT_PAGE_INPUT_SELECTOR
    )
    if not next_page_input or not form_state_input or not form_ie_input:
        return (transactions, None, None)

    next_page_post_url = str(form_tag["action"])
    next_page_post_data = {
        "ppw-widgetState": str(form_state_input["value"]),
        "ie": str(form_ie_input["value"]),
        str(next_page_input["name"]): "",
    }

    return (transactions, next_page_post_url, next_page_post_data)
