from dataclasses import dataclass, field
import pandas as pd
from typing import List

COLUMNS = {"datetime": "datetime64", "value": float}


@dataclass
class TimeSeries:
    parameter: str
    location: str
    active: bool = False
    empty: bool = True
    new: bool = True
    complete: bool = False
    datetime_created: pd.Timestamp = pd.Timestamp.now()
    df: pd.DataFrame = None

    def __post_init__(self):
        df = pd.DataFrame(columns=list(COLUMNS.keys()))
        for col in df.columns:
            df[col] = df[col].astype(COLUMNS[col])
        df.set_index("datetime", inplace=True)
        self.df = df

    @property
    def label(self):
        return (self.location, self.parameter)


@dataclass
class TimeSeriesSets:
    time_series: List[TimeSeries] = field(default_factory=list)

    @property
    def labels(self):
        return [i.label for i in self.time_series]

    def set_active(self, labels):
        for i in self.time_series:
            if (i.location, i.parameter) in labels:
                i.active = True
            else:
                i.active = False

    def append_from_labels(self, labels: List[tuple]):
        labels = [i for i in labels if i not in self.labels]
        time_series = [TimeSeries(location=i[0], parameter=i[1]) for i in labels]
        self.time_series += time_series
