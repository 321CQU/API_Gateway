import os

__all__ = ['BASE_DIR']

BASE_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

if __name__ == '__main__':
    print(BASE_DIR)
