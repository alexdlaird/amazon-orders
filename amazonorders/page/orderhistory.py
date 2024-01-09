from amazonorders.entity.order import Order

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.2"


class OrderHistory:
    def __init__(self, amazon_session) -> None:
        self.amazon_session = amazon_session

    def get_orders(self):
        # TODO: identify if session isn't logged in

        response = self.amazon_session.get(url='https://www.amazon.com/gp/css/order-history')
        if self.amazon_session.debug:
            page_name = self.amazon_session._get_page_from_url(response.url)
            with open(page_name, "w") as html_file:
                html_file.write(response.text)

        # TODO: just a WIP to show output that we've parsed the page
        for card in self.amazon_session.last_request_parsed.find_all("div", {"class": "order-card"}):
            order = Order(card)
            print(order)

        # TODO: Add pagination support
        return response.text
