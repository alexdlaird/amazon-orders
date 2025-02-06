__copyright__ = "Copyright (c) 2024 Jeff Sawatzky"
__license__ = "MIT"

import datetime
import os
from unittest.mock import Mock, patch

import responses
from bs4 import BeautifulSoup

from amazonorders.session import AmazonSession
from amazonorders.transactions import AmazonTransactions, _parse_transaction_form_tag
from tests.unittestcase import UnitTestCase


class TestOrders(UnitTestCase):
    temp_order_history_file_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), "output", "temp-order-history.html"
    )
    temp_order_details_file_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), "output", "temp-order-details.html"
    )

    def setUp(self):
        super().setUp()

        self.amazon_session = AmazonSession(
            "some-username", "some-password", config=self.test_config
        )

        self.amazon_transactions = AmazonTransactions(self.amazon_session)

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_transactions_command(self, mock_get_today: Mock):
        # GIVEN
        mock_get_today.date.today.return_value = datetime.date(2024, 10, 11)
        days = 1
        self.amazon_session.is_authenticated = True
        with open(
                os.path.join(self.RESOURCES_DIR, "get-transactions.html"),
                "r",
                encoding="utf-8",
        ) as f:
            responses.add(
                responses.GET,
                f"{self.test_config.constants.TRANSACTION_HISTORY_LANDING_URL}",
                body=f.read(),
                status=200,
            )

        # WHEN
        transactions = self.amazon_transactions.get_transactions(days=days)

        # THEN
        self.assertEqual(1, len(transactions))

    def test_parse_transaction_form_tag(self):
        # GIVEN
        parsed = BeautifulSoup(TEST_PARSE_TRANSACTION_FORM_TAG_HTML, self.test_config.bs4_parser)
        form_tag = parsed.select_one("form")

        # WHEN
        transactions, next_page_url, next_page_data = _parse_transaction_form_tag(
            form_tag, self.test_config
        )

        # THEN
        self.assertEqual(len(transactions), 2)
        self.assertEqual(
            next_page_url, "https://www.amazon.com:443/cpe/yourpayments/transactions"
        )
        self.assertEqual(
            next_page_data,
            {
                "ppw-widgetState": "the-ppw-widgetState",
                "ie": "UTF-8",
                'ppw-widgetEvent:DefaultNextPageNavigationEvent:{"nextPageKey":"key"}': "",
            },
        )


TEST_PARSE_TRANSACTION_FORM_TAG_HTML = """
<form action="https://www.amazon.com:443/cpe/yourpayments/transactions" class="a-spacing-none" method="post"><input
        name="ppw-widgetState" type="hidden" value="the-ppw-widgetState" /><input name="ie" type="hidden"
        value="UTF-8" />
    <div class="a-box-group a-spacing-base">
        <div class="a-box a-spacing-none a-box-title apx-transactions-sleeve-header-container">
            <div class="a-box-inner a-padding-base"><span class="a-size-base a-text-bold">Completed</span></div>
        </div>
        <div class="a-box a-spacing-base">
            <div class="a-box-inner a-padding-none">
                <div class="a-section a-spacing-base a-padding-base apx-transaction-date-container pmts-portal-component pmts-portal-components-pp-kXMaEm-3"
                    data-pmts-component-id="pp-kXMaEm-3"><span>October 11, 2024</span></div>
                <div class="a-section a-spacing-base pmts-portal-component pmts-portal-components-pp-kXMaEm-3"
                    data-pmts-component-id="pp-kXMaEm-3">
                    <div class="a-section a-spacing-base apx-transactions-line-item-component-container">
                        <div class="a-row pmts-portal-component pmts-portal-components-pp-kXMaEm-4"
                            data-pmts-component-id="pp-kXMaEm-4">
                            <div class="a-column a-span9"><span class="a-size-base a-text-bold">Visa ****1234</span>
                            </div>
                            <div class="a-column a-span3 a-text-right a-span-last"><span
                                    class="a-size-base-plus a-text-bold">-CA$45.19</span></div>
                        </div>
                        <div class="a-section a-spacing-none a-spacing-top-mini pmts-portal-component pmts-portal-components-pp-kXMaEm-4"
                            data-pmts-component-id="pp-kXMaEm-4">
                            <div class="a-row">
                                <div class="a-column a-span12"><a class="a-link-normal"
                                        href="https://www.amazon.ca/gp/css/summary/edit.html?orderID=123-4567890-1234567"
                                        id="pp-kXMaEm-50">Order #123-4567890-1234567</a></div>
                            </div>
                        </div>
                        <div class="a-section a-spacing-none a-spacing-top-mini pmts-portal-component pmts-portal-components-pp-kXMaEm-4"
                            data-pmts-component-id="pp-kXMaEm-4">
                            <div class="a-row">
                                <div class="a-column a-span12"><span class="a-size-base">AMZN Mktp CA</span></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="a-section a-spacing-base a-padding-base apx-transaction-date-container pmts-portal-component pmts-portal-components-pp-kXMaEm-8"
                    data-pmts-component-id="pp-kXMaEm-8"><span>October 9, 2024</span></div>
                <div class="a-section a-spacing-base pmts-portal-component pmts-portal-components-pp-kXMaEm-8"
                    data-pmts-component-id="pp-kXMaEm-8">
                    <div class="a-section a-spacing-base apx-transactions-line-item-component-container">
                        <div class="a-row pmts-portal-component pmts-portal-components-pp-kXMaEm-9"
                            data-pmts-component-id="pp-kXMaEm-9">
                            <div class="a-column a-span9"><span class="a-size-base a-text-bold">Mastercard
                                    ****1234</span></div>
                            <div class="a-column a-span3 a-text-right a-span-last"><span
                                    class="a-size-base-plus a-text-bold">-CA$28.79</span></div>
                        </div>
                        <div class="a-section a-spacing-none a-spacing-top-mini pmts-portal-component pmts-portal-components-pp-kXMaEm-9"
                            data-pmts-component-id="pp-kXMaEm-9">
                            <div class="a-row">
                                <div class="a-column a-span12"><a class="a-link-normal"
                                        href="https://www.amazon.ca/gp/css/summary/edit.html?orderID=123-4567890-1234567"
                                        id="pp-kXMaEm-52">Order #123-4567890-1234567</a></div>
                            </div>
                        </div>
                        <div class="a-section a-spacing-none a-spacing-top-mini pmts-portal-component pmts-portal-components-pp-kXMaEm-9"
                            data-pmts-component-id="pp-kXMaEm-9">
                            <div class="a-row">
                                <div class="a-column a-span12"><span class="a-size-base">Amazon.ca</span></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <div class="a-row a-spacing-top-extra-large">
        <div class="a-column a-span2 a-text-center"><span class="a-button a-button-span12 a-button-base"><span
                    class="a-button-inner"><input class="a-button-input"
                        name='ppw-widgetEvent:DefaultPreviousPageNavigationEvent:{"previousPageKey":"key"}'
                        type="submit" /><span aria-hidden="true" class="a-button-text">Previous
                        Page</span></span></span></div>
        <div class="a-column a-span2 a-text-center a-span-last"><span
                class="a-button a-button-span12 a-button-base"><span class="a-button-inner"><input
                        class="a-button-input"
                        name='ppw-widgetEvent:DefaultNextPageNavigationEvent:{"nextPageKey":"key"}'
                        type="submit" /><span aria-hidden="true" class="a-button-text">Next Page</span></span></span>
        </div>
    </div>
</form>
"""  # noqa
