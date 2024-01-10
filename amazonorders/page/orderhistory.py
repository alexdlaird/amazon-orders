import datetime
import sys

from bs4 import BeautifulSoup

from amazonorders.entity.order import Order
from amazonorders.session import BASE_URL

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.3"


class OrderHistory:
    def __init__(self,
                 amazon_session,
                 debug=False,
                 year=datetime.date.today().year,
                 print_output=False,
                 full_details=False) -> None:
        self.amazon_session = amazon_session

        self.debug = debug
        self.year = year
        self.print_output = print_output
        self.full_details = full_details

    def get_orders(self):
        if not self.amazon_session.is_authenticated:
            print("Call AmazonSession.login() to authenticate first.")

            sys.exit(1)

        orders = []
        next_page = "{}/your-orders/orders?timeFilter=year-{}".format(BASE_URL, self.year)
        while next_page:
            self.amazon_session.get(next_page)
            response = self.amazon_session.last_response
            response_parsed = self.amazon_session.last_response_parsed

            if self.debug:
                page_name = self.amazon_session._get_page_from_url(response.url)
                with open(page_name, "w") as html_file:
                    html_file.write(response.text)

            for card in response_parsed.find_all("div", {"class": "order-card"}):
                order = Order(card)

                if self.full_details:
                    # TODO: this needs finished
                    order_details_response = BeautifulSoup(self.amazon_session.get(order.order_details_link).text,
                                                           "html.parser")
                    order = Order(order_details_response.find("div", id="orderDetails"), clone=order)

                orders.append(order)

            try:
                next_page = "{}{}".format(self.amazon_session.BASE_URL,
                                          response_parsed.find("ul", {"class", "a-pagination"}).find(
                                              "li", {"class": "a-last"}).find("a").attrs["href"])
            except AttributeError:
                next_page = None

        if self.print_output:
            for order in orders:
                print(order)

        return orders
