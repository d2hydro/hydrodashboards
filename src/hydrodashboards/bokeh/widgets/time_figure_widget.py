from bokeh.plotting import figure
from bokeh.layouts import column
from bokeh.events import PanEnd, MouseWheel
from bokeh.models.widgets import Div
from bokeh.models import (
    HoverTool,
    FuncTickFormatter,
    Range1d,
    NumeralTickFormatter,
    CustomJSHover,
)
from bokeh.models.glyphs import Line, Patch
from bokeh.palettes import Category10_10 as palette
import pandas as pd
from itertools import cycle
from hydrodashboards.bokeh.sources import (
    time_series_template,
    view_period_patch_source,
    time_series_to_source,
    thresholds_to_source,
)

colors = cycle(palette)
#%%
SIZING_MODE = "stretch_both"
DELTA = 0.1
THRESHOLD_NAME = "threshold"
SEARCH_PATCH_COLOR = "lightgrey"

DT_JS_FORMAT = r"""
    var date = new Date({});
    return date.toLocaleDateString('nl-NL', {{
        hour: '2-digit',
        minute: '2-digit',
        year: 'numeric',
        hour12: false,
        month: 'numeric',
        day: 'numeric'
    }});
"""
LABEL_LEN = 50


def trucate_label(label, length=LABEL_LEN):
    if len(label) > length:
        label = f"{label[0:length-3]}..."

    return label


def range_defaults():
    return -DELTA / 2, DELTA / 2


def move_delta_ends(start, end):
    diff = (DELTA - (end - start)) / 2
    start -= diff
    end += diff
    return start, end


def correct_ends(start, end):
    if pd.isna(start):
        if pd.isna(end):
            start, end = range_defaults()
        else:
            start = end - DELTA
    elif pd.isna(end):
        end = start + DELTA
    elif start > end - DELTA:
        start, end = move_delta_ends(start, end)
    return start, end


# %%
def date_time_range_as_datetime(date_time_range):
    """Get the view_x_range start and end as datetime."""

    def _to_timestamp(i):
        if isinstance(i, (float, int)):
            return pd.Timestamp(i * 10**6)
        else:
            return i

    start = _to_timestamp(date_time_range.start)
    end = _to_timestamp(date_time_range.end)

    return start, end


def empty_fig(text="No graph has been generated", color="black"):
    return Div(
        text=f'<p style="margin-left:400px;color:{color};">{text}</p>',
        align="end",
        sizing_mode="stretch_width",
        width_policy="max",
        css_classes=["time_figure"],
    )


def empty_layout(name):
    time_figure = empty_fig()
    return column(time_figure, name=name, sizing_mode="stretch_both")


def warning_figure(figure_layout, text, color="#f16996"):
    figure_layout.children.pop()
    figure_layout.children.append(empty_fig(text=text, color=color))


def valid_layout(time_figure_layout):
    return type(time_figure_layout.children[0]) != Div


def make_x_range(data, graph="top_figs"):
    if graph == "top_figs":
        x_range = Range1d(
            start=data.view_start,
            end=data.view_end,
            bounds=(
                data.search_start,
                data.search_end,
            ),
        )
        x_range.min_interval = pd.Timedelta(minutes=15)
    elif graph == "search_fig":
        x_range = Range1d(
            start=data.search_start,
            end=data.search_end,
            bounds=(
                data.history_start,
                data.search_end,
            ),
        )
        x_range.min_interval = pd.Timedelta(days=1)
    return x_range


def make_y_range(time_series, bounds=None):
    time_series = [i for i in time_series if not i.df.empty]
    if len(time_series) > 0:
        y_start = min((i.df["value"].min() for i in time_series))
        y_end = max((i.df["value"].max() for i in time_series))
        y_start, y_end = correct_ends(y_start, y_end)
    else:
        y_start, y_end = range_defaults()
    y_range = Range1d(start=y_start, end=y_end)
    y_range.min_interval = 0.01
    return y_range


def _get_sources(renderers):
    return [
        i.data_source
        for i in renderers
        if (len(i.data_source.data["value"]) > 0) & (i.name != THRESHOLD_NAME)
    ]


def _ends(renderers):
    sources = _get_sources(renderers)
    if len(sources) > 0:
        start = min((i.data["value"].min() for i in sources))
        end = max((i.data["value"].max() for i in sources))
        if start > end - DELTA:
            start, end = move_delta_ends(start, end)
    else:
        start, end = range_defaults()
    return start, end


def update_time_series_y_ranges(time_figure_layout, fit_y_axis=False):
    def update_range(fig, fit_y_axis=False):
        ends = _ends(fig.renderers)
        if fit_y_axis:
            fig.y_range.start, fig.y_range.end = ends
        fig.y_range.reset_start, fig.y_range.reset_end = ends

    if valid_layout(time_figure_layout):
        top_figs = time_figure_layout.children[0].children
        for fig in top_figs:
            update_range(fig, fit_y_axis=fit_y_axis)


def update_search_time_series_y_ranges(search_time_figure_layout):
    if valid_layout(search_time_figure_layout):
        fig = search_time_figure_layout.children[0]

        # update y-axis
        renderers = [i for i in fig.renderers if type(i.glyph) == Line]
        ends = _ends(renderers)
        fig.y_range.start, fig.y_range.end = ends


def toggle_threshold_graphs(time_figure_layout, active):
    if valid_layout(time_figure_layout):
        top_figs = time_figure_layout.children[0].children
        for fig in top_figs:
            for renderer in fig.renderers:
                if renderer.name == THRESHOLD_NAME:
                    renderer.visible = active


def search_fig(
    search_time_figure_layout,
    time_series,
    x_range,
    periods,
    color="#1f77b4",
    search_source=None,
    sample_config=None
):
    def _add_line():
        time_fig.line(x="datetime", y="value", source=search_source, color=color)

    # get source
    x_start, x_end = date_time_range_as_datetime(x_range)
    source = time_series_to_source(
        time_series, start_date_time=x_start, end_date_time=x_end, sample_config=sample_config
    )

    # get y-axis start and end
    values = source.data["value"]
    if len(values) == 0:
        y_start, y_end = range_defaults()
    else:
        y_start = values.min()
        y_end = values.max()
        y_start, y_end = correct_ends(y_start, y_end)

    # create or update graph
    if isinstance(search_time_figure_layout.children[0], Div):
        search_time_figure_layout.children.pop()
        y_range = Range1d(start=y_start, end=y_end)
        time_fig = figure(
            sizing_mode=SIZING_MODE,
            x_range=x_range,
            y_range=y_range,
            toolbar_location=None,
            css_classes=["time_figure"],
        )
        time_fig.toolbar.active_drag = None
        time_fig.toolbar.active_scroll = None
        time_fig.toolbar.active_tap = None
        time_fig.yaxis.visible = False

        time_fig.patch(
            x="x",
            y="y",
            source=view_period_patch_source(periods),
            alpha=0.5,
            line_width=2,
            fill_color=SEARCH_PATCH_COLOR,
            line_color=SEARCH_PATCH_COLOR,
        )
        _add_line()
        search_time_figure_layout.children.append(time_fig)
    else:
        # get time_fig from layout
        time_fig = search_time_figure_layout.children[0]

        # update patch data_source
        time_fig.renderers[0].data_source.data.update(
            view_period_patch_source(periods).data
        )

        # update time_series source
        time_fig.renderers[1].data_source.data.update(source.data)
        time_fig.renderers[1].glyph.line_color = color
        time_fig.renderers[1].data_source.name = source.name

        # set y_range end and start
        time_fig.y_range.start = y_start
        time_fig.y_range.end = y_end

        # remove and add time_fig_renderer
        # time_fig.renderers.remove(time_fig.renderers[1])
        # _add_line(time_fig, source, color)


def top_fig(
    group: tuple,
    x_range: Range1d,
    y_axis_label: str,
    threshold_groups={},
    threshold_visible=False,
    press_up_event=None,
    renderers_on_change=[],
    sample_config=None
):

    """Generate a time-figure from supplied bokeh input parameters."""

    parameter_group, time_series = group
    # define tools
    time_hover = HoverTool(
        tooltips=[("datum-tijd", "@datetime{%F %H:%M}"), ("waarde", "@value{'0.0'}")],
        formatters={
            "@datetime": CustomJSHover(code=DT_JS_FORMAT.format("special_vars.data_x"))
        },
    )
    time_hover.toggleable = False

    tools = [
        "pan",
        "box_zoom",
        "xwheel_zoom",
        "zoom_in",
        "zoom_out",
        "undo",
        "redo",
        "reset",
        #        "save",
        time_hover,
    ]

    y_range = make_y_range(time_series)
    parameters = list(set([i.parameter_name for i in time_series]))
    # y_axis_label = f"{parameter_group} [{time_series[0].units}]"

    time_fig = figure(
        tools=tools,
        sizing_mode="stretch_width",
        x_range=x_range,
        y_range=y_range,
        y_axis_label=y_axis_label,
        active_scroll="xwheel_zoom",
        active_drag="box_zoom",
        toolbar_location="above",
        css_classes=["time_figure"],
    )

    time_fig.toolbar.logo = None
    time_fig.toolbar.autohide = False

    time_fig.title.align = "center"

    time_fig.xaxis.formatter = FuncTickFormatter(code=DT_JS_FORMAT.format("tick"))
    time_fig.xaxis.visible = True
    time_fig.yaxis[0].formatter = NumeralTickFormatter(format="0.00")

    # add lines to figure
    x_start, x_end = date_time_range_as_datetime(x_range)
    for i in time_series:
        label = i.label
        legend_label = trucate_label(i.label)
        source = time_series_to_source(i, start_date_time=x_start, end_date_time=x_end, sample_config=sample_config)
        renderer = time_fig.line(
            x="datetime",
            y="value",
            source=source,
            color=next(colors),
            legend_label=legend_label,
            name=label,
        )
        for i in renderers_on_change:
            renderer.on_change(*i)

    # add thresholds to figure
    thresholds = threshold_groups[parameter_group]
    for k, v in thresholds.items():
        source = thresholds_to_source(v)
        renderer = time_fig.multi_line(
            xs="datetime",
            ys="value",
            source=thresholds_to_source(v),
            name=THRESHOLD_NAME,
            line_width=v["line_width"],
            line_dash="dashed",
            visible=threshold_visible,
            color=v["color"],
        )

    # make up legend
    time_fig.legend.click_policy = "hide"
    time_fig.legend.visible = True

    if len(time_fig.legend) > 0:
        time_fig.add_layout(time_fig.legend[0], "right")
        time_fig.legend[0].label_text_font_size = "9pt"
        time_fig.legend[0].spacing = -2
        time_fig.legend[0].padding = -5
        time_fig.legend[0].label_height = 5
        time_fig.legend[0].margin = 5

        time_fig.legend[0].border_line_width = 0
    if press_up_event is not None:
        time_fig.on_event(PanEnd, press_up_event)
        time_fig.on_event(MouseWheel, press_up_event)

    return time_fig


def create_time_figures(
    time_figure_layout: column,
    time_series_groups: dict,
    group_y_labels: dict,
    threshold_groups: dict,
    threshold_visible: bool,
    x_range,
    renderers_on_change=[],
    press_up_event=None,
    sample_config=None,
):
    time_figure_layout.children.pop()
    top_figs = [
        top_fig(
            i,
            x_range,
            y_axis_label=group_y_labels[i[0]],
            threshold_groups=threshold_groups,
            threshold_visible=threshold_visible,
            renderers_on_change=renderers_on_change,
            press_up_event=press_up_event,
            sample_config=sample_config,
        )
        for i in time_series_groups.items()
    ]
    top_figs[-1].xaxis.visible = True
    time_figure_layout.children.append(column(*top_figs, sizing_mode="stretch_width"))

    time_series_sources = {}
    for i in top_figs:
        for j in i.renderers:
            if j.name != THRESHOLD_NAME:
                time_series_sources[j.name] = {}
                time_series_sources[j.name]["source"] = j.data_source
                time_series_sources[j.name]["color"] = j.glyph.line_color

    return time_series_sources
