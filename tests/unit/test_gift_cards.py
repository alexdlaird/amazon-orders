__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import os
from unittest.mock import patch

import responses

from amazonorders.exception import AmazonOrdersAuthRedirectError, AmazonOrdersError
from amazonorders.gift_cards import AmazonGiftCards
from amazonorders.session import AmazonSession
from tests.unittestcase import UnitTestCase


class TestGiftCards(UnitTestCase):
    def setUp(self):
        super().setUp()

        self.amazon_session = AmazonSession("some-username@gmail.com",
                                            "some-password",
                                            config=self.test_config)

        self.amazon_gift_cards = AmazonGiftCards(self.amazon_session)

    def given_gift_card_page_exists(self, html_file):
        with open(os.path.join(self.RESOURCES_DIR, "giftcards", html_file), "r", encoding="utf-8") as f:
            return responses.add(
                responses.GET,
                f"{self.test_config.constants.GIFT_CARD_BALANCE_URL}",
                body=f.read(),
                status=200,
            )

    def read_gift_card_page(self, html_file):
        with open(os.path.join(self.RESOURCES_DIR, "giftcards", html_file), "r", encoding="utf-8") as f:
            return f.read()

    def test_get_balance_unauthenticated(self):
        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_gift_cards.get_balance()

        self.assertEqual("Call AmazonSession.login() to authenticate first.", str(cm.exception))

    def test_get_gift_card_activity_unauthenticated(self):
        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_gift_cards.get_gift_card_activity()

        self.assertEqual("Call AmazonSession.login() to authenticate first.", str(cm.exception))

    @responses.activate
    def test_get_balance_session_expires(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        auth_redirect_response = self.given_authenticated_url_renders_login()
        signout_response = self.given_logout_response_success()

        # WHEN
        with self.assertRaises(AmazonOrdersAuthRedirectError) as cm:
            self.amazon_gift_cards.get_balance()

        self.assertIn("Amazon redirected to login.", str(cm.exception))
        self.assertFalse(self.amazon_session.is_authenticated)
        self.assertEqual(1, auth_redirect_response.call_count)
        self.assertEqual(1, signout_response.call_count)

    @responses.activate
    def test_get_balance(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        resp = self.given_gift_card_page_exists("gift-card-balance-activity.html")

        # WHEN
        balance = self.amazon_gift_cards.get_balance()

        # THEN
        self.assertEqual(0.00, balance)
        self.assertEqual(1, resp.call_count)

    @responses.activate
    def test_get_balance_invalid_page(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        with open(os.path.join(self.RESOURCES_DIR, "500.html"), "r", encoding="utf-8") as f:
            resp = responses.add(
                responses.GET,
                f"{self.test_config.constants.GIFT_CARD_BALANCE_URL}",
                body=f.read(),
                status=200,
            )

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_gift_cards.get_balance()

        # THEN
        self.assertEqual(1, resp.call_count)
        self.assertIn("Could not parse Gift Card balance.", str(cm.exception))

    @responses.activate
    @patch("amazonorders.gift_cards.datetime", wraps=datetime)
    def test_get_gift_card_activity(self, mock_today):
        # GIVEN
        mock_today.date.today.return_value = datetime.date(2026, 5, 15)
        self.amazon_session.is_authenticated = True
        resp = self.given_gift_card_page_exists("gift-card-balance-activity.html")

        # WHEN
        activity = self.amazon_gift_cards.get_gift_card_activity(keep_paging=False)

        # THEN
        self.assertEqual(15, len(activity))
        self.assertEqual(1, resp.call_count)
        entry = activity[0]
        self.assertEqual(datetime.date(2026, 5, 12), entry.activity_date)
        self.assertEqual("Gift Card applied to Amazon.com order", entry.description)
        self.assertEqual(-19.48, entry.amount)
        self.assertFalse(entry.is_credit)
        self.assertEqual(0.00, entry.closing_balance)
        self.assertEqual("111-5500901-2478601", entry.order_number)
        self.assertEqual("https://www.amazon.com/gp/your-account/order-details/ref=gcf_b_bp_lpo_c_d_b_x"
                         "?ie=UTF8&orderID=111-5500901-2478601", entry.order_details_link)
        entry = activity[1]
        self.assertEqual("Gift Card Balance added from Reload", entry.description)
        self.assertEqual(19.48, entry.amount)
        self.assertTrue(entry.is_credit)
        self.assertEqual(19.48, entry.closing_balance)
        entry = activity[6]
        self.assertEqual(-2.90, entry.amount)
        self.assertEqual("D01-1000111-2000222", entry.order_number)
        self.assertIn("orderID=D01-1000111-2000222", entry.order_details_link)
        entry = activity[7]
        self.assertEqual("Refund from Amazon.com order", entry.description)
        self.assertTrue(entry.is_credit)
        self.assertIsNone(entry.order_number)
        self.assertIsNone(entry.order_details_link)

    @responses.activate
    @patch("amazonorders.gift_cards.datetime", wraps=datetime)
    def test_get_gift_card_activity_paginated(self, mock_today):
        # GIVEN
        mock_today.date.today.return_value = datetime.date(2026, 5, 15)
        self.amazon_session.is_authenticated = True
        resp1 = self.given_gift_card_page_exists("gift-card-balance-activity.html")
        resp2 = self.given_gift_card_page_exists("gift-card-balance-activity-page-2.html")
        resp3 = self.given_gift_card_page_exists("gift-card-balance-activity-last-page.html")

        # WHEN
        activity = self.amazon_gift_cards.get_gift_card_activity(days=4000)

        # THEN
        self.assertEqual(41, len(activity))
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(1, resp3.call_count)
        self.assertIn("next=", resp2.calls[0].request.url)
        self.assertIn("next=", resp3.calls[0].request.url)
        self.assertEqual(datetime.date(2015, 12, 30), activity[-1].activity_date)

    @responses.activate
    @patch("amazonorders.gift_cards.datetime", wraps=datetime)
    def test_get_gift_card_activity_days_filter(self, mock_today):
        # GIVEN
        mock_today.date.today.return_value = datetime.date(2026, 5, 12)
        self.amazon_session.is_authenticated = True
        resp = self.given_gift_card_page_exists("gift-card-balance-activity.html")

        # WHEN
        activity = self.amazon_gift_cards.get_gift_card_activity(days=5)

        # THEN
        self.assertEqual(2, len(activity))
        self.assertEqual(datetime.date(2026, 5, 11), activity[1].activity_date)
        self.assertEqual(1, resp.call_count)

    @responses.activate
    def test_get_gift_card_activity_zero_activity(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        resp = self.given_gift_card_page_exists("gift-card-balance-zero-activity.html")

        # WHEN
        activity = self.amazon_gift_cards.get_gift_card_activity()

        # THEN
        self.assertEqual([], activity)
        self.assertEqual(1, resp.call_count)

    @responses.activate
    def test_get_gift_card_activity_invalid_page(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        with open(os.path.join(self.RESOURCES_DIR, "500.html"), "r", encoding="utf-8") as f:
            resp = responses.add(
                responses.GET,
                f"{self.test_config.constants.GIFT_CARD_BALANCE_URL}",
                body=f.read(),
                status=200,
            )

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_gift_cards.get_gift_card_activity(keep_paging=False)

        # THEN
        self.assertEqual(1, resp.call_count)
        self.assertIn("Could not parse Gift Card activity.", str(cm.exception))

    def test_parse_gift_card_activity_redemptions(self):
        # GIVEN
        html = self.read_gift_card_page("gift-card-balance-activity-page-2.html")

        # WHEN
        activity = AmazonGiftCards.parse_gift_card_activity(html, self.test_config)

        # THEN
        self.assertEqual(15, len(activity))
        entry = activity[0]
        self.assertEqual(datetime.date(2025, 7, 14), entry.activity_date)
        self.assertEqual("Gift Card added", entry.description)
        self.assertEqual(13.70, entry.amount)
        self.assertTrue(entry.is_credit)
        self.assertEqual(212.53, entry.closing_balance)
        self.assertIsNone(entry.order_number)
        self.assertIsNone(entry.order_details_link)
        self.assertEqual("D01-1004551-2009102", activity[1].order_number)

    def test_parse_gift_card_activity_legacy_order_numbers(self):
        # GIVEN
        html = self.read_gift_card_page("gift-card-balance-activity-last-page.html")

        # WHEN
        activity = AmazonGiftCards.parse_gift_card_activity(html, self.test_config)

        # THEN
        self.assertEqual(11, len(activity))
        self.assertEqual(["4000-100001-2000001", "4000-100002-2000002", "4000-100003-2000003", "4000-100004-2000004"],
                         [entry.order_number for entry in activity[6:10]])
        self.assertIn("orderID=4000-100001-2000001", activity[6].order_details_link)

    def test_parse_gift_card_activity_closing_balances_chain(self):
        # GIVEN
        html = self.read_gift_card_page("gift-card-balance-activity.html")

        # WHEN
        activity = AmazonGiftCards.parse_gift_card_activity(html, self.test_config)

        # THEN
        for newer, older in zip(activity, activity[1:]):
            self.assertAlmostEqual(older.closing_balance + newer.amount, newer.closing_balance, places=2)
