__all__ = ['Singleton', 'singleton']


class Singleton(type):
    instance = {}

    def __call__(cls, *args, **kwargs):
        if cls.__name__ not in Singleton.instance.keys():
            Singleton.instance[cls.__name__] = super(Singleton, cls).__call__(*args, **kwargs)
        return Singleton.instance[cls.__name__]


def singleton(cls):
    def wrapper(*args, **kwargs):
        if cls not in Singleton.instance:
            Singleton.instance[cls] = cls(*args, **kwargs)
        return Singleton.instance[cls]

    return wrapper
