from bokeh.plotting import figure
from bokeh.layouts import column
from bokeh.models.widgets import Div


def empty_fig():
    return Div(text="No graph has been generated")


def make_time_figure():
    top_figs = [figure()]
    return column(*top_figs, sizing_mode="stretch_both")
