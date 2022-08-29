"""Bokeh HydroDashboard"""

from bokeh.io import curdoc
from bokeh.layouts import column
from data import Data
from config import TITLE, BOUNDS, MAP_OVERLAYS, MAX_VIEW_PERIOD, LOG_DIR

# import bokeh sources
import hydrodashboards.bokeh.sources as sources
from hydrodashboards.bokeh.widgets import (
    download_widget,
    time_figure_widget,
    map_figure_widget,
    filters_widgets,
    search_period_widget,
    update_graph_widget,
    view_period_widget,
)
from bokeh.models.widgets import Div, Select
from hydrodashboards.bokeh.log_utils import import_logger
import inspect

from hydrodashboards.bokeh.language import update_graph_title


from datetime import datetime
import pandas as pd

LANG = "dutch"
HTML_TYPE = "table"


"""
Supporting functions
"""


def enable_view_time_series_controls():
    """Enable view period (used when first graph is loaded)."""
    if view_period.disabled:  # at app init view_period is disabled
        view_period.disabled = False
        view_period.bar_color = "#e6e6e6"
    
    if download_search_time_series.disabled:
        download_search_time_series.disabled = False


def enable_update_graph():
    """Enable update_graph if locations ánd paramters are selected."""
    if (len(locations.value) > 0) & (len(parameters.value) > 0):
        update_graph.disabled = False
    else:
        update_graph.disabled = True


def update_time_series_sources(stream=False):
    """Update of time_series_sources assigned to top_figs."""
    start, end = view_x_range_as_datetime()
    for k, v in time_series_sources.items():
        time_series = data.time_series_sets.get_by_label(k)        
        if stream:
            exluded_date_times = v["source"].data["datetime"]
            _source = sources.time_series_to_source(time_series=time_series,
                                                    start_date_time=start,
                                                    end_date_time=end,
                                                    excluded_date_times=exluded_date_times,
                                                    unreliables=False)
            v["source"].stream(_source.data)
        else:
            _source = sources.time_series_to_source(time_series=time_series,
                                                    start_date_time=start,
                                                    end_date_time=end,
                                                    unreliables=False)
            v["source"].data.update(_source.data)

def view_x_range_as_datetime():
    """Get the view_x_range start and end as datetime."""
    def _to_timestamp(i):
        if isinstance(i, (float, int)):
            return pd.Timestamp(i * 10 ** 6)
        else:
            return i

    start = _to_timestamp(view_x_range.start)
    end = _to_timestamp(view_x_range.end)

    return start, end


"""
All callbacks used in the app
"""


# callbacks
def update_on_filter_value(attrname, old, new):
    """Updates locations values in locations filter when filters filter is updated"""
    logger.debug(inspect.stack()[0][3])

    # update datamodel
    values = filters_widgets.get_filters_values(filters)
    data.update_on_filter_select(values)

    # update widgets
    locations.options = data.locations.options
    locations.value = data.locations.value
    parameters.options = data.parameters.options
    parameters.value = data.parameters.value

    # update source
    locations_source.data = data.locations.map_locations

    # update selected
    indices = [locations_source.data["id"].index(i) for i in locations.value]
    locations_source.selected.indices = indices

    # update app status
    app_status.text = data.app_status(html_type=HTML_TYPE)


def update_on_locations_source_select(attr, old, new):
    """Update locations values in locations filter when locations_source is selected"""
    logger.debug(inspect.stack()[0][3])

    # get selected ids
    ids = [locations_source.data["id"][i] for i in locations_source.selected.indices]

    # update locations and data.locations value
    locations.value = data.locations.value = ids


def update_on_locations_value(attrname, old, new):
    """Update when values in locations filter are selected"""
    logger.debug(inspect.stack()[0][3])

    # limit to max 10 locations
    if len(locations.value) > 10:
        locations.value = locations.value[:10]

    # update location source selected
    indices = [list(locations_source.data["id"]).index(i) for i in locations.value]
    locations_source.selected.indices = indices

    # update datamodel
    data.update_on_locations_select(locations.value)

    # update parameters options for (de)selected locations
    parameters.options = data.parameters.options
    parameters.value = data.parameters.value

    # update app status
    app_status.text = data.app_status(html_type=HTML_TYPE)

    # enable update_graph button
    enable_update_graph()


def update_on_parameters_value(attrname, old, new):
    """Update when values in locations filter are selected"""
    logger.debug(inspect.stack()[0][3])

    # update datemodel
    data.parameters.value = parameters.value

    # update app status
    app_status.text = data.app_status(html_type=HTML_TYPE)

    # enable update_graph button
    enable_update_graph()


def update_on_search_period_value(attrname, old, new):
    """Update when search_period_value changes"""
    logger.debug(inspect.stack()[0][3])

    search_start = datetime.strptime(search_period.children[0].value, "%Y-%m-%d")
    search_end = datetime.strptime(search_period.children[1].value, "%Y-%m-%d")

    if not data.time_series_sets.within_period(search_start, search_end):
        enable_update_graph()
        data.time_series_sets.remove_inactive()

    # update data.periods for next purpose
    data.periods.search_start = search_start
    data.periods.search_end = search_end

    # update widgets
    search_x_range.start = data.periods.search_start
    search_x_range.end = data.periods.search_end
    view_period.start = data.periods.search_start
    view_period.end = data.periods.search_end
    view_x_range.bounds = (data.periods.search_start, data.periods.search_end)

    # update app status
    app_status.text = data.app_status(html_type=HTML_TYPE)


def update_map_figure_background_control(attrname, old, new):
    """Update map_figure when background is selected"""
    logger.debug(inspect.stack()[0][3])
    tile_source = map_figure_widget.get_tilesource(map_options.children[2].labels[new])
    idx = next(
        idx for idx, i in enumerate(map_figure.renderers) if i.name == "background"
    )
    map_figure.renderers[idx].tile_source = tile_source


def update_map_figure_overlay_control(attrname, old, new):
    """Update visible map-overlays on change"""
    logger.debug(inspect.stack()[0][3])
    map_overlays = map_options.children[0]
    map_fig_idx = {
        i.name: idx
        for idx, i in enumerate(map_figure.renderers)
        if i.name in map_overlays.labels
    }
    for idx, i in enumerate(map_overlays.labels):
        if idx in new:
            map_figure.renderers[map_fig_idx[i]].visible = True
        else:
            map_figure.renderers[map_fig_idx[i]].visible = False


def start_time_series_loader():
    """Start time_series loader and start update_time_series"""
    #logger.debug(inspect.stack()[0][3])
    update_graph.css_classes = ["loader_time_fig"]

    # now we go downloading a view 
    curdoc().add_next_tick_callback(update_time_series_view)


def update_time_series_view():
    """Update time_series and stop time_fig_loader"""
    global time_series_sources # we update the global variable time_series_sources

    logger.debug(inspect.stack()[0][3])
    data.update_time_series()

    # update time_series_layout (top figures)
    parameter_groups = data.parameters.get_groups()
    time_series_groups = data.time_series_sets.by_parameter_groups(parameter_groups, active_only=True)

    time_series_sources = time_figure_widget.create_time_figures(time_figure_layout=time_figure_layout,
                                                                 time_series_groups=time_series_groups,
                                                                 x_range=view_x_range,
                                                                 press_up_event=press_up_event)

    # update search_time_series
    search_time_series.options = data.time_series_sets.active_labels
    if search_time_series.value not in search_time_series.options:
        search_time_series.value = search_time_series.options[0]

    # add_search time_series
    _time_series = data.time_series_sets.get_by_label(search_time_series.value)
    time_figure_widget.search_fig(search_time_figure_layout,
                                  time_series=_time_series,
                                  x_range=search_x_range,
                                  periods=data.periods,
                                  color=time_series_sources[search_time_series.value]["color"],
                                  search_source=search_source)

    # update app status
    app_status.text = data.app_status(html_type=HTML_TYPE)

    # enable view_period if disabled (at first timeseries load)
    enable_view_time_series_controls()

    # go to the next callback
    curdoc().add_next_tick_callback(update_time_series_search)


def update_time_series_search():

    # update full history of all non-complete time-series
    data.update_time_series_search()

    # updating the sources in the used as glyph data_sources
    update_time_series_sources()

    # updating the figure_layout y_ranges
    time_figure_widget.update_time_series_y_ranges(time_figure_layout)

    # stop loader and disable update_graph
    update_graph.css_classes = ["stoploading_time_fig"]
    update_graph.disabled = True


def update_on_search_time_series_value(attrname, old, new):
    """Update source of search_time_figure when search_time_series_value changes"""
    logger.debug(inspect.stack()[0][3])

    # change search time_series
    time_figure_widget.search_fig(search_time_figure_layout,
                                  time_series=data.time_series_sets.get_by_label(label=search_time_series.value),
                                  x_range=search_x_range,
                                  periods=data.periods,
                                  color=time_series_sources[search_time_series.value]["color"],
                                  search_source=search_source)


def update_on_view_period_value(attrname, old, new):
    """Update periods when view_period value changes"""
    #logger.debug(inspect.stack()[0][3])

    # keep end and start within MAX_VIEW_PERIOD
    if MAX_VIEW_PERIOD is not None:
        start_datetime, end_datetime = view_period.value_as_datetime
        if (end_datetime - start_datetime).days > MAX_VIEW_PERIOD.days:
            if old[0] != new[0]:
                view_period.value = (
                    start_datetime,
                    start_datetime + MAX_VIEW_PERIOD,
                )
            elif old[1] != new[1]:
                view_period.value = (end_datetime - MAX_VIEW_PERIOD, end_datetime)

    # update datamodel to keep things in sync
    data.periods.view_start, data.periods.view_end = view_period.value_as_datetime

    # update patch source
    search_time_figure_layout.children[0].renderers[0].data_source.data.update(
        sources.view_period_patch_source(data.periods).data)


def update_on_view_period_value_throttled(attrname, old, new):
    """Update time_series_sources as view_x_range"""
    #logger.debug(inspect.stack()[0][3])

    update_time_series_sources()

    # updating the figure_layout y_ranges
    time_figure_widget.update_time_series_y_ranges(time_figure_layout)


def update_on_view_x_range_change(attrname, old, new):
    """Update view_period widget when view_x_range changes."""
    #logger.debug(inspect.stack()[0][3])

    start, end = view_x_range_as_datetime()
    view_x_range.reset_start = start
    view_x_range.reset_end = end

    view_period.value = (start, end)


def press_up_event(event=None):
    update_time_series_sources()

    # updating the figure_layout y_ranges
    time_figure_widget.update_time_series_y_ranges(time_figure_layout)

"""
We initialize the dataclass
"""

now = datetime.now()
logger = import_logger(log_dir=LOG_DIR)
data = Data(logger=logger, now=now)

"""
We define all sources used in this main document
"""

locations_source = sources.locations_source()
locations_source.selected.on_change("indices", update_on_locations_source_select)
time_series_sources = sources.time_series_sources
search_source = sources.time_series_template()

"""
In this section we define all widgets. We pass callbacks and sources to every widget
"""

# Filters widget
on_change = [("value", update_on_filter_value)]
filters = filters_widgets.make_filters(data=data.filters, on_change=on_change)

# Locations widget
on_change = [("value", update_on_locations_value)]
locations = filters_widgets.make_filter(data=data.locations, on_change=on_change)

# Parameters widget
on_change = [("value", update_on_parameters_value)]
parameters = filters_widgets.make_filter(data=data.parameters, on_change=on_change)

# Search period widget
on_change = [("value", update_on_search_period_value)]
search_period = search_period_widget.make_search_period(data.periods, on_change=on_change)


# Update graph widget
update_graph = update_graph_widget.make_update_graph(update_graph_title[LANG])
update_graph.on_click(start_time_series_loader)

# Map figure widget
map_figure = map_figure_widget.make_map(
    bounds=BOUNDS, locations_source=locations_source, map_overlays=MAP_OVERLAYS
)

# Map options widget
map_options = map_figure_widget.make_options(
    map_overlays=MAP_OVERLAYS,
    overlays_change=update_map_figure_overlay_control,
    background_title="Achtergrond",
    background_change=update_map_figure_background_control,
)

# Status widget
app_status = Div(text=data.app_status(html_type=HTML_TYPE))

# Time figure widget
view_x_range = time_figure_widget.make_x_range(data.periods, graph="top_figs")
view_x_range.on_change("end", update_on_view_x_range_change)
view_x_range.on_change("start", update_on_view_x_range_change)

time_figure = time_figure_widget.empty_fig()

# Search time series widget
search_time_series = Select(value=None, options=[])
search_time_series.on_change("value", update_on_search_time_series_value)

# Search download search time series widget
download_search_time_series = download_widget.make_button(source=search_source)

# View period widget
view_period = view_period_widget.make_view_period(data.periods)
view_period.on_change("value", update_on_view_period_value)
view_period.on_change("value_throttled", update_on_view_period_value_throttled)
view_period.js_link("value_throttled", view_x_range, "start", attr_selector=0)
view_period.js_link("value_throttled", view_x_range, "end", attr_selector=1)

# Search time figure widget
search_x_range = time_figure_widget.make_x_range(data.periods, graph="search_fig")
search_time_figure = time_figure_widget.empty_fig()

"""
In this section we add all widgets to the curdoc
"""
# left column layout
curdoc().add_root(column(column(Div(text=f"<h3>{TITLE}</h3>")), name="app_title", sizing_mode="stretch_width"))
curdoc().add_root(column(filters, name="filters", sizing_mode="stretch_width"))
curdoc().add_root(column(locations, name="locations", sizing_mode="stretch_width"))
curdoc().add_root(column(parameters, name="parameters", sizing_mode="stretch_width"))
curdoc().add_root(
    column(search_period, name="search_period", sizing_mode="stretch_both")
)
curdoc().add_root(
    column(update_graph, name="update_graph", sizing_mode="stretch_width")
)

# map-figure layout
curdoc().add_root(column(map_figure, name="map_figure", sizing_mode="stretch_both"))
curdoc().add_root(column(map_options, name="map_options", sizing_mode="stretch_both"))
curdoc().add_root(column(app_status, name="app_status", sizing_mode="stretch_both"))

# time-figure layout
time_figure_layout = column(time_figure, name="time_figure", sizing_mode="stretch_both")
curdoc().add_root(time_figure_layout)
curdoc().add_root(
    column(
        search_time_series, name="select_search_time_series", sizing_mode="stretch_both"
    )
)
curdoc().add_root(
    column(
        download_search_time_series,
        name="download_search_time_series",
        sizing_mode="stretch_width",
    )
)
curdoc().add_root(column(view_period, name="view_period", sizing_mode="stretch_both"))
search_time_figure_layout = column(search_time_figure, name="search_time_figure", sizing_mode="stretch_both")
curdoc().add_root(search_time_figure_layout)


curdoc().title = TITLE