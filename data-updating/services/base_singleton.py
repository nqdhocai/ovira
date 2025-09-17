import threading
from typing import Any, TypeVar, cast

from typing_extensions import override

T = TypeVar(name="T")


class SingletonMeta(type):
    _instances: dict[type, object] = {}
    _lock: threading.Lock = threading.Lock()

    @override
    def __call__(cls: type[T], *args: Any, **kwargs: Any) -> T:
        if cls not in SingletonMeta._instances:
            # If the instance doesn't exist, acquire the lock.
            # Only one thread can enter this block at a time to avoid any race condition
            with SingletonMeta._lock:
                # Second check (crucial):
                # We must check again *inside* the lock. This is because another thread might have created the instance while we were waiting to acquire the lock.
                if cls not in SingletonMeta._instances:
                    instance = super().__call__(*args, **kwargs)
                    SingletonMeta._instances[cls] = instance

        return cast(T, SingletonMeta._instances[cls])
