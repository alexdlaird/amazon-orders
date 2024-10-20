__copyright__ = "Copyright (c) 2024 Jeff Sawatzky"
__license__ = "MIT"

from datetime import date

from bs4 import BeautifulSoup

from amazonorders.entity.transaction import Transaction
from tests.unittestcase import UnitTestCase


class TestTransaction(UnitTestCase):
    def test_parse(self):
        # GIVEN
        html = """
<div class="a-section a-spacing-base apx-transactions-line-item-component-container">
    <div data-pmts-component-id="pp-nlFfdK-6" class="a-row pmts-portal-component pmts-portal-components-pp-nlFfdK-6">
        <div class="a-column a-span9">
            <span class="a-size-base a-text-bold">My Payment Method</span>
        </div>
        <div class="a-column a-span3 a-text-right a-span-last">
            <span class="a-size-base-plus a-text-bold">-CA$12.34</span>
        </div>
    </div>
    <div data-pmts-component-id="pp-nlFfdK-6" class="a-section a-spacing-none a-spacing-top-mini pmts-portal-component pmts-portal-components-pp-nlFfdK-6">
        <div class="a-row">
            <div class="a-column a-span12">
                <a id="pp-nlFfdK-52" class="a-link-normal" href="https://www.amazon.com/gp/css/summary/edit.html?orderID=123-4567890-1234567">Order #123-4567890-1234567</a>
            </div>
        </div>
    </div>
    <div data-pmts-component-id="pp-nlFfdK-6" class="a-section a-spacing-none a-spacing-top-mini pmts-portal-component pmts-portal-components-pp-nlFfdK-6">
        <div class="a-row">
            <div class="a-column a-span12">
                <span class="a-size-base">AMZN Mktp COM</span>
            </div>
        </div>
    </div>
</div>
"""  # noqa

        parsed = BeautifulSoup(html, "html.parser")

        # WHEN
        transaction = Transaction(parsed, self.test_config, date(2024, 1, 1))

        # THEN
        self.assertEqual(transaction.completed_date, date(2024, 1, 1))
        self.assertEqual(transaction.payment_method, "My Payment Method")
        self.assertEqual(transaction.order_number, "123-4567890-1234567")
        self.assertEqual(transaction.seller, "AMZN Mktp COM")
        self.assertEqual(transaction.grand_total, -12.34)
        self.assertEqual(transaction.is_refund, False)
        self.assertEqual(str(transaction), "Transaction 2024-01-01: Order #123-4567890-1234567, Grand Total -12.34")
        self.assertEqual(
            repr(transaction), '<Transaction 2024-01-01: "Order #123-4567890-1234567", "Grand Total -12.34">'
        )

    def test_parse_refund(self):
        # GIVEN
        html = """
<div class="a-section a-spacing-base apx-transactions-line-item-component-container">
    <div data-pmts-component-id="pp-nlFfdK-6" class="a-row pmts-portal-component pmts-portal-components-pp-nlFfdK-6">
        <div class="a-column a-span9">
            <span class="a-size-base a-text-bold">My Payment Method</span>
        </div>
        <div class="a-column a-span3 a-text-right a-span-last">
            <span class="a-size-base-plus a-text-bold">+CA$12.34</span>
        </div>
    </div>
    <div data-pmts-component-id="pp-nlFfdK-6" class="a-section a-spacing-none a-spacing-top-mini pmts-portal-component pmts-portal-components-pp-nlFfdK-6">
        <div class="a-row">
            <div class="a-column a-span12">
                <a id="pp-nlFfdK-52" class="a-link-normal" href="https://www.amazon.com/gp/css/summary/edit.html?orderID=123-4567890-1234567">Refund: Order #123-4567890-1234567</a>
            </div>
        </div>
    </div>
    <div data-pmts-component-id="pp-nlFfdK-6" class="a-section a-spacing-none a-spacing-top-mini pmts-portal-component pmts-portal-components-pp-nlFfdK-6">
        <div class="a-row">
            <div class="a-column a-span12">
                <span class="a-size-base">AMZN Mktp COM</span>
            </div>
        </div>
    </div>
</div>
"""  # noqa

        parsed = BeautifulSoup(html, "html.parser")

        # WHEN
        transaction = Transaction(parsed, self.test_config, date(2024, 1, 1))

        # THEN
        self.assertEqual(transaction.completed_date, date(2024, 1, 1))
        self.assertEqual(transaction.payment_method, "My Payment Method")
        self.assertEqual(transaction.order_number, "123-4567890-1234567")
        self.assertEqual(transaction.seller, "AMZN Mktp COM")
        self.assertEqual(transaction.grand_total, 12.34)
        self.assertEqual(transaction.is_refund, True)
        self.assertEqual(str(transaction), "Transaction 2024-01-01: Order #123-4567890-1234567, Grand Total 12.34")
        self.assertEqual(
            repr(transaction), '<Transaction 2024-01-01: "Order #123-4567890-1234567", "Grand Total 12.34">'
        )
