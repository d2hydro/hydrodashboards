from bokeh.plotting import figure
from bokeh.layouts import column
from bokeh.models.layouts import Column
from bokeh.events import PanEnd, MouseWheel
from bokeh.models.widgets import Div
from bokeh.models import (
    HoverTool,
    FuncTickFormatter,
    Legend,
    Range1d,
    NumeralTickFormatter,
    CustomJSHover,
    WheelZoomTool,
)
from bokeh.models.annotations import LegendItem
from bokeh.models.glyphs import Line
from bokeh.palettes import Category10_10 as palette
import pandas as pd
from hydrodashboards.bokeh.sources import (
    view_period_patch_source,
    time_series_to_source,
    thresholds_to_source,
)

from dataclasses import dataclass


# %%
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


@dataclass
class Colors:
    palette = palette
    used = {}

    def __post_init__(self):
        self.reset()

    @property
    def min_used(self):
        return min(self.used.values())

    def reset(self):
        self.used = {k: 0 for k in self.palette}

    def next(self, use=True):
        color = next(k for k, v in self.used.items() if v == self.min_used)
        if use:
            self.add(color)
        return color

    def add(self, color):
        if color in palette:
            self.used[color] += 1

    def remove(self, color):
        if color in palette:
            self.used[color] = max(self.used[color] - 1, 0)


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


def _get_renderers(top_figs):
    renderers = (j for i in [i.renderers for i in top_figs] for j in i)
    return [i for i in renderers if i.name != THRESHOLD_NAME]


def _get_timeseries_sources(top_figs):
    return {
        i.name: dict(source=i.data_source, color=i.glyph.line_color)
        for i in _get_renderers(top_figs)
    }


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


def get_legend(time_fig):
    """Get the legend of a figure (add one if not initiated)."""
    if not time_fig.legend:
        legend = Legend(name=time_fig.name, location=(1, 1))
        legend.visible = True
        legend.click_policy = "hide"
        legend.label_text_font_size = "9pt"
        legend.border_line_width = 0
        legend.spacing = -2
        legend.padding = -5
        legend.label_height = 5
        legend.margin = 5
        time_fig.add_layout(legend, "right")

    return time_fig.legend[0]


def append_to_legend(renderer, legend):
    """Append a renderer to the legend."""
    legend.items.append(
        LegendItem(
            label=trucate_label(renderer.name), name=renderer.name, renderers=[renderer]
        )
    )


def time_series_to_fig(
    time_series, time_fig, colors, sample_config, renderers_on_change
):
    """Add a time_series to the figure."""
    legend = get_legend(time_fig)

    for i in time_series:
        label = i.label
        x_start, x_end = date_time_range_as_datetime(time_fig.x_range)
        source = time_series_to_source(
            i, start_date_time=x_start, end_date_time=x_end, sample_config=sample_config
        )
        renderer = time_fig.line(
            x="datetime",
            y="value",
            source=source,
            color=colors.next(),
            name=label,
        )
        append_to_legend(renderer, legend)
        for i in renderers_on_change:
            renderer.on_change(*i)


def thresholds_to_fig(thresholds, time_fig, threshold_visible):
    """Append thresholds to the figure."""
    for k, v in thresholds.items():
        time_fig.multi_line(
            xs="datetime",
            ys="value",
            source=thresholds_to_source(v),
            name=THRESHOLD_NAME,
            line_width=v["line_width"],
            line_dash="dashed",
            visible=threshold_visible,
            color=v["color"],
        )


def search_fig(
    search_time_figure_layout,
    time_series,
    x_range,
    periods,
    patch_source,
    color="#1f77b4",
    search_source=None,
    sample_config=None,
):
    def _add_line():
        time_fig.line(x="datetime", y="value", source=search_source, color=color)

    # get source
    x_start, x_end = date_time_range_as_datetime(x_range)
    source = time_series_to_source(
        time_series,
        start_date_time=x_start,
        end_date_time=x_end,
        sample_config=sample_config,
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
            source=patch_source,
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
        patch_source.data.update(view_period_patch_source(periods).data)

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


def create_top_fig(
    group: tuple,
    x_range: Range1d,
    y_axis_label: str,
    threshold_groups={},
    threshold_visible=False,
    press_up_event=None,
    renderers_on_change=[],
    sample_config=None,
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

    wheel_zoom = WheelZoomTool(speed=0.001, dimensions="width")

    tools = [
        "pan",
        "box_zoom",
        wheel_zoom,
        "reset",
        time_hover,
    ]

    y_range = make_y_range(time_series)
    time_fig = figure(
        tools=tools,
        sizing_mode="stretch_width",
        x_range=x_range,
        y_range=y_range,
        y_axis_label=y_axis_label,
        active_scroll=wheel_zoom,
        active_drag="box_zoom",
        toolbar_location="above",
        css_classes=["time_figure"],
        name=parameter_group,
    )

    time_fig.toolbar.logo = None
    time_fig.toolbar.autohide = False

    time_fig.title.align = "center"

    time_fig.xaxis.formatter = FuncTickFormatter(code=DT_JS_FORMAT.format("tick"))
    time_fig.xaxis.visible = True

    time_fig.yaxis[0].formatter = NumeralTickFormatter(format="0.00")

    # add time_series to figure
    colors = Colors()
    time_series_to_fig(
        time_series, time_fig, colors, sample_config, renderers_on_change
    )

    # add thresholds to figure
    thresholds = threshold_groups[parameter_group]
    thresholds_to_fig(thresholds, time_fig, threshold_visible)

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
    # we will clean all existing top-figs (if there are figures)
    top_figs = []
    if type(time_figure_layout.children[0]) == Column:
        for time_fig in time_figure_layout.children[0].children:
            # if the time_fig.name exists in parameter_groups, we keep it
            if time_fig.name in time_series_groups.keys():
                colors = Colors()
                parameter_group = time_fig.name
                time_series = time_series_groups[time_fig.name]

                # delete un-used renderers and update used
                labels = [i.label for i in time_series]
                renderers = []
                for renderer in time_fig.renderers:
                    # if renderer is not in time-series or is threshold, we remove it
                    if renderer.name in labels:
                        single_time_series = next(
                            i for i in time_series if i.label == renderer.name
                        )
                        x_start, x_end = date_time_range_as_datetime(time_fig.x_range)
                        source = time_series_to_source(
                            single_time_series,
                            start_date_time=x_start,
                            end_date_time=x_end,
                            sample_config=sample_config,
                        )
                        renderer.data_source.data.update(source.data)
                        renderers.append(renderer)

                        # add the color, so we know it's used
                        colors.add(renderer.glyph.line_color)

                # need to re-add all renderers and legends to figure (pop/remove doesn't work properly) # noqa
                legend = time_fig.legend[0]
                legend.items = []
                time_fig.renderers = []
                renderer_names = []
                for renderer in renderers:
                    time_fig.renderers.append(renderer)
                    append_to_legend(renderer, legend)
                    renderer_names.append(renderer.name)

                # add missing time_series to time_fig
                time_series = (i for i in time_series if i.label not in renderer_names)
                time_series_to_fig(
                    time_series, time_fig, colors, sample_config, renderers_on_change
                )

                # add thresholds to time_fig
                thresholds = threshold_groups[parameter_group]
                thresholds_to_fig(thresholds, time_fig, threshold_visible)

                # we finish the time_fig
                time_fig.yaxis.axis_label = group_y_labels[parameter_group]
                time_fig.xaxis.visible = False

                # we add the fig to the figure-list and remove it from the group
                top_figs += [time_fig]
                time_series_groups.pop(time_fig.name)

    # we remove the time-series column from the layout (we add it later again)
    time_figure_layout.children.pop()

    # if there are new groups, we add a new figure
    for group in time_series_groups.items():
        y_axis_label = group_y_labels[group[0]]
        top_figs += [
            create_top_fig(
                group,
                x_range,
                y_axis_label=y_axis_label,
                threshold_groups=threshold_groups,
                threshold_visible=threshold_visible,
                renderers_on_change=renderers_on_change,
                press_up_event=press_up_event,
                sample_config=sample_config,
            )
        ]

    # add top_figs to the layout again
    top_figs[-1].xaxis.visible = True
    time_figure_layout.children.append(column(*top_figs, sizing_mode="stretch_width"))

    # updating the figure_layout y_ranges
    update_time_series_y_ranges(time_figure_layout, fit_y_axis=True)

    return _get_timeseries_sources(top_figs)
