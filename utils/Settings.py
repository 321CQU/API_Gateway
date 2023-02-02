import os
from _321CQU.tools import ConfigHandler

__all__ = ['BASE_DIR', 'ConfigManager']

BASE_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


class ConfigManager(ConfigHandler):
    def __init__(self):
        super().__init__(str(BASE_DIR) + "/utils/config.cfg")


if __name__ == '__main__':
    print(BASE_DIR)
