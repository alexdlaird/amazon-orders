import datetime
import sys

from amazonorders.entity.order import Order

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.2"


class OrderHistory:
    BASE_URL = "https://www.amazon.com"

    def __init__(self,
                 amazon_session,
                 debug=False,
                 year=datetime.date.today().year,
                 print_output=False) -> None:
        self.amazon_session = amazon_session

        self.debug = debug
        self.year = year
        self.print_output = print_output

    def get_orders(self):
        if not self.amazon_session.is_authenticated:
            print("Call AmazonSession.login() to authenticate first.")

            sys.exit(1)

        orders = []
        next_page = "{}/your-orders/orders?timeFilter=year-{}".format(self.BASE_URL, self.year)
        while next_page:
            self.amazon_session.get(next_page)

            if self.debug:
                page_name = self.amazon_session._get_page_from_url(self.amazon_session.last_response.url)
                with open(page_name, "w") as html_file:
                    html_file.write(self.amazon_session.last_response.text)

            # TODO: just a WIP to show output that we've parsed the page
            for card in self.amazon_session.last_response_parsed.find_all("div", {"class": "order-card"}):
                orders.append(Order(card))

            try:
                next_page = "{}{}".format(self.BASE_URL, self.amazon_session.last_response_parsed.find("ul", {"class", "a-pagination"}).find("li", {"class": "a-last"}).find("a").attrs["href"])
            except AttributeError:
                next_page = None

        if self.print_output:
            for order in orders:
                print(order)

        return orders
