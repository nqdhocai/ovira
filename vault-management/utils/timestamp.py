import datetime


def floor_to_hour(ts: int) -> int:
    dt = datetime.datetime.utcfromtimestamp(ts)
    floored = dt.replace(minute=0, second=0, microsecond=0)
    return int(floored.timestamp())
