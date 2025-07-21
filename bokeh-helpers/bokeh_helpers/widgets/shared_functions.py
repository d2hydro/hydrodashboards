import datetime
import math
import numbers
from typing import Literal, Union

import pytz
from bokeh.models import DatetimeTickFormatter
from dateutil import tz


def get_formatter(format="%Y-%m-%d %H:%M:%S"):
    return DatetimeTickFormatter(years=format, days=format, hours=format, minutes=format)


def round_seconds(ts_seconds, td_seconds, method):
    if method in ["floor", "ceil"]:
        rounder = getattr(math, method)
    else:
        rounder = round

    return rounder(ts_seconds / td_seconds) * td_seconds


def round_datetime(dt, timedelta_round, method: Literal["floor", "ceil", "round"] = "round"):
    ts_seconds = dt.timestamp()
    td_seconds = timedelta_round.total_seconds()
    rounded_seconds = round_seconds(ts_seconds, td_seconds, method)
    # local_tz = pytz.timezone("Europe/Amsterdam")
    local_tz = datetime.UTC

    return datetime.datetime.fromtimestamp(rounded_seconds, tz=local_tz)
