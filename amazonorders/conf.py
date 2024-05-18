import copy
import logging
import os
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "amazonorders")
_DEFAULT_CONFIG = {
    "locale": "en-US",
    "output_dir": os.getcwd(),
    "cookie_jar_path": os.path.join(_DEFAULT_CONFIG_DIR, "cookies.json")
}


class AmazonOrdersConfig:
    def __init__(self,
                 config_path: Optional[str] = None,
                 data: Optional[Dict[str, Any]] = None):
        self.config_path: Optional[str] = os.path.join(_DEFAULT_CONFIG_DIR,
                                                       "config.yml") if config_path is None else config_path
        self._config_cache: Dict[str, Dict[str, Any]] = {}

        if not os.path.exists(self.config_path):
            self._install_default_config(data)

    def get_config(self,
                   use_cache: bool = True):
        if self.config_path not in self._config_cache or not use_cache:
            with open(self.config_path, "r") as config_file:
                config = yaml.safe_load(config_file)
                if config is None:
                    config = _DEFAULT_CONFIG

            self._config_cache[self.config_path] = config

        return self._config_cache[self.config_path]

    def update_config(self,
                      key,
                      value,
                      save=True):
        config = self.get_config()

        config[key] = value

        # TODO: cleanup this up
        if save:
            with open(self.config_path, "w") as config_file:
                logger.debug(f"Saving config to {self.config_path} ...")

                yaml.dump(config, config_file)

    def _install_default_config(self,
                                data: Optional[Dict[str, Any]] = None) -> None:
        if data is None:
            data = {}
        else:
            data = copy.deepcopy(data)

        data.update(_DEFAULT_CONFIG)

        config_dir = os.path.dirname(self.config_path)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        if not os.path.exists(data["output_dir"]):
            os.makedirs(data["output_dir"])
        if not os.path.exists(self.config_path):
            open(self.config_path, "w").close()

        with open(self.config_path, "w") as config_file:
            logger.debug(f"Installing default config to {self.config_path} ...")

            yaml.dump(data, config_file)
