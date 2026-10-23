#!/usr/bin/env python

__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import logging
import os
import platform
import re
import sys
import threading
import time
from typing import Any, List, Optional, Set, Tuple

import click
from click.core import Context

from amazonorders import __version__, util
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.contrib.browser.playwright import PlaywrightBrowserLauncher, PlaywrightBrowserLogin
from amazonorders.entity.invoice import Invoice
from amazonorders.exception import (
    AmazonOrdersAuthError,
    AmazonOrdersAuthRedirectError,
    AmazonOrdersBrowserNotInstalledError,
    AmazonOrdersError,
)
from amazonorders.gift_cards import AmazonGiftCards
from amazonorders.orders import AmazonOrders
from amazonorders.output import OutputFormatter
from amazonorders.prime import AmazonPrime
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

    @staticmethod
    def prompt_for_choice(msg: str,
                          choices: List[str]) -> str:
        for number, choice in enumerate(choices, start=1):
            click.echo(f"{number}: {choice}")
        click.echo(f"--> {msg} [1]: ", nl=False)

        while True:
            key = click.getchar()
            if key in ("\r", "\n"):
                number = 1
            elif key.isdigit() and 1 <= int(key) <= len(choices):
                number = int(key)
            else:
                continue

            click.echo(number)
            return choices[number - 1]

    @staticmethod
    def print_banner() -> None:
        click.echo(banner.format(version=__version__), err=True)

    @staticmethod
    def echo_session_expired() -> None:
        click.echo("... Amazon redirected to login, so it wants the persisted session's sign-in confirmed. Call the "
                   "`login` command to sign in again, or `login --browser` to log in on Amazon's own page.\n")


class ProgressSpinner:
    """
    While a fetch runs, show a spinner and how many ``noun`` have been found so far on a single ``stderr`` line,
    redrawn in place, and how many are expected if a total is known. The line is cleared when the fetch ends, whether
    or not it succeeded. Pass it as a ``progress`` or ``progress_with_total`` callback. When not ``enabled``, nothing
    is shown.
    """

    FRAMES = "|/-\\"
    INTERVAL_SECONDS = 0.1

    def __init__(self,
                 noun: str,
                 enabled: bool) -> None:
        self.noun: str = noun
        self.enabled: bool = enabled
        self._count: int = 0
        self._total: Optional[int] = None
        self._line_length: int = 0
        self._lock: threading.Lock = threading.Lock()
        self._stopped: threading.Event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def __call__(self,
                 count: int,
                 total: Optional[int] = None) -> None:
        with self._lock:
            self._count = count
            self._total = total

    def __enter__(self) -> "ProgressSpinner":
        if self.enabled:
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()

        return self

    def __exit__(self,
                 *exc_info: Any) -> None:
        if self._thread:
            self._stopped.set()
            self._thread.join()
            click.echo(f"\r{' ' * self._line_length}\r", nl=False, err=True)

    def _spin(self) -> None:
        frame = 0
        while not self._stopped.is_set():
            with self._lock:
                count = self._count
                optional_total = f" of {self._total}" if self._total is not None else ""
            self._redraw(f"{self.FRAMES[frame % len(self.FRAMES)]} {self.noun} found so far: {count}{optional_total}")
            frame += 1
            self._stopped.wait(self.INTERVAL_SECONDS)

    def _redraw(self,
                line: str) -> None:
        click.echo(f"\r{line.ljust(self._line_length)}", nl=False, err=True)
        self._line_length = max(self._line_length, len(line))


class CliAuth:
    def __init__(self,
                 amazon_session: AmazonSession) -> None:
        self.amazon_session: AmazonSession = amazon_session

    def authenticate(self,
                     retries: int = 0) -> None:
        amazon_session = self.amazon_session
        try:
            if amazon_session.auth_cookies_stored():
                if amazon_session.username or amazon_session.password:
                    click.echo(
                        "Info: The given username and password are being ignored because a previous session still "
                        "exists. To reauthenticate, call the `login` command.\n")
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
                        f"Info: Authenticating '{amazon_session.username}' failed. If using 2FA, wait a minute "
                        "before retrying with a new OTP.\n")

                amazon_session.password = None

                self.authenticate(retries=retries + 1)
            else:
                raise e

    def authenticate_with_browser(self) -> None:
        browser_login = PlaywrightBrowserLogin(self.amazon_session)
        try:
            browser_login.login()
        except AmazonOrdersBrowserNotInstalledError as e:
            if not sys.stdin.isatty():
                raise

            browser_types = (e.meta or {})["browser_types"]
            if len(browser_types) == 1:
                click.echo(f"Info: {browser_types[0]} isn't installed.\n")
                if not click.confirm(f"--> Download {browser_types[0]} now?", default=True):
                    raise
                browser_type = browser_types[0]
            else:
                click.echo("Info: No default browser was found, so one to sign in with needs to be downloaded.\n")
                browser_type = IOClick.prompt_for_choice("Choose a browser to download", browser_types)

            browser_selected = PlaywrightBrowserLauncher(self.amazon_session.config).install(browser_type)
            click.echo("")
            if browser_selected:
                click.echo(f"Info: Config \"browser\" updated to \"{browser_type}\".\n")
            browser_login.login()


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
@click.option("--domain",
              help="The Amazon domain to target (e.g. amazon.com, amazon.co.uk, amazon.com.au). "
                   "Defaults to amazon.com.")
@click.option("--progress/--no-progress", default=None,
              help="Show a running count while fetching. Defaults to showing it only in an interactive terminal, "
                   "and not with --debug.")
@click.pass_context
def amazon_orders_cli(ctx: Context,
                      **kwargs: Any) -> None:
    """
    amazon-orders is an unofficial library that provides a CLI (and Python API) for Amazon order history.

    This package works by parsing data from Amazon's consumer-facing website. A periodic build validates functionality
    to ensure its stability, but as Amazon provides no official API to use, this package may break at any time. Check
    for updates regularly to ensure you always have the latest stable release.

    This package reads Amazon's pages in English, on amazon.com and, with --domain, any other Amazon site that offers
    English. Other languages are supported through language packages.

    Documentation can be found at https://amazon-orders.readthedocs.io.
    """
    if ctx.invoked_subcommand != "version":
        IOClick.print_banner()

    ctx.ensure_object(dict)
    for key, value in kwargs.items():
        if value:
            ctx.obj[key] = value

    if kwargs["debug"]:
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.StreamHandler())

    ctx.obj["show_progress"] = (kwargs["progress"] if kwargs["progress"] is not None
                                else _is_interactive_terminal() and not kwargs["debug"])

    data = {}
    if kwargs.get("output_dir"):
        data["output_dir"] = kwargs["output_dir"]
    if kwargs.get("max_auth_attempts"):
        data["max_auth_attempts"] = kwargs["max_auth_attempts"]
    if kwargs.get("domain"):
        data["domain"] = kwargs["domain"]
    ctx.obj["conf_data"] = data

    if ctx.invoked_subcommand == "version":
        return

    try:
        ctx.obj["conf"] = AmazonOrdersConfig(config_path=kwargs.get("config_path"),
                                             data=data)
    except AmazonOrdersError as e:
        if ctx.invoked_subcommand == "update-config":
            return

        ctx.fail(f"{e} Call the `update-config` command to fix it.")

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
@click.option("--year", type=int, default=None,
              help="The year for which to get Order history. Defaults to the current year if no "
                   "time filter is specified.")
@click.option("--last-30-days", "last_30_days", is_flag=True, default=False,
              help="Get Order history for the last 30 days.")
@click.option("--last-3-months", "last_3_months", is_flag=True, default=False,
              help="Get Order history for the past 3 months.")
@click.option("--start-index", type=int,
              help="The index of the Order from which to start fetching in the history.")
@click.option("--single-page", is_flag=True, default=False,
              help="Only one page should be fetched.")
@click.option("--full-details", is_flag=True, default=False,
              help="Get the full details for each Order in the history. "
                   "This will execute an additional request per Order.")
@click.option("--order-filter", "order_filter", default=None,
              help="The order type filter to use, e.g. digital-orders for Kindle and other digital purchases, "
                   "which the default history doesn't include.")
@click.option("--family-member-id", "family_member_id", default=None,
              help="Get the Orders of this Amazon Household member, such as a linked Teen account, instead. "
                   "See the family-members command for IDs.")
@click.option("-o", "--output", type=click.Choice(OutputFormatter.OUTPUT_FORMATS), default="text",
              help="The output format. Defaults to text.")
def orders(ctx: Context,
           **kwargs: Any) -> None:
    """
    Get the Amazon Order history for a given time period.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        CliAuth(amazon_session).authenticate()

        year = kwargs["year"]
        last_30_days = kwargs["last_30_days"]
        last_3_months = kwargs["last_3_months"]
        start_index = kwargs["start_index"]
        single_page = kwargs["single_page"]
        full_details = kwargs["full_details"]
        order_filter = kwargs["order_filter"]
        family_member_id = kwargs["family_member_id"]
        output = kwargs["output"]

        exclusive_flags = [year, last_3_months, last_30_days]
        if sum(1 for item in exclusive_flags if item) > 1:
            ctx.fail("Only one of --last-30-days, --last-3-months, or --year may be used at a time.")

        # Determine time filter
        time_filter = None
        if last_30_days:
            time_filter = amazon_session.config.constants.LAST_30_DAYS_TIME_FILTER
            filter_description = "last 30 days"
        elif last_3_months:
            time_filter = amazon_session.config.constants.LAST_3_MONTHS_TIME_FILTER
            filter_description = "past 3 months"
        else:
            if year is None:
                year = datetime.date.today().year
            filter_description = str(year)

        optional_start_index = f", from index {start_index}" if start_index else ""
        optional_start_index += ", one page" if single_page else ", all pages"
        optional_full_details = ", with full details" if full_details else ""
        click.echo("""-----------------------------------------------------------------------
Order History for {filter_description}{optional_start_index}{optional_full_details}
-----------------------------------------------------------------------\n"""
                   .format(filter_description=filter_description,
                           optional_start_index=optional_start_index,
                           optional_full_details=optional_full_details), err=True)
        if not ctx.obj["show_progress"]:
            click.echo("Info: Fetching Order history, this might take a minute ...", err=True)

        config = ctx.obj["conf"]
        amazon_orders = AmazonOrders(amazon_session,
                                     config=config)

        start_time = time.time()
        with ProgressSpinner("Orders", ctx.obj["show_progress"]) as progress:
            order_list = amazon_orders.get_orders(year=year,
                                                  start_index=start_index,
                                                  full_details=full_details,
                                                  keep_paging=not single_page,
                                                  time_filter=time_filter,
                                                  order_filter=order_filter,
                                                  family_member_id=family_member_id,
                                                  progress_with_total=progress)
        end_time = time.time()

        click.echo(config.output_cls(config).format(order_list, output))

        click.echo(
            "... {total} Orders parsed in {time} seconds.\n".format(total=len(order_list),
                                                                    time=int(end_time - start_time)), err=True)
    except AmazonOrdersAuthRedirectError:
        IOClick.echo_session_expired()
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@amazon_orders_cli.command()
@click.pass_context
@click.argument("order_id")
@click.option("-o", "--output", type=click.Choice(OutputFormatter.OUTPUT_FORMATS), default="text",
              help="The output format. Defaults to text.")
def order(ctx: Context,
          order_id: str,
          **kwargs: Any) -> None:
    """
    Get the full details for a given Amazon Order ID.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        CliAuth(amazon_session).authenticate()

        config = ctx.obj["conf"]
        amazon_orders = AmazonOrders(amazon_session,
                                     config=config)

        output = kwargs["output"]

        o = amazon_orders.get_order(order_id)

        click.echo(config.output_cls(config).format([o], output))
    except AmazonOrdersAuthRedirectError:
        IOClick.echo_session_expired()
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@amazon_orders_cli.command()
@click.pass_context
@click.argument("order_ids", nargs=-1, required=True)
@click.option("--download", "download_dir", type=click.Path(file_okay=False),
              help="Save the documents (HTML and PDFs) to this directory, replacing any of the same name from an "
                   "earlier run.")
@click.option("-o", "--output", type=click.Choice(OutputFormatter.OUTPUT_FORMATS), default="text",
              help="The output format. Defaults to text.")
def invoices(ctx: Context,
             order_ids: Tuple[str, ...],
             download_dir: Optional[str],
             **kwargs: Any) -> None:
    """
    Get the invoices for the given Amazon Order IDs (the Printable Order Summary, and any invoice and credit note
    PDFs), and optionally download them.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        CliAuth(amazon_session).authenticate()

        config = ctx.obj["conf"]
        amazon_orders = AmazonOrders(amazon_session,
                                     config=config)

        invoice_list = []
        for order_id in order_ids:
            order_invoices = amazon_orders.get_invoices(order_id)
            if not order_invoices:
                click.echo(f"No invoices for Order {order_id}.", err=True)
            invoice_list += order_invoices

        click.echo(config.output_cls(config).format(invoice_list, kwargs["output"]))

        if download_dir:
            os.makedirs(download_dir, exist_ok=True)
            saved_paths: Set[str] = set()
            for document in invoice_list:
                path = _invoice_path(download_dir, document, saved_paths)
                with open(path, "wb") as invoice_file:
                    invoice_file.write(amazon_orders.download_invoice(document))
                click.echo(f"Saved {path}", err=True)

        click.echo(f"... {len(invoice_list)} Invoices for {len(order_ids)} Orders.\n", err=True)
    except AmazonOrdersAuthRedirectError:
        IOClick.echo_session_expired()
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@amazon_orders_cli.command("order-transactions")
@click.pass_context
@click.argument("order_id")
@click.option("-o", "--output", type=click.Choice(OutputFormatter.OUTPUT_FORMATS), default="text",
              help="The output format. Defaults to text.")
def order_transactions(ctx: Context,
                       order_id: str,
                       **kwargs: Any) -> None:
    """
    Get the Transactions for a given Amazon Order ID.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        CliAuth(amazon_session).authenticate()

        config = ctx.obj["conf"]
        amazon_transactions = AmazonTransactions(amazon_session,
                                                 config=config)

        output = kwargs["output"]

        start_time = time.time()
        with ProgressSpinner("Transactions", ctx.obj["show_progress"]) as progress:
            order_transaction_list = amazon_transactions.get_transactions(order_id=order_id, progress=progress)
        end_time = time.time()

        click.echo(config.output_cls(config).format(order_transaction_list, output))

        click.echo(
            "... {total} Transactions parsed in {time} seconds.\n".format(total=len(order_transaction_list),
                                                                          time=int(end_time - start_time)), err=True)
    except AmazonOrdersAuthRedirectError:
        IOClick.echo_session_expired()
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@amazon_orders_cli.command("search-orders")
@click.pass_context
@click.argument("query")
@click.option("--single-page", is_flag=True, default=False,
              help="Only one page should be fetched.")
@click.option("-o", "--output", type=click.Choice(OutputFormatter.OUTPUT_FORMATS), default="text",
              help="The output format. Defaults to text.")
def search_orders(ctx: Context,
                  query: str,
                  **kwargs: Any) -> None:
    """
    Search the Order history, across every year, for a product, Order number, address, or recipient.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        CliAuth(amazon_session).authenticate()

        config = ctx.obj["conf"]
        amazon_orders = AmazonOrders(amazon_session,
                                     config=config)

        start_time = time.time()
        with ProgressSpinner("Items", ctx.obj["show_progress"]) as progress:
            results = amazon_orders.search_orders(query,
                                                  keep_paging=not kwargs["single_page"],
                                                  progress=progress)
        end_time = time.time()

        click.echo(config.output_cls(config).format(results, kwargs["output"]))

        click.echo(
            "... {total} matching Items found in {time} seconds.\n".format(
                total=len(results), time=int(end_time - start_time)), err=True)
    except AmazonOrdersAuthRedirectError:
        IOClick.echo_session_expired()
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@amazon_orders_cli.command("prime-payments")
@click.pass_context
@click.option("-o", "--output", type=click.Choice(OutputFormatter.OUTPUT_FORMATS), default="text",
              help="The output format. Defaults to text.")
def prime_payments(ctx: Context, **kwargs: Any) -> None:
    """
    Get the Prime membership payment history.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        CliAuth(amazon_session).authenticate()

        config = ctx.obj["conf"]
        amazon_prime = AmazonPrime(amazon_session,
                                   config=config)

        start_time = time.time()
        prime_payments = amazon_prime.get_prime_payments()
        end_time = time.time()

        click.echo(config.output_cls(config).format(prime_payments, kwargs["output"]))

        click.echo(
            "... {total} Prime payments parsed in {time} seconds.\n".format(
                total=len(prime_payments), time=int(end_time - start_time)), err=True)
    except AmazonOrdersAuthRedirectError:
        IOClick.echo_session_expired()
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@amazon_orders_cli.command()
@click.pass_context
@click.option("--days", default=365,
              help="The number of days of Transactions to get.")
@click.option("-o", "--output", type=click.Choice(OutputFormatter.OUTPUT_FORMATS), default="text",
              help="The output format. Defaults to text.")
def transactions(ctx: Context, **kwargs: Any) -> None:
    """
    Get Amazon Transaction history for a given number of days.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        CliAuth(amazon_session).authenticate()

        days = kwargs["days"]
        output = kwargs["output"]

        click.echo(
            """-----------------------------------------------------------------------
Transaction History for {days} days
-----------------------------------------------------------------------\n""".format(days=days), err=True
        )
        if not ctx.obj["show_progress"]:
            click.echo("Info: Fetching Transaction history, this might take a minute ...", err=True)

        config = ctx.obj["conf"]
        amazon_transactions = AmazonTransactions(amazon_session,
                                                 config=config)

        start_time = time.time()
        with ProgressSpinner("Transactions", ctx.obj["show_progress"]) as progress:
            transaction_list = amazon_transactions.get_transactions(days=days, progress=progress)
        end_time = time.time()

        click.echo(config.output_cls(config).format(transaction_list, output))

        click.echo(
            "... {total} Transactions parsed in {time} seconds.\n".format(total=len(transaction_list),
                                                                          time=int(end_time - start_time)), err=True)
    except AmazonOrdersAuthRedirectError:
        IOClick.echo_session_expired()
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@amazon_orders_cli.command("family-members")
@click.pass_context
@click.option("-o", "--output", type=click.Choice(OutputFormatter.OUTPUT_FORMATS), default="text",
              help="The output format. Defaults to text.")
def family_members(ctx: Context, **kwargs: Any) -> None:
    """
    Get the Amazon Household members whose Orders this account can view, such as linked Teen accounts.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        CliAuth(amazon_session).authenticate()

        config = ctx.obj["conf"]
        amazon_orders = AmazonOrders(amazon_session,
                                     config=config)

        start_time = time.time()
        members = amazon_orders.get_family_members()
        end_time = time.time()

        click.echo(config.output_cls(config).format(members, kwargs["output"]))

        click.echo(
            "... {total} Amazon Household members parsed in {time} seconds.\n".format(
                total=len(members), time=int(end_time - start_time)), err=True)
    except AmazonOrdersAuthRedirectError:
        IOClick.echo_session_expired()
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@amazon_orders_cli.command()
@click.pass_context
@click.option("--days", default=365,
              help="The number of days of Gift Card activity to get. 0 gets only the balance (and today's activity).")
@click.option("--single-page", is_flag=True, default=False,
              help="Only one page should be fetched.")
@click.option("-o", "--output", type=click.Choice(OutputFormatter.OUTPUT_FORMATS), default="text",
              help="The output format. Defaults to text.")
def gift_cards(ctx: Context, **kwargs: Any) -> None:
    """
    Get the Amazon Gift Card balance, and its activity for a given number of days.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        CliAuth(amazon_session).authenticate()

        days = kwargs["days"]
        output = kwargs["output"]

        click.echo(
            """-----------------------------------------------------------------------
Gift Cards, with {days} days of activity
-----------------------------------------------------------------------\n""".format(days=days), err=True
        )
        if not ctx.obj["show_progress"]:
            click.echo("Info: Fetching Gift Cards, this might take a minute ...", err=True)

        config = ctx.obj["conf"]
        amazon_gift_cards = AmazonGiftCards(amazon_session,
                                            config=config)

        start_time = time.time()
        with ProgressSpinner("Gift Card activity entries", ctx.obj["show_progress"]) as progress:
            gift_card_results = amazon_gift_cards.get_gift_cards(days=days,
                                                                 keep_paging=not kwargs["single_page"],
                                                                 progress=progress)
        end_time = time.time()

        click.echo(config.output_cls(config).format_gift_cards(gift_card_results, output))

        if output == "csv" and gift_card_results.balance is not None:
            click.echo(f"Gift Card Balance: {config.constants.format_currency(gift_card_results.balance)}",
                       err=True)
        click.echo(
            "... {total} Gift Card activity entries parsed in {time} seconds.\n".format(
                total=len(gift_card_results.items), time=int(end_time - start_time)), err=True)
    except AmazonOrdersAuthRedirectError:
        IOClick.echo_session_expired()
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@amazon_orders_cli.command(short_help="Check if a persisted session exists, and that Amazon still accepts it.")
@click.pass_context
def check_session(ctx: Context) -> None:
    """
    Check if a persisted session exists, meaning commands can be called without needing to provide credentials. If
    one does, Amazon is asked whether it still accepts it, since a session's cookies outlive it.
    """
    amazon_session = ctx.obj["amazon_session"]
    if not amazon_session.auth_cookies_stored():
        click.echo("Info: No persisted session exists.\n")
        return

    try:
        if amazon_session.check_signed_in():
            click.echo("Info: A persisted session exists, and Amazon accepts it.\n")
        else:
            click.echo("Info: A persisted session exists, but Amazon's response didn't say whether it still accepts "
                       "it. Try again later.\n")
    except AmazonOrdersAuthRedirectError:
        click.echo("Info: A persisted session exists, but Amazon no longer accepts it.\n")
        IOClick.echo_session_expired()
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))


@amazon_orders_cli.command()
@click.pass_context
@click.option("--browser", is_flag=True, default=False,
              help="Sign in with a browser window, so amazon-orders never needs to store your credentials. "
                   "Requires the browser extra.")
def login(ctx: Context, **kwargs: Any) -> None:
    """
    Log in to establish an Amazon session and cookies.
    """
    amazon_session = ctx.obj["amazon_session"]

    try:
        if amazon_session.auth_cookies_stored():
            click.echo("Info: Logging out of the persisted session first, so this login starts fresh.\n")
            amazon_session.logout()

        if kwargs["browser"]:
            CliAuth(amazon_session).authenticate_with_browser()
        else:
            CliAuth(amazon_session).authenticate()
    except AmazonOrdersError as e:
        logger.debug("An error occurred.", exc_info=True)
        ctx.fail(str(e))

    click.echo("Info: Successfully logged in to Amazon, session persisted.\n")


@amazon_orders_cli.command()
@click.pass_context
def logout(ctx: Context) -> None:
    """
    Log out of existing Amazon sessions and clear cookies.
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
    typed_value = util.to_type(value)

    try:
        conf = AmazonOrdersConfig(config_path=ctx.obj.get("config_path"),
                                  data={**ctx.obj["conf_data"], key: typed_value})
    except AmazonOrdersError as e:
        ctx.fail(f"Config \"{key}\" was not updated: {e}")

    conf.update_config(key, typed_value)

    click.echo(f"Info: Config \"{key}\" updated to \"{value}\".\n")


@amazon_orders_cli.command()
@click.pass_context
def version(ctx: Context) -> None:
    """
    Show the banner and package version.
    """
    click.echo(f"amazon-orders/{__version__} Python/{platform.python_version()}")
    ctx.exit(0)


def _is_interactive_terminal() -> bool:
    return sys.stderr.isatty() and os.environ.get("TERM") != "dumb"


def _invoice_path(download_dir: str,
                  invoice: Invoice,
                  saved_paths: Set[str]) -> str:
    # e.g. "302-0000000-0000000_invoice-2.pdf", with a counter if the name repeats within an Order. A file from an
    # earlier run is overwritten, so downloading again doesn't duplicate it.
    name = re.sub(r"[^a-z0-9]+", "-", (invoice.name or "").lower()).strip("-") or "invoice"
    extension = invoice.format or "pdf"
    path = os.path.join(download_dir, f"{invoice.order_number}_{name}.{extension}")
    i = 2
    while path in saved_paths:
        path = os.path.join(download_dir, f"{invoice.order_number}_{name}-{i}.{extension}")
        i += 1
    saved_paths.add(path)
    return path


if __name__ == "__main__":
    amazon_orders_cli(obj={})
