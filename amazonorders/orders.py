from bs4 import BeautifulSoup

from amazonorders.auth import get_session, close_session, HEADERS

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.2"


def get_orders():
    session = get_session()

    r = session.get(url='https://www.amazon.com/gp/css/order-history',
                    headers=HEADERS)
    print(r.url + " - " + str(r.status_code))
    html = r.text
    with open("orders.html", "w") as text_file:
        text_file.write(html)
    close_session()

    soup = BeautifulSoup(html, "html.parser")

    # TODO: just a WIP to show output that we've parsed the page
    for order in soup.find_all("div", {"class": "order-card"}):
        product = order.find("div", {"class": "yohtmlc-product-title"})
        print(product.text)
        print("\n")

    # TODO: Add pagination support

    return r.content
