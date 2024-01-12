import datetime

from amazonorders.entity.order import Order
from amazonorders.exception import AmazonOrdersError
from amazonorders.session import BASE_URL

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.3"


class AmazonOrders:
    def __init__(self,
                 amazon_session,
                 debug=False,
                 print_output=False) -> None:
        self.amazon_session = amazon_session

        self.debug = debug
        self.print_output = print_output

    def get_order_history(self,
                          year=datetime.date.today().year,
                          start_index=None,
                          full_details=False):
        if not self.amazon_session.is_authenticated:
            raise AmazonOrdersError("Call AmazonSession.login() to authenticate first.")

        orders = []
        next_page = "{}/your-orders/orders?timeFilter=year-{}{}".format(BASE_URL,
                                                                        year,
                                                                        "&startIndex={}".format(
                                                                            start_index) if start_index else "")
        while next_page:
            self.amazon_session.get(next_page)
            response = self.amazon_session.last_response
            response_parsed = self.amazon_session.last_response_parsed

            if self.debug:
                page_name = self.amazon_session._get_page_from_url(response.url)
                with open(page_name, "w") as html_file:
                    html_file.write(response.text)

            for order_tag in response_parsed.find_all("div", {"class": "order-card"}):
                order = Order(order_tag)

                if full_details:
                    self.amazon_session.get(order.order_details_link)
                    order_details_tag = self.amazon_session.last_response_parsed.find("div", id="orderDetails")
                    order = Order(order_details_tag, full_details=True, clone=order)

                orders.append(order)

            next_page = None
            if not start_index:
                try:
                    next_page = "{}{}".format(BASE_URL,
                                              response_parsed.find("ul", {"class", "a-pagination"}).find(
                                                  "li", {"class": "a-last"}).find("a").attrs["href"])
                except AttributeError:
                    pass

        if self.print_output:
            for order in orders:
                print(order)

        return orders

    def get_order(self, order_id):
        if not self.amazon_session.is_authenticated:
            raise AmazonOrdersError("Call AmazonSession.login() to authenticate first.")

        self.amazon_session.get("{}/gp/your-account/order-details?orderID={}".format(BASE_URL, order_id))

        if self.debug:
            page_name = self.amazon_session._get_page_from_url(self.amazon_session.last_response.url)
            with open(page_name, "w") as html_file:
                html_file.write(self.amazon_session.last_response.text)

        order_details_tag = self.amazon_session.last_response_parsed.find("div", id="orderDetails")
        order = Order(order_details_tag, full_details=True)

        if self.print_output:
            print(order)

        return order
