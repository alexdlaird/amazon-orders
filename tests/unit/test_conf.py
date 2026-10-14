__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
import pickle
from unittest.mock import patch

import yaml

from amazonorders import conf
from amazonorders.conf import AmazonOrdersConfig
from amazonorders.constants import Constants
from amazonorders.entity.order import Order
from amazonorders.exception import AmazonOrdersError
from amazonorders.output import OutputFormatter
from amazonorders.selectors import Selectors
from amazonorders.transactions import TransactionsPage
from tests.unit import example_language_package
from tests.unit.test_constants import RegionOverrideConstants
from tests.unittestcase import UnitTestCase


class CustomOrder(Order):
    pass


class TestConf(UnitTestCase):
    def test_provision_config(self):
        # WHEN
        config_path = os.path.join(conf.DEFAULT_CONFIG_DIR, "config.yml")
        self.assertFalse(os.path.exists(conf.DEFAULT_CONFIG_DIR))
        self.assertFalse(os.path.exists(config_path))
        self.assertFalse(os.path.exists(self.test_output_dir))
        self.assertFalse(os.path.exists(self.test_cookie_jar_path))

        # GIVEN
        config = AmazonOrdersConfig(data={
            "output_dir": self.test_output_dir,
            "cookie_jar_path": self.test_cookie_jar_path
        })

        # THEN constructing the config touches nothing on disk
        self.assertEqual(5, config.auth_reattempt_wait)
        self.assertEqual(config_path, config.config_path)
        self.assertFalse(os.path.exists(conf.DEFAULT_CONFIG_DIR))
        self.assertFalse(os.path.exists(config_path))
        self.assertFalse(os.path.exists(self.test_output_dir))
        self.assertFalse(os.path.exists(os.path.dirname(self.test_cookie_jar_path)))
        self.assertEqual(10, config.max_cookie_attempts)
        self.assertEqual(0.5, config.cookie_reattempt_wait)
        self.assertEqual(10, config.max_auth_attempts)
        self.assertEqual(1, config.max_auth_retries)
        self.assertEqual(self.test_output_dir, config.output_dir)
        self.assertEqual(self.test_cookie_jar_path, config.cookie_jar_path)
        self.assertEqual("html.parser", config.bs4_parser)
        self.assertFalse(config.warn_on_missing_required_field)
        self.assertIsNone(config.request_timeout)

        # GIVEN
        config.save()

        # THEN save() provisions the config dir itself
        thread_pool_size = os.cpu_count() * 4
        self.assertTrue(os.path.exists(conf.DEFAULT_CONFIG_DIR))
        self.assertTrue(os.path.exists(config_path))
        self.assertFalse(os.path.exists(self.test_output_dir))
        with open(config.config_path, "r") as f:
            self.assertEqual("""auth_forms_classes: []
auth_reattempt_wait: 5
browser_timeout: 30
bs4_parser: html.parser
connection_pool_size: {connection_pool_size}
constants_class: amazonorders.constants.Constants
cookie_jar_path: {cookie_jar_path}
cookie_reattempt_wait: 0.5
item_class: amazonorders.entity.item.Item
language_package: null
max_auth_attempts: 10
max_auth_retries: 1
max_cookie_attempts: 10
order_class: amazonorders.entity.order.Order
output_class: amazonorders.output.OutputFormatter
output_dir: {output_dir}
request_timeout: null
selectors_class: amazonorders.selectors.Selectors
shipment_class: amazonorders.entity.shipment.Shipment
thread_pool_size: {thread_pool_size}
transaction_class: amazonorders.entity.transaction.Transaction
transactions_page_class: amazonorders.transactions.TransactionsPage
warn_on_missing_required_field: false
"""
                             .format(connection_pool_size=thread_pool_size * 2,
                                     cookie_jar_path=self.test_cookie_jar_path,
                                     output_dir=self.test_output_dir,
                                     thread_pool_size=thread_pool_size), f.read())

    def test_override_default(self):
        # GIVEN
        # Default is 10
        config = AmazonOrdersConfig(data={
            "max_auth_attempts": 11,
            "request_timeout": 15
        })

        self.assertEqual(11, config.max_auth_attempts)
        self.assertEqual(15, config.request_timeout)

    def test_load_from_file(self):
        # GIVEN
        config_path = os.path.join(conf.DEFAULT_CONFIG_DIR, "load-from-config.yml")
        test_output_dir = os.path.join(conf.DEFAULT_CONFIG_DIR, "load-from-config-output")
        test_cookie_jar_path = os.path.join(conf.DEFAULT_CONFIG_DIR, "load-from-config-cookies.json")
        os.makedirs(conf.DEFAULT_CONFIG_DIR)
        with open(config_path, "w") as f:
            f.write("""cookie_jar_path: {cookie_jar_path}
max_auth_attempts: 11
output_dir: {output_dir}
some_custom_config: {custom_config}
"""
                    .format(cookie_jar_path=test_cookie_jar_path,
                            output_dir=test_output_dir,
                            custom_config="my-custom-config"))

        # WHEN
        config = AmazonOrdersConfig(config_path=config_path)

        self.assertEqual(config_path, config.config_path)
        self.assertEqual(11, config.max_auth_attempts)
        self.assertEqual(test_output_dir, config.output_dir)
        self.assertEqual(test_cookie_jar_path, config.cookie_jar_path)
        self.assertEqual("my-custom-config", config.some_custom_config)

    def test_unavailable_bs4_parser_falls_back_to_html_parser(self):
        # GIVEN / WHEN
        with self.assertLogs("amazonorders.conf", level="DEBUG") as logs:
            config = AmazonOrdersConfig(data={
                "bs4_parser": "this-parser-does-not-exist"
            })

        # THEN
        self.assertEqual("html.parser", config.bs4_parser)
        self.assertTrue(any("this-parser-does-not-exist" in m for m in logs.output))

    def test_update_config(self):
        # GIVEN
        config = AmazonOrdersConfig(data={
            "max_auth_attempts": 11
        })

        self.assertEqual(11, config.max_auth_attempts)

        # WHEN
        config.update_config("max_auth_attempts", 7)
        config.update_config("username", "test-username")
        config.update_config("otp_secret_key", "test-otp-secret-key")

        # THEN
        self.assertEqual(7, config.max_auth_attempts)
        self.assertEqual("test-username", config.username)
        self.assertEqual("test-otp-secret-key", config.otp_secret_key)
        with open(config.config_path, "r") as f:
            persisted_config = yaml.safe_load(f)
            self.assertEqual(7, persisted_config["max_auth_attempts"])
            self.assertEqual("test-username", persisted_config["username"])
            self.assertEqual("test-otp-secret-key", persisted_config["otp_secret_key"])

    def test_classes_can_be_assigned_directly(self):
        # GIVEN
        config = AmazonOrdersConfig(data={"output_dir": self.test_output_dir})

        # WHEN
        config.order_cls = CustomOrder
        config.shipment_cls = CustomOrder
        config.item_cls = CustomOrder
        config.output_cls = CustomOrder

        # THEN
        self.assertEqual(CustomOrder, config.order_cls)
        self.assertEqual(CustomOrder, config.shipment_cls)
        self.assertEqual(CustomOrder, config.item_cls)
        self.assertEqual(CustomOrder, config.output_cls)

    def test_unresolvable_class_path_raises_on_use(self):
        # GIVEN
        config = AmazonOrdersConfig(data={
            "output_dir": self.test_output_dir,
            "order_class": "amazonorders.entity.order.DoesNotExist"
        })

        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            config.order_cls

        # THEN
        self.assertIn("order_class", str(cm.exception))

    def test_malformed_class_path_raises_at_construction(self):
        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            AmazonOrdersConfig(data={
                "output_dir": self.test_output_dir,
                "order_class": "NotADottedPath"
            })

        # THEN
        self.assertIn("order_class", str(cm.exception))

    def test_language_package_provides_classes_left_at_default(self):
        # WHEN
        config = AmazonOrdersConfig(data={
            "output_dir": self.test_output_dir,
            "language_package": "tests.unit.example_language_package"
        })

        # THEN
        self.assertIsInstance(config.selectors, example_language_package.Selectors)
        self.assertIsInstance(config.constants, example_language_package.Constants)
        self.assertEqual(Order, config.order_cls)
        self.assertEqual(example_language_package.TransactionsPage, config.transactions_page_cls)
        self.assertEqual(OutputFormatter, config.output_cls)

    def test_explicit_class_wins_over_language_package(self):
        # WHEN
        config = AmazonOrdersConfig(data={
            "output_dir": self.test_output_dir,
            "language_package": "tests.unit.example_language_package",
            "constants_class": "tests.unit.test_constants.RegionOverrideConstants"
        })

        # THEN
        self.assertIsInstance(config.constants, RegionOverrideConstants)
        self.assertIsInstance(config.selectors, example_language_package.Selectors)

    def test_language_package_applies_over_saved_default_class_paths(self):
        # GIVEN
        config_path = os.path.join(conf.DEFAULT_CONFIG_DIR, "config.yml")
        AmazonOrdersConfig(config_path=config_path, data={"output_dir": self.test_output_dir}).save()

        # WHEN
        config = AmazonOrdersConfig(config_path=config_path,
                                    data={"language_package": "tests.unit.example_language_package"})

        # THEN
        self.assertIsInstance(config.selectors, example_language_package.Selectors)
        self.assertIsInstance(config.constants, example_language_package.Constants)

    def test_unimportable_language_package_raises_at_construction(self):
        # WHEN
        with self.assertRaises(AmazonOrdersError) as cm:
            AmazonOrdersConfig(data={
                "output_dir": self.test_output_dir,
                "language_package": "does_not_exist"
            })

        # THEN
        self.assertIn("language_package", str(cm.exception))

    def test_language_package_that_is_not_a_module_path_raises(self):
        for value in (True, 123, "not a module"):
            with self.subTest(value=value):
                # WHEN
                with self.assertRaises(AmazonOrdersError) as cm:
                    AmazonOrdersConfig(data={
                        "output_dir": self.test_output_dir,
                        "language_package": value
                    })

                # THEN
                self.assertIn("language_package", str(cm.exception))

    def test_language_package_classes_that_are_not_subclasses_are_ignored(self):
        # WHEN
        with self.assertLogs("amazonorders.conf", level="WARNING") as cm:
            config = AmazonOrdersConfig(data={
                "output_dir": self.test_output_dir,
                "language_package": "tests.unit.misnamed_language_package"
            })
            transactions_page_cls = config.transactions_page_cls

        # THEN
        self.assertIs(Selectors, type(config.selectors))
        self.assertIs(Constants, type(config.constants))
        self.assertIs(TransactionsPage, transactions_page_cls)
        self.assertEqual(3, len(cm.output))
        self.assertIn("defines Selectors, but it isn't a subclass of amazonorders.selectors.Selectors",
                      "".join(cm.output))

    def given_config_file(self, contents):
        config_path = os.path.join(conf.DEFAULT_CONFIG_DIR, "config.yml")
        os.makedirs(conf.DEFAULT_CONFIG_DIR, exist_ok=True)
        with open(config_path, "w") as f:
            f.write(contents)
        return config_path

    def test_environment_variable_sets_config_value_as_yaml(self):
        # GIVEN / WHEN
        with patch.dict(os.environ, {"AMAZON_MAX_AUTH_ATTEMPTS": "20", "AMAZON_AUTH_FORMS_CLASSES": "[a.b.C]",
                                     "AMAZON_WARN_ON_MISSING_REQUIRED_FIELD": "true"}):
            config = AmazonOrdersConfig()

        # THEN
        self.assertEqual(20, config.max_auth_attempts)
        self.assertEqual(["a.b.C"], config.auth_forms_classes)
        self.assertIs(True, config.warn_on_missing_required_field)

    def test_environment_variable_without_default_is_used_verbatim(self):
        # GIVEN / WHEN
        with patch.dict(os.environ, {"AMAZON_PASSWORD": "0123", "AMAZON_BROWSER": "yes"}):
            config = AmazonOrdersConfig()

        # THEN
        self.assertEqual("0123", config.password)
        self.assertEqual("yes", config.browser)

    def test_environment_variable_wins_over_data_and_config_file(self):
        # GIVEN
        config_path = self.given_config_file("max_auth_attempts: 11\noutput_dir: /from/file\n")

        # WHEN
        with patch.dict(os.environ, {"AMAZON_MAX_AUTH_ATTEMPTS": "20"}):
            config = AmazonOrdersConfig(config_path=config_path, data={"max_auth_attempts": 15})

        # THEN
        self.assertEqual(20, config.max_auth_attempts)
        self.assertEqual("/from/file", config.output_dir)
        self.assertIn("max_auth_attempts", config)

    def test_environment_variable_wins_over_update_config(self):
        # GIVEN
        with patch.dict(os.environ, {"AMAZON_MAX_AUTH_ATTEMPTS": "20"}):
            config = AmazonOrdersConfig()

        # WHEN
        config.update_config("max_auth_attempts", 7, save=False)

        # THEN
        self.assertEqual(20, config.max_auth_attempts)

    def test_empty_environment_variable_is_ignored(self):
        # GIVEN / WHEN
        with patch.dict(os.environ, {"AMAZON_MAX_AUTH_ATTEMPTS": ""}):
            config = AmazonOrdersConfig()

        # THEN
        self.assertEqual(10, config.max_auth_attempts)

    def test_invalid_yaml_environment_variable_raises(self):
        # WHEN
        with patch.dict(os.environ, {"AMAZON_AUTH_FORMS_CLASSES": "[unclosed"}):
            with self.assertRaises(AmazonOrdersError) as cm:
                AmazonOrdersConfig()

        # THEN
        self.assertIn("Environment variable AMAZON_AUTH_FORMS_CLASSES is not valid YAML", str(cm.exception))

    def test_environment_variables_are_never_persisted(self):
        # GIVEN
        with patch.dict(os.environ, {"AMAZON_PASSWORD": "secret", "AMAZON_MAX_AUTH_ATTEMPTS": "20"}):
            config = AmazonOrdersConfig(data={"output_dir": self.test_output_dir})

        # WHEN
        config.update_config("max_auth_attempts", 7)

        # THEN
        with open(config.config_path, "r") as f:
            persisted_config = yaml.safe_load(f)
        self.assertNotIn("password", persisted_config)
        self.assertEqual(7, persisted_config["max_auth_attempts"])

    def test_environment_values_survive_pickling(self):
        # GIVEN
        with patch.dict(os.environ, {"AMAZON_MAX_AUTH_ATTEMPTS": "20"}):
            config = AmazonOrdersConfig()

        # WHEN
        unpickled_config = pickle.loads(pickle.dumps(config))

        # THEN
        self.assertEqual(20, unpickled_config.max_auth_attempts)
        self.assertEqual(20, unpickled_config.environment_value("max_auth_attempts"))

    def test_environment_variable_sets_domain(self):
        # GIVEN / WHEN
        with patch.dict(os.environ, {"AMAZON_DOMAIN": "amazon.co.uk"}):
            config = AmazonOrdersConfig()

        # THEN
        self.assertEqual("https://www.amazon.co.uk", config.constants.BASE_URL)

    def test_deprecated_base_url_environment_variable_still_applies_below_config(self):
        # GIVEN
        with patch.dict(os.environ, {"AMAZON_BASE_URL": "amazon.co.uk"}):
            # WHEN
            with self.assertLogs("amazonorders.constants", level="WARNING") as cm:
                config = AmazonOrdersConfig()
            config_with_domain = AmazonOrdersConfig(data={"domain": "amazon.ca"})

        # THEN
        self.assertEqual("https://www.amazon.co.uk", config.constants.BASE_URL)
        self.assertIn("AMAZON_BASE_URL is deprecated", "".join(cm.output))
        self.assertEqual("https://www.amazon.ca", config_with_domain.constants.BASE_URL)
