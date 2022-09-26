"""Bokeh HydroDashboard"""

from bokeh.io import curdoc
from bokeh.layouts import column
try:
    from data import Data
    from config import Config
except:
    from hydrodashboards.bokeh.data import Data
    from hydrodashboards.bokeh.config import Config
from pathlib import Path
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
    thresholds_widget,
)
from bokeh.models.widgets import Div, Select
from hydrodashboards.bokeh.log_utils import import_logger
import inspect

from hydrodashboards.bokeh.language import update_graph_title

from datetime import datetime, timedelta
import pandas as pd

LANG = "dutch"
HTML_TYPE = "table"


"""
Supporting functions
"""


def toggle_view_time_series_controls(value=True):
    """Enable view period (used when first graph is loaded)."""
    view_period.disabled = value
    view_period.bar_color = "#e6e6e6"
    download_time_series.disabled = value


def toggle_download_button_on_sources(sources):
    if len(sources) == 0:
        disabled = True
        max_events_visible = 0
    else:
        max_events_visible = max((len(i.data["value"]) for i in sources))
        if max_events_visible > 1000000:
            disabled = True
        else:
            disabled = False
    data.time_series_sets.max_events_visible = max_events_visible
    download_time_series.disabled = disabled


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


def get_visible_renderers(figs):
    renderers = (j for i in [i.renderers for i in figs] for j in i)
    return [i for i in renderers if i.visible]


def get_visible_sources(figs):
    renderers = get_visible_renderers(figs)
    return [i.data_source for i in renderers]


def value_as_datetime(value):
    ''' Convenience property to retrieve the value tuple as a tuple of
    datetime objects.

    Added in version 1.1
    '''
    if value is None:
        return None
    v1, v2 = value
    if isinstance(v1, float):
        v1 = datetime.utcfromtimestamp(v1 / 1000)
    if isinstance(v2, float):
        v1 = datetime.utcfromtimestamp(v2 / 1000)
    return v1, v2

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
    if len(ids) > 10:
        ids.sort()
        ids = ids[:10]

    # update locations and data.locations value
    locations.value = ids


def update_on_locations_value(attr, old, new):
    """Update when values in locations filter are selected"""
    logger.debug(inspect.stack()[0][3])

    # limit to max 10 locations
    if len(new) > 10:
        locations.value = old

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
    # data.time_series_sets.time_series = []
    enable_update_graph()
    # update data.periods for next purpose
    data.periods.set_search_period(search_start, search_end)

    # update widgets
    view_period_widget.update_view_period(view_period, data.periods)
    search_x_range.start = data.periods.search_start
    search_x_range.end = data.periods.search_end
    view_x_range.bounds = (data.periods.search_start, data.periods.search_end)
    view_x_range.start, view_x_range.end = data.periods.view_start, data.periods.view_end

    # update sources
    update_time_series_sources()

    # updating the figure_layout y_ranges
    time_figure_widget.update_time_series_y_ranges(time_figure_layout)

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
    logger.debug(inspect.stack()[0][3])
    update_graph.css_classes = ["loader_time_fig"]

    # disable view_period
    toggle_view_time_series_controls(value=True)

    # now we go downloading a view
    curdoc().add_next_tick_callback(update_time_series_view)


def update_time_series_view():
    """Update time_series and stop time_fig_loader"""
    global time_series_sources # we update the global variable time_series_sources

    logger.debug(inspect.stack()[0][3])
    data.update_time_series()

    # update time_series_layout (top figures)
    parameter_groups = data.parameters.get_groups()
    time_series_groups = data.time_series_sets.by_parameter_groups(
        parameter_groups,
        active_only=True
        )

    threshold_groups = data.threshold_groups(time_series_groups)

    if config.thresholds:
        thresholds_active = thresholds_button.active
    else:
        thresholds_active = False
    time_series_sources = time_figure_widget.create_time_figures(
        time_figure_layout=time_figure_layout,
        time_series_groups=time_series_groups,
        threshold_groups=threshold_groups,
        threshold_visible=thresholds_active,
        x_range=view_x_range,
        press_up_event=press_up_event,
        renderers_on_change=[("visible", set_visible_labels)]
        )

    # update search_time_series
    search_time_series.options = data.time_series_sets.active_labels
    if search_time_series.value not in search_time_series.options:
        search_time_series.value = search_time_series.options[0]

    # add_search time_series
    _time_series = data.time_series_sets.get_by_label(search_time_series.value)
    time_figure_widget.search_fig(
        search_time_figure_layout,
        time_series=_time_series,
        x_range=search_x_range,
        periods=data.periods,
        color=time_series_sources[search_time_series.value]["color"],
        search_source=search_source
        )

    # update app status
    app_status.text = data.app_status(html_type=HTML_TYPE)

    # go to the next callback
    curdoc().add_next_tick_callback(update_time_series_search)


def update_time_series_search():

    logger.debug(inspect.stack()[0][3])
    # update full history of all non-complete time-series
    data.update_time_series_search()

    # updating the sources in the used as glyph data_sources
    update_time_series_sources()

    # updating the figure_layout y_ranges
    time_figure_widget.update_time_series_y_ranges(time_figure_layout)

    # enable view_timeseries_controls
    toggle_view_time_series_controls(value=False)
    sources = [i["source"] for i in time_series_sources.values()]
    toggle_download_button_on_sources(sources)

    # update app status
    app_status.text = data.app_status(html_type=HTML_TYPE)

    # stop loader and disable update_graph
    update_graph.css_classes = ["stoploading_time_fig"]
    update_graph.disabled = True


def update_on_search_time_series_value(attrname, old, new):
    """Update source of search_time_figure when search_time_series_value changes"""
    logger.debug(inspect.stack()[0][3])

    # change search time_series
    time_figure_widget.search_fig(search_time_figure_layout,
                                  time_series=data.time_series_sets.get_by_label(
                                      label=search_time_series.value
                                      ),
                                  x_range=search_x_range,
                                  periods=data.periods,
                                  color=time_series_sources[
                                      search_time_series.value
                                      ]["color"],
                                  search_source=search_source)


def update_on_view_period_value(attrname, old, new):
    """Update periods when view_period value changes"""
    #logger.debug(inspect.stack()[0][3])

    is_moving = all((new[0] != old[0], new[1] != old[1]))
    if is_moving:
        force = True
    else:
        force = False
    values_accepted = data.periods.set_view_period(*view_period.value_as_datetime, force)
    if not values_accepted:
        view_period.value = (data.periods.view_start, data.periods.view_end)

    # update patch source
    if type(search_time_figure_layout.children[0]) != Div:
        search_time_figure_layout.children[0].renderers[0].data_source.data.update(
            sources.view_period_patch_source(data.periods).data)


def update_on_view_period_value_throttled(attrname, old, new):
    """Update time_series_sources as view_x_range"""
    logger.debug(inspect.stack()[0][3])

    view_x_range.start, view_x_range.end = (data.periods.view_start, data.periods.view_end)

    update_time_series_sources()
    # updating the figure_layout y_ranges
    time_figure_widget.update_time_series_y_ranges(time_figure_layout, fit_y_axis=True)
    # toggle download button
    figs = time_figure_layout.children[0].children
    toggle_download_button_on_sources(get_visible_sources(figs))

    # update patch source
    if type(search_time_figure_layout.children[0]) != Div:
        search_time_figure_layout.children[0].renderers[0].data_source.data.update(
            sources.view_period_patch_source(data.periods).data)

    # update app status
    app_status.text = data.app_status(html_type=HTML_TYPE)


def update_on_view_x_range_change(attrname, old, new):
    """Update view_period widget when view_x_range changes."""
    #logger.debug(inspect.stack()[0][3])

    start, end = view_x_range_as_datetime()
    view_x_range.reset_start = start
    view_x_range.reset_end = end

    view_period.value = (start, end)


def press_up_event(event=None):
    logger.debug(inspect.stack()[0][3])
    update_time_series_sources()

    # updating the figure_layout y_ranges
    time_figure_widget.update_time_series_y_ranges(time_figure_layout)


def toggle_thresholds(active):
    logger.debug(inspect.stack()[0][3])
    time_figure_widget.toggle_threshold_graphs(time_figure_layout, active)


def set_visible_labels(attr, old, new):
    """Get the max length of sources in active glyphs."""
    logger.debug(inspect.stack()[0][3])
    figs = time_figure_layout.children[0].children

    # sync visible data
    renderers = get_visible_renderers(figs)
    labels = [i.data_source.name for i in renderers]
    data.time_series_sets.set_visible(labels=labels)

    # enable/disable download button
    sources = [i.data_source for i in renderers]
    toggle_download_button_on_sources(sources)

    # update app status
    app_status.text = data.app_status(html_type=HTML_TYPE)


"""
We read the config
"""

config = Config.from_json(Path(__file__).parent.joinpath("config.json"))

"""
We initialize the dataclass
"""

now = datetime.now()
logger = import_logger(log_dir=config.log_dir)
data = Data(logger=logger, now=now, config=config)

"""
We define all sources used in this main document
"""

locations_source = sources.locations_source()
locations_source.selected.on_change("indices", update_on_locations_source_select)
time_series_sources = sources.time_series_sources()
search_source = sources.time_series_template()

"""
In this section we define all widgets. We pass callbacks and sources to every widget
"""

# Filters widget
on_change = [("value", update_on_filter_value)]
filters = filters_widgets.make_filters(data=data.filters, on_change=on_change, filter_type=config.filter_type)

# Locations widget
on_change = [("value", update_on_locations_value)]
locations = filters_widgets.make_filter(data=data.locations, on_change=on_change, filter_type=config.filter_type)

# Parameters widget
on_change = [("value", update_on_parameters_value)]
parameters = filters_widgets.make_filter(data=data.parameters, on_change=on_change, filter_type=config.filter_type)

# Search period widget
on_change = [("value", update_on_search_period_value)]
search_period = search_period_widget.make_search_period(data.periods, on_change=on_change)


# Update graph widget
update_graph = update_graph_widget.make_update_graph(update_graph_title[LANG])
update_graph.on_click(start_time_series_loader)

# Map figure widget
map_figure = map_figure_widget.make_map(
    bounds=config.bounds, locations_source=locations_source, map_overlays=config.map_overlays
)

# Map options widget
map_options = map_figure_widget.make_options(
    map_overlays=config.map_overlays,
    overlays_change=update_map_figure_overlay_control,
    background_title="Achtergrond",
    background_change=update_map_figure_background_control,
)

# Status widget
app_status = Div(text=data.app_status(html_type=HTML_TYPE))

# Thresholds widget
if config.thresholds:
    thresholds_button = thresholds_widget.make_button(toggle_thresholds)

# Time figure widget
view_x_range = time_figure_widget.make_x_range(data.periods, graph="top_figs")
view_x_range.on_change("end", update_on_view_x_range_change)
view_x_range.on_change("start", update_on_view_x_range_change)

time_figure = time_figure_widget.empty_fig()

# Search time series widget
search_time_series = Select(value=None, options=[])
search_time_series.on_change("value", update_on_search_time_series_value)

# Search download search time series widget
#download_search_time_series = download_widget.make_button(source=search_source)

# View period widget
view_period = view_period_widget.make_view_period(data.periods)
view_period.on_change("value", update_on_view_period_value)
view_period.on_change("value_throttled", update_on_view_period_value_throttled)
#view_period.js_link("value_throttled", view_x_range, "start", attr_selector=0)
#view_period.js_link("value_throttled", view_x_range, "end", attr_selector=1)

# Search time figure widget
search_x_range = time_figure_widget.make_x_range(data.periods, graph="search_fig")
search_time_figure = time_figure_widget.empty_fig()

"""
In this section we add all widgets to the curdoc
"""


# left column layout
curdoc().add_root(column(Div(text=f"<h3>{config.title}</h3>"),
                         name="app_title",
                         sizing_mode="stretch_width"))

filters_layout = column(filters, name="filters", sizing_mode="stretch_width")
if config.filter_type == "MultiSelect":
    filters_widgets.clear_control(filters_layout)
curdoc().add_root(filters_layout)
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
if config.thresholds:
    curdoc().add_root(
        column(thresholds_button, name="thresholds_button", sizing_mode="stretch_both")
        )

time_figure_layout = column(time_figure, name="time_figure", sizing_mode="stretch_both")
curdoc().add_root(time_figure_layout)


download_time_series = download_widget.make_button(time_figure_layout=time_figure_layout)
curdoc().add_root(
    column(download_time_series,
           name="download_time_series",
           sizing_mode="stretch_width")
    )

# search tim-figure layout
curdoc().add_root(
    column(
       search_time_series, name="select_search_time_series", sizing_mode="stretch_both"
    )
)
curdoc().add_root(column(view_period, name="view_period", sizing_mode="stretch_both"))
search_time_figure_layout = column(search_time_figure, name="search_time_figure", sizing_mode="stretch_both")
curdoc().add_root(search_time_figure_layout)

curdoc().title = config.title

"""
In this section we parse all url parameters
"""


def locations_in_filter(location_ids, filter_id):
    return data.locations.sets[filter_id].index.isin(location_ids).any()

def convert_to_datetime(date_time):
    try:
        return datetime.strptime(date_time, "%Y-%m-%d")
    except ValueError:
        return None


try:
    if config.filter_type == "MultiSelect":
        args = curdoc().session_context.request.arguments
        start_date, end_date = view_period.value_as_datetime
        update_period = False
        if "filter_id" in args.keys():
            filter_ids = [i.decode("utf-8") for i in args.get("filter_id")]
            filters_widgets.set_filter_values(filters, filter_ids)
    
        if "location_id" in args.keys():
            location_ids = [i.decode("utf-8") for i in args.get("location_id")]
            if "filter_id" not in args.keys():
                # get all filters in cache
                data.update_on_filter_select(data.filters.values)
                # get and select the filter ids that contain one or more location_ids
                filter_ids = [i for i in data.filters.values if locations_in_filter(location_ids, i)]
                filters_widgets.set_filter_values(filters, filter_ids)
    
            # make sure there is no rubbish and set loction_ids
            location_ids = [j for j in location_ids if j in [i[0] for i in locations.options]]
            locations.value = location_ids
        if "parameter_id" in args.keys():
            parameter_ids = [i.decode("utf-8") for i in args.get("parameter_id")]
            parameter_ids = [j for j in parameter_ids if j in [i[0] for i in parameters.options]]
            parameters.value = parameter_ids
        if "start_date" in args.keys():
            start_date = convert_to_datetime(args.get("start_date")[0].decode("utf-8"))
            update_period = True
        if "end_date" in args.keys():
            end_date = convert_to_datetime(args.get("end_date")[0].decode("utf-8"))
            update_period = True
        if update_period:
            end_date = min(data.periods.view_end, end_date)
            if start_date < end_date:
                search_start = start_date - timedelta(days=1)
                search_end = min(start_date - timedelta(days=1), data.periods.search_end)
                data.periods.set_search_period(search_start, search_end)
                data.periods.set_view_period(start_date, end_date)
                view_period.value = (data.periods.view_start, data.periods.view_end)
    
        if (len(locations.value) > 0) & (len(parameters.value) > 0):
            start_time_series_loader()


except AttributeError as e:
    logger.error(f"reading args failed with error: {e}")
    pass
