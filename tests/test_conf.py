__copyright__ = "Copyright (c) 2024 Alex Laird"
__license__ = "MIT"

import os
import shutil
from unittest import TestCase

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

        # GIVEN
        config = AmazonOrdersConfig(data={
            "output_dir": self.test_output_dir,
            "cookie_jar_path": self.test_cookie_jar_path
        })

        # THEN
        self.assertEqual(config_path, config.config_path)
        self.assertTrue(os.path.exists(conf.DEFAULT_CONFIG_DIR))
        self.assertFalse(os.path.exists(config_path))
        self.assertEqual("en-US", config.locale)
        self.assertEqual(10, config.max_auth_attempts)
        self.assertEqual(self.test_output_dir, config.output_dir)
        self.assertEqual(self.test_cookie_jar_path, config.cookie_jar_path)

        # GIVEN
        config.save()

        # THEN
        self.assertTrue(os.path.exists(config_path))
        with open(config.config_path, "r") as f:
            self.assertEqual("""cookie_jar_path: {}
locale: en-US
max_auth_attempts: 10
output_dir: {}
""".format(self.test_cookie_jar_path, self.test_output_dir), f.read())

    def test_update_config(self):
        # TODO: implement
        pass
