from dataclasses import dataclass, field
import pandas as pd
from typing import List
from datetime import datetime

COLUMNS = {"datetime": "datetime64", "value": float}


@dataclass
class TimeSeries:
    parameter: str
    parameter_name: str
    location: str
    label: str
    active: bool = False
    empty: bool = True
    complete: bool = False
    datetime_created: datetime = datetime.now()
    start_datetime: datetime = None
    end_datetime: datetime = None
    df: pd.DataFrame = None

    def __post_init__(self):
        df = pd.DataFrame(columns=list(COLUMNS.keys()))
        for col in df.columns:
            df[col] = df[col].astype(COLUMNS[col])
        df.set_index("datetime", inplace=True)
        self.df = df

    @property
    def index(self):
        return (self.location, self.parameter)

    def within_period(self, period, selection="view"):
        within_period = False
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

    def __len__(self):
        return len(self.time_series)

    @property
    def active_length(self):
        return len([1 for i in self.time_series if i.active])

    @property
    def indices(self):
        return [i.index for i in self.time_series]

    @property
    def first_active(self):
        return next((i for i in self.time_series if i.active), None)

    def select_view(self, periods):
        def _selector(ts, periods):
            return ts.active & (not (ts.complete | ts.within_period(periods)))

        return [i for i in self.time_series if _selector(i, periods)]

    def select_incomplete(self):
        def _selector(ts):
            return ts.active & (not ts.complete) & (not ts.empty)

        return [i for i in self.time_series if _selector(i)]

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

    def append_from_dict(self, properties: List[dict]):
        properties = [
            i for i in properties if (i["location"], i["parameter"]) not in self.indices
        ]
        time_series = [TimeSeries(**i) for i in properties]
        self.time_series += time_series

    def by_parameter_groups(self, parameter_groups: dict, active_only=False):
        groups = {k: [] for k in parameter_groups.keys()}
        for i in self.time_series:
            if active_only:
                if i.active:
                    groups[i.__dict__["parameter"]].append(i)
            else:
                groups[i.__dict__["parameter"]].append(i)
        return groups
