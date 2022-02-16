"""
Utility functions for date and time
"""

from datetime import datetime
from dateutil import parser


INVERVALS_IN_DAYS = {
    "day": 1,
    "week": 7,
    "month": 30,
}

def timestamp_to_datetime(timestamp_ms: int):
    dt = datetime.utcfromtimestamp(timestamp_ms/1000)
    return dt

def get_interval_from_period(period: str) -> int:

    interval = INVERVALS_IN_DAYS.get(period)
    if interval:
        return interval * 24 * 3600 * 1000
    else:
        return 0

def datetime_to_timestamp(datetime_str: str) -> int:
    """Parse datetime string and return timestamp in milliseconds"""
    date = parser.parse(datetime_str)
    return int(datetime.timestamp(date) * 1000)
