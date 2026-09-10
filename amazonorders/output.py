__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import csv
import io
import json
import logging
from typing import Any, Dict, List, Sequence

import yaml

from amazonorders.conf import AmazonOrdersConfig
from amazonorders.entity.order import Order
from amazonorders.entity.parsable import Parsable
from amazonorders.entity.transaction import Transaction

logger = logging.getLogger(__name__)


class OutputFormatter:
    """
    A class that renders entities for output. Extend and override with ``output_class`` in the config:

    .. code-block:: python

        from amazonorders.conf import AmazonOrdersConfig

        config = AmazonOrdersConfig(data={"output_class": "my_module.MyOutputFormatter"})

    ``json``, ``yaml``, and ``csv`` are built from
    :func:`~amazonorders.entity.parsable.Parsable.to_dict`, so any
    :class:`~amazonorders.entity.parsable.Parsable` can be rendered in them, nested entities included.
    ``text`` is rendered by this class's per-entity methods, falling back to the entity's own ``__str__``.

    ``csv`` renders one row per entity, since a spreadsheet cannot nest: a nested entity becomes
    ``parent_child`` columns (e.g. ``recipient_name``), and a list becomes a ``<field>_count`` column
    alongside its values joined by :attr:`CSV_LIST_DELIMITER`. Columns are the union of the fields
    present, so an empty result has no columns and renders as an empty document, where ``json`` and
    ``yaml`` render as an empty list.
    """

    #: The formats accepted by the CLI's ``--output`` option.
    OUTPUT_FORMATS = ["text", "json", "yaml", "csv"]
    #: Joins a list's values within a single CSV column.
    CSV_LIST_DELIMITER = "; "
    #: Fields tried, in order, to summarize a nested entity in a CSV column.
    CSV_SUMMARY_FIELDS = ["title", "name"]

    def __init__(self,
                 config: AmazonOrdersConfig) -> None:
        #: The config to use.
        self.config: AmazonOrdersConfig = config

    def format(self,
               entities: Sequence[Parsable],
               output_format: str) -> str:
        """
        Render the given entities in the given format.

        :param entities: The entities to render.
        :param output_format: One of :attr:`OUTPUT_FORMATS`.
        :return: The rendered output.
        """
        if output_format == "text":
            return "\n".join(f"{self.text(entity)}\n" for entity in entities)

        serialized = [entity.to_dict() for entity in entities]
        if output_format == "json":
            return f"{json.dumps(serialized, indent=2)}\n"
        elif output_format == "yaml":
            return yaml.safe_dump(serialized, sort_keys=False, allow_unicode=True, default_flow_style=False)

        return self._csv(serialized)

    def text(self,
             entity: Parsable) -> str:
        """
        Render a single entity as human-readable text.

        :param entity: The entity to render.
        :return: The entity as text.
        """
        if isinstance(entity, Order):
            return self.order_text(entity)
        elif isinstance(entity, Transaction):
            return self.transaction_text(entity)

        return str(entity)

    def order_text(self,
                   order: Order) -> str:
        """
        Render an Order as human-readable text.

        :param order: The Order to render.
        :return: The Order as text.
        """
        order_str = """-----------------------------------------------------------------------
Order #{order_number}
-----------------------------------------------------------------------""".format(
            order_number=order.order_number)

        order_str += f"\n  Shipments: {order.shipments}"
        order_str += f"\n  Order Details Link: {order.order_details_link}"
        if order.grand_total:
            order_str += f"\n  Grand Total: {self.config.constants.format_currency(order.grand_total)}"
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
            order_str += f"\n  Subtotal: {self.config.constants.format_currency(order.subtotal)}"
        if order.shipping_total:
            order_str += f"\n  Shipping Total: {self.config.constants.format_currency(order.shipping_total)}"
        if order.free_shipping:
            order_str += f"\n  Free Shipping: {self.config.constants.format_currency(order.free_shipping)}"
        if order.subscription_discount:
            order_str += ("\n  Subscription Discount: "
                          f"{self.config.constants.format_currency(order.subscription_discount)}")
        if order.total_before_tax:
            order_str += f"\n  Total Before Tax: {self.config.constants.format_currency(order.total_before_tax)}"
        if order.estimated_tax:
            order_str += f"\n  Estimated Tax: {self.config.constants.format_currency(order.estimated_tax)}"
        if order.refund_total:
            order_str += f"\n  Refund Total: {self.config.constants.format_currency(order.refund_total)}"

        order_str += "\n-----------------------------------------------------------------------"

        return order_str

    def transaction_text(self,
                         transaction: Transaction) -> str:
        """
        Render a Transaction as human-readable text.

        :param transaction: The Transaction to render.
        :return: The Transaction as text.
        """
        transaction_str = f"Transaction: {transaction.completed_date}"
        transaction_str += f"\n  Order #{transaction.order_number}"
        if transaction.grand_total:
            transaction_str += f"\n  Grand Total: {self.config.constants.format_currency(transaction.grand_total)}"
        transaction_str += f"\n  Order Details Link: {transaction.order_details_link}"

        return transaction_str

    def _csv(self,
             entities: List[Dict[str, Any]]) -> str:
        if not entities:
            return ""

        rows = [self._flatten_for_csv(entity) for entity in entities]
        columns: List[str] = []
        for row in rows:
            columns += [column for column in row if column not in columns]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

        return output.getvalue()

    def _flatten_for_csv(self,
                         entity: Dict[str, Any]) -> Dict[str, Any]:
        row: Dict[str, Any] = {}
        for field, value in entity.items():
            if isinstance(value, dict):
                for nested_field, nested_value in self._flatten_for_csv(value).items():
                    row[f"{field}_{nested_field}"] = nested_value
            elif isinstance(value, list):
                row[f"{field}_count"] = len(value)
                row[field] = self.CSV_LIST_DELIMITER.join(self._csv_summary(item) for item in value)
            elif isinstance(value, str):
                row[field] = self._single_line(value)
            else:
                row[field] = value

        return row

    def _csv_summary(self,
                     item: Any) -> str:
        if isinstance(item, dict):
            for field in self.CSV_SUMMARY_FIELDS:
                if item.get(field):
                    return self._single_line(str(item[field]))

            return ""

        return self._single_line(str(item))

    def _single_line(self,
                     value: str) -> str:
        return " ".join(value.split())
