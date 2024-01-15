import datetime
import logging
import os

import click

from amazonorders.exception import AmazonOrdersError
from amazonorders.orders import AmazonOrders

from amazonorders.session import AmazonSession

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.5"

logger = logging.getLogger("amazonorders")


@click.group(invoke_without_command=True)
@click.option('--username', default=os.environ.get("AMAZON_USERNAME"), help="An Amazon username.")
@click.option('--password', default=os.environ.get("AMAZON_PASSWORD"), help="An Amazon password.")
@click.option('--debug', is_flag=True, default=False, help="Enable debugging and send output to command line.")
@click.pass_context
def amazon_orders_cli(ctx, **kwargs):
    ctx.ensure_object(dict)
    for key, value in kwargs.items():
        if value:
            ctx.obj[key] = value

    if not kwargs["username"] or not kwargs["password"]:
        ctx.fail("Must provide --username and --password for Amazon.")

    if kwargs["debug"]:
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.StreamHandler())

    ctx.obj["amazon_session"] = AmazonSession(kwargs["username"],
                                              kwargs["password"],
                                              debug=kwargs["debug"])


@amazon_orders_cli.command(help="Retrieve Amazon order history for a given year.")
@click.pass_context
@click.option('--year', default=datetime.date.today().year,
              help="The year for which to get order history, defaults to the current year.")
@click.option('--start-index', help="Retrieve the single page of history at the given index.")
@click.option('--full-details', is_flag=True, default=False,
              help="Retrieve the full details for each order in the history.")
def history(ctx, **kwargs):
    amazon_session = ctx.obj["amazon_session"]
    amazon_session.login()

    amazon_orders = AmazonOrders(amazon_session,
                                 debug=amazon_session.debug,
                                 print_output=True)

    try:
        amazon_orders.get_order_history(year=kwargs["year"],
                                        start_index=kwargs["start_index"],
                                        full_details=kwargs["full_details"])
    except AmazonOrdersError as e:
        ctx.fail(str(e))

    amazon_session.close()


@amazon_orders_cli.command(help="Retrieve the full details for the given Amazon order ID.")
@click.pass_context
@click.argument("order_id")
def order(ctx, order_id):
    amazon_session = ctx.obj["amazon_session"]
    amazon_session.login()

    amazon_orders = AmazonOrders(amazon_session,
                                 debug=amazon_session.debug,
                                 print_output=True)

    try:
        amazon_orders.get_order(order_id)
    except AmazonOrdersError as e:
        ctx.fail(str(e))

    amazon_session.close()


if __name__ == "__main__":
    amazon_orders_cli(obj={})
