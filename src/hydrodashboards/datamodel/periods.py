from hydrodashboards.bokeh.language import (
    search_period_start_title,
    search_period_end_title,
)

from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class Periods:
    now: datetime
    default_search_period: int = 365
    default_view_period: int = 21
    history_period_days: int = 3652
    view_start: datetime = None
    view_end: datetime = None
    history_start: datetime = None
    search_start: datetime = None
    search_end: datetime = None
    search_start_title: str = None
    search_end_title: str = None
    language: str = "dutch"

    def __post_init__(self):
        next_day = datetime(*self.now.timetuple()[:3]) + timedelta(days=1)
        self.view_end = self.now
        self.view_start = self.now - timedelta(self.default_view_period)
        self.search_end = next_day
        self.history_start = next_day - timedelta(self.history_period_days)
        self.search_start = next_day - timedelta(self.default_search_period)
        self.search_start_title = search_period_start_title[self.language]
        self.search_end_title = search_period_end_title[self.language]

    @property
    def view_period(self):
        return self.view_end - self.view_start

    @property
    def search_period(self):
        return self.search_end - self.search_start

    @property
    def history_period(self):
        return self.search_end - self.history_start

    @property
    def search_dates(self):
        return self.search_start, self.search_end

    def set_search_period(self, search_start, search_end):

        # check if new search period isn't smaller than current view_period
        nw_search_period = search_end - search_start
        period = min(self.view_period, nw_search_period)

        # keep the view_period within search period
        if search_start > self.view_start:
            self.view_start = search_start
            self.view_end = search_start + period
        elif search_end < self.view_end:
            self.view_end = search_end
            self.view_start = search_end - period

        # set search period
        self.search_start = search_start
        self.search_end = search_end

    def set_view_period(self, view_start, view_end, force=False):
        nw_view_period = view_end - view_start
        if (nw_view_period.total_seconds() > 1800) | force:
            self.view_start = view_start
            self.view_end = view_end
            print(f"data set: {self.view_start}, {self.view_end}")
            return True
        else:
            return False
