import threading


class SingletonBase:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SingletonBase, cls).__new__(cls)
        return cls._instance
