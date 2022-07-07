from dataclasses import dataclass
from bokeh.models.widgets import (
    Button,
    CheckboxGroup,
    Div,
    RadioGroup,
    Select,
    DateRangeSlider,
)
from bokeh.layouts import row, column
from bokeh.plotting import figure
from datetime import datetime, timedelta


@dataclass
class MapFigure:
    @property
    def bokeh(self):
        map_fig = figure()
        return row(map_fig, name="map_figure", sizing_mode="stretch_both")


@dataclass
class MapOptions:
    @property
    def bokeh(self):
        map_options = ["kaartoptie 1", "kaartoptie 2"]
        map_layers = CheckboxGroup(labels=map_options, active=[])
        background = RadioGroup(labels=["topografie", "luchtfoto"], active=0)
        map_controls = column(
            Div(text="Kaartlagen"), map_layers, Div(text="Achtergrond"), background
        )
        return row(map_controls, name="map_options", sizing_mode="stretch_both")


@dataclass
class Status:
    @property
    def bokeh(self):
        status = Div(text="status placeholder")
        return column(status, name="status", sizing_mode="stretch_both")


@dataclass
class TimeFigure:
    @property
    def bokeh(self):
        time_fig = figure()
        return row(time_fig, name="time_figure", sizing_mode="stretch_both")


@dataclass
class SelectSearchTimeSeries:
    @property
    def bokeh(self):
        select_search_timeseries = Select(value=None, options=[])
        return column(
            select_search_timeseries,
            name="select_search_time_series",
            sizing_mode="stretch_both",
        )


@dataclass
class DownloadSearchTimeSeries:
    @property
    def bokeh(self):
        button_download = Button(label="Download", button_type="success")
        return column(
            button_download,
            name="download_search_time_series",
            sizing_mode="stretch_width",
        )


@dataclass
class ViewPeriod:
    @property
    def bokeh(self):
        now = datetime.now()
        value = (now - timedelta(days=14), now)
        start = now - timedelta(days=365)
        end = now

        period_slider = DateRangeSlider(value=value, start=start, end=end)
        period_slider.format = "%d-%m-%Y"
        return row(period_slider, name="view_period", sizing_mode="stretch_both")


@dataclass
class SearchTimeFigure:
    @property
    def bokeh(self):
        time_fig = figure()
        return row(time_fig, name="search_time_figure", sizing_mode="stretch_both")
