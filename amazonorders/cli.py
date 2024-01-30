import datetime
import logging
from typing import Any, Optional

import click
from click.core import Context

from amazonorders.conf import DEFAULT_OUTPUT_DIR
from amazonorders.exception import AmazonOrdersError
from amazonorders.orders import AmazonOrders
from amazonorders.session import AmazonSession, IODefault

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.8"

logger = logging.getLogger("amazonorders")


class IOClick(IODefault):
    def echo(self,
             msg: str,
             fg: Optional[str] = None,
             **kwargs: Any):
        click.secho(msg, fg=fg)

    def prompt(self,
               msg: str,
               type: str = None,
               **kwargs: Any):
        return click.prompt(msg, type=type)


@click.group()
@click.option('--username', help="An Amazon username.")
@click.option('--password', help="An Amazon password.")
@click.option('--debug', is_flag=True, default=False, help="Enable debugging and send output to command line.")
@click.option('--max-auth-attempts', default=10,
              help="Will continue in the login auth loop this many times (successes and failures).")
@click.option('--output-dir', default=DEFAULT_OUTPUT_DIR,
              help="The directory where any output files should be produced.")
@click.pass_context
def amazon_orders_cli(ctx: Context,
                      **kwargs: Any):
    """
    amazon-orders is an unofficial library that provides a command line interface alongside a programmatic API that
    can be used to interact with Amazon.com's consumer-facing website.

    This works by parsing website data from Amazon.com. A nightly build validates functionality to ensure its
    stability, but as Amazon provides no official API to use, this package may break at any time. This
    package only supports the English version of the website.

    Documentation can be found at https://amazon-orders.readthedocs.io.

    Session data is persisted between requests and interactions with the CLI, minimizing the need to reauthenticate
    after a successful login attempt.
    """
    _print_banner()

    ctx.ensure_object(dict)
    for key, value in kwargs.items():
        if value:
            ctx.obj[key] = value

    if kwargs["debug"]:
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.StreamHandler())

    username = kwargs.get("username")
    password = kwargs.get("password")

    amazon_session = AmazonSession(username,
                                   password,
                                   debug=kwargs["debug"],
                                   io=IOClick(),
                                   max_auth_attempts=kwargs["max_auth_attempts"],
                                   output_dir=kwargs["output_dir"])

    ctx.obj["amazon_session"] = amazon_session


@amazon_orders_cli.command()
@click.pass_context
@click.option('--year', default=datetime.date.today().year,
              help="The year for which to get order history, defaults to the current year.")
@click.option('--start-index', help="Retrieve the single page of history at the given index.")
@click.option('--full-details', is_flag=True, default=False,
              help="Retrieve the full details for each order in the history.")
def history(ctx: Context,
            **kwargs: Any):
    """
    Retrieve Amazon order history for a given year.
    """
    amazon_session = ctx.obj["amazon_session"]

    year = kwargs["year"]
    start_index = kwargs["start_index"]
    full_details = kwargs["full_details"]

    click.echo("""-----------------------------------------------------------------------
Order History for {}{}{}
-----------------------------------------------------------------------\n""".format(year,
                                                                                    ", startIndex={}, one page".format(
                                                                                        start_index) if start_index else ", all pages",
                                                                                    ", with full details" if full_details else ""))

    click.echo("Info: This might take a minute ...\n")

    try:
        _authenticate(ctx, amazon_session)

        amazon_orders = AmazonOrders(amazon_session,
                                     debug=amazon_session.debug,
                                     output_dir=ctx.obj["output_dir"])

        orders = amazon_orders.get_order_history(year=kwargs["year"],
                                                 start_index=kwargs["start_index"],
                                                 full_details=kwargs["full_details"], )

        for order in orders:
            click.echo("{}\n".format(_order_output(order)))
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@amazon_orders_cli.command()
@click.pass_context
@click.argument("order_id")
def order(ctx: Context,
          order_id: str):
    """
    Retrieve the full details for the given Amazon order ID.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        _authenticate(ctx, amazon_session)

        amazon_orders = AmazonOrders(amazon_session,
                                     debug=amazon_session.debug,
                                     output_dir=ctx.obj["output_dir"])

        order = amazon_orders.get_order(order_id)

        click.echo("{}\n".format(_order_output(order)))
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@amazon_orders_cli.command(short_help="Check if persisted session exists.")
@click.pass_context
def check_session(ctx: Context):
    """
    Check if a persisted session exists, meaning commands can be called without needing to provide credentials.
    """
    amazon_session = ctx.obj["amazon_session"]
    if amazon_session.auth_cookies_stored():
        click.echo("Info: A persisted session exists.\n")
    else:
        click.echo("Info: No persisted session exists.\n")


@amazon_orders_cli.command()
@click.pass_context
def logout(ctx: Context):
    """
    Logout of existing Amazon sessions and clear cookies.
    """
    amazon_session = ctx.obj["amazon_session"]
    amazon_session.logout()

    click.echo("Info: Successfully logged out of the Amazon session.\n")


@amazon_orders_cli.command()
def version():
    """
    Get the package version.
    """
    click.echo("Version: {}\n".format(__version__))


def _print_banner():
    click.echo("""
=======================================================================
  ___                                   _____         _               
 / _ \                                 |  _  |       | |              
/ /_\ \_ __ ___   __ _ _______  _ __   | | | |_ __ __| | ___ _ __ ___ 
|  _  | '_ ` _ \ / _` |_  / _ \| '_ \  | | | | '__/ _` |/ _ \ '__/ __|
| | | | | | | | | (_| |/ / (_) | | | | \ \_/ / | | (_| |  __/ |  \__ \\
\_| |_/_| |_| |_|\__,_/___\___/|_| |_|  \___/|_|  \__,_|\___|_|  |___/                                                                   
=======================================================================\n""")


def _authenticate(ctx: Context,
                  amazon_session: AmazonSession):
    if not amazon_session.username and not amazon_session.password:
        click.echo(ctx.get_help())

        ctx.fail("Amazon --username and --password must be provided, since no previous session was found.")

    if amazon_session.auth_cookies_stored():
        if amazon_session.username or amazon_session.password:
            click.echo("Info: You've provided --username and --password, but because a previous session still exists,"
                       "that is being ignored. If you would like to reauthenticate, call the `logout` command first.\n")

    amazon_session.login()


def _order_output(order):
    order_str = """-----------------------------------------------------------------------
Order #{}
-----------------------------------------------------------------------""".format(order.order_number)

    order_str += "\n  Shipments: {}".format(order.shipments)
    order_str += "\n  Order Details Link: {}".format(order.order_details_link)
    order_str += "\n  Grand Total: ${:,.2f}".format(order.grand_total)
    order_str += "\n  Order Placed Date: {}".format(order.order_placed_date)
    order_str += "\n  {}".format(order.recipient)
    if order.payment_method:
        order_str += "\n  Payment Method: {}".format(order.payment_method)
    if order.payment_method_last_4:
        order_str += "\n  Payment Method Last 4: {}".format(order.payment_method_last_4)
    if order.subtotal:
        order_str += "\n  Subtotal: ${:,.2f}".format(order.subtotal)
    if order.shipping_total:
        order_str += "\n  Shipping Total: ${:,.2f}".format(order.shipping_total)
    if order.subscription_discount:
        order_str += "\n  Subscription Discount: ${:,.2f}".format(order.subscription_discount)
    if order.total_before_tax:
        order_str += "\n  Total Before Tax: ${:,.2f}".format(order.total_before_tax)
    if order.estimated_tax:
        order_str += "\n  Estimated Tax: ${:,.2f}".format(order.estimated_tax)
    if order.refund_total:
        order_str += "\n  Refund Total: ${:,.2f}".format(order.refund_total)
    if order.order_shipped_date:
        order_str += "\n  Order Shipped Date: {}".format(order.order_shipped_date)
    if order.refund_completed_date:
        order_str += "\n  Refund Completed Date: {}".format(order.refund_completed_date)

    order_str += "\n-----------------------------------------------------------------------"

    return order_str


if __name__ == "__main__":
    amazon_orders_cli(obj={})
