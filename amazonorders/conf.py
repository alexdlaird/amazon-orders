__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import importlib
import logging
import os
from typing import Any, Dict, Optional

from amazonauth.conf import (
    DEFAULT_COOKIE_JAR_SITE,
    ENVIRONMENT_VARIABLE_PREFIX,
    AmazonAuthConfig,
    config_file_lock,
    cookies_file_lock,
    debug_output_file_lock,
)
from amazonauth.util import load_class

from amazonorders.exception import AmazonOrdersError

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "amazonorders")

__all__ = [
    "DEFAULT_CONFIG_DIR",
    "config_file_lock",
    "cookies_file_lock",
    "debug_output_file_lock",
    "ENVIRONMENT_VARIABLE_PREFIX",
    "DEFAULT_COOKIE_JAR_SITE",
    "AmazonOrdersConfig",
]

_LANGUAGE_PACKAGE_CLASSES = {
    "constants_class": "Constants",
    "selectors_class": "Selectors",
    "order_class": "Order",
    "shipment_class": "Shipment",
    "item_class": "Item",
    "transaction_class": "Transaction",
    "transactions_page_class": "TransactionsPage",
}


class AmazonOrdersConfig(AmazonAuthConfig):
    """
    An object containing ``amazon-orders``'s configuration. The state of this object is populated from the config file,
    if present, when it is instantiated, and it is also persisted back to the config file when :func:`~save` is called.

    The config file is ``~/.config/amazonorders/config.yml``, unless another ``config_path`` is given (or
    ``--config-path`` on the CLI). For instance:

    .. code-block:: yaml

        domain: amazon.co.uk
        auth_forms_classes:
          - amazonauth.contrib.browser.playwright.PlaywrightAcicForm
          - amazonauth.contrib.browser.playwright.PlaywrightJSAuthForm

    A value can also be persisted from the command line with ``amazon-orders update-config <key> <value>``.

    If overrides are passed in ``data`` parameter when this object is instantiated, they will be used to populate the
    new object, but not persisted to the config file until :func:`~save` is called.

    Every config value can also be set with an ``AMAZON_<KEY>`` environment variable, for instance
    ``AMAZON_MAX_AUTH_ATTEMPTS=20`` for ``max_auth_attempts``. An environment variable takes precedence over every
    other source, then values passed in code (including CLI options), then the config file, then the defaults. The
    value of a key with a default is read as YAML, as it would be in the config file, and any other value is used
    as-is. Environment variables are never persisted to the config file.

    Default values provisioned with the config can be found
    `here <https://amazon-orders.readthedocs.io/_modules/amazonorders/conf.html#AmazonOrdersConfig>`_.
    """

    #: The package named in messages that suggest installing something, e.g. ``pip install amazon-orders[lxml]``.
    PACKAGE_NAME: str = "amazon-orders"

    def __init__(self,
                 config_path: Optional[str] = None,
                 data: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(os.path.join(DEFAULT_CONFIG_DIR, "config.yml") if config_path is None else config_path,
                         data)

    @staticmethod
    def _default_data() -> Dict[str, Any]:
        """
        Provision the default config values.

        :return: The default config values.
        """
        return {
            **AmazonAuthConfig._default_data(),
            # The session for ``amazon.com``; every other site's is kept beside it (see :attr:`cookie_jar_path`)
            "cookie_jar_path": AmazonOrdersConfig._default_cookie_jar_path(),
            "constants_class": "amazonorders.constants.Constants",
            "selectors_class": "amazonorders.selectors.Selectors",
            "order_class": "amazonorders.entity.order.Order",
            "shipment_class": "amazonorders.entity.shipment.Shipment",
            "item_class": "amazonorders.entity.item.Item",
            "transaction_class": "amazonorders.entity.transaction.Transaction",
            "output_class": "amazonorders.output.OutputFormatter",
            "transactions_page_class": "amazonorders.transactions.TransactionsPage",
            "language_package": None,
            "thread_pool_size": (os.cpu_count() or 1) * 4,
            # Set ``True`` to log a warning message instead of raising an exception when a required field is missing.
            "warn_on_missing_required_field": False
        }

    @staticmethod
    def _default_cookie_jar_path() -> str:
        return os.path.join(DEFAULT_CONFIG_DIR, "cookies.json")

    def _validate_class_paths(self) -> None:
        """
        Check the shape of every lazily resolved class path, and of the ``language_package``, at construction, so a
        malformed value still fails here rather than at first use, without importing the modules they name.

        :raises AmazonOrdersError: If a class path is not a dotted path to a class, or the ``language_package`` is
            not a dotted module path.
        """
        for key in ("order_class", "shipment_class", "item_class", "transaction_class", "output_class",
                    "transactions_page_class"):
            value = self._get(key)
            if (not isinstance(value, str) or "." not in value
                    or not all(part.isidentifier() for part in value.split("."))):
                raise AmazonOrdersError(f"Config value for \"{key}\" is not a dotted class path: {value!r}")

        language_package = self._get("language_package")
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
        if key in self._assigned_classes:
            return self._assigned_classes[key]

        if key not in self._resolved_classes:
            class_path = self._class_path(key)
            class_split = class_path.split(".")
            try:
                self._resolved_classes[key] = load_class(class_split[:-1], class_split[-1])
            except (AttributeError, ImportError) as e:
                raise AmazonOrdersError(f"Could not resolve \"{key}\" ({class_path}): {e}") from e

        return self._resolved_classes[key]

    def _class_path(self,
                    key: str) -> str:
        """
        Get the class path for the given config key. A key left at its default uses the class of the same name
        from the ``language_package``, if one is configured and defines it as a subclass of the default, so an
        explicitly configured class always wins. A value equal to the default counts as unset, since :func:`save`
        persists every default, and so does ``amazon-auth``'s default, which it persists to the same config file. A
        class of that name that isn't a subclass of the default (for instance, the default itself, imported into
        the package) is ignored with a warning.

        :param key: The config key naming the class.
        :return: The class path.
        :raises AmazonOrdersError: If the ``language_package`` cannot be imported.
        """
        class_path = self._get(key)
        if class_path == AmazonAuthConfig._default_data().get(key):
            class_path = self._default_data()[key]
        language_package = self._get("language_package")
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
        default_class: Any = load_class(class_split[:-1], class_split[-1])
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
        self._assigned_classes[key] = value

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
