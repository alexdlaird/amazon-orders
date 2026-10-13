__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os

from amazonorders.orders import AmazonOrders
from tests.unittestcase import UnitTestCase


class TestInvoice(UnitTestCase):
    def given_invoice_list(self, filename):
        with open(os.path.join(self.RESOURCES_DIR, "invoices", filename), "r", encoding="utf-8") as f:
            return f.read()

    def test_parse_invoices_single(self):
        # WHEN
        invoices = AmazonOrders.parse_invoices(self.given_invoice_list("invoices-single.html"), self.test_config,
                                               order_number="302-0000000-0000001")

        # THEN
        self.assertEqual(1, len(invoices))
        invoice = invoices[0]
        self.assertEqual("302-0000000-0000001", invoice.order_number)
        self.assertEqual("Invoice", invoice.name)
        self.assertEqual(f"{self.test_config.constants.BASE_URL}/-/en/documents/download/"
                         f"00000000-0000-4000-8000-000000000001/invoice.pdf", invoice.link)
        self.assertFalse(invoice.credit_note)

    def test_parse_invoices_multiple_with_credit_note(self):
        # WHEN
        invoices = AmazonOrders.parse_invoices(self.given_invoice_list("invoices-multiple.html"), self.test_config,
                                               order_number="302-0000000-0000002")

        # THEN
        self.assertEqual(["Invoice 1", "Invoice 2", "Invoice 3", "Invoice 4", "Credit note"],
                         [invoice.name for invoice in invoices])
        self.assertEqual([False, False, False, False, True], [invoice.credit_note for invoice in invoices])
        for invoice in invoices:
            self.assertTrue(invoice.link.endswith("/invoice.pdf"))

    def test_parse_invoices_leaves_out_order_summary_and_request_link(self):
        # WHEN
        invoices = AmazonOrders.parse_invoices(self.given_invoice_list("invoices-none.html"), self.test_config)

        # THEN
        self.assertEqual([], invoices)

    def test_invoice_to_dict(self):
        # GIVEN
        invoice = AmazonOrders.parse_invoices(self.given_invoice_list("invoices-single.html"), self.test_config,
                                              order_number="302-0000000-0000001")[0]

        # WHEN
        serialized = invoice.to_dict()

        # THEN
        self.assertEqual({
            "order_number": "302-0000000-0000001",
            "name": "Invoice",
            "link": f"{self.test_config.constants.BASE_URL}/-/en/documents/download/"
                    f"00000000-0000-4000-8000-000000000001/invoice.pdf",
            "credit_note": False,
        }, serialized)
