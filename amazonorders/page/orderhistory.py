from bs4 import BeautifulSoup

from amazonorders.entity.order import Order

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.2"


class OrderHistory:
  def __init__(self, amazon_session) -> None:
    self.amazon_session = amazon_session

  def get_orders(self):
    # TODO: identify if session isn't logged in

    r = self.amazon_session.get(
        url='https://www.amazon.com/gp/css/order-history')
    print(r.url + " - " + str(r.status_code))
    html = r.text
    with open("orders.html", "w") as text_file:
      text_file.write(html)

    soup = BeautifulSoup(html, "html.parser")

    # TODO: just a WIP to show output that we've parsed the page
    for card in soup.find_all("div", {"class": "order-card"}):
      order = Order(card)
      print(order)

    # TODO: Add pagination support

    return r.content
