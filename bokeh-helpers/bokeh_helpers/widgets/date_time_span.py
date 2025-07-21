import numbers
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Union

import pytz
from bokeh.models import Span
from dateutil import tz

from bokeh_helpers.widgets.shared_functions import round_datetime, round_seconds


@dataclass
class DateTimeSpan:
    start: Union[datetime, int]
    end: Union[datetime, int]
    location: Union[datetime, int]
    step: Union[timedelta, int]
    kwargs: dict = field(default_factory=dict)
    widget: Union[Span, None] = None

    def __post_init__(self):
        # convert all to milisconds
        if isinstance(self.start, datetime):
            start = self.start.timestamp() * 1000
        else:
            start = self.start

        if isinstance(self.end, datetime):
            end = self.end.timestamp() * 1000
        else:
            end = self.end

        if isinstance(self.location, datetime):
            location = self.location.timestamp() * 1000
        else:
            location = self.location

        if isinstance(self.step, timedelta):
            step = self.step.total_seconds() * 1000
        else:
            step = self.step

        # validate values
        if start >= end:
            raise ValueError(f"start >= end: {start} >= {end}")

        if location < start:
            raise ValueError(f"location < start: {location} < {start}")

        if location > end:
            raise ValueError(f"location > end: {location} > {end}")

        # set start, stop step
        self.start = round_seconds(start, step, "floor")
        self.end = round_seconds(end, step, "ceil")
        self.location = round_seconds(location, step, "round")
        self.step = step

        self.widget = Span(
            location=location,
            **self.kwargs,
        )

    @property
    def step_as_timedelta(self):
        if isinstance(self.step, timedelta):
            return self.step
        else:
            return timedelta(seconds=self.step / 1000)

    @property
    def start_as_datetime(self):
        return datetime.fromtimestamp(self.start / 1000)

    @property
    def end_as_datetime(self):
        return datetime.fromtimestamp(self.end / 1000)

    @property
    def steps(self):
        step = int(self.widget.step)
        start = int(self.widget.start)
        stop = int(self.widget.end + step)
        return list(range(start, stop, step))

    @property
    def snapped_location(self):
        """Return the location snapped to self.step"""
        if isinstance(self.widget.location, numbers.Number):
            location = self.widget.location
        else:
            location = self.widget.location.timestamp() * 1000

        return round_seconds(location, self.step, "round")

    @property
    def snapped_location_as_datetime(self):
        """Return the location as datetime snapped to self.step"""
        if isinstance(self.widget.location, numbers.Number):
            # local_tz = datetime.now().astimezone().tzinfo
            # local_tz = pytz.timezone("UTC")
            # local_tz = pytz.timezone("Europe/Amsterdam")
            # local_tz = tz.tzlocal()
            # change the tz in shared_functions.round_datetime
            location = datetime.fromtimestamp(self.widget.location / 1000)  # , tz=local_tz)
        else:
            location = self.widget.location

        if isinstance(self.step, timedelta):
            step = self.step
        else:
            step = timedelta(seconds=self.step / 1000)

        return round_datetime(location, step)

    def set_location(self, value=Union[int, datetime]):
        if isinstance(value, datetime):
            value = value.timestamp() * 1000

        value = round_seconds(value, self.step, "round")
        if self.location != value:
            self.location = value
            self.widget.location = value

    def set_step(self, value=Union[int, datetime]):
        """Change the step size. This is the 'chunksize' on which selections can be made.
        Each selectable timestep is a step.
        """
        if isinstance(value, timedelta):
            value = self.step.total_seconds() * 1000
        self.step = value
        self.set_location(self.location)
        self.start = round_seconds(self.start, value, "floor")
        self.end = round_seconds(self.end, value, "ceil")

    def round_startdate(self):
        start_datetime = self.start_as_datetime
        start_datetime = datetime(start_datetime.year, start_datetime.month, start_datetime.day)
        self.start = start_datetime.timestamp() * 1000
        return self.start_as_datetime
