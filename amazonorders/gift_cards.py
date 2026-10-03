__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import logging
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from amazonorders import util
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.gift_card_activity import GiftCardActivity
from amazonorders.entity.parsable import Parsable
from amazonorders.exception import AmazonOrdersError
from amazonorders.session import AmazonSession

logger = logging.getLogger(__name__)


def _parse_gift_card_activity_page(parsed: Tag,
                                   config: AmazonOrdersConfig) -> Tuple[List[GiftCardActivity], Optional[str]]:
    table_tag = util.select_one(parsed, config.selectors.GIFT_CARD_ACTIVITY_TABLE_SELECTOR)

    if not table_tag:
        # A balance with no table is an account that has no Gift Card activity
        if util.select_one(parsed, config.selectors.GIFT_CARD_BALANCE_SELECTOR):
            return [], None

        raise AmazonOrdersError("Could not parse Gift Card activity. Check if Amazon changed the HTML.")

    activity = [GiftCardActivity(row_tag, config)
                for row_tag in util.select(table_tag, config.selectors.GIFT_CARD_ACTIVITY_SELECTOR)]

    next_page_url = None
    next_page_link = util.select_one(parsed, config.selectors.GIFT_CARD_ACTIVITY_NEXT_PAGE_LINK_SELECTOR)
    if next_page_link and next_page_link.get("href"):
        next_page_url = str(next_page_link["href"])
        if not next_page_url.startswith("http"):
            next_page_url = f"{config.constants.BASE_URL}{next_page_url}"

    return activity, next_page_url


class AmazonGiftCards:
    """
    Using an authenticated :class:`~amazonorders.session.AmazonSession`, can be used to query Amazon
    for the Gift Card balance and activity.
    """

    def __init__(self,
                 amazon_session: AmazonSession,
                 debug: Optional[bool] = None,
                 config: Optional[AmazonOrdersConfig] = None) -> None:
        if not debug:
            debug = amazon_session.debug
        if not config:
            config = amazon_session.config

        #: The session to use for requests.
        self.amazon_session: AmazonSession = amazon_session
        #: The config to use.
        self.config: AmazonOrdersConfig = config

        #: Setting logger to ``DEBUG`` will send output to ``stderr``.
        self.debug: bool = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)

    @staticmethod
    def parse_gift_card_activity(html: str,
                                 config: AmazonOrdersConfig) -> List[GiftCardActivity]:
        """
        Parse an already-fetched Amazon Gift Card balance page into its GiftCardActivity, without a session
        driving the fetch. Only the GiftCardActivity on the given page is returned; paging is a fetch concern.

        :param html: The Gift Card balance page HTML to parse.
        :param config: The config providing the selectors used for parsing.
        :return: A list of the parsed GiftCardActivity, newest first.
        """
        parsed = BeautifulSoup(html, config.bs4_parser)
        activity, _ = _parse_gift_card_activity_page(parsed, config)

        return activity

    def get_balance(self) -> float:
        """
        Get the current Amazon Gift Card balance.

        :return: The Gift Card balance.
        """
        if not self.amazon_session.is_authenticated:
            raise AmazonOrdersError("Call AmazonSession.login() to authenticate first.")

        page_response = self.amazon_session.get(self.config.constants.GIFT_CARD_BALANCE_URL)
        self.amazon_session.check_response(page_response)

        balance_tag = util.select_one(page_response.parsed, self.config.selectors.GIFT_CARD_BALANCE_SELECTOR)
        balance = Parsable(balance_tag, self.config).to_currency(balance_tag.text) if balance_tag else None
        if balance is None:
            raise AmazonOrdersError("Could not parse Gift Card balance. Check if Amazon changed the HTML.")

        return balance

    def get_gift_card_activity(self,
                               days: int = 365,
                               next_page_url: Optional[str] = None,
                               keep_paging: bool = True) -> List[GiftCardActivity]:
        """
        Get Amazon Gift Card activity for a given number of days.

        :param days: The number of days worth of Gift Card activity to get.
        :param next_page_url: If a call to this method previously errored out, passing the exception's
            :attr:`~amazonorders.exception.AmazonOrdersError.meta` value for ``next_page_url`` will continue
            paging where it left off.
        :param keep_paging: ``False`` if only one page should be fetched.
        :return: A list of the requested GiftCardActivity, newest first.
        """
        if not self.amazon_session.is_authenticated:
            raise AmazonOrdersError("Call AmazonSession.login() to authenticate first.")

        url = next_page_url or self.config.constants.GIFT_CARD_BALANCE_URL
        min_date = datetime.date.today() - datetime.timedelta(days=days)

        activity: List[GiftCardActivity] = []
        while url:
            page_response = self.amazon_session.get(url)
            self.amazon_session.check_response(page_response, meta={"next_page_url": url})

            loaded_activity, next_page_url = _parse_gift_card_activity_page(page_response.parsed, self.config)

            for entry in loaded_activity:
                if entry.activity_date is None or entry.activity_date >= min_date:
                    activity.append(entry)
                else:
                    next_page_url = None
                    break

            url = next_page_url if keep_paging else None

        return activity
