import logging
import os
from typing import Any, Dict, Optional

import yaml

from amazonorders import util

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "amazonorders")


class AmazonOrdersConfig:
    """
    An object containing ``amazon-orders``'s configuration. The state of this object is populated from the config file,
    if present, when it is instantiated, and it is also persisted back to the config file when :func:`~save` is called.

    If overrides are passed in ``data`` parameter when this object is instantiated, they will be used in the
    instantiated object, but not persisted to the config file until :func:`~save` is called.
    """

    def __init__(self,
                 config_path: Optional[str] = None,
                 data: Optional[Dict[str, Any]] = None) -> None:
        #: The path to use for the config file.
        self.config_path: str = os.path.join(DEFAULT_CONFIG_DIR, "config.yml") if config_path is None else config_path

        # Provision default configs
        self._data = {
            "max_auth_attempts": 10,
            "output_dir": os.path.join(os.getcwd(), "output"),
            "cookie_jar_path": os.path.join(DEFAULT_CONFIG_DIR, "cookies.json"),
            "constants_class": "amazonorders.constants.Constants",
            "selectors_class": "amazonorders.selectors.Selectors",
            "order_class": "amazonorders.entity.order.Order",
            "shipment_class": "amazonorders.entity.shipment.Shipment",
            "item_class": "amazonorders.entity.item.Item",
            "bs4_parser": "html.parser",
        }

        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as config_file:
                logger.debug(f"Loading config from {self.config_path} ...")
                config = yaml.safe_load(config_file)
                if config is not None:
                    config.update(data or {})
                    data = config

        # Overload defaults if values passed
        self._data.update(data or {})

        # Ensure directories and files exist for config data
        config_dir = os.path.dirname(self.config_path)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        cookie_jar_dir = os.path.dirname(self.cookie_jar_path)
        if not os.path.exists(cookie_jar_dir):
            os.makedirs(cookie_jar_dir)

        constants_class_split = self.constants_class.split(".")
        selectors_class_split = self.selectors_class.split(".")
        order_class_split = self.order_class.split(".")
        shipment_class_split = self.shipment_class.split(".")
        item_class_split = self.item_class.split(".")

        self.constants = util.load_class(constants_class_split[:-1], constants_class_split[-1])()
        self.selectors = util.load_class(selectors_class_split[:-1], selectors_class_split[-1])()
        self.order_cls = util.load_class(order_class_split[:-1], order_class_split[-1])
        self.shipment_cls = util.load_class(shipment_class_split[:-1], shipment_class_split[-1])
        self.item_cls = util.load_class(item_class_split[:-1], item_class_split[-1])

    def __getattr__(self,
                    key: str) -> Any:
        return self._data[key]

    def update_config(self,
                      key: str,
                      value: str,
                      save: bool = True) -> None:
        """
        Update the given key/value pair in the config object. By default, this update will also be persisted to the
        config file, but if only the object should be updated without persisted, passing ``save=False``.

        :param key: The to be updated.
        :param value: The new value.
        :param save: True if the config should be persisted.
        """
        self._data[key] = value

        if save:
            self.save()

    def save(self) -> None:
        """
        Persist the current state of this config object to the config file.
        """
        with open(self.config_path, "w") as config_file:
            logger.debug(f"Saving config to {self.config_path} ...")

            yaml.dump(self._data, config_file)
