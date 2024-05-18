__copyright__ = "Copyright (c) 2024 Alex Laird"
__license__ = "MIT"

from amazonorders.exception import AmazonOrdersNotFoundError
from tests.integrationtestcase import IntegrationTestCase


class TestIntegration(IntegrationTestCase):
    """
    These integration tests look for and assert against specific orders. To run these tests and have them pass,
    contact the owner of the GitHub repo.
    """

    def test_get_order_history(self):
        # GIVEN
        year = 2018

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year)

        # THEN
        self.assertEqual(85, len(orders))
        self.assert_order_112_0399923_3070642(orders[3], False)

    def test_get_order_history_full_details(self):
        # GIVEN
        year = 2020
        start_index = 40

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year,
                                                      start_index=start_index,
                                                      full_details=True)

        # THEN
        self.assertEqual(10, len(orders))
        self.assert_order_114_9460922_7737063(orders[3], True)

    def test_get_order_history_multiple_items(self):
        # GIVEN
        year = 2020
        start_index = 40

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year,
                                                      start_index=start_index,
                                                      full_details=True)

        # THEN
        self.assert_order_113_1625648_3437067_multiple_items(orders[6], True)

    def test_get_order_history_return(self):
        # GIVEN
        year = 2020
        start_index = 50

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year,
                                                      start_index=start_index,
                                                      full_details=True)

        # THEN
        self.assert_order_112_2961628_4757846_return(orders[1], True)

    def test_get_order_history_quantity(self):
        # GIVEN
        year = 2020
        start_index = 50

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year,
                                                      start_index=start_index)

        # THEN
        self.assert_order_112_8888666_5244209_quantity(orders[7])

    def test_get_order_history_multiple_items_shipments_sellers(self):
        # GIVEN
        year = 2023
        start_index = 10

        # WHEN
        orders = self.amazon_orders.get_order_history(year=year,
                                                      start_index=start_index,
                                                      full_details=True)

        # THEN
        self.assert_order_112_9685975_5907428_multiple_items_shipments_sellers(
            orders[3], True)

    def test_get_order(self):
        # GIVEN
        order_id = "112-9685975-5907428"

        # WHEN
        order = self.amazon_orders.get_order(order_id)

        # THEN
        self.assert_order_112_9685975_5907428_multiple_items_shipments_sellers(
            order, True)

    def test_get_order_does_not_exist(self):
        # GIVEN
        order_id = "1234-fake-id"

        # WHEN
        with self.assertRaises(AmazonOrdersNotFoundError):
            self.amazon_orders.get_order(order_id)
