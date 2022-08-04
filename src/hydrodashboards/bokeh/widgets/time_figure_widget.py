from bokeh.plotting import figure
from bokeh.layouts import column
from bokeh.models.widgets import Div
from bokeh.models import (
    HoverTool,
    DatetimeTickFormatter,
    Range1d,
    WheelZoomTool,
    NumeralTickFormatter
    )
from bokeh.palettes import Category10_10 as palette
import pandas as pd
from itertools import cycle
from hydrodashboards.bokeh.sources import time_series_template, view_period_patch_source

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


def search_fig(search_time_figure_layout, source, x_range, periods, color="#1f77b4"):
    def _add_line(time_fig, source, color):
        time_fig.line(x="datetime",
                      y="value",
                      source=source,
                      color=color)
    
    if isinstance(search_time_figure_layout.children[0], Div):
        search_time_figure_layout.children.pop()
        values = source.data["value"]
        if len(values) == 0:
            y_start, y_end = range_defaults
        else:
            y_start = values.min()
            y_end = values.max()
            y_start, y_end = check_nan(y_start, y_end)
        y_range = Range1d(start=y_start, end=y_end)
        time_fig = figure(sizing_mode=SIZING_MODE,
                          x_range=x_range,
                          y_range=y_range,
                          toolbar_location=None)

        time_fig.yaxis.visible = False
        time_fig.patch(x="x", y="y", source=view_period_patch_source(periods), alpha=0.5, line_width=2)
        _add_line(time_fig, source, color)
        search_time_figure_layout.children.append(time_fig)
    else:
        # get time_fig from layout
        time_fig = search_time_figure_layout.children[0]

        # update patch data_source
        time_fig.renderers[0].data_source.data.update(view_period_patch_source(periods).data)

        # remove and add time_fig_renderer
        time_fig.renderers.remove(time_fig.renderers[1])
        _add_line(time_fig, source, color)
    


def top_fig(group: tuple, time_series_sources: dict, x_range: Range1d):

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

    # misc settings
    #wheel_zoom = next((i for i in time_fig.tools if type(i) == WheelZoomTool), None)
    #if wheel_zoom:
    #    wheel_zoom.speed = 0.0001

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
    for i in time_series:
        label = i.label
        source = time_series_sources[time_series[0].label]
        time_fig.line(x="datetime",
                      y="value",
                      source=source,
                      color=next(colors),
                      legend_label=label)

    # make up legend
    time_fig.legend.click_policy = "hide"

    time_fig.add_layout(time_fig.legend[0], "right")
    time_fig.legend[0].label_text_font_size = "9pt"
    return time_fig


def create_time_figures(time_figure_layout: column, time_series_groups: dict, time_series_sources: dict, x_range):
    time_figure_layout.children.pop()
    top_figs = [top_fig(i, time_series_sources, x_range) for i in  time_series_groups.items()]
    top_figs[-1].xaxis.visible = True
    time_figure_layout.children.append(column(*top_figs, sizing_mode="stretch_both"))
