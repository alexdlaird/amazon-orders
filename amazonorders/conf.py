__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import importlib
import inspect
import logging
import os
import threading
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse

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

ENVIRONMENT_VARIABLE_PREFIX = "AMAZON_"

#: The Amazon site whose session is kept in the default ``cookie_jar_path`` itself, rather than in a jar of its own.
DEFAULT_COOKIE_JAR_SITE = "amazon.com"

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

    The config file is ``~/.config/amazonorders/config.yml``, unless another ``config_path`` is given (or
    ``--config-path`` on the CLI). For instance:

    .. code-block:: yaml

        domain: amazon.co.uk
        auth_forms_classes:
          - amazonorders.contrib.browser.playwright.PlaywrightAcicForm
          - amazonorders.contrib.browser.playwright.PlaywrightJSAuthForm

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

    def __init__(self,
                 config_path: Optional[str] = None,
                 data: Optional[Dict[str, Any]] = None) -> None:
        #: The path to use for the config file.
        self.config_path: str = os.path.join(DEFAULT_CONFIG_DIR, "config.yml") if config_path is None else config_path

        self._data: Dict[str, Any] = self._default_data()
        self._environment: Dict[str, Any] = self.read_environment()
        self._resolved_classes: Dict[str, Any] = {}
        self._assigned_classes: Dict[str, Any] = {}

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

    @classmethod
    def read_environment(cls) -> Dict[str, Any]:
        """
        Read the config values set with ``AMAZON_<KEY>`` environment variables. An empty variable is ignored.

        :return: The config values set in the environment, by config key.
        :raises AmazonOrdersError: If the value of a key with a default is not valid YAML.
        """
        default_data = cls._default_data()
        environment = {}
        for name, value in os.environ.items():
            if not name.startswith(ENVIRONMENT_VARIABLE_PREFIX) or not value:
                continue

            key = name[len(ENVIRONMENT_VARIABLE_PREFIX):].lower()
            if key not in default_data:
                environment[key] = value
                continue

            try:
                environment[key] = yaml.safe_load(value)
            except yaml.YAMLError as e:
                raise AmazonOrdersError(f"Environment variable {name} is not valid YAML: {e}") from e

        return environment

    def environment_value(self,
                          key: str) -> Any:
        """
        Get the value set for the given config key with its ``AMAZON_<KEY>`` environment variable.

        :param key: The config key.
        :return: The value, or ``None`` if the environment variable isn't set.
        """
        return self._environment.get(key)

    def _get(self,
             key: str) -> Any:
        if key in self._environment:
            return self._environment[key]

        return self._data.get(key)

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

    @staticmethod
    def _default_cookie_jar_path() -> str:
        return os.path.join(DEFAULT_CONFIG_DIR, "cookies.json")

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
        class_path = self._get(key)
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
        self._assigned_classes[key] = value

    def _validate_bs4_parser(self) -> None:
        bs4_parser = self._get("bs4_parser")
        try:
            BeautifulSoup("", str(bs4_parser))
        except FeatureNotFound:
            logger.warning(
                f"Configured bs4_parser '{bs4_parser}' is unavailable; "
                f"using the default 'html.parser'. To use it, install the parser "
                f"(e.g. `pip install amazon-orders[lxml]`)."
            )
            source = self._environment if "bs4_parser" in self._environment else self._data
            source["bs4_parser"] = "html.parser"

    def _instantiate_constants(self) -> Any:
        constants_class_split = self._class_path("constants_class").split(".")
        constants_cls = util.load_class(constants_class_split[:-1], constants_class_split[-1])
        # Pass ``self`` only when the constants class accepts a config arg, to keep backward
        # compatibility with existing zero-arg ``constants_class`` subclasses.
        init_params = inspect.signature(constants_cls.__init__).parameters
        if len(init_params) > 1:
            return constants_cls(self)
        return constants_cls()

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

    def set_domain(self,
                   domain: str) -> None:
        """
        Set the active Amazon domain and rebuild :attr:`~amazonorders.conf.AmazonOrdersConfig.constants`
        so URL-derived attributes and region-sensitive headers reflect the change.

        :param domain: The Amazon domain (e.g. ``amazon.com.au``) or full URL.
        """
        self._data["domain"] = domain
        self.constants = self._instantiate_constants()

    @property
    def site(self) -> str:
        """The active Amazon site, the host of the ``domain`` without ``www.`` (e.g. ``amazon.de``)."""
        return (urlparse(self.constants.BASE_URL).hostname or "").removeprefix("www.")

    @property
    def cookie_jar_path(self) -> str:
        """
        The path the session for the active ``domain`` is persisted to, since each Amazon site has its own sign-in.
        With the default ``cookie_jar_path``, the ``amazon.com`` session is kept there (``cookies.json``), and every
        other site's beside it, named for the site (e.g. ``cookies.amazon.de.json``). Any other ``cookie_jar_path``
        is used as-is, whatever the site.
        """
        cookie_jar_path = self._get("cookie_jar_path")
        if cookie_jar_path != self._default_cookie_jar_path() or self.site == DEFAULT_COOKIE_JAR_SITE:
            return cookie_jar_path

        root, extension = os.path.splitext(cookie_jar_path)
        return f"{root}.{self.site}{extension}"

    @cookie_jar_path.setter
    def cookie_jar_path(self,
                        value: str) -> None:
        self._data["cookie_jar_path"] = value

    @property
    def shared_cookie_jar_path(self) -> Optional[str]:
        """
        The default ``cookie_jar_path``, which every site's session was persisted to before each site had its own,
        when the active ``domain`` now has a jar of its own (see :attr:`cookie_jar_path`), otherwise ``None``.
        """
        shared_cookie_jar_path = self._get("cookie_jar_path")
        if self.cookie_jar_path == shared_cookie_jar_path:
            return None

        return shared_cookie_jar_path

    def __getattr__(self,
                    key: str) -> Any:
        return self._get(key)

    def __contains__(self,
                     key: str) -> bool:
        return key in self._environment or key in self._data

    def __getstate__(self) -> Dict[str, Any]:
        return {"config_path": self.config_path, "_data": self._data, "_environment": self._environment,
                "_assigned_classes": self._assigned_classes}

    def __setstate__(self,
                     state: Dict[str, Any]) -> None:
        self.__dict__.update(state)
        self.__dict__.setdefault("_environment", {})
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
        previous_data = dict(self._data)
        self._data[key] = value
        try:
            self._validate_bs4_parser()
            self._validate_class_paths()
            self._load_classes()
        except (AmazonOrdersError, AttributeError, ImportError):
            self._data = previous_data
            self._load_classes()
            raise

        self._assigned_classes.pop(key, None)
        self._resolved_classes = {}

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
