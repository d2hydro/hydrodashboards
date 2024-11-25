from dataclasses import dataclass, field
import pandas as pd
from typing import List
from datetime import datetime
from hydrodashboards.datamodel.cache import Cache

COLUMNS = {"datetime": "datetime64", "value": float}
KEY = "__{location}__{parameter}__"
CACHE = Cache("time_series", data_frame=False, compression=False, load_data=False)


@dataclass
class TimeSeries:
    parameter: str
    parameter_name: str
    location: str
    label: str
    units: str
    active: bool = False
    visible: bool = False
    empty: bool = True
    complete: bool = False
    cache: Cache = field(default_factory=lambda: CACHE)
    datetime_created: datetime = datetime.now()
    start_datetime: datetime = None
    end_datetime: datetime = None
    df: pd.DataFrame = None
    tags: list = field(default_factory=list)

    def __post_init__(self):
        df = pd.DataFrame(columns=list(COLUMNS.keys()))
        for col in df.columns:
            df[col] = df[col].astype(COLUMNS[col])
        df.set_index("datetime", inplace=True)
        self.df = df

    @property
    def index(self):
        return (self.location, self.parameter)

    @property
    def key(self):
        return KEY.format(location=self.location, parameter=self.parameter)

    @property
    def data_start(self):
        if not self.df.empty:
            return pd.to_datetime(self.df.index.min())

    @property
    def data_end(self):
        if not self.df.empty:
            return pd.to_datetime(self.df.index.max())

    def to_cache(self):
        self.complete = True
        self.cache.set_data(self, self.key)

    def within_period(self, period, selection="view"):
        within_period = False
        if self.cache.exists(self.key):
            within_period = True
        else:
            if selection == "view":
                ref_start = period.view_start
                ref_end = period.view_end
            elif selection == "search":
                ref_start = period.search_start
                ref_end = period.search_end
            if (self.start_datetime is not None) & (self.end_datetime is not None):
                if (self.start_datetime <= ref_start) & (self.end_datetime >= ref_end):
                    within_period = True
        return within_period


@dataclass
class TimeSeriesSets:
    time_series: List[TimeSeries] = field(default_factory=list)
    search_start: datetime = None
    search_end: datetime = None
    cache: Cache = field(default_factory=lambda: CACHE)
    max_events_visible: int = 0

    def __len__(self):
        return len(self.time_series)

    def __post_init__(self):
        self.cache.mkdir()

    @property
    def active_length(self):
        return len(self.active_labels)

    @property
    def active_labels(self):
        return [i.label for i in self.time_series if i.active]

    @property
    def indices(self):
        return [i.index for i in self.time_series]

    @property
    def first_active(self):
        return next((i for i in self.time_series if i.active), None)

    @property
    def any_active(self):
        return any([i.active for i in self.time_series])

    @property
    def max_events_loaded(self):
        visible_ts = [i for i in self.time_series if i.visible]
        if len(visible_ts) > 0:
            length = max((len(i.df) for i in visible_ts))
        else:
            length = 0
        return length

    def exists(self, index):
        return next((True for i in self.time_series if i.index == index), False)

    def remove_inactive(self):
        self.time_series = [i for i in self.time_series if i.active]

    def remove(self, index):
        self.time_series = [i for i in self.time_series if i.index != index]

    def within_period(self, start_datetime: datetime, end_datetime: datetime):
        if (self.search_start is not None) | (self.search_end is not None):
            within_period = (self.search_start <= start_datetime) & (
                self.search_end >= start_datetime
            )
        else:
            within_period = None
        return within_period

    def set_search_period(self, start_datetime: datetime, end_datetime: datetime):
        self.search_start = start_datetime
        self.search_end = end_datetime

    def get_by_label(self, label):
        return next((i for i in self.time_series if i.label == label), None)

    def select_view(self, periods):
        def _selector(ts, periods):
            return ts.active & (not (ts.complete | ts.within_period(periods)))

        return [i for i in self.time_series if _selector(i, periods)]

    def select_incomplete(self):
        return [i for i in self.time_series if not i.complete]

    def set_empty(self):
        for i in self.time_series:
            if i.active and (not i.complete):
                i.empty = True

    def set_active(self, labels):
        for i in self.time_series:
            if (i.location, i.parameter) in labels:
                i.active = True
            else:
                i.active = False

    def set_visible(self, indices=None, labels=None):
        for i in self.time_series:
            if indices is not None:
                i.visible = (i.location, i.parameter) in indices
            elif labels is not None:
                i.visible = i.label in labels
            else:
                i.visible = False

    def append_from_cache(self, location, parameter, start, end):
        key = KEY.format(location=location, parameter=parameter)
        if self.cache.exists(key):
            time_series = self.cache.get_data(key)
            time_series.complete = True
            time_series.df = time_series.df.loc[
                (time_series.df.index >= start) & (time_series.df.index <= end)
            ]
            self.time_series += [time_series]

    def append_from_dict(self, properties: List[dict]):
        properties = [
            i for i in properties if (i["location"], i["parameter"]) not in self.indices
        ]
        time_series = [TimeSeries(**i) for i in properties]
        self.time_series += time_series

    def by_parameter_groups(self, parameter_groups: dict, active_only=False):
        groups = {k: [] for k in set(parameter_groups.values())}
        if active_only:
            time_series = [i for i in self.time_series if i.active]
        else:
            time_series = self.time_series
        for i in time_series:
            group = parameter_groups[i.__dict__["parameter"]]
            groups[group].append(i)
        return groups
