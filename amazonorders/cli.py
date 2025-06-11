#!/usr/bin/env python

__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import pandas as pd
import csv
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
from amazonorders.exception import AmazonOrdersError, AmazonOrdersAuthError, AmazonOrdersNotFoundError
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
@click.option("--no-captcha", is_flag=True, default=False,
              help="Skip CAPTCHA challenges (bypass CaptchaForm).")
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
    # if ctx.invoked_subcommand != "version":
    #     _print_banner()

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

    # amazon_session = AmazonSession(username,
    #                                password,
    #                                debug=kwargs["debug"],
    #                                io=IOClick(),
    #                                config=ctx.obj["conf"])
    
    # Build auth_forms override if requested
    if kwargs.get("no_captcha"):
        from amazonorders.forms import SignInForm, MfaDeviceSelectForm, MfaForm, JSAuthBlocker
        config = ctx.obj["conf"]
        auth_forms = [
            SignInForm(config),
            MfaDeviceSelectForm(config),
            MfaForm(config),
            JSAuthBlocker(config, config.constants.JS_ROBOT_TEXT_REGEX)
        ]
    else:
        # if not auth_forms:
        #     auth_forms = [SignInForm(config),
        #                   MfaDeviceSelectForm(config),
        #                   MfaForm(config),
        #                   CaptchaForm(config),
        #                   CaptchaForm(config,
        #                               config.selectors.CAPTCHA_2_FORM_SELECTOR,
        #                               config.selectors.CAPTCHA_2_ERROR_SELECTOR,
        #                               "field-keywords"),
        #                   MfaForm(config,
        #                           config.selectors.CAPTCHA_OTP_FORM_SELECTOR),
        #                   JSAuthBlocker(config,
        #                                 config.constants.JS_ROBOT_TEXT_REGEX)]
        auth_forms = None

    amazon_session = AmazonSession(username,
                                   password,
                                   debug=kwargs["debug"],
                                   io=IOClick(),
                                   config=ctx.obj["conf"],
                                   auth_forms=auth_forms)
    ctx.obj["amazon_session"] = amazon_session


@amazon_orders_cli.command()
@click.pass_context
@click.option("--year", default=datetime.date.today().year,
              help="The year for which to get order history, defaults to the current year.")
@click.option("--start-index",
              help="The index of the Order from which to start fetching in the history.")
@click.option("--single-page", is_flag=True, default=False,
              help="Only one page should be fetched.")
@click.option("--full-details", is_flag=True, default=False,
              help="Get the full details for each order in the history. "
                   "This will execute an additional request per Order.")
@click.option("--csv", is_flag=True, default=False,
              help="Export the order history to a CSV file.")
@click.option("--invoices", is_flag=True, default=False,
              help="Download an invoice PDF for each order.")
def history(ctx: Context,
            **kwargs: Any) -> None:
    """
    Get the Amazon order history for a given year.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        _authenticate(amazon_session)

        year = kwargs["year"]
        start_index = kwargs["start_index"]
        single_page = kwargs["single_page"]
        full_details = kwargs["full_details"]

        optional_start_index = f", startIndex={start_index}, one page" if single_page else ", all pages"
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
        amazon_transactions = AmazonTransactions(amazon_session,
                                                 config=config)

        start_time = time.time()
        # total = 0

        orders = amazon_orders.get_order_history(
            year=kwargs["year"],
            start_index=kwargs["start_index"],
            full_details=kwargs["full_details"],
            keep_paging=not kwargs["single_page"],
        )

        if kwargs["full_details"]:
            order_map = {o.order_id: o for o in orders}
            transactions = amazon_transactions.get_transactions_by_year(year)
            for t in transactions:
                order = order_map.get(t.order_id)
                if not order:
                    order = amazon_orders.get_order(t.order_id)
                if order:
                    order.payment_date = t.completed_date
                    if t.grand_total and not order.payment_amount:
                        order.payment_amount = t.grand_total
                    if t.payment_method and not order.payment_method:
                        order.payment_method = t.payment_method
                    t.order = order
                    orders.append(order)

        if kwargs["invoices"]:
            for o in orders:
                file_paths = amazon_orders.download_invoice(
                    o.order_id,
                    o.payment_date,
                    config.output_dir,
                    o.invoice_link,
                )
                for p in file_paths:
                    click.echo(f"Invoice saved to {p}")

        if kwargs["csv"]:
            # Convert list of dataclass‐like objects into a list of dicts
            orders_dict = []
            for o in orders:
                if o.payment_amount not in (0, None):
                    order_dict = o.__dict__.copy()
                    # Format dates as yyyy/mm/dd
                    if isinstance(o.order_date, datetime.date):
                        order_dict["order_date"] = o.order_date.strftime("%Y/%m/%d")
                    if isinstance(o.payment_date, datetime.date):
                        order_dict["payment_date"] = o.payment_date.strftime("%Y/%m/%d")
                    orders_dict.append(order_dict)

            # Convert list of dataclass‐like objects into a list of dicts
            df = pd.DataFrame(orders_dict)

            df = df.rename(
                columns={
                    "index": "Index",
                    "order_date": "Order Date",
                    "order_id": "Order ID",
                    "item_quantity": "Item quantity",
                    "item_subtotal": "Item subtotal",
                    "item_shipping_and_handling": "Item shipping and handling",
                    "item_promotion": "Item promotion",
                    "item_federal_tax": "Item Federal Tax",
                    "item_provincial_tax": "Item Provincial Tax",
                    "item_regulatory_fee": "Item Regulatory Fee",
                    "item_net_total": "Item net total",
                    "payment_method": "Payment Method",
                    "payment_method_last_4": "Payment Method Last 4",
                    "payment_reference_id": "Payment Reference ID",
                    "payment_date": "Payment date",
                    "payment_amount": "Payment amount",
                    "shipments": "Shipments",
                    "title": "Title",
                    "amazon_internal_product_category": "Amazon Internal Product Category",
                    "amazon_class": "Class",
                    "amazon_commodity": "Commodity",
                    "items": "Items",
                    "order_details_link": "Order Details Link",
                    "grand_total": "Grand Total",
                    "recipient": "Recipient",
                    "free_shipping": "Free Shipping",
                    "coupon_savings": "Coupon Savings",
                    "subscription_discount": "Subscription Discount",
                    "total_before_tax": "Total Before Tax",
                    "estimated_tax": "Estimated Tax",
                    "refund_total": "Refund Total",
                }
            )[
                [
                    "Index",
                    "Order Date",
                    "Order ID",
                    "Item quantity",
                    "Item subtotal",
                    "Item shipping and handling",
                    "Item promotion",
                    "Item Federal Tax",
                    "Item Provincial Tax",
                    "Item Regulatory Fee",
                    "Item net total",
                    "Payment Method",
                    "Payment Method Last 4",
                    "Payment Reference ID",
                    "Payment date",
                    "Payment amount",
                    "Shipments",
                    "Title",
                    "Amazon Internal Product Category",
                    "Class",
                    "Commodity",
                    "Items",
                    "Order Details Link",
                    "Grand Total",
                    "Recipient",
                    "Free Shipping",
                    "Coupon Savings",
                    "Subscription Discount",
                    "Total Before Tax",
                    "Estimated Tax",
                    "Refund Total",
                ]
            ]

            # Export to CSV (no index column)
            df.to_csv(
                f"orders-{kwargs['year']}.csv",
                index=False,
                quoting=csv.QUOTE_MINIMAL,
            )  # quote fields with commas
        else:
            for o in orders:
                click.echo(f"{_order_output(o, config)}\n")

        total = len(orders)
        end_time = time.time()

        click.echo(
            "... {total} orders parsed in {time} seconds.\n".format(total=total,
                                                                    time=int(end_time - start_time)))
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@amazon_orders_cli.command()
@click.pass_context
@click.argument("order_id")
def order(ctx: Context,
          order_id: str) -> None:
    """
    Get the full details for a given Amazon order ID.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        _authenticate(amazon_session)

        config = ctx.obj["conf"]
        amazon_orders = AmazonOrders(amazon_session,
                                     config=config)

        o = amazon_orders.get_order(order_id)

        click.echo(f"{_order_output(o, config)}\n")
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@amazon_orders_cli.command()
@click.pass_context
@click.option("--year", default=datetime.date.today().year,
              help="The year for which to get transaction's order, defaults to the current year.")
@click.option("--days", default=365,
              help="The number of days of transactions to get.")
@click.option("--full-details", is_flag=True, default=False,
              help="Get the full details for each transaction's order. This will execute an additional request per Order.")
@click.option("--csv", is_flag=True, default=False,
              help="Export the transaction history to a CSV file.")
@click.option("--invoices", is_flag=True, default=False,
              help="Download an invoice PDF for each transaction's order.")
def transactions(ctx: Context, **kwargs: Any):
    """
    Get Amazon transaction history for a given number of days.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        _authenticate(amazon_session)

        year = kwargs["year"]
        days = kwargs["days"]
        full_details = kwargs["full_details"]

        click.echo("-----------------------------------------------------------------------")
        if year:
            click.echo("Transaction History for {year} year".format(year=year))
        else:
            click.echo("Transaction History for {days} days".format(days=days))
        click.echo("-----------------------------------------------------------------------")
        click.echo("Info: Fetching transaction history, this might take a minute ...")

        config = ctx.obj["conf"]
        amazon_transactions = AmazonTransactions(amazon_session,
                                                 config=config)
        amazon_orders = AmazonOrders(amazon_session,
                                     config=config)

        start_time = time.time()

        if kwargs["year"]:
            transactions = amazon_transactions.get_transactions_by_year(year)
        else:
            transactions = amazon_transactions.get_transactions(days=days)

        if kwargs["full_details"]:
            for t in transactions:
                try: 
                    order = amazon_orders.get_order(t.order_id)
                    order.payment_date = t.completed_date
                    order.payment_amount = t.grand_total
                    order.payment_method = t.payment_method
                    # order.payment_method_last_4 = t.payment_method_last_4
                    t.order = order
                except AmazonOrdersNotFoundError as e:
                    logger.debug(f"Error getting order {t.order_id}: {e}")
                    t.order = None

        if kwargs["invoices"]:
            for t in transactions:
                o = t.order
                if not o:
                    continue
                file_paths = amazon_orders.download_invoice(
                    o.order_id,
                    o.payment_date,
                    config.output_dir,
                    o.invoice_link,
                )
                for p in file_paths:
                    click.echo(f"Invoice saved to {p}")

        if kwargs["csv"]:
            orders_dict = []
            for t in transactions:
                o = t.order
                if not o or o.payment_amount in (0, None):
                    continue
                order_dict = o.__dict__.copy()
                if isinstance(o.order_date, datetime.date):
                    order_dict["order_date"] = o.order_date.strftime("%Y/%m/%d")
                if isinstance(o.payment_date, datetime.date):
                    order_dict["payment_date"] = o.payment_date.strftime("%Y/%m/%d")
                orders_dict.append(order_dict)

            df = pd.DataFrame(orders_dict)

            df = df.rename(
                columns={
                    "index": "Index",
                    "order_date": "Order Date",
                    "order_id": "Order ID",
                    "item_quantity": "Item quantity",
                    "item_subtotal": "Item subtotal",
                    "item_shipping_and_handling": "Item shipping and handling",
                    "item_promotion": "Item promotion",
                    "item_federal_tax": "Item Federal Tax",
                    "item_provincial_tax": "Item Provincial Tax",
                    "item_regulatory_fee": "Item Regulatory Fee",
                    "item_net_total": "Item net total",
                    "payment_method": "Payment Method",
                    "payment_method_last_4": "Payment Method Last 4",
                    "payment_reference_id": "Payment Reference ID",
                    "payment_date": "Payment date",
                    "payment_amount": "Payment amount",
                    "shipments": "Shipments",
                    "title": "Title",
                    "amazon_internal_product_category": "Amazon Internal Product Category",
                    "amazon_class": "Class",
                    "amazon_commodity": "Commodity",
                    "items": "Items",
                    "order_details_link": "Order Details Link",
                    "grand_total": "Grand Total",
                    "recipient": "Recipient",
                    "free_shipping": "Free Shipping",
                    "coupon_savings": "Coupon Savings",
                    "subscription_discount": "Subscription Discount",
                    "total_before_tax": "Total Before Tax",
                    "estimated_tax": "Estimated Tax",
                    "refund_total": "Refund Total",
                }
            )[
                [
                    "Index",
                    "Order Date",
                    "Order ID",
                    "Item quantity",
                    "Item subtotal",
                    "Item shipping and handling",
                    "Item promotion",
                    "Item Federal Tax",
                    "Item Provincial Tax",
                    "Item Regulatory Fee",
                    "Item net total",
                    "Payment Method",
                    "Payment Method Last 4",
                    "Payment Reference ID",
                    "Payment date",
                    "Payment amount",
                    "Shipments",
                    "Title",
                    "Amazon Internal Product Category",
                    "Class",
                    "Commodity",
                    "Items",
                    "Order Details Link",
                    "Grand Total",
                    "Recipient",
                    "Free Shipping",
                    "Coupon Savings",
                    "Subscription Discount",
                    "Total Before Tax",
                    "Estimated Tax",
                    "Refund Total",
                ]
            ]

            df.to_csv(
                f"transactions-{days}.csv",
                index=False,
                quoting=csv.QUOTE_MINIMAL,
            )
        else:
            for t in transactions:
                click.echo(f"{_transaction_output(t, config)}\n")

        total = len(transactions)

        end_time = time.time()

        click.echo(
            "... {total} transactions parsed in {time} seconds.\n".format(total=total,
                                                                          time=int(end_time - start_time)))
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
                    "Info: The given username and password are being ignored because a previous session still exists. "
                    "If you would like to reauthenticate, call the `logout` command first.\n")
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


def _order_output(o: Order,
                  config: AmazonOrdersConfig) -> str:
    order_str = """-----------------------------------------------------------------------
Order #{order_id}
-----------------------------------------------------------------------""".format(order_id=o.order_id)

    order_str += f"\n  Shipments: {o.shipments}"
    order_str += f"\n  Order Details Link: {o.order_details_link}"
    order_str += f"\n  Grand Total: {config.constants.format_currency(o.grand_total)}"
    order_str += f"\n  Order Placed Date: {o.order_date}"
    if o.payment_date:
        order_str += f"\n  Payment Date: {o.payment_date}"
    if o.recipient:
        order_str += f"\n  Recipient: {o.recipient}"
    else:
        order_str += "\n  Recipient: None"

    if o.payment_method:
        order_str += f"\n  Payment Method: {o.payment_method}"
    if o.payment_method_last_4:
        order_str += f"\n  Payment Method Last 4: {o.payment_method_last_4}"
    if o.item_subtotal:
        order_str += f"\n  Subtotal: {config.constants.format_currency(o.item_subtotal)}"
    if o.item_shipping_and_handling:
        order_str += f"\n  Shipping Total: {config.constants.format_currency(o.item_shipping_and_handling)}"
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
    transaction_str += f"\n  Order #{t.order_id}"
    transaction_str += f"\n  Grand Total: {config.constants.format_currency(t.grand_total)}"
    transaction_str += f"\n  Order Details Link: {t.order_details_link}"

    return transaction_str


if __name__ == "__main__":
    amazon_orders_cli(obj={})
