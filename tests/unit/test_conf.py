__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import os
import shutil
from unittest import TestCase

import yaml

from amazonorders import conf
from amazonorders.conf import AmazonOrdersConfig


class TestConf(TestCase):
    def setUp(self):
        conf.DEFAULT_CONFIG_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), ".config")
        self.test_output_dir = os.path.join(conf.DEFAULT_CONFIG_DIR, "output")
        self.test_cookie_jar_path = os.path.join(conf.DEFAULT_CONFIG_DIR, "cookies.json")

    def tearDown(self):
        if os.path.exists(conf.DEFAULT_CONFIG_DIR):
            shutil.rmtree(conf.DEFAULT_CONFIG_DIR)

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

        # THEN
        self.assertEqual(5, config.auth_reattempt_wait)
        self.assertEqual(config_path, config.config_path)
        self.assertTrue(os.path.exists(conf.DEFAULT_CONFIG_DIR))
        self.assertFalse(os.path.exists(config_path))
        self.assertTrue(os.path.exists(self.test_output_dir))
        self.assertEqual(10, config.max_cookie_attempts)
        self.assertEqual(0.5, config.cookie_reattempt_wait)
        self.assertEqual(10, config.max_auth_attempts)
        self.assertEqual(1, config.max_auth_retries)
        self.assertEqual(self.test_output_dir, config.output_dir)
        self.assertEqual(self.test_cookie_jar_path, config.cookie_jar_path)
        self.assertEqual("html.parser", config.bs4_parser)
        self.assertFalse(config.warn_on_missing_required_field)

        # GIVEN
        config.save()

        # THEN
        thread_pool_size = os.cpu_count() * 4
        self.assertTrue(os.path.exists(config_path))
        with open(config.config_path, "r") as f:
            self.assertEqual("""auth_reattempt_wait: 5
bs4_parser: html.parser
connection_pool_size: {connection_pool_size}
constants_class: amazonorders.constants.Constants
cookie_jar_path: {cookie_jar_path}
cookie_reattempt_wait: 0.5
item_class: amazonorders.entity.item.Item
max_auth_attempts: 10
max_auth_retries: 1
max_cookie_attempts: 10
order_class: amazonorders.entity.order.Order
output_dir: {output_dir}
selectors_class: amazonorders.selectors.Selectors
shipment_class: amazonorders.entity.shipment.Shipment
thread_pool_size: {thread_pool_size}
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
            "max_auth_attempts": 11
        })

        self.assertEqual(11, config.max_auth_attempts)

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
