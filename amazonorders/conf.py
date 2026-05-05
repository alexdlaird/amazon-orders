import logging
import os
import threading
from typing import Any, Dict, Optional, Union

import yaml

from amazonorders import util

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "amazonorders")

config_file_lock = threading.Lock()
cookies_file_lock = threading.Lock()
debug_output_file_lock = threading.Lock()


class AmazonOrdersConfig:
    """
    An object containing ``amazon-orders``'s configuration. The state of this object is populated from the config file,
    if present, when it is instantiated, and it is also persisted back to the config file when :func:`~save` is called.

    If overrides are passed in ``data`` parameter when this object is instantiated, they will be used to populate the
    new object, but not persisted to the config file until :func:`~save` is called.

    Default values provisioned with the config can be found
    `here <https://amazon-orders.readthedocs.io/_modules/amazonorders/conf.html#AmazonOrdersConfig>`_.
    """

    def __init__(self,
                 config_path: Optional[str] = None,
                 data: Optional[Dict[str, Any]] = None) -> None:
        #: The path to use for the config file.
        self.config_path: str = os.path.join(DEFAULT_CONFIG_DIR, "config.yml") if config_path is None else config_path

        # Provision default configs
        thread_pool_size = (os.cpu_count() or 1) * 4
        self._data = {
            # The maximum number of times to retry provisioning initial cookies before failing
            "max_cookie_attempts": 10,
            # The number of seconds to wait before retrying to provision initial cookies
            "cookie_reattempt_wait": 0.5,
            # The maximum number of authentication forms to try before failing
            "max_auth_attempts": 10,
            # The number of seconds to wait before retrying the auth flow
            "auth_reattempt_wait": 5,
            # Where output files (for instance, HTML pages, when ``debug`` mode is enabled) will be written
            "output_dir": os.path.join(os.getcwd(), "output"),
            "cookie_jar_path": os.path.join(DEFAULT_CONFIG_DIR, "cookies.json"),
            "constants_class": "amazonorders.constants.Constants",
            "selectors_class": "amazonorders.selectors.Selectors",
            "order_class": "amazonorders.entity.order.Order",
            "shipment_class": "amazonorders.entity.shipment.Shipment",
            "item_class": "amazonorders.entity.item.Item",
            "bs4_parser": "html.parser",
            "thread_pool_size": (os.cpu_count() or 1) * 4,
            "connection_pool_size": thread_pool_size * 2,
            # The maximum number of failed attempts to allow before failing CLI authentication
            "max_auth_retries": 1,
            # Set ``True`` to log a warning message instead of raising an exception when a required field is missing.
            "warn_on_missing_required_field": False
        }

        with config_file_lock:
            # Ensure directories and files exist for config data
            config_dir = os.path.dirname(self.config_path)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)

            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as config_file:
                    logger.debug(f"Loading config from {self.config_path} ...")
                    config = yaml.safe_load(config_file)
                    if config is not None:
                        config.update(data or {})
                        data = config

        # Overload defaults if values passed
        self._data.update(data or {})

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        with cookies_file_lock:
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
        return self._data.get(key, None)

    def __contains__(self,
                     key: str) -> bool:
        return key in self._data

    def __getstate__(self) -> Dict[str, Any]:
        return self._data

    def __setstate__(self,
                     state: Dict[str, Any]) -> None:
        self._data = state
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

    def update_config(self,
                      key: str,
                      value: Union[str, int, float],
                      save: bool = True) -> None:
        """
        Update the given key/value pair in the config object. By default, this update will also be persisted to the
        config file. If only the object should be updated without persisting, pass ``save=False``.

        :param key: The key to be updated.
        :param value: The new value.
        :param save: ``True`` if the config should be persisted.
        """
        self._data[key] = value

        if save:
            self.save()

    def save(self) -> None:
        """
        Persist the current state of this config object to the config file.
        """
        with config_file_lock:
            with open(self.config_path, "w") as config_file:
                logger.debug(f"Saving config to {self.config_path} ...")

                yaml.dump(self._data, config_file)
