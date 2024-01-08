import click

from amazonorders.auth import login
from amazonorders.parser import get_orders

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.2"


@click.group(invoke_without_command=True)
@click.pass_context
def amazon_orders(ctx, **kwargs):
    login()

    get_orders()


if __name__ == "__main__":
    amazon_orders(obj={})
