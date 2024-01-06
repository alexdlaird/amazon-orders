import click

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.1"


@click.group(invoke_without_command=True)
@click.pass_context
def amazon_orders(ctx, **kwargs):
    pass


if __name__ == "__main__":
    amazon_orders(obj={})
