__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import os
import re
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

    def test_get_gift_cards_unauthenticated(self):
        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_gift_cards.get_gift_cards()

        self.assertEqual("Call AmazonSession.login() to authenticate first.", str(cm.exception))

    @responses.activate
    def test_get_gift_cards_session_expires(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        auth_redirect_response = self.given_authenticated_url_renders_login()
        signout_response = self.given_logout_response_success()

        # WHEN
        with self.assertRaises(AmazonOrdersAuthRedirectError) as cm:
            self.amazon_gift_cards.get_gift_cards()

        self.assertIn("Amazon redirected to login.", str(cm.exception))
        self.assertTrue(self.amazon_session.is_authenticated)
        self.assertEqual(1, auth_redirect_response.call_count)
        self.assertEqual(0, signout_response.call_count)

    @responses.activate
    @patch("amazonorders.gift_cards.datetime", wraps=datetime)
    def test_get_gift_cards_balance_only(self, mock_today):
        # GIVEN
        mock_today.date.today.return_value = datetime.date(2026, 5, 15)
        self.amazon_session.is_authenticated = True
        resp = self.given_gift_card_page_exists("gift-card-balance-activity.html")

        # WHEN
        gift_cards = self.amazon_gift_cards.get_gift_cards(days=0)

        # THEN
        self.assertEqual(0.00, gift_cards.balance)
        self.assertEqual([], gift_cards.items)
        self.assertEqual(1, resp.call_count)

    @responses.activate
    @patch("amazonorders.gift_cards.datetime", wraps=datetime)
    def test_get_gift_cards(self, mock_today):
        # GIVEN
        mock_today.date.today.return_value = datetime.date(2026, 5, 15)
        self.amazon_session.is_authenticated = True
        resp = self.given_gift_card_page_exists("gift-card-balance-activity.html")

        # WHEN
        gift_cards = self.amazon_gift_cards.get_gift_cards(keep_paging=False)

        # THEN
        self.assertEqual(0.00, gift_cards.balance)
        activity = gift_cards.items
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
    def test_get_gift_cards_paginated(self, mock_today):
        # GIVEN
        mock_today.date.today.return_value = datetime.date(2026, 5, 15)
        self.amazon_session.is_authenticated = True
        resp1 = self.given_gift_card_page_exists("gift-card-balance-activity.html")
        resp2 = self.given_gift_card_page_exists("gift-card-balance-activity-page-2.html")
        resp3 = self.given_gift_card_page_exists("gift-card-balance-activity-last-page.html")

        # WHEN
        gift_cards = self.amazon_gift_cards.get_gift_cards(days=4000)

        # THEN
        self.assertEqual(0.00, gift_cards.balance)
        activity = gift_cards.items
        self.assertEqual(41, len(activity))
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(1, resp3.call_count)
        self.assertIn("next=", resp2.calls[0].request.url)
        self.assertIn("next=", resp3.calls[0].request.url)
        self.assertEqual(datetime.date(2015, 12, 30), activity[-1].activity_date)

    @responses.activate
    @patch("amazonorders.gift_cards.datetime", wraps=datetime)
    def test_get_gift_cards_stops_at_external_next_page(self, mock_today):
        # GIVEN
        mock_today.date.today.return_value = datetime.date(2026, 5, 15)
        self.amazon_session.is_authenticated = True
        body = self.read_gift_card_page("gift-card-balance-activity.html")
        body = re.sub(r'(<li class="a-last"><a href=")[^"]+',
                      r'\1https://evil.example/gc/balance?next=fake', body, count=1)
        first_page = responses.add(responses.GET,
                                   self.test_config.constants.GIFT_CARD_BALANCE_URL,
                                   body=body,
                                   status=200)
        external_page = responses.add(responses.GET,
                                      "https://evil.example/gc/balance?next=fake",
                                      body=self.read_gift_card_page("gift-card-balance-zero-activity.html"),
                                      status=200)

        # WHEN
        self.amazon_gift_cards.get_gift_cards(days=4000)

        # THEN
        self.assertEqual(1, first_page.call_count)
        self.assertEqual(0, external_page.call_count)

    @responses.activate
    @patch("amazonorders.gift_cards.datetime", wraps=datetime)
    def test_get_gift_cards_reports_progress_per_page(self, mock_today):
        # GIVEN
        mock_today.date.today.return_value = datetime.date(2026, 5, 15)
        self.amazon_session.is_authenticated = True
        self.given_gift_card_page_exists("gift-card-balance-activity.html")
        self.given_gift_card_page_exists("gift-card-balance-activity-page-2.html")
        self.given_gift_card_page_exists("gift-card-balance-activity-last-page.html")
        counts = []

        # WHEN
        self.amazon_gift_cards.get_gift_cards(days=4000, progress=counts.append)

        # THEN
        self.assertEqual([15, 30, 41], counts)

    @responses.activate
    @patch("amazonorders.gift_cards.datetime", wraps=datetime)
    def test_get_gift_cards_days_filter(self, mock_today):
        # GIVEN
        mock_today.date.today.return_value = datetime.date(2026, 5, 12)
        self.amazon_session.is_authenticated = True
        resp = self.given_gift_card_page_exists("gift-card-balance-activity.html")

        # WHEN
        activity = self.amazon_gift_cards.get_gift_cards(days=5).items

        # THEN
        self.assertEqual(2, len(activity))
        self.assertEqual(datetime.date(2026, 5, 11), activity[1].activity_date)
        self.assertEqual(1, resp.call_count)

    @responses.activate
    def test_get_gift_cards_zero_activity(self):
        # GIVEN
        self.amazon_session.is_authenticated = True
        resp = self.given_gift_card_page_exists("gift-card-balance-zero-activity.html")

        # WHEN
        gift_cards = self.amazon_gift_cards.get_gift_cards()

        # THEN
        self.assertIsNotNone(gift_cards.balance)
        self.assertEqual([], gift_cards.items)
        self.assertEqual(1, resp.call_count)

    @responses.activate
    def test_get_gift_cards_invalid_page(self):
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
            self.amazon_gift_cards.get_gift_cards(keep_paging=False)

        # THEN
        self.assertEqual(1, resp.call_count)
        self.assertIn("Could not parse Gift Card activity.", str(cm.exception))

    @responses.activate
    @patch("amazonorders.gift_cards.datetime", wraps=datetime)
    def test_deprecated_balance_and_activity(self, mock_today):
        # GIVEN
        mock_today.date.today.return_value = datetime.date(2026, 5, 15)
        self.amazon_session.is_authenticated = True
        self.given_gift_card_page_exists("gift-card-balance-activity.html")

        # WHEN
        with self.assertWarns(DeprecationWarning):
            balance = self.amazon_gift_cards.get_balance()
        with self.assertWarns(DeprecationWarning):
            activity = self.amazon_gift_cards.get_gift_card_activity(keep_paging=False)
        with self.assertWarns(DeprecationWarning):
            parsed_activity = AmazonGiftCards.parse_gift_card_activity(
                self.read_gift_card_page("gift-card-balance-activity.html"), self.test_config)

        # THEN
        self.assertEqual(0.00, balance)
        self.assertEqual(15, len(activity))
        self.assertEqual(15, len(parsed_activity))

    @responses.activate
    @patch("amazonorders.gift_cards.datetime", wraps=datetime)
    def test_get_gift_cards_page_limit_and_cursor(self, mock_today):
        # GIVEN
        mock_today.date.today.return_value = datetime.date(2026, 5, 15)
        self.amazon_session.is_authenticated = True
        resp1 = self.given_gift_card_page_exists("gift-card-balance-activity.html")
        resp2 = self.given_gift_card_page_exists("gift-card-balance-activity-page-2.html")
        resp3 = self.given_gift_card_page_exists("gift-card-balance-activity-last-page.html")

        # WHEN
        first_page = self.amazon_gift_cards.get_gift_cards_page(days=4000, limit=1)
        next_page = self.amazon_gift_cards.get_gift_cards_page(cursor=first_page.cursor)

        # THEN
        self.assertEqual(0.00, first_page.balance)
        self.assertEqual(15, len(first_page.items))
        self.assertTrue(first_page.has_more)
        self.assertIn("next=", first_page.cursor["next_page_url"])
        self.assertEqual("2015-06-02", first_page.cursor["min_date"])
        self.assertEqual(26, len(next_page.items))
        self.assertIsNotNone(next_page.balance)
        self.assertFalse(next_page.has_more)
        self.assertIsNone(next_page.cursor)
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertEqual(1, resp3.call_count)

    def test_get_gift_cards_page_rejects_cursor_on_another_site(self):
        # GIVEN
        self.amazon_session.is_authenticated = True

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            self.amazon_gift_cards.get_gift_cards_page(cursor={"next_page_url": "https://evil.example/gc/balance",
                                                               "min_date": "2026-01-01"})

        # THEN
        self.assertEqual("The cursor's next page is not on this Amazon site.", str(cm.exception))

    def test_parse_gift_cards_balance(self):
        # GIVEN
        html = self.read_gift_card_page("gift-card-balance-activity.html")

        # WHEN
        gift_cards = AmazonGiftCards.parse_gift_cards(html, self.test_config)

        # THEN
        self.assertEqual(0.00, gift_cards.balance)
        self.assertEqual(15, len(gift_cards.items))
        self.assertIsNone(gift_cards.cursor)
        self.assertEqual({"balance", "items", "cursor", "has_more"}, set(gift_cards.to_dict()))

    def test_parse_gift_cards_redemptions(self):
        # GIVEN
        html = self.read_gift_card_page("gift-card-balance-activity-page-2.html")

        # WHEN
        activity = AmazonGiftCards.parse_gift_cards(html, self.test_config).items

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

    def test_parse_gift_cards_legacy_order_numbers(self):
        # GIVEN
        html = self.read_gift_card_page("gift-card-balance-activity-last-page.html")

        # WHEN
        activity = AmazonGiftCards.parse_gift_cards(html, self.test_config).items

        # THEN
        self.assertEqual(11, len(activity))
        self.assertEqual(["4000-100001-2000001", "4000-100002-2000002", "4000-100003-2000003", "4000-100004-2000004"],
                         [entry.order_number for entry in activity[6:10]])
        self.assertIn("orderID=4000-100001-2000001", activity[6].order_details_link)

    def test_parse_gift_cards_closing_balances_chain(self):
        # GIVEN
        html = self.read_gift_card_page("gift-card-balance-activity.html")

        # WHEN
        activity = AmazonGiftCards.parse_gift_cards(html, self.test_config).items

        # THEN
        for newer, older in zip(activity, activity[1:]):
            self.assertAlmostEqual(older.closing_balance + newer.amount, newer.closing_balance, places=2)
