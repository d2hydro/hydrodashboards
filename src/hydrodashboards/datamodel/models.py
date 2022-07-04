from typing import List
from bokeh.models import MultiSelect
from bokeh.layouts import column
from bokeh.models.widgets import DatePicker
from dataclasses import dataclass, field
from datetime import datetime

MAX_FILTER_LEN = 5
SIZING_MODE = "stretch_width"


@dataclass
class Filter:
    language: str = "dutch"
    title: str = None
    name: str = None
    options: List[tuple] = field(default_factory=list)
    value: list = field(default_factory=list)
    _bokeh: column = None

    @property
    def bokeh(self) -> MultiSelect:
        if self._bokeh is None:
            title = self.title
            bokeh_filter = MultiSelect(title=title,
                                       value=self.value,
                                       options=self.options)
            bokeh_filter.size = min(len(bokeh_filter.options), MAX_FILTER_LEN)
            bokeh_filter.sizing_mode = SIZING_MODE
            self._bokeh = column(bokeh_filter, name=self.name, sizing_mode=SIZING_MODE)
        return self._bokeh


@dataclass
class DateSelect:
    language: str = "dutch"
    title: str = None
    value: datetime = None
    min_date: datetime = None
    max_date: datetime = None
    _bokeh: DatePicker = None

    @property
    def bokeh(self) -> DatePicker:
        if self._bokeh is None:
            self._bokeh = DatePicker(
                title=self.title,
                value=self.value.strftime("%Y-%m-%d"),
                min_date=self.min_date.strftime("%Y-%m-%d"),
                max_date=self.max_date.strftime("%Y-%m-%d"),
                sizing_mode="stretch_width"
                )
        return self._bokeh
