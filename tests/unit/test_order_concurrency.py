__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import responses

from amazonorders.exception import AmazonOrdersError
from amazonorders.orders import AmazonOrders
from amazonorders.session import AmazonSession
from tests.unittestcase import UnitTestCase


class TestOrderConcurrency(UnitTestCase):
    def setUp(self):
        super().setUp()
        self.amazon_session = AmazonSession("example-user", "example-password", config=self.test_config)
        self.amazon_session.is_authenticated = True
        self.amazon_orders = AmazonOrders(self.amazon_session)

    def fetch_history(self, paged, full_details=False):
        if paged:
            return self.amazon_orders.get_order_history_page(
                year=2024, limit=10, full_details=full_details).items
        return self.amazon_orders.get_order_history(year=2024, keep_paging=False, full_details=full_details)

    @responses.activate
    def test_history_bounds_active_builds(self):
        for paged in [False, True]:
            with self.subTest(paged=paged):
                # GIVEN
                responses.reset()
                self.given_order_history_exists(2024)
                self.test_config.update_config("thread_pool_size", 2, save=False)
                build_order = self.amazon_orders._build_order
                lock = threading.Lock()
                release = threading.Event()
                over_limit = threading.Event()
                state = {"active": 0, "peak": 0}

                def blocked_build(*args):
                    with lock:
                        state["active"] += 1
                        state["peak"] = max(state["peak"], state["active"])
                        if state["active"] > 2:
                            over_limit.set()
                    try:
                        if not release.wait(5):
                            raise AssertionError("Order-build release deadline exceeded")
                        return build_order(*args)
                    finally:
                        with lock:
                            state["active"] -= 1

                def release_builds():
                    over_limit.wait(1)
                    release.set()

                coordinator = threading.Thread(target=release_builds)
                coordinator.start()

                # WHEN
                try:
                    with patch.object(self.amazon_orders, "_build_order", side_effect=blocked_build), \
                            patch.object(self.amazon_orders, "get_order", side_effect=lambda order_id, clone: clone):
                        orders = self.fetch_history(paged, full_details=True)
                finally:
                    release.set()
                    coordinator.join(5)

                # THEN
                self.assertFalse(coordinator.is_alive())
                self.assertEqual(len(orders), 10)
                self.assertEqual([order.index for order in orders], list(range(10)))
                self.assertGreater(state["peak"], 0)
                self.assertLessEqual(state["peak"], 2)
                self.assertEqual(state["active"], 0)

    @responses.activate
    def test_history_propagates_build_error_and_shuts_down_executor(self):
        for paged in [False, True]:
            with self.subTest(paged=paged):
                # GIVEN
                responses.reset()
                self.given_order_history_exists(2024)
                self.test_config.update_config("thread_pool_size", 2, save=False)
                pools = []

                def create_pool(**kwargs):
                    pool = ThreadPoolExecutor(**kwargs)
                    pools.append(pool)
                    return pool

                # WHEN
                with patch("amazonorders.orders.concurrent.futures.ThreadPoolExecutor", side_effect=create_pool), \
                        patch.object(self.amazon_orders, "_build_order",
                                     side_effect=AmazonOrdersError("Order build failed")):
                    with self.assertRaisesRegex(AmazonOrdersError, "Order build failed"):
                        self.fetch_history(paged)

                # THEN
                self.assertTrue(pools)
                for pool in pools:
                    with self.assertRaises(RuntimeError):
                        pool.submit(lambda: None)
