from hydrodashboards.bokeh.language import (
    search_period_start_title,
    search_period_end_title
    )
from hydrodashboards.datamodel.models import DateSelect
from bokeh.layouts import column, row
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class SearchPeriod:
    language: str = "dutch"
    min_date: datetime = datetime.now() - timedelta(days=3652)
    max_date: datetime = datetime.now()
    start_date: datetime = datetime.now() - timedelta(days=14)
    start_date_title: str = None
    end_date: datetime = datetime.now()
    end_date_title: str = None
    _bokeh: column() = None

    def __post_init__(self):
        self.start_date_title = search_period_start_title[self.language]
        self.end_date_title = search_period_end_title[self.language]

    @property
    def bokeh(self):
        if self._bokeh is None:
            start_date_picker = DateSelect(title=self.start_date_title,
                                           value=self.start_date,
                                           min_date=self.min_date,
                                           max_date=self.end_date).bokeh
            end_date_picker = DateSelect(title=self.start_date_title,
                                         value=self.start_date,
                                         min_date=self.start_date,
                                         max_date=self.max_date).bokeh
            #start_date_picker_bokeh = start_date_picker.bokeh
            #end_date_picker_bokeh = end_date_picker.bokeh
            start_date_picker.js_link("value", end_date_picker, "min_date")
            end_date_picker.js_link("value", start_date_picker, "max_date")

            self._bokeh = column(row(start_date_picker, end_date_picker),
                                 name="search_period",
                                 sizing_mode="stretch_both")
        return self._bokeh
