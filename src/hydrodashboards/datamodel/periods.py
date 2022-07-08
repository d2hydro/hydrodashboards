from hydrodashboards.bokeh.language import (
    search_period_start_title,
    search_period_end_title,
)

from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class Periods:
    now: datetime
    default_search_period: timedelta = timedelta(days=365)
    default_view_period: timedelta = timedelta(days=21)
    history_period: timedelta = timedelta(days=3652)
    view_start: datetime = None
    view_end: datetime = None
    history_start: datetime = None
    search_start: datetime = None
    search_end: datetime = None
    search_start_title: str = None
    search_end_title: str = None
    language: str = "dutch"

    def __post_init__(self):
        self.view_end = self.now
        self.view_start = self.now - self.default_view_period
        self.search_end = self.now
        self.history_start = self.now - self.history_period
        self.search_start = self.now - self.default_search_period
        self.search_end_title = search_period_start_title[self.language]
        self.search_start_title = search_period_end_title[self.language]

    @property
    def view_period(self):
        return self.view_end - self.view_start

    @property
    def search_period(self):
        return self.search_end - self.search_start
