import os

import click

from amazonorders.page.orderhistory import OrderHistory

from amazonorders.session import AmazonSession

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.2"


@click.group(invoke_without_command=True)
@click.pass_context
def amazon_orders(ctx, **kwargs):
    amazon_session = AmazonSession(os.environ["AMAZON_USERNAME"], os.environ["AMAZON_PASSWORD"])
    amazon_session.login()

    order_history = OrderHistory(amazon_session, year=2023)
    order_history.get_orders()

    amazon_session.close()


if __name__ == "__main__":
    amazon_orders(obj={})
