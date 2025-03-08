#!/usr/bin/env python

__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import logging
import os
import platform
from typing import Any, Optional

import click
from click.core import Context

from amazonorders import __version__, util
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.order import Order
from amazonorders.entity.transaction import Transaction
from amazonorders.exception import AmazonOrdersError, AmazonOrdersAuthError
from amazonorders.orders import AmazonOrders
from amazonorders.session import AmazonSession, IODefault
from amazonorders.transactions import AmazonTransactions

logger = logging.getLogger("amazonorders")

banner_path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                           "banner.txt")
with open(banner_path) as f:
    banner = f.read()


class IOClick(IODefault):
    def echo(self,
             msg: str,
             fg: Optional[str] = None,
             **kwargs: Any) -> None:
        click.secho(msg, fg=fg)

    def prompt(self,
               msg: str,
               type: Optional[Any] = None,
               **kwargs: Any) -> Any:
        for choice in kwargs.get("choices", []):
            self.echo(choice, **kwargs)

        return click.prompt(f"--> {msg}", type=type)


@click.group()
@click.option("--username", help="An Amazon username.")
@click.option("--password", help="An Amazon password.")
@click.option("--debug", is_flag=True, default=False,
              help="Enable debugging and send output to "
                   "command line.")
@click.option("--config-path",
              help="The config path.")
@click.option("--max-auth-attempts",
              help="The max auth loop attempts to make (successes and failures), passing this overrides config value.")
@click.option("--output-dir",
              help="The directory where any output files should be produced, passing this overrides config value.")
@click.pass_context
def amazon_orders_cli(ctx: Context,
                      **kwargs: Any) -> None:
    """
    amazon-orders is an unofficial library that provides a command line interface alongside a programmatic API that
    can be used to interact with Amazon.com's consumer-facing website.

    This works by parsing website data from Amazon.com. A periodic build validates functionality to ensure its
    stability, but as Amazon provides no official API to use, this package may break at any time. This
    package only supports the English version of the website.

    Documentation can be found at https://amazon-orders.readthedocs.io.

    Session data is persisted between requests and interactions with the CLI, minimizing the need to reauthenticate
    after a successful login attempt.
    """
    if ctx.invoked_subcommand != "version":
        _print_banner()

    ctx.ensure_object(dict)
    for key, value in kwargs.items():
        if value:
            ctx.obj[key] = value

    if kwargs["debug"]:
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.StreamHandler())

    data = {}
    if kwargs.get("output_dir"):
        data["output_dir"] = kwargs["output_dir"]
    if kwargs.get("max_auth_attempts"):
        data["max_auth_attempts"] = kwargs["max_auth_attempts"]
    ctx.obj["conf"] = AmazonOrdersConfig(config_path=kwargs.get("config_path"),
                                         data=data)

    username = kwargs.get("username")
    password = kwargs.get("password")

    amazon_session = AmazonSession(username,
                                   password,
                                   debug=kwargs["debug"],
                                   io=IOClick(),
                                   config=ctx.obj["conf"])

    ctx.obj["amazon_session"] = amazon_session


@amazon_orders_cli.command()
@click.pass_context
@click.option("--year", default=datetime.date.today().year,
              help="The year for which to get order history, defaults to the current year.")
@click.option("--start-index",
              help="Retrieve the single page of history at the given index.")
@click.option("--full-details", is_flag=True, default=False,
              help="Retrieve the full details for each order in the history.")
def history(ctx: Context,
            **kwargs: Any) -> None:
    """
    Retrieve Amazon order history for a given year.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        _authenticate(amazon_session)

        year = kwargs["year"]
        start_index = kwargs["start_index"]
        full_details = kwargs["full_details"]

        optional_start_index = f", startIndex={start_index}, one page" if start_index else ", all pages"
        optional_full_details = ", with full details" if full_details else ""
        click.echo("""-----------------------------------------------------------------------
Order History for {year}{optional_start_index}{optional_full_details}
-----------------------------------------------------------------------\n"""
                   .format(year=year,
                           optional_start_index=optional_start_index,
                           optional_full_details=optional_full_details))
        click.echo("Info: Fetching order history, this might take a minute ...")

        config = ctx.obj["conf"]
        amazon_orders = AmazonOrders(amazon_session,
                                     config=config)

        orders = amazon_orders.get_order_history(year=kwargs["year"],
                                                 start_index=kwargs[
                                                     "start_index"],
                                                 full_details=kwargs[
                                                     "full_details"], )

        click.echo("... {} orders parsed.\n".format(len(orders)))

        for order in orders:
            click.echo(f"{_order_output(order, config)}\n")
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@amazon_orders_cli.command()
@click.pass_context
@click.argument("order_id")
def order(ctx: Context,
          order_id: str) -> None:
    """
    Retrieve the full details for the given Amazon order ID.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        _authenticate(amazon_session)

        config = ctx.obj["conf"]
        amazon_orders = AmazonOrders(amazon_session,
                                     config=config)

        order = amazon_orders.get_order(order_id)

        click.echo(f"{_order_output(order, config)}\n")
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@amazon_orders_cli.command()
@click.pass_context
@click.option("--days", default=365,
              help="The number of days of transactions to get.")
def transactions(ctx: Context, **kwargs: Any):
    """
    Retrieve Amazon order history for a given year.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        _authenticate(amazon_session)

        days = kwargs["days"]

        click.echo(
            """-----------------------------------------------------------------------
Transaction History for {days} days
-----------------------------------------------------------------------\n""".format(
                days=days
            )
        )
        click.echo("Info: Fetching transaction history, this might take a minute ...")

        config = ctx.obj["conf"]
        amazon_transactions = AmazonTransactions(amazon_session,
                                                 config=config)

        transactions = amazon_transactions.get_transactions(days=days)

        click.echo("... {} transactions parsed.\n".format(len(transactions)))

        for transaction in transactions:
            click.echo(f"{_transaction_output(transaction, config)}\n")
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@amazon_orders_cli.command(short_help="Check if persisted session exists.")
@click.pass_context
def check_session(ctx: Context) -> None:
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
def login(ctx: Context) -> None:
    """
    Login to establish an Amazon session and cookies.
    """
    amazon_session = ctx.obj["amazon_session"]

    if amazon_session.auth_cookies_stored():
        click.echo(
            "Info: A persisted session exists. Call the `logout` command first to change users.\n")
    else:
        _authenticate(amazon_session)

        click.echo("Info: Successfully logged in to Amazon, session persisted.\n")


@amazon_orders_cli.command()
@click.pass_context
def logout(ctx: Context) -> None:
    """
    Logout of existing Amazon sessions and clear cookies.
    """
    amazon_session = ctx.obj["amazon_session"]
    amazon_session.logout()

    click.echo("Info: Successfully logged out of the Amazon session.\n")


@amazon_orders_cli.command()
@click.pass_context
@click.argument("key")
@click.argument("value")
def update_config(ctx: Context,
                  key: str,
                  value: str) -> None:
    """
    Persist the given config value to the config file.
    """
    conf = ctx.obj["conf"]

    conf.update_config(key, util.to_type(value))

    click.echo(f"Info: Config \"{key}\" updated to \"{value}\".\n")


@amazon_orders_cli.command()
@click.pass_context
def version(ctx: Context) -> None:
    """
    Show the banner and package version.
    """
    click.echo(f"amazon-orders/{__version__} Python/{platform.python_version()}")
    ctx.exit(0)


def _print_banner() -> None:
    click.echo(banner.format(version=__version__))


def _authenticate(amazon_session: AmazonSession,
                  retries: int = 0) -> None:
    try:
        if amazon_session.auth_cookies_stored():
            if amazon_session.username or amazon_session.password:
                click.echo(
                    "Info: The --username and --password flags are ignored because a previous session "
                    "still exists. If you would like to reauthenticate, call the `logout` command "
                    "first.\n")
        else:
            if not amazon_session.username:
                amazon_session.username = click.prompt("Username")
            if not amazon_session.password:
                amazon_session.password = click.prompt("Password", hide_input=True)
                click.echo("")

        amazon_session.login()
    except AmazonOrdersAuthError as e:
        if retries < 1:
            if amazon_session.username:
                click.echo(
                    f"Info: Authenticating '{amazon_session.username}' failed, retrying ...\n")

            amazon_session.password = None

            _authenticate(amazon_session, retries=retries + 1)
        else:
            raise e


def _order_output(order: Order,
                  config: AmazonOrdersConfig) -> str:
    order_str = """-----------------------------------------------------------------------
Order #{}
-----------------------------------------------------------------------""".format(
        order.order_number)

    order_str += f"\n  Shipments: {order.shipments}"
    order_str += f"\n  Order Details Link: {order.order_details_link}"
    order_str += f"\n  Grand Total: {config.constants.format_currency(order.grand_total)}"
    order_str += f"\n  Order Placed Date: {order.order_placed_date}"
    if order.recipient:
        order_str += f"\n  {order.recipient}"
    else:
        order_str += "\n  Recipient: None"

    if order.payment_method:
        order_str += f"\n  Payment Method: {order.payment_method}"
    if order.payment_method_last_4:
        order_str += f"\n  Payment Method Last 4: {order.payment_method_last_4}"
    if order.subtotal:
        order_str += f"\n  Subtotal: {config.constants.format_currency(order.subtotal)}"
    if order.shipping_total:
        order_str += f"\n  Shipping Total: {config.constants.format_currency(order.shipping_total)}"
    if order.free_shipping:
        order_str += f"\n  Free Shipping: {config.constants.format_currency(order.free_shipping)}"
    if order.subscription_discount:
        order_str += f"\n  Subscription Discount: {config.constants.format_currency(order.subscription_discount)}"
    if order.total_before_tax:
        order_str += f"\n  Total Before Tax: {config.constants.format_currency(order.total_before_tax)}"
    if order.estimated_tax:
        order_str += f"\n  Estimated Tax: {config.constants.format_currency(order.estimated_tax)}"
    if order.refund_total:
        order_str += f"\n  Refund Total: {config.constants.format_currency(order.refund_total)}"

    order_str += "\n-----------------------------------------------------------------------"

    return order_str


def _transaction_output(transaction: Transaction,
                        config: AmazonOrdersConfig) -> str:
    transaction_str = f"Transaction: {transaction.completed_date}"
    transaction_str += f"\n  Order #{transaction.order_number}"
    transaction_str += f"\n  Grand Total: {config.constants.format_currency(transaction.grand_total)}"
    transaction_str += f"\n  Order Details Link: ${transaction.order_details_link}"

    return transaction_str


if __name__ == "__main__":
    amazon_orders_cli(obj={})
