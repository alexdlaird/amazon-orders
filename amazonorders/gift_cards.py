__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from amazonorders import util
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.gift_card_activity import GiftCardActivity
from amazonorders.exception import AmazonOrdersError
from amazonorders.paging import PagedResults
from amazonorders.session import AmazonSession

logger = logging.getLogger(__name__)


class GiftCards(PagedResults[GiftCardActivity]):
    """
    The Amazon Gift Card balance, with a batch of its activity and the cursor to fetch the next batch, from
    :func:`~amazonorders.gift_cards.AmazonGiftCards.get_gift_cards` or
    :func:`~amazonorders.gift_cards.AmazonGiftCards.get_gift_cards_page`.
    """

    def __init__(self,
                 items: List[GiftCardActivity],
                 cursor: Optional[Dict[str, Any]],
                 balance: Optional[float]) -> None:
        super().__init__(items, cursor)

        #: The current Gift Card balance, or ``None`` if Amazon didn't show one.
        self.balance: Optional[float] = balance

    def to_dict(self,
                exclude_none: bool = False) -> Dict[str, Any]:
        """
        Serialize the Gift Cards to a ``dict`` of primitives, suitable for JSON, as
        :func:`~amazonorders.paging.PagedResults.to_dict` does, with the ``balance``.

        :param exclude_none: Passed to each GiftCardActivity's ``to_dict``, and leaves out a ``None`` balance.
        :return: The ``balance``, ``items``, ``cursor``, and ``has_more``.
        """
        serialized = super().to_dict(exclude_none=exclude_none)
        if exclude_none and self.balance is None:
            return serialized

        return {"balance": self.balance, **serialized}


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

    @classmethod
    def parse_gift_cards(cls,
                         html: str,
                         config: AmazonOrdersConfig) -> GiftCards:
        """
        Parse an already-fetched Amazon Gift Card balance page into its balance and GiftCardActivity, without a
        session driving the fetch. Only the GiftCardActivity on the given page is returned; paging is a fetch concern.

        :param html: The Gift Card balance page HTML to parse.
        :param config: The config providing the selectors used for parsing.
        :return: The Gift Card balance and the page's GiftCardActivity, newest first.
        """
        parsed = BeautifulSoup(html, config.bs4_parser)
        activity, _ = cls._parse_gift_card_activity_page(parsed, config)

        return GiftCards(activity, None, cls._parse_gift_card_balance(parsed, config))

    def get_gift_cards(self,
                       days: int = 365,
                       keep_paging: bool = True,
                       progress: Optional[Callable[[int], None]] = None) -> GiftCards:
        """
        Get the Amazon Gift Card balance, and its activity for a given number of days. Both are on the same page, so
        ``days=0`` gets the balance (and only today's activity) in one request.

        :param days: The number of days worth of Gift Card activity to get.
        :param keep_paging: ``False`` if only one page should be fetched.
        :param progress: Called after each page of activity is fetched, with the number of GiftCardActivity
            entries found so far.
        :return: The Gift Card balance and the requested GiftCardActivity, newest first.
        """
        if not self.amazon_session.is_authenticated:
            raise AmazonOrdersError("Call AmazonSession.login() to authenticate first.")

        min_date = datetime.date.today() - datetime.timedelta(days=days)
        activity, balance, _ = self._collect_gift_cards(self.config.constants.GIFT_CARD_BALANCE_URL, min_date,
                                                        keep_paging, None, progress)

        return GiftCards(activity, None, balance)

    def get_gift_cards_page(self,
                            days: int = 365,
                            limit: Optional[int] = None,
                            cursor: Optional[Dict[str, Any]] = None,
                            progress: Optional[Callable[[int], None]] = None) -> GiftCards:
        """
        Get the Amazon Gift Card balance, and a batch of its activity for a given number of days, with a cursor to
        fetch the next batch.

        :param days: The number of days worth of Gift Card activity to get. Ignored when ``cursor`` is given.
        :param limit: Stop fetching activity pages once at least this many GiftCardActivity entries are collected.
            Whole pages are fetched, so the batch can hold up to a page more than ``limit``. ``None`` fetches every
            page.
        :param cursor: The :attr:`~amazonorders.paging.PagedResults.cursor` of the previous batch, to fetch the
            next one. The ``days`` window it was fetched with carries over.
        :param progress: Called after each page of activity is fetched, with the number of GiftCardActivity
            entries found so far in this batch.
        :return: The Gift Card balance, the batch of GiftCardActivity, and the cursor for the next one.
        """
        if not self.amazon_session.is_authenticated:
            raise AmazonOrdersError("Call AmazonSession.login() to authenticate first.")

        if cursor:
            url = util.resolve_site_url(cursor["next_page_url"], self.config.constants.BASE_URL)
            if not url:
                raise AmazonOrdersError("The cursor's next page is not on this Amazon site.")
            min_date = datetime.date.fromisoformat(cursor["min_date"])
        else:
            url = self.config.constants.GIFT_CARD_BALANCE_URL
            min_date = datetime.date.today() - datetime.timedelta(days=days)

        activity, balance, next_page_url = self._collect_gift_cards(url, min_date, True, limit, progress)
        next_cursor = {
            "next_page_url": next_page_url,
            "min_date": min_date.isoformat(),
        } if next_page_url else None

        return GiftCards(activity, next_cursor, balance)

    def _collect_gift_cards(self,
                            url: Optional[str],
                            min_date: datetime.date,
                            keep_paging: bool,
                            limit: Optional[int],
                            progress: Optional[Callable[[int], None]]
                            ) -> Tuple[List[GiftCardActivity], Optional[float], Optional[str]]:
        """
        Fetch Gift Card balance pages until the activity ends, an entry is older than ``min_date``, ``keep_paging``
        is ``False`` after the first page, or at least ``limit`` entries are collected.

        :return: The GiftCardActivity, the balance from the first page fetched, and the next page's URL (``None`` if
            there is none).
        """
        balance: Optional[float] = None
        activity: List[GiftCardActivity] = []
        first_page = True
        while url and (first_page or (keep_paging and (limit is None or len(activity) < limit))):
            page_response = self.amazon_session.get(url)
            self.amazon_session.check_response(page_response, meta={"next_page_url": url})

            if first_page:
                balance = self._parse_gift_card_balance(page_response.parsed, self.config)
                first_page = False

            loaded_activity, url = self._parse_gift_card_activity_page(page_response.parsed, self.config)

            for entry in loaded_activity:
                if entry.activity_date is None or entry.activity_date >= min_date:
                    activity.append(entry)
                else:
                    url = None
                    break

            if progress:
                progress(len(activity))

        return activity, balance, url

    @staticmethod
    def _parse_gift_card_balance(parsed: Tag,
                                 config: AmazonOrdersConfig) -> Optional[float]:
        balance_tag = util.select_one(parsed, config.selectors.GIFT_CARD_BALANCE_SELECTOR)

        return config.constants.parse_currency(balance_tag.text) if balance_tag else None

    @classmethod
    def _parse_gift_card_activity_page(cls,
                                       parsed: Tag,
                                       config: AmazonOrdersConfig) -> Tuple[List[GiftCardActivity], Optional[str]]:
        """
        Parse the GiftCardActivity rows and the next page link off a Gift Card balance page.

        :param parsed: The parsed Gift Card balance page.
        :param config: The config providing the selectors.
        :return: The page's GiftCardActivity, and the next page's URL or ``None`` on the last page.
        """
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
            next_page_url = util.resolve_site_url(str(next_page_link["href"]), config.constants.BASE_URL)

        return activity, next_page_url
