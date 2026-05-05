#!/usr/bin/env python

__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import logging
import os
import platform
import time
from typing import Any, Optional

import click
from click.core import Context

from amazonorders import __version__, util
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.order import Order
from amazonorders.entity.transaction import Transaction
from amazonorders.exception import AmazonOrdersError, AmazonOrdersAuthError, AmazonOrdersAuthRedirectError
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
@click.option("--domain", help="The Amazon domain (e.g. https://www.amazon.com, https://www.amazon.co.uk, https://www.amazon.de).")
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
    amazon-orders is an unofficial library that provides a CLI (and Python API) for Amazon order history.

    This package works by parsing data from Amazon's consumer-facing website. A periodic build validates functionality
    to ensure its stability, but as Amazon provides no official API to use, this package may break at any time. Check
    for updates regularly to ensure you always have the latest stable release.

    This package only officially supports the English, .com version of Amazon.

    Documentation can be found at https://amazon-orders.readthedocs.io.
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
    domain   = kwargs.get("domain")

    amazon_session = AmazonSession(username,
                                   password,
                                   debug=kwargs["debug"],
                                   io=IOClick(),
                                   base_url=domain if domain else "https://www.amazon.com",
                                   config=ctx.obj["conf"])

    ctx.obj["amazon_session"] = amazon_session


@amazon_orders_cli.command()
@click.pass_context
@click.option("--year", type=int, default=None,
              help="The year for which to get Order history. Defaults to the current year if no "
                   "time filter is specified.")
@click.option("--last-30-days", "last_30_days", is_flag=True, default=False,
              help="Get Order history for the last 30 days.")
@click.option("--last-3-months", "last_3_months", is_flag=True, default=False,
              help="Get Order history for the past 3 months.")
@click.option("--start-index",
              help="The index of the Order from which to start fetching in the history.")
@click.option("--single-page", is_flag=True, default=False,
              help="Only one page should be fetched.")
@click.option("--full-details", is_flag=True, default=False,
              help="Get the full details for each Order in the history. "
                   "This will execute an additional request per Order.")
def history(ctx: Context,
            **kwargs: Any) -> None:
    """
    Get the Amazon Order history for a given time period.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        _authenticate(amazon_session)

        year = kwargs["year"]
        last_30_days = kwargs["last_30_days"]
        last_3_months = kwargs["last_3_months"]
        start_index = kwargs["start_index"]
        single_page = kwargs["single_page"]
        full_details = kwargs["full_details"]

        exclusive_flags = [year, last_3_months, last_30_days]
        if not all(not item for item in exclusive_flags) and sum(exclusive_flags) == 1:
            ctx.fail("Only one of --last-30-days, --last-3-months, or --year may be used at a time.")

        # Determine time filter
        time_filter = None
        if last_30_days:
            time_filter = "last30"
            filter_description = "last 30 days"
        elif last_3_months:
            time_filter = "months-3"
            filter_description = "past 3 months"
        else:
            if year is None:
                year = datetime.date.today().year
            filter_description = str(year)

        optional_start_index = f", startIndex={start_index}, one page" if single_page else ", all pages"
        optional_full_details = ", with full details" if full_details else ""
        click.echo("""-----------------------------------------------------------------------
Order History for {filter_description}{optional_start_index}{optional_full_details}
-----------------------------------------------------------------------\n"""
                   .format(filter_description=filter_description,
                           optional_start_index=optional_start_index,
                           optional_full_details=optional_full_details))
        click.echo("Info: Fetching Order history, this might take a minute ...")

        config = ctx.obj["conf"]
        amazon_orders = AmazonOrders(amazon_session,
                                     config=config)

        start_time = time.time()
        total = 0
        for o in amazon_orders.get_order_history(year=year,
                                                 start_index=start_index,
                                                 full_details=full_details,
                                                 keep_paging=not single_page,
                                                 time_filter=time_filter):
            click.echo(f"{_order_output(o, config)}\n")
            total += 1
        end_time = time.time()

        click.echo(
            "... {total} Orders parsed in {time} seconds.\n".format(total=total,
                                                                    time=int(end_time - start_time)))
    except AmazonOrdersAuthRedirectError:
        _prompt_to_reauth_flow()
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@amazon_orders_cli.command()
@click.pass_context
@click.argument("order_id")
def order(ctx: Context,
          order_id: str) -> None:
    """
    Get the full details for a given Amazon Order ID.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        _authenticate(amazon_session)

        config = ctx.obj["conf"]
        amazon_orders = AmazonOrders(amazon_session,
                                     config=config)

        o = amazon_orders.get_order(order_id)

        click.echo(f"{_order_output(o, config)}\n")
    except AmazonOrdersAuthRedirectError:
        _prompt_to_reauth_flow()
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@amazon_orders_cli.command()
@click.pass_context
@click.option("--days", default=365,
              help="The number of days of Transactions to get.")
def transactions(ctx: Context, **kwargs: Any):
    """
    Get Amazon Transaction history for a given number of days.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        _authenticate(amazon_session)

        days = kwargs["days"]

        click.echo(
            """-----------------------------------------------------------------------
Transaction History for {days} days
-----------------------------------------------------------------------\n""".format(days=days)
        )
        click.echo("Info: Fetching Transaction history, this might take a minute ...")

        config = ctx.obj["conf"]
        amazon_transactions = AmazonTransactions(amazon_session,
                                                 config=config)

        start_time = time.time()
        total = 0
        for t in amazon_transactions.get_transactions(days=days):
            click.echo(f"{_transaction_output(t, config)}\n")
            total += 1
        end_time = time.time()

        click.echo(
            "... {total} Transactions parsed in {time} seconds.\n".format(total=total,
                                                                          time=int(end_time - start_time)))
    except AmazonOrdersAuthRedirectError:
        _prompt_to_reauth_flow()
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@amazon_orders_cli.command(short_help="Check if a persisted session exists.")
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

    click.echo("Info: Successfully logged out of Amazon.\n")


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
                    "Info: The given username and password are being ignored because a previous session still exists. "
                    "To reauthenticate, call the `logout` command first.\n")
        else:
            if not amazon_session.username:
                amazon_session.username = click.prompt("Username")
            if not amazon_session.password:
                amazon_session.password = click.prompt("Password", hide_input=True)
                click.echo("")

        amazon_session.login()
    except AmazonOrdersAuthError as e:
        if retries < amazon_session.config.max_auth_retries:
            if amazon_session.username:
                click.secho(str(f"{e}\n"), fg="red")
                click.echo(
                    f"Info: Authenticating '{amazon_session.username}' failed. If using 2FA, wait a minute before "
                    "retrying with a new OTP.\n")

            amazon_session.password = None

            _authenticate(amazon_session, retries=retries + 1)
        else:
            raise e


def _prompt_to_reauth_flow() -> None:
    click.echo("... Amazon redirected to login, which likely means the persisted session is stale. It was logged "
               "out, so try running the command again.\n")


def _order_output(o: Order,
                  config: AmazonOrdersConfig) -> str:
    order_str = """-----------------------------------------------------------------------
Order #{order_number}
-----------------------------------------------------------------------""".format(order_number=o.order_number)

    order_str += f"\n  Shipments: {o.shipments}"
    order_str += f"\n  Order Details Link: {o.order_details_link}"
    if o.grand_total:
        order_str += f"\n  Grand Total: {config.constants.format_currency(o.grand_total)}"
    order_str += f"\n  Order Placed Date: {o.order_placed_date}"
    if o.recipient:
        order_str += f"\n  {o.recipient}"
    else:
        order_str += "\n  Recipient: None"

    if o.payment_method:
        order_str += f"\n  Payment Method: {o.payment_method}"
    if o.payment_method_last_4:
        order_str += f"\n  Payment Method Last 4: {o.payment_method_last_4}"
    if o.subtotal:
        order_str += f"\n  Subtotal: {config.constants.format_currency(o.subtotal)}"
    if o.shipping_total:
        order_str += f"\n  Shipping Total: {config.constants.format_currency(o.shipping_total)}"
    if o.free_shipping:
        order_str += f"\n  Free Shipping: {config.constants.format_currency(o.free_shipping)}"
    if o.subscription_discount:
        order_str += f"\n  Subscription Discount: {config.constants.format_currency(o.subscription_discount)}"
    if o.total_before_tax:
        order_str += f"\n  Total Before Tax: {config.constants.format_currency(o.total_before_tax)}"
    if o.estimated_tax:
        order_str += f"\n  Estimated Tax: {config.constants.format_currency(o.estimated_tax)}"
    if o.refund_total:
        order_str += f"\n  Refund Total: {config.constants.format_currency(o.refund_total)}"

    order_str += "\n-----------------------------------------------------------------------"

    return order_str


def _transaction_output(t: Transaction,
                        config: AmazonOrdersConfig) -> str:
    transaction_str = f"Transaction: {t.completed_date}"
    transaction_str += f"\n  Order #{t.order_number}"
    if t.grand_total:
        transaction_str += f"\n  Grand Total: {config.constants.format_currency(t.grand_total)}"
    transaction_str += f"\n  Order Details Link: {t.order_details_link}"

    return transaction_str


if __name__ == "__main__":
    amazon_orders_cli(obj={})
