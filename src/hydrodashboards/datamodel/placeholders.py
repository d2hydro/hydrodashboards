from dataclasses import dataclass
from bokeh.models.widgets import (
    Button,
    CheckboxGroup,
    Div,
    RadioGroup,
    Select,
    DateRangeSlider
    )
from bokeh.layouts import row, column
from bokeh.plotting import figure
from datetime import datetime, timedelta


@dataclass
class UpdateGraph:
    _bokeh: row = None

    @property
    def bokeh(self):
        if self._bokeh is None:
            time_fig_button = Button(
                label="Update grafiek",
                css_classes=['stoploading_time_fig'],
                sizing_mode="stretch_width",
                button_type="primary"
                )
            self._bokeh = row(time_fig_button,
                              name="update_graph",
                              sizing_mode="stretch_both")
        return self._bokeh


@dataclass
class MapFigure:
    _bokeh: row = None

    @property
    def bokeh(self):
        if self._bokeh is None:
            map_fig = figure()
            self._bokeh = row(map_fig,
                              name="map_figure",
                              sizing_mode="stretch_both")
        return self._bokeh


@dataclass
class MapOptions:
    _bokeh: row = None

    @property
    def bokeh(self):
        if self._bokeh is None:
            map_options = ["kaartoptie 1", "kaartoptie 2"]
            map_layers = CheckboxGroup(labels=map_options, active=[])
            background = RadioGroup(labels=["topografie", "luchtfoto"], active=0)
            map_controls = column(Div(text="Kaartlagen"),
                                  map_layers,
                                  Div(text="Achtergrond"),
                                  background)
            self._bokeh = row(map_controls,
                              name="map_options",
                              sizing_mode="stretch_both")
        return self._bokeh


@dataclass
class Status:
    _bokeh = None

    @property
    def bokeh(self):
        if self._bokeh is None:
            status = Div(text="status placeholder")

            self._bokeh = column(status,
                                 name="status",
                                 sizing_mode="stretch_both")
        return self._bokeh


@dataclass
class TimeFigure:
    _bokeh: row = None

    @property
    def bokeh(self):
        if self._bokeh is None:
            time_fig = figure()
            self._bokeh = row(time_fig,
                              name="time_figure",
                              sizing_mode="stretch_both")
        return self._bokeh


@dataclass
class SelectSearchTimeSeries:
    _bokeh: row = None

    @property
    def bokeh(self):
        if self._bokeh is None:
            select_search_timeseries = Select(value=None, options=[])
            self._bokeh = column(select_search_timeseries,
                                 name="select_search_time_series",
                                 sizing_mode="stretch_both")
        return self._bokeh


@dataclass
class DownloadSearchTimeSeries:
    _bokeh: row = None

    @property
    def bokeh(self):
        if self._bokeh is None:
            button_download = Button(label="Download",
                                     button_type="success")
            self._bokeh = column(button_download,
                                 name="download_search_time_series",
                                 sizing_mode="stretch_width")
        return self._bokeh


@dataclass
class ViewPeriod:
    _bokeh: row = None

    @property
    def bokeh(self):
        if self._bokeh is None:
            now = datetime.now()
            value = (now - timedelta(days=14), now)
            start = now - timedelta(days=365)
            end = now

            period_slider = DateRangeSlider(
                value=value,
                start=start,
                end=end)
            period_slider.format = "%d-%m-%Y"

            self._bokeh = row(period_slider,
                              name="view_period",
                              sizing_mode="stretch_both")
        return self._bokeh


@dataclass
class SearchTimeFigure:
    _bokeh: row = None

    @property
    def bokeh(self):
        if self._bokeh is None:
            time_fig = figure()
            self._bokeh = row(time_fig,
                              name="search_time_figure",
                              sizing_mode="stretch_both")
        return self._bokeh
