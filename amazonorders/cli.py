import datetime
import os

import click

from amazonorders.page.orderhistory import OrderHistory

from amazonorders.session import AmazonSession

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.2"


@click.group(invoke_without_command=True)
@click.pass_context
@click.option('--year', default=datetime.date.today().year, help="The year for which to get order history.")
@click.option('--username', default=os.environ.get("AMAZON_USERNAME"), help="An Amazon username.")
@click.option('--password', default=os.environ.get("AMAZON_PASSWORD"), help="An Amazon password")
def amazon_orders(ctx, **kwargs):
    if not kwargs["username"] or not kwargs["password"]:
        ctx.fail("Must provide but --username and --password for Amazon.")

    amazon_session = AmazonSession(kwargs["username"], kwargs["password"])
    amazon_session.login()

    order_history = OrderHistory(amazon_session, year=kwargs["year"], print_output=True)
    order_history.get_orders()

    amazon_session.close()


if __name__ == "__main__":
    amazon_orders(obj={})
