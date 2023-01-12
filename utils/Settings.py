import os
from configparser import ConfigParser
from typing import List

from utils.Singleton import Singleton

__all__ = ['BASE_DIR', 'ConfigHandler']

BASE_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


class ConfigHandler(metaclass=Singleton):
    def __init__(self):
        self._config_parser = ConfigParser()
        self._config_parser.read(str(BASE_DIR) + "/utils/config.cfg")

    def get_config(self, section: str, option: str) -> str:
        return self._config_parser.get(section, option)

    def get_options(self, section: str) -> List[str]:
        return self._config_parser.options(section)


if __name__ == '__main__':
    print(BASE_DIR)
