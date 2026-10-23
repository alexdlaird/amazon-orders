__copyright__ = "Copyright (c) 2026 Alex Laird"
__license__ = "MIT"

import os

import pytest

from tests.integrationtestcase import IntegrationTestCase


skip_unless_prime_payments = pytest.mark.skipif(
    not os.environ.get("AMAZON_INTEGRATION_TEST_PRIME_PAYMENTS", "False") == "True",
    reason="This test needs a Prime membership with at least one payment. Set "
           "AMAZON_INTEGRATION_TEST_PRIME_PAYMENTS=True explicitly to run.")


@skip_unless_prime_payments
class TestIntegrationAccount(IntegrationTestCase):
    """
    These integration tests run first, on a fresh session, since Amazon throttles some account pages, like the Prime
    payments, for a few minutes after a burst of requests, like the Order history with full details.
    """

    def test_get_prime_payments(self):
        # WHEN
        payments = self.amazon_prime.get_prime_payments()

        # THEN
        self.assertGreaterEqual(len(payments), 1)
        for payment in payments:
            self.assertIsNotNone(payment.payment_date)
            self.assertIsNotNone(payment.grand_total)
