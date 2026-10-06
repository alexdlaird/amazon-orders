import importlib
import inspect
import logging
import os
import threading
from typing import Any, Dict, Optional, Union

import yaml
from bs4 import BeautifulSoup
from bs4.exceptions import FeatureNotFound

from amazonorders import util
from amazonorders.exception import AmazonOrdersError

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "amazonorders")

config_file_lock = threading.Lock()
cookies_file_lock = threading.Lock()
debug_output_file_lock = threading.Lock()

_LANGUAGE_PACKAGE_CLASSES = {
    "constants_class": "Constants",
    "selectors_class": "Selectors",
    "order_class": "Order",
    "shipment_class": "Shipment",
    "item_class": "Item",
    "transaction_class": "Transaction",
    "transactions_page_class": "TransactionsPage",
}


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

        self._data: Dict[str, Any] = self._default_data()
        self._resolved_classes: Dict[str, Any] = {}

        with config_file_lock:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as config_file:
                    logger.debug(f"Loading config from {self.config_path} ...")
                    config = yaml.safe_load(config_file)
                    if config is not None:
                        config.update(data or {})
                        data = config

        # Overload defaults if values passed
        self._data.update(data or {})

        self._validate_bs4_parser()
        self._validate_class_paths()

        #: The :class:`~amazonorders.constants.Constants` in use, rebuilt when the domain changes.
        self.constants: Any

        self._load_classes()

    @staticmethod
    def _default_data() -> Dict[str, Any]:
        """
        Provision the default config values.

        :return: The default config values.
        """
        thread_pool_size = (os.cpu_count() or 1) * 4
        return {
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
            "transaction_class": "amazonorders.entity.transaction.Transaction",
            "output_class": "amazonorders.output.OutputFormatter",
            "transactions_page_class": "amazonorders.transactions.TransactionsPage",
            "language_package": None,
            "bs4_parser": "html.parser",
            "auth_forms_classes": [],
            # Timeout in seconds for browser-based challenge detection and resolution
            "browser_timeout": 30,
            # Timeout in seconds for HTTP requests; ``None`` leaves requests with no timeout
            "request_timeout": None,
            "thread_pool_size": (os.cpu_count() or 1) * 4,
            "connection_pool_size": thread_pool_size * 2,
            # The maximum number of failed attempts to allow before failing CLI authentication
            "max_auth_retries": 1,
            # Set ``True`` to log a warning message instead of raising an exception when a required field is missing.
            "warn_on_missing_required_field": False
        }

    def _load_classes(self) -> None:
        """
        Instantiate the constants and selectors, which the auth layer itself uses and so are always
        needed. The entity, output, and Transactions page classes resolve on first use instead.
        """
        selectors_class_split = self._class_path("selectors_class").split(".")

        self.constants = self._instantiate_constants()
        self.selectors = util.load_class(selectors_class_split[:-1], selectors_class_split[-1])()

    def _validate_class_paths(self) -> None:
        """
        Check the shape of every lazily resolved class path, and of the ``language_package``, at construction, so a
        malformed value still fails here rather than at first use, without importing the modules they name.

        :raises AmazonOrdersError: If a class path is not a dotted path to a class, or the ``language_package`` is
            not a dotted module path.
        """
        for key in ("order_class", "shipment_class", "item_class", "transaction_class", "output_class",
                    "transactions_page_class"):
            value = self._data.get(key)
            if (not isinstance(value, str) or "." not in value
                    or not all(part.isidentifier() for part in value.split("."))):
                raise AmazonOrdersError(f"Config value for \"{key}\" is not a dotted class path: {value!r}")

        language_package = self._data.get("language_package")
        if language_package is not None and (not isinstance(language_package, str) or
                                             not all(part.isidentifier() for part in language_package.split("."))):
            raise AmazonOrdersError(f"Config value for \"language_package\" is not a dotted module path: "
                                    f"{language_package!r}")

    def _resolve_class(self,
                       key: str) -> Any:
        """
        Resolve and cache the class named by the given config key.

        :param key: The config key naming the class.
        :return: The resolved class.
        :raises AmazonOrdersError: If the configured class path cannot be imported.
        """
        if key not in self._resolved_classes:
            class_path = self._class_path(key)
            class_split = class_path.split(".")
            try:
                self._resolved_classes[key] = util.load_class(class_split[:-1], class_split[-1])
            except (AttributeError, ImportError) as e:
                raise AmazonOrdersError(f"Could not resolve \"{key}\" ({class_path}): {e}") from e

        return self._resolved_classes[key]

    def _class_path(self,
                    key: str) -> str:
        """
        Get the class path for the given config key. A key left at its default uses the class of the same name
        from the ``language_package``, if one is configured and defines it as a subclass of the default, so an
        explicitly configured class always wins. A value equal to the default counts as unset, since :func:`save`
        persists every default. A class of that name that isn't a subclass of the default (for instance, the default
        itself, imported into the package) is ignored with a warning.

        :param key: The config key naming the class.
        :return: The class path.
        :raises AmazonOrdersError: If the ``language_package`` cannot be imported.
        """
        class_path = self._data[key]
        language_package = self._data.get("language_package")
        if (key not in _LANGUAGE_PACKAGE_CLASSES or not language_package or
                class_path != self._default_data()[key]):
            return class_path

        try:
            package = importlib.import_module(language_package)
        except ImportError as e:
            raise AmazonOrdersError(f"Could not import \"language_package\" ({language_package}): {e}") from e

        class_name = _LANGUAGE_PACKAGE_CLASSES[key]
        package_class = getattr(package, class_name, None)
        if package_class is None:
            return class_path

        class_split = class_path.split(".")
        default_class: Any = util.load_class(class_split[:-1], class_split[-1])
        if (not isinstance(package_class, type) or package_class is default_class or
                not issubclass(package_class, default_class)):
            logger.warning(f"\"language_package\" ({language_package}) defines {class_name}, but it isn't a subclass "
                           f"of {class_path}, so {class_path} is used.")
            return class_path

        logger.debug(f"Using {language_package}.{class_name} for \"{key}\".")
        return f"{language_package}.{class_name}"

    def _set_class(self,
                   key: str,
                   value: Any) -> None:
        """
        Override the resolved class for the given config key, so a class can be assigned directly as
        well as named through its config path.

        :param key: The config key naming the class.
        :param value: The class to use.
        """
        self._resolved_classes[key] = value

    @property
    def order_cls(self) -> Any:
        """The :class:`~amazonorders.entity.order.Order` class in use."""
        return self._resolve_class("order_class")

    @order_cls.setter
    def order_cls(self,
                  value: Any) -> None:
        self._set_class("order_class", value)

    @property
    def shipment_cls(self) -> Any:
        """The :class:`~amazonorders.entity.shipment.Shipment` class in use."""
        return self._resolve_class("shipment_class")

    @shipment_cls.setter
    def shipment_cls(self,
                     value: Any) -> None:
        self._set_class("shipment_class", value)

    @property
    def item_cls(self) -> Any:
        """The :class:`~amazonorders.entity.item.Item` class in use."""
        return self._resolve_class("item_class")

    @item_cls.setter
    def item_cls(self,
                 value: Any) -> None:
        self._set_class("item_class", value)

    @property
    def transaction_cls(self) -> Any:
        """The :class:`~amazonorders.entity.transaction.Transaction` class in use."""
        return self._resolve_class("transaction_class")

    @transaction_cls.setter
    def transaction_cls(self,
                        value: Any) -> None:
        self._set_class("transaction_class", value)

    @property
    def output_cls(self) -> Any:
        """The :class:`~amazonorders.output.OutputFormatter` class in use."""
        return self._resolve_class("output_class")

    @output_cls.setter
    def output_cls(self,
                   value: Any) -> None:
        self._set_class("output_class", value)

    @property
    def transactions_page_cls(self) -> Any:
        """The :class:`~amazonorders.transactions.TransactionsPage` class in use."""
        return self._resolve_class("transactions_page_class")

    @transactions_page_cls.setter
    def transactions_page_cls(self,
                              value: Any) -> None:
        self._set_class("transactions_page_class", value)

    def _validate_bs4_parser(self) -> None:
        try:
            BeautifulSoup("", str(self._data["bs4_parser"]))
        except FeatureNotFound:
            logger.debug(
                f"Configured bs4_parser '{self._data['bs4_parser']}' is unavailable; "
                f"using the default 'html.parser'. To use it, install the parser "
                f"(e.g. `pip install amazon-orders[lxml]`)."
            )
            self._data["bs4_parser"] = "html.parser"

    def _instantiate_constants(self) -> Any:
        constants_class_split = self._class_path("constants_class").split(".")
        constants_cls = util.load_class(constants_class_split[:-1], constants_class_split[-1])
        # Pass ``self`` only when the constants class accepts a config arg, to keep backward
        # compatibility with existing zero-arg ``constants_class`` subclasses.
        init_params = inspect.signature(constants_cls.__init__).parameters
        if len(init_params) > 1:
            return constants_cls(self)
        return constants_cls()

    def set_domain(self,
                   domain: str) -> None:
        """
        Set the active Amazon domain and rebuild :attr:`~amazonorders.conf.AmazonOrdersConfig.constants`
        so URL-derived attributes and region-sensitive headers reflect the change.

        :param domain: The Amazon domain (e.g. ``amazon.com.au``) or full URL.
        """
        self._data["domain"] = domain
        self.constants = self._instantiate_constants()

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
        self._resolved_classes = {}
        self._load_classes()

    def update_config(self,
                      key: str,
                      value: Union[str, int, float, bool, None],
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
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            with open(self.config_path, "w") as config_file:
                logger.debug(f"Saving config to {self.config_path} ...")

                yaml.dump(self._data, config_file)
