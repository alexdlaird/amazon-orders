import logging
import os
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "amazonorders")


class AmazonOrdersConfig:
    def __init__(self,
                 config_path: Optional[str] = None,
                 data: Optional[Dict[str, Any]] = None):
        if not data:
            data = {}

        self.config_path: str = os.path.join(DEFAULT_CONFIG_DIR, "config.yml") if config_path is None else config_path

        # Provision default configs
        self._data = {
            "locale": "en-US",
            "max_auth_attempts": 10,
            "output_dir": os.path.join(os.getcwd(), "output"),
            "cookie_jar_path": os.path.join(DEFAULT_CONFIG_DIR, "cookies.json")
        }

        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as config_file:
                logger.debug(f"Loading config from {self.config_path} ...")
                config = yaml.safe_load(config_file)
                if config is not None:
                    config.update(data)
                    data = config

        # Overload defaults if values passed
        self._data.update(data)

        # Ensure directories and files exist for config data
        config_dir = os.path.dirname(self.config_path)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        cookie_jar_dir = os.path.dirname(self.cookie_jar_path)
        if not os.path.exists(cookie_jar_dir):
            os.makedirs(cookie_jar_dir)

    def __getattr__(self, key):
        return self._data[key]

    # def __setattr__(self, key, value):
    #     self.data[key] = value

    def update_config(self, key, value, save=True):
        self._data[key] = value

        if save:
            self.save()

    def save(self):
        with open(self.config_path, "w") as config_file:
            logger.debug(f"Saving config to {self.config_path} ...")

            yaml.dump(self._data, config_file)
