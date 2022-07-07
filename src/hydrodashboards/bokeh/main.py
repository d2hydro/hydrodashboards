"""Bokeh HydroDashboard"""

from bokeh.io import curdoc
from bokeh.layouts import column
from data import Data
from config import TITLE, BOUNDS, MAP_OVERLAYS

# import bokeh sources
import hydrodashboards.bokeh.sources as sources
from hydrodashboards.bokeh.widgets import (
    time_figure_widget,
    map_figure_widget,
    filters_widgets,
    search_period_widget,
    update_graph_widget,
)
from bokeh.models.widgets import Div
from hydrodashboards.bokeh.log_utils import import_logger
import inspect

from hydrodashboards.bokeh.language import update_graph_title

import time

LANG = "dutch"

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

    # update app status
    app_status.text = data.app_status


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
    app_status.text = data.app_status


def update_on_parameters_value(attrname, old, new):
    """Update when values in locations filter are selected"""
    logger.debug(inspect.stack()[0][3])

    # update datemodel
    data.parameters.value = parameters.value

    # update app status
    app_status.text = data.app_status


def update_map_figure_background_control(attrname, old, new):
    """Update map_figure when background is selected"""
    logger.debug(inspect.stack()[0][3])
    tile_source = map_figure_widget.get_tilesource(map_options.children[3].labels[new])
    idx = next(
        idx for idx, i in enumerate(map_figure.renderers) if i.name == "background"
    )
    map_figure.renderers[idx].tile_source = tile_source


def update_map_figure_overlay_control(attrname, old, new):
    """Update visible map-overlays on change"""
    logger.debug(inspect.stack()[0][3])
    map_overlays = map_options.children[1]
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
    logger.debug(inspect.stack()[0][3])
    update_graph.css_classes = ["loader_time_fig"]
    curdoc().add_next_tick_callback(update_time_series)


def update_time_series():
    """Update time_series and stop time_fig_loader"""
    logger.debug(inspect.stack()[0][3])
    data.update_time_series()
    time.sleep(2)
    print(len(data.time_series_sets.time_series))
    update_graph.css_classes = ["stoploading_time_fig"]


"""
We initialize the dataclass
"""

logger = import_logger()
data = Data(logger=logger)

"""
We define all sources used in this main document
"""

locations_source = sources.locations_source()
locations_source.selected.on_change("indices", update_on_locations_source_select)

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
search_period = search_period_widget.make_search_period(data.periods)

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
    overlays_title="Kaartlagen",
    overlays_change=update_map_figure_overlay_control,
    background_title="Achtergrond",
    background_change=update_map_figure_background_control,
)

# Status widget
app_status = Div(text=data.app_status)

# Time figure widget
time_figure = time_figure_widget.empty_fig()

# Search time series widget
search_time_series = data.select_search_time_series.bokeh

# Search download search time series widget
download_search_time_series = data.download_search_time_series.bokeh

# View period widget
view_period = data.view_period.bokeh

# Search time figure widget
search_time_figure = time_figure_widget.empty_fig()

"""
In this section we add all widgets to the curdoc
"""
# left column layout
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
curdoc().add_root(column(time_figure, name="time_figure", sizing_mode="stretch_both"))
curdoc().add_root(search_time_series)
curdoc().add_root(download_search_time_series)
curdoc().add_root(view_period)
curdoc().add_root(column(search_time_figure, name="search_time_figure", sizing_mode="stretch_both"))

curdoc().title = TITLE
