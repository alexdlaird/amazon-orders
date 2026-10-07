__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import logging
from typing import List, Optional

from bs4 import BeautifulSoup, Tag

from amazonorders import util
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.prime_payment import PrimePayment
from amazonorders.exception import AmazonOrdersError
from amazonorders.session import AmazonSession

logger = logging.getLogger(__name__)


class AmazonPrime:
    """
    Using an authenticated :class:`~amazonorders.session.AmazonSession`, can be used to query Amazon
    for the Prime membership payment history.

    Membership fees are digital Orders (``D01-`` IDs) that neither the Order history nor the Digital Orders
    tab lists, so the Prime payments page is the only listing of them. Each
    :class:`~amazonorders.entity.prime_payment.PrimePayment` carries the Order number, and the Order itself
    is fetched with :func:`~amazonorders.orders.AmazonOrders.get_order`.
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
    def parse_prime_payments(cls,
                             html: str,
                             config: AmazonOrdersConfig) -> List[PrimePayment]:
        """
        Parse an already-fetched Prime payments page into its PrimePayments, without a session driving the fetch.

        :param html: The Prime payments page HTML to parse.
        :param config: The config providing the selectors used for parsing.
        :return: A list of the parsed PrimePayments, newest first.
        """
        parsed = BeautifulSoup(html, config.bs4_parser)

        return cls._parse_prime_payments(parsed, config)

    def get_prime_payments(self) -> List[PrimePayment]:
        """
        Get every charge in the Prime membership payment history.

        This is best-effort: Membership Central has served this library an error page in place of the payments,
        on a session that had just read the Order history, while a browser on the same account got them. If
        that happens, the page fetched in a browser can be parsed with :func:`parse_prime_payments`.

        :return: A list of the PrimePayments, newest first.
        """
        if not self.amazon_session.is_authenticated:
            raise AmazonOrdersError("Call AmazonSession.login() to authenticate first.")

        page_response = self.amazon_session.get(self.config.constants.PRIME_PAYMENTS_URL)
        self.amazon_session.check_response(page_response)

        return self._parse_prime_payments(page_response.parsed, self.config)

    @classmethod
    def _parse_prime_payments(cls,
                              parsed: Tag,
                              config: AmazonOrdersConfig) -> List[PrimePayment]:
        """
        Parse the PrimePayment cards off a Prime payments page.

        :param parsed: The parsed Prime payments page.
        :param config: The config providing the selectors.
        :return: The page's PrimePayments, or an empty list when the payment history has none.
        """
        widget_tag = util.select_one(parsed, config.selectors.PRIME_PAYMENTS_WIDGET_SELECTOR)

        if not widget_tag:
            raise AmazonOrdersError("Could not parse Prime payments. Check if Amazon changed the HTML.")

        return [PrimePayment(payment_tag, config)
                for payment_tag in util.select(widget_tag, config.selectors.PRIME_PAYMENT_SELECTOR)]
