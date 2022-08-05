from bokeh.plotting import figure
from bokeh.layouts import column
from bokeh.events import PanEnd, MouseWheel
from bokeh.models.widgets import Div
from bokeh.models import (
    HoverTool,
    ZoomOutTool,
    DatetimeTickFormatter,
    Range1d,
    WheelZoomTool,
    NumeralTickFormatter
    )
from bokeh.palettes import Category10_10 as palette
import pandas as pd
from itertools import cycle
from hydrodashboards.bokeh.sources import time_series_template, view_period_patch_source, time_series_to_source

colors = cycle(palette)

SIZING_MODE = "stretch_both"

def range_defaults():
    return -0.05, 0.05

def check_nan(start, end):
    if pd.isna(start):
        if pd.isna(end):
            start, end = range_defaults()
        else:
            start = end - 0.1
    elif pd.isna(end):
        end = start + 0.1
    return start, end


def date_time_range_as_datetime(date_time_range):
    """Get the view_x_range start and end as datetime."""
    def _to_timestamp(i):
        if isinstance(i, (float, int)):
            return pd.Timestamp(i * 10 ** 6)
        else:
            return i

    start = _to_timestamp(date_time_range.start)
    end = _to_timestamp(date_time_range.end)

    return start, end

def empty_fig():
    return Div(text="No graph has been generated")


def make_x_range(data, graph="top_figs"):
    if graph == "top_figs":
        x_range = Range1d(start=data.view_start,
                          end=data.view_end,
                          bounds=(
                              data.search_start,
                              data.search_end,
                              ))

    elif graph == "search_fig":
        x_range = Range1d(start=data.search_start,
                          end=data.search_end,
                          bounds=(
                              data.history_start,
                              data.now,
                              ))
        x_range.min_interval = pd.Timedelta(days=1)
    return x_range


def make_y_range(time_series, bounds=None):
    y_start = min((i.df["value"].min() for i in time_series))
    y_end = max((i.df["value"].max() for i in time_series))
    y_start, y_end = check_nan(y_start, y_end)
    y_range = Range1d(start=y_start,
                      end=y_end)
    y_range.min_interval = 0.01
    return y_range


def search_fig(search_time_figure_layout, time_series, x_range, periods, color="#1f77b4"):
    def _add_line(time_fig, source, color):
        time_fig.line(x="datetime",
                      y="value",
                      source=time_series_template(),
                      color=color)

    # get y-axis start and end
    values = time_series.df["value"].values
    if len(values) == 0:
        y_start, y_end = range_defaults()
    else:
        y_start = values.min()
        y_end = values.max()
        y_start, y_end = check_nan(y_start, y_end)

    # get source
    x_start, x_end = date_time_range_as_datetime(x_range)
    source = time_series_to_source(time_series,
                                   start_date_time=x_start,
                                   end_date_time=x_end)

    # create or update graph
    if isinstance(search_time_figure_layout.children[0], Div):
        search_time_figure_layout.children.pop()
        y_range = Range1d(start=y_start, end=y_end)
        time_fig = figure(sizing_mode=SIZING_MODE,
                          x_range=x_range,
                          y_range=y_range,
                          toolbar_location=None)
        time_fig.toolbar.active_drag = None
        time_fig.toolbar.active_scroll = None
        time_fig.toolbar.active_tap = None
        time_fig.yaxis.visible = False

        time_fig.patch(x="x", y="y", source=view_period_patch_source(periods), alpha=0.5, line_width=2)
        _add_line(time_fig, source, color)
        search_time_figure_layout.children.append(time_fig)
    else:
        # get time_fig from layout
        time_fig = search_time_figure_layout.children[0]

        # update patch data_source
        time_fig.renderers[0].data_source.data.update(view_period_patch_source(periods).data)

        # update time_series source
        time_fig.renderers[1].data_source.data.update(source.data)

        # set y_range end and start
        time_fig.y_range.start = y_start
        time_fig.y_range.end = y_end

        # remove and add time_fig_renderer
        #time_fig.renderers.remove(time_fig.renderers[1])
        #_add_line(time_fig, source, color)



def top_fig(group: tuple,
            x_range: Range1d,
            press_up_event=None):

    """Generate a time-figure from supplied bokeh input parameters."""

    label, time_series = group
    # define tools
    time_hover = HoverTool(tooltips=[("datum-tijd", "@datetime{%F}"),
                                     ("waarde", "@value{(0.00)}")],
                           formatters={"@datetime": "datetime"})
    time_hover.toggleable = False

    tools = ["pan",
             "box_zoom",
             "xwheel_zoom",
             "zoom_in",
             "zoom_out",
             "reset",
             "undo",
             "redo",
             "save",
             time_hover]

    y_range = make_y_range(time_series)
    parameters = list(set([i.parameter_name for i in time_series]))
    if len(parameters) == 1:
        y_axis_label = parameters[0]
    else:
        y_axis_label = label


    time_fig = figure(tools=tools,
                      sizing_mode=SIZING_MODE,
                      x_range=x_range,
                      y_range=y_range,
                      y_axis_label=y_axis_label,
                      active_scroll="xwheel_zoom",
                      active_drag="box_zoom",
                      toolbar_location="above")

    time_fig.toolbar.logo = None
    time_fig.toolbar.autohide = False

    time_fig.title.align = "center"

    time_fig.xaxis.formatter = DatetimeTickFormatter(hours=["%H:%M"],
                                                     days=["%d-%m-%Y"],
                                                     months=["%d-%m-%Y"],
                                                     years=["%d-%m-%Y"],
                                                     )
    time_fig.xaxis.visible = False
    time_fig.yaxis[0].formatter = NumeralTickFormatter(format="0.00")

    # add lines to figure
    x_start, x_end = date_time_range_as_datetime(x_range)
    for i in time_series:
        label = i.label
        time_fig.line(x="datetime",
                      y="value",
                      source=time_series_to_source(i,
                                                   start_date_time=x_start,
                                                   end_date_time=x_end),
                      color=next(colors),
                      legend_label=label,
                      name=label)

    # make up legend
    time_fig.legend.click_policy = "hide"

    time_fig.add_layout(time_fig.legend[0], "right")
    time_fig.legend[0].label_text_font_size = "9pt"
    if press_up_event is not None:
        time_fig.on_event(PanEnd, press_up_event)
        time_fig.on_event(MouseWheel, press_up_event)
    return time_fig


def create_time_figures(time_figure_layout: column,
                        time_series_groups: dict,
#                        time_series_sources: dict,
                        x_range,
                        press_up_event=None):
    time_figure_layout.children.pop()
    top_figs = [top_fig(i,
                        x_range,
                        press_up_event=press_up_event) for i in  time_series_groups.items()]
    top_figs[-1].xaxis.visible = True
    time_figure_layout.children.append(column(*top_figs, sizing_mode="stretch_both"))

    time_series_sources = {}
    for i in top_figs:
        for j in i.renderers:
            time_series_sources[j.name] = j.data_source

    return time_series_sources
