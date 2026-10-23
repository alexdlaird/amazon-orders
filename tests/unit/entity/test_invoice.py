__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os

from bs4 import BeautifulSoup

from amazonorders.entity.invoice import Invoice
from amazonorders.orders import AmazonOrders
from tests.unittestcase import UnitTestCase


class TestInvoice(UnitTestCase):
    def given_invoice_list(self, filename):
        with open(os.path.join(self.RESOURCES_DIR, "invoices", filename), "r", encoding="utf-8") as f:
            return f.read()

    def test_parse_invoices_single(self):
        # WHEN
        html = self.given_invoice_list("invoice-pdfs-single.html")
        invoices = AmazonOrders.parse_invoices(html, self.test_config, order_number="302-0000000-0000001")

        # THEN
        self.assertEqual(2, len(invoices))
        summary = invoices[0]
        self.assertEqual("Printable Order Summary", summary.name)
        self.assertEqual("html", summary.format)
        self.assertIn("/gp/css/summary/print.html?orderID=302-0000000-0000001", summary.link)
        self.assertFalse(summary.is_credit_note)
        invoice = invoices[1]
        self.assertEqual("302-0000000-0000001", invoice.order_number)
        self.assertEqual("Invoice", invoice.name)
        self.assertEqual("pdf", invoice.format)
        self.assertEqual(f"{self.test_config.constants.BASE_URL}/-/en/documents/download/"
                         f"00000000-0000-4000-8000-000000000001/invoice.pdf", invoice.link)
        self.assertFalse(invoice.is_credit_note)

    def test_parse_invoices_multiple_with_credit_note(self):
        # WHEN
        html = self.given_invoice_list("invoice-pdfs-multiple.html")
        invoices = AmazonOrders.parse_invoices(html, self.test_config, order_number="302-0000000-0000002")

        # THEN
        self.assertEqual(["Printable Order Summary", "Invoice 1", "Invoice 2", "Invoice 3", "Invoice 4",
                          "Credit note"], [invoice.name for invoice in invoices])
        self.assertEqual(["html", "pdf", "pdf", "pdf", "pdf", "pdf"], [invoice.format for invoice in invoices])
        self.assertEqual([False, False, False, False, False, True], [invoice.is_credit_note for invoice in invoices])
        for invoice in invoices[1:]:
            self.assertTrue(invoice.link.endswith("/invoice.pdf"))

    def test_parse_invoices_only_order_summary_leaves_out_request_link(self):
        # WHEN
        html = self.given_invoice_list("invoice-pdfs-none.html")
        invoices = AmazonOrders.parse_invoices(html, self.test_config)

        # THEN
        self.assertEqual([("Printable Order Summary", "html")],
                         [(invoice.name, invoice.format) for invoice in invoices])

    def test_parse_invoices_leaves_out_seller_receipt(self):
        # WHEN
        html = self.given_invoice_list("invoice-pdfs-receipt-only.html")
        invoices = AmazonOrders.parse_invoices(html, self.test_config)

        # THEN
        self.assertEqual([("Printable Order Summary", "html")],
                         [(invoice.name, invoice.format) for invoice in invoices])

    def test_deprecated_parse_invoice_pdfs(self):
        # GIVEN
        html = self.given_invoice_list("invoice-pdfs-multiple.html")

        # WHEN
        with self.assertWarns(DeprecationWarning):
            invoices = AmazonOrders.parse_invoice_pdfs(html, self.test_config, order_number="302-0000000-0000002")

        # THEN
        self.assertEqual(5, len(invoices))
        self.assertEqual({"pdf"}, {invoice.format for invoice in invoices})

    def test_invoice_without_name_or_link(self):
        # WHEN
        invoice = Invoice(BeautifulSoup("<a> </a>", "html.parser").a, self.test_config)

        # THEN
        self.assertIsNone(invoice.name)
        self.assertIsNone(invoice.link)
        self.assertIsNone(invoice.format)
        self.assertFalse(invoice.is_credit_note)

    def test_invoice_to_dict(self):
        # GIVEN
        html = self.given_invoice_list("invoice-pdfs-single.html")
        invoice = AmazonOrders.parse_invoices(html, self.test_config, order_number="302-0000000-0000001")[1]

        # WHEN
        serialized = invoice.to_dict()

        # THEN
        self.assertEqual({
            "order_number": "302-0000000-0000001",
            "format": "pdf",
            "name": "Invoice",
            "link": f"{self.test_config.constants.BASE_URL}/-/en/documents/download/"
                    f"00000000-0000-4000-8000-000000000001/invoice.pdf",
            "is_credit_note": False,
        }, serialized)
