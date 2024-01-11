import datetime
import os

import click

from amazonorders.exception import AmazonOrdersError
from amazonorders.orders import AmazonOrders

from amazonorders.session import AmazonSession

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.3"


@click.group(invoke_without_command=True)
@click.pass_context
@click.option('--year', default=datetime.date.today().year, help="The year for which to get order history.")
@click.option('--username', default=os.environ.get("AMAZON_USERNAME"), help="An Amazon username.")
@click.option('--password', default=os.environ.get("AMAZON_PASSWORD"), help="An Amazon password.")
@click.option('--full-details', is_flag=True, default=False,
              help="True if the full details should be retreived for each order.")
def get_order_history(ctx, **kwargs):
    if not kwargs["username"] or not kwargs["password"]:
        ctx.fail("Must provide but --username and --password for Amazon.")

    amazon_session = AmazonSession(kwargs["username"], kwargs["password"])
    amazon_session.login()

    amazon_orders = AmazonOrders(amazon_session,
                                 print_output=True)

    try:
        amazon_orders.get_order_history(year=kwargs["year"],
                                        full_details=kwargs["full_details"])
    except AmazonOrdersError as e:
        ctx.fail(str(e))

    amazon_session.close()


if __name__ == "__main__":
    get_order_history(obj={})
