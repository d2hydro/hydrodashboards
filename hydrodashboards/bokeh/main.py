"""Bokeh HydroDashboard"""

from bokeh.io import curdoc
from bokeh.layouts import column

try:
    from data import Data
    from config import Config
    from pathlib import Path
    from log_utils import import_logger

    CONFIG_JSON = Path(__file__).parent.joinpath("config.json")
except ImportError:
    from hydrodashboards.bokeh.data import Data
    from hydrodashboards.bokeh.config import Config
    from hydrodashboards.bokeh.log_utils import import_logger
    from hydrodashboards.bokeh import CONFIG_JSON

# import bokeh sources
import hydrodashboards.bokeh.sources as sources
from hydrodashboards.bokeh.widgets import (
    download_widget,
    filters_widgets,
    map_figure_widget,
    search_period_widget,
    save_widget,
    thresholds_widget,
    time_figure_widget,
    update_graph_widget,
    view_period_widget,
    ghost_buttons,
)

from bokeh.models.widgets import Div, Select

import inspect


from hydrodashboards.bokeh.language import update_graph_title

from datetime import datetime, timedelta
import pandas as pd

LANG = "dutch"
HTML_TYPE = "table"


"""
Supporting functions
"""


def filters_on_change():
    if config.thematic_view:
        on_change = {
            "themes": [update_on_theme_selector],
            "filters": [update_on_filter_selector],
        }
    else:
        on_change = [update_on_filter_selector]
    return on_change


def toggle_view_time_series_controls(value=True):
    """Enable view period (used when first graph is loaded)."""
    view_period.disabled = value
    view_period.bar_color = "#e6e6e6"
    download_time_series_csv.disabled = value
    download_time_series_xls.disabled = value
    save_time_series.disabled = value
    history_search_time_series.disabled = value
    search_time_series.disabled = value


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
    download_time_series_csv.disabled = disabled
    download_time_series_xls.disabled = disabled
    save_time_series.disabled = disabled
    history_search_time_series.disabled = disabled
    search_time_series.disabled = disabled


def enable_update_graph():
    """Enable update_graph if locations ánd paramters are selected."""
    if all(
        (len(getattr(i, config.filter_selector)) > 0 for i in (locations, parameters))
    ):
        update_graph.disabled = False
    else:
        update_graph.disabled = True


def update_time_series_sources():
    """Update of time_series_sources assigned to top_figs."""
    start, end = view_x_range_as_datetime()
    for k, v in time_series_sources.items():
        time_series = data.time_series_sets.get_by_label(k)
        _source = sources.time_series_to_source(
            time_series=time_series,
            start_date_time=start,
            end_date_time=end,
            unreliables=False,
            sample_config=config.time_series_sampling,
        )
        v["source"].data.update(_source.data)


def update_search_time_series_source():
    """Update search source assigned to search_fig"""
    time_series = data.time_series_sets.get_by_label(search_time_series.value)

    _source = sources.time_series_to_source(
        time_series, sample_config=search_sample_config
    )
    search_source.data.update(_source.data)


def _to_timestamp(i):
    if isinstance(i, (float, int)):
        return pd.Timestamp(i * 10**6)
    else:
        return i


def view_x_range_as_datetime():
    """Get the view_x_range start and end as datetime."""

    start = _to_timestamp(view_x_range.start)
    end = _to_timestamp(view_x_range.end)

    return start, end


def get_visible_renderers(figs):
    renderers = (j for i in [i.renderers for i in figs] for j in i)
    return [i for i in renderers if i.visible]


def get_visible_sources(figs):
    renderers = get_visible_renderers(figs)
    return [i.data_source for i in renderers]


def order_filter(bokeh_filter, filter_cls, active=None):
    if active is None:
        active = list(bokeh_filter.active)
    ordered = False

    # case when no filter-values are active
    if len(active) == 0:
        filter_cls.order_options([])
        bokeh_filter.labels = filter_cls.labels
    # case when all are active
    elif not (max(active) == len(active) - 1):
        ordered = True
        filter_cls.order_options(active)
        bokeh_filter.labels = filter_cls.labels
        bokeh_filter.active = filter_cls.active
    # case where we miss labels
    elif len(bokeh_filter.labels) != len(filter_cls.labels):
        bokeh_filter.labels = filter_cls.labels
    return ordered


def report_state():
    logger.debug(
        (
            f"filters: {data.filters.value(thematic_view=config.thematic_view)}",
            f"locations: {data.locations.value}",
            f"parameters: {data.parameters.value}",
        )
    )


"""
All callbacks used in the app
"""


# callbacks
def update_on_theme_selector(attr, old, new):
    """Updates filters in filters filter when filters filter is updated"""
    logger.debug(inspect.stack()[0][3])

    filters_filter = filters[1]
    # get labels
    options, _, labels = data.filters.get_filter_options(active=new)

    active_labels = [filters_filter.labels[i] for i in filters_filter.active]

    # update data
    data.filters.thematic_filters[1].options = options

    # set filters_filter
    filters_filter.labels = labels
    filters_filter.active = [labels.index(i) for i in active_labels if i in labels]


def update_on_filter_selector(attrname, old, new):
    """Updates locations values in locations filter when filters filter is updated"""
    logger.debug(inspect.stack()[0][3])

    actives = filters_widgets.get_filters_actives(filters, config.thematic_view)
    data.update_on_filter_select(actives)
    locations.labels = data.locations.labels
    parameters.labels = data.parameters.labels
    parameters.active = data.parameters.active
    # update source
    locations_source.data = data.locations.map_locations

    # update selected
    indices = [locations_source.data["id"].index(i) for i in data.locations.value]
    locations_source.selected.indices = indices

    # update app status
    app_status.text = data.app_status(html_type=HTML_TYPE)

    logger.debug(f"{inspect.stack()[0][3]} finished")

    if locations.active != data.locations.active:
        curdoc().add_next_tick_callback(sync_locations_active_with_data)


def sync_locations_active_with_data():
    """Next tick callback to sync locations.active with data.locations.active."""
    logger.debug(inspect.stack()[0][3])
    locations.active = data.locations.active


def update_on_locations_source_select(attr, old, new):
    """Update locations values in locations filter when locations_source is selected"""
    logger.debug(inspect.stack()[0][3])

    # get selected ids
    ids = [locations_source.data["id"][i] for i in locations_source.selected.indices]

    if len(ids) > 10:
        ids.sort()
        ids = ids[:10]
        locations_source.selected.indices = [
            locations_source.data["id"].index(i) for i in ids
        ]
    else:
        options_ids = [i[0] for i in data.locations.options]
        active = [options_ids.index(i) for i in ids]

        if active:
            order_filter(locations, data.locations, active=active)
        else:
            locations.active = []


def update_location_options_on_search_input(attr, old, new):
    if len(new) >= 3:
        data.locations.limit_options_on_search_input(new)
        locations.labels = data.locations.labels
        locations_source.data.update(
            data.locations.app_df.loc[[i[0] for i in data.locations.options]]
            .reset_index()
            .to_dict(orient="list")
        )
    else:
        data.locations.search_input = None
        if len(old) >= 3:
            unselected_options = [
                i
                for i in data.locations._options
                if i not in data.locations.selected_options
            ]
            data.locations.options = data.locations.selected_options + unselected_options
            locations.labels = data.locations.labels
            
            locations_source.data.update(
                data.locations.app_df.loc[[i[0] for i in data.locations.options]]
                .reset_index()
                .to_dict(orient="list")
            )


def update_on_locations_selector(attr, old, new):
    """Update when values in locations filter are selected"""
    logger.debug(inspect.stack()[0][3])

    # disable search if locations are selected
    if len(new) > 0:
        locations_layout[0].children[-1].disabled = True
    else:
        locations_layout[0].children[-1].disabled = False

    # limit selected locations to max 10
    if len(new) > 10:
        setattr(locations, config.filter_selector, old)

    # order filter so selected come on top (will introduce a new callback)
    filter_ordered = order_filter(locations, data.locations)

    if not filter_ordered:
        # update datamodel
        data.locations.set_active(locations.active)
        data.update_on_locations_select(data.locations.value)

        # update parameters options for (de)selected locations
        if len(new) == 0:
            actives = filters_widgets.get_filters_actives(filters, config.thematic_view)
            data.update_on_filter_select(actives)
            data.parameters.limit_options_on_search_input()
            parameters.active = []
            parameters.active = data.parameters.active
            parameters.labels = data.parameters.labels
            parameters.disabled = True
        else:
            order_filter(parameters, data.parameters, active=data.parameters.active)
            parameters.disabled = False

        # update location source selected
        indices = [
            list(locations_source.data["id"]).index(i) for i in data.locations.value
        ]
        locations_source.selected.indices = indices

        # update app status
        app_status.text = data.app_status(html_type=HTML_TYPE)

        # enable update_graph button
        enable_update_graph()


def update_parameter_options_on_search_input(attr, old, new):
    if len(new) >= 3:
        data.parameters.limit_options_on_search_input(new)
        parameters.labels = data.parameters.labels
    else:
        data.parameters.search_input = None
        if len(old) >= 3:
            data.parameters.set_options()
            parameters.labels = data.parameters.labels


def update_on_parameters_selector(attrname, old, new):
    """Update when values in locations filter are selected"""
    logger.debug(inspect.stack()[0][3])

    # order filter so selected come on top (will introduce a new callback)
    filter_ordered = order_filter(parameters, data.parameters)

    if not filter_ordered:
        data.parameters.set_active(parameters.active)

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
    view_x_range.start, view_x_range.end = (
        data.periods.view_start,
        data.periods.view_end,
    )

    # update sources
    update_time_series_sources()

    # updating the figure_layout y_ranges
    time_figure_widget.update_time_series_y_ranges(time_figure_layout)

    # update app status
    app_status.text = data.app_status(html_type=HTML_TYPE)


def update_on_history_search_time_series():
    """Get full history for search time series"""
    logger.debug(inspect.stack()[0][3])

    # get data for the full period
    df = data.update_history_time_series_search(search_time_series.value)

    # update search_source
    search_source.data.update(
        sources.df_to_source(df, sample_config=search_sample_config).data
    )

    # update search_period
    search_start, search_end = data.get_history_period(search_source.data["datetime"])
    search_period_widget.update_period(search_period, search_start, search_end)

    # update search_time_figure y-range
    time_figure_widget.update_search_time_series_y_ranges(search_time_figure_layout)

    # kick of time series loader
    curdoc().add_next_tick_callback(start_time_series_loader)


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

    # report app-state
    report_state()

    # disable view_period
    toggle_view_time_series_controls(value=True)
    _scale_graphs.disabled = False

    # now we go downloading a view
    curdoc().add_next_tick_callback(update_time_series_view)


def update_time_series_view():
    """Update time_series and stop time_fig_loader"""
    global time_series_sources  # we update the global variable time_series_sources
    logger.debug(inspect.stack()[0][3])  # Log the function name
    data.update_time_series()

    if data.time_series_sets.any_active:
        # update time_series_layout (top figures)
        parameter_groups = data.parameters.get_groups()   
        group_y_labels = data.parameters.get_y_labels(config.vertical_datum)
        time_series_groups = data.time_series_sets.by_parameter_groups(
            parameter_groups, active_only=True
        )
        
        threshold_groups = data.threshold_groups(time_series_groups)

        if config.thresholds:
            thresholds_active = thresholds_button.active
        else:
            thresholds_active = False

        time_series_sources = time_figure_widget.create_time_figures(
            time_figure_layout=time_figure_layout,
            time_series_groups=time_series_groups,
            group_y_labels=group_y_labels,
            threshold_groups=threshold_groups,
            threshold_visible=thresholds_active,
            x_range=view_x_range,
            press_up_event=press_up_event,
            renderers_on_change=[("visible", set_visible_labels)],
            sample_config=config.time_series_sampling,
            step_enumeration=config.step_enumeration
        )


        # update search_time_series
        search_time_series.options = data.time_series_sets.active_labels
        if search_time_series.value not in search_time_series.options:
            search_time_series.value = search_time_series.options[0]

        # add_search time_series
        _time_series = data.time_series_sets.get_by_label(search_time_series.value)

        step_mode = any(pattern in search_time_series.value for pattern in config.step_enumeration.keys())
        
        time_figure_widget.search_fig(
            search_time_figure_layout,
            time_series=_time_series,
            x_range=search_x_range,
            periods=data.periods,
            patch_source=patch_source,
            color=time_series_sources[search_time_series.value]["color"],
            search_source=search_source,
            sample_config=config.time_series_sampling,
            step_mode=step_mode
        )

        _scale_graphs.disabled = True

        # enable view_timeseries_controls
        toggle_view_time_series_controls(value=False)
        sources = [i["source"] for i in time_series_sources.values()]
        toggle_download_button_on_sources(sources)
        
        # update app status
        app_status.text = data.app_status(html_type=HTML_TYPE)
    else:
        warning = "no time series for selected locations and parameters"
        time_figure_widget.warning_figure(time_figure_layout, warning)
        time_figure_widget.warning_figure(search_time_figure_layout, warning)

    # stop loader and disable update_graph
    update_graph.css_classes = ["stoploading_time_fig"]
    update_graph.disabled = True

    # update app status
    app_status.text = data.app_status(html_type=HTML_TYPE)



def update_on_search_time_series_value(attrname, old, new):
    """Update source of search_time_figure when search_time_series_value changes"""
    logger.debug(inspect.stack()[0][3])
    # Determine if step_mode should be True based on keywords in search_time_series.value
    step_mode = any(pattern in search_time_series.value for pattern in config.step_enumeration.keys())

    # change search time_series
    time_figure_widget.search_fig(
        search_time_figure_layout,
        time_series=data.time_series_sets.get_by_label(label=search_time_series.value),
        x_range=search_x_range,
        periods=data.periods,
        patch_source=patch_source,
        color=time_series_sources[search_time_series.value]["color"],
        search_source=search_source,
        sample_config=config.time_series_sampling,
        step_mode=step_mode
    )


def update_on_view_period_value_throttled(attrname, old, new):
    """Update time_series_sources as view_x_range"""
    logger.debug(inspect.stack()[0][3])

    is_moving = all((new[0] != old[0], new[1] != old[1]))
    values_accepted = data.periods.set_view_period(
        *view_period.value_as_datetime, is_moving
    )
    if not values_accepted:
        view_period.value = (data.periods.view_start, data.periods.view_end)

    view_x_range.start, view_x_range.end = (
        data.periods.view_start,
        data.periods.view_end,
    )

    update_time_series_sources()
    # updating the figure_layout y_ranges
    time_figure_widget.update_time_series_y_ranges(time_figure_layout, fit_y_axis=True)
    # toggle download button
    figs = time_figure_layout.children[0].children
    toggle_download_button_on_sources(get_visible_sources(figs))

    # update app status
    app_status.text = data.app_status(html_type=HTML_TYPE)


def update_on_view_x_range_start_change(attrname, old, new):
    """Update view_period widget when view_x_range changes."""
    # logger.debug(inspect.stack()[0][3])

    if old != new:
        start = _to_timestamp(new)
        view_x_range.reset_start = start
        view_period.value = (start, view_period.value[1])


def update_on_view_x_range_end_change(attrname, old, new):
    """Update view_period widget when view_x_range changes."""
    # logger.debug(inspect.stack()[0][3])

    if old != new:
        end = _to_timestamp(new)
        view_x_range.reset_end = end
        view_period.value = (view_period.value[0], end)


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


""" def start_timeseries_downloader():
    logger.debug(inspect.stack()[0][3])

    # get all data in sourced
    update_time_series_sources()

    # trigger jscript downloading process
    _download_time_series.disabled = not _download_time_series.disabled """

def start_timeseries_downloader():
    """Start the timeseries downloading process for XLS."""
    logger.debug(inspect.stack()[0][3])

    # get all data in sourced
    update_time_series_sources()

    # trigger JavaScript downloading process for XLS
    _download_time_series_xls.disabled = not _download_time_series_xls.disabled

def start_csv_downloader():
    """Start the timeseries downloading process for CSV."""
    logger.debug(inspect.stack()[0][3])

    # get all data in sourced
    update_time_series_sources()

    # trigger JavaScript downloading process for CSV
    _download_time_series_csv.disabled = not _download_time_series_csv.disabled
"""
We read the config
"""

config = Config.from_json(CONFIG_JSON)
if config.time_series_sampling is not None:
    search_sample_config = {k: v for k, v in config.time_series_sampling.items()}
    search_sample_config["max_samples"] = 40000
else:
    search_sample_config = None

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
patch_source = sources.view_period_patch_source(data.periods)

"""
In this section we define all widgets. We pass callbacks and sources to every widget
"""

# Filters widget

filters = filters_widgets.make_filters(
    data=data.filters,
    on_change=filters_on_change(),
    thematic_view=config.thematic_view,
)

# Locations widget
on_change = [update_on_locations_selector]
locations = filters_widgets.make_filter(data=data.locations, on_change=on_change)

# Parameters widget
on_change = [update_on_parameters_selector]
parameters = filters_widgets.make_filter(
    data=data.parameters, on_change=on_change, disabled=True
)

# Search period widget
on_change = [("value", update_on_search_period_value)]
search_period = search_period_widget.make_search_period(
    data.periods, on_change=on_change
)


# Update graph widget
update_graph = update_graph_widget.make_update_graph(update_graph_title[LANG])
update_graph.on_click(start_time_series_loader)

# Map figure widget
map_figure = map_figure_widget.make_map(
    bounds=config.bounds,
    locations_source=locations_source,
    map_overlays=config.map_overlays,
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

# View period widget
view_period = view_period_widget.make_view_period(data.periods, patch_source)
view_period.on_change("value_throttled", update_on_view_period_value_throttled)

# Time figure widget
view_x_range = time_figure_widget.make_x_range(data.periods, graph="top_figs")
view_x_range.on_change("start", update_on_view_x_range_start_change)
view_x_range.on_change("end", update_on_view_x_range_end_change)

time_figure_layout = time_figure_widget.empty_layout(name="time_figure")

# Search time series widget
search_time_series = Select(
    value=None, options=[], css_classes=["select_search_time_series"]
)
search_time_series.on_change("value", update_on_search_time_series_value)


# Search time figure widget
search_x_range = time_figure_widget.make_x_range(data.periods, graph="search_fig")
search_time_figure_layout = time_figure_widget.empty_layout(name="search_time_figure")

# all buttons

#  download data
""" download_time_series = download_widget.make_button(on_click=start_timeseries_downloader)

_download_time_series = download_widget.make_ghost_button(
    time_figure_layout=time_figure_layout,
    disclaimer_file=config.disclaimer_file,
    graph_count=config.graph_count,
) """


# download data
download_time_series_xls = download_widget.make_button(on_click=start_timeseries_downloader)
download_time_series_csv = download_widget.make_button(on_click=start_csv_downloader)

_download_time_series_xls = download_widget.make_ghost_button_xls(
    time_figure_layout=time_figure_layout,
    disclaimer_file=config.disclaimer_file,
    graph_count=config.graph_count,
)

_download_time_series_csv = download_widget.make_ghost_button_csv(
    time_figure_layout=time_figure_layout,
    disclaimer_file=config.disclaimer_file,
    graph_count=config.graph_count,
)

#  save picture
save_time_series = save_widget.make_button()

# set full history for search time_series
history_search_time_series = search_period_widget.make_button(
    on_click=update_on_history_search_time_series
)


# button to scale top-figs to graph_count
_scale_graphs = ghost_buttons.make_button(
    time_figure_layout=time_figure_layout, graph_count=config.graph_count
)

"""
In this section we add all widgets to the curdoc
"""

# left column layout
curdoc().add_root(
    column(
        Div(text=f"<h3>{config.title}</h3>", css_classes=["app_title"]),
        name="app_title",
        sizing_mode="stretch_width",
    )
)

filters_widgets.add_css_classes(filters, locations, parameters)
filters_layout = filters_widgets.finish_filters(
    filters, thematic_view=config.thematic_view, reset_button=True
)
curdoc().add_root(filters_layout)

# search_input = update_location_options_on_search_input

locations_layout = filters_widgets.finish_filter(
    locations, search_input=update_location_options_on_search_input, reset_button=True
)
curdoc().add_root(
    column(locations_layout, name="locations", sizing_mode="stretch_width")
)


parameters_layout = filters_widgets.finish_filter(
    parameters, search_input=update_parameter_options_on_search_input, reset_button=True
)
curdoc().add_root(
    column(parameters_layout, name="parameters", sizing_mode="stretch_width")
)
curdoc().add_root(
    column(search_period, name="search_period", sizing_mode="stretch_both")
)
curdoc().add_root(
    column(update_graph, name="update_graph", sizing_mode="stretch_width")
)

""" curdoc().add_root(
    column(
        download_time_series, name="download_time_series", sizing_mode="stretch_width"
    )
)"""

curdoc().add_root(
    column(save_time_series, name="save_time_series", sizing_mode="stretch_width")
) 

curdoc().add_root(
    column(
        download_time_series_xls, name="download_time_series_xls", sizing_mode="stretch_width"
    )
)

curdoc().add_root(
    column(
        download_time_series_csv, name="download_time_series_csv", sizing_mode="stretch_width"
    )
)

curdoc().add_root(
    column(
        _download_time_series_xls,
        name="download_time_series_dummy_xls",
        sizing_mode="stretch_width",
    )
)

curdoc().add_root(
    column(
        _download_time_series_csv,
        name="download_time_series_dummy_csv",
        sizing_mode="stretch_width",
    )
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

curdoc().add_root(time_figure_layout)


# search time-figure layout
curdoc().add_root(
    column(
        history_search_time_series,
        name="history_search_time_series",
        sizing_mode="stretch_width",
    )
)

curdoc().add_root(
    column(
        search_time_series, name="select_search_time_series", sizing_mode="stretch_both"
    )
)

curdoc().add_root(column(view_period, name="view_period", sizing_mode="stretch_both"))
curdoc().add_root(search_time_figure_layout)

# add ghost buttons
curdoc().add_root(
    column(_scale_graphs, name="scale_graphs_dummy", sizing_mode="stretch_width")
)

""" curdoc().add_root(
    column(
        _download_time_series,
        name="download_time_series_dummy",
        sizing_mode="stretch_width",
    )
) """

curdoc().title = config.title

"""
In this section we parse all url parameters
"""


def locations_in_filter(location_ids, filter_id):
    return data.locations.sets.data[filter_id].index.isin(location_ids).any()


def convert_to_datetime(date_time):
    try:
        return datetime.strptime(date_time, "%Y-%m-%d")
    except ValueError:
        return None


def args_parser(args):
    start_date, end_date = view_period.value_as_datetime
    update_period = False
    # select filters
    if "filter_id" in args.keys():
        filter_ids = [i.decode("utf-8") for i in args.get("filter_id")]
        filters_widgets.set_filter_values(
            filters, filter_ids, config.thematic_view, data.filters
        )

    # select locations
    if "location_id" in args.keys():
        location_ids = [i.decode("utf-8") for i in args.get("location_id")]
        if "filter_id" not in args.keys():
            # get all filters in cache
            data.update_on_filter_select(data.filters.values, actives=False)
            # get and select the filter ids that contain one or more location_ids
            filter_ids = [
                i for i in data.filters.values if locations_in_filter(location_ids, i)
            ]
            filters_widgets.set_filter_values(
                filters, filter_ids, config.thematic_view, data.filters
            )

        # make sure there is no rubbish and set loction_ids
        location_values = [i[0] for i in data.locations.options]
        locations_active = [
            location_values.index(i) for i in location_ids if i in location_values
        ]
        locations.active = locations_active

    # select parameters
    if "parameter_id" in args.keys():
        parameter_ids = [i.decode("utf-8") for i in args.get("parameter_id")]
        parameter_values = [i[0] for i in data.parameters.options]
        parameters_active = [
            parameter_values.index(i) for i in parameter_ids if i in parameter_values
        ]
        parameters.active = parameters_active

    # update period
    if "start_date" in args.keys():
        start_date = convert_to_datetime(args.get("start_date")[0].decode("utf-8"))
        if start_date is not None:
            update_period = True
    if "end_date" in args.keys():
        end_date = convert_to_datetime(args.get("end_date")[0].decode("utf-8"))
        if end_date is not None:
            update_period = True
    if update_period:
        end_date = min(data.periods.view_end, end_date)
        if start_date < end_date:
            search_start = start_date - timedelta(days=1)
            search_end = min(end_date + timedelta(days=1), data.periods.search_end)
            data.periods.set_search_period(search_start, search_end)
            data.periods.set_view_period(start_date, end_date)
            search_period.children[0].value = search_start.strftime("%Y-%m-%d")
            search_period.children[1].value = search_end.strftime("%Y-%m-%d")
            view_period.value = (data.periods.view_start, data.periods.view_end)

    if (len(locations.active) > 0) & (len(parameters.active) > 0):
        start_time_series_loader()


if curdoc().session_context:
    args = curdoc().session_context.request.arguments
    args_parser(args)
