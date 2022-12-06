from hydrodashboards.bokeh.main import (
    convert_to_datetime,
    data,
    download_time_series,
    filters,
    get_visible_sources,
    locations,
    parameters,
    search_period,
    search_time_figure_layout,
    search_time_series,
    search_source,
    start_time_series_loader,
    time_figure_layout,
    toggle_download_button_on_sources,
    update_on_history_search_time_series,
    update_on_view_period_value_throttled,
    update_time_series_view,
    update_time_series_search,
    view_period,
    view_x_range,
)

# from hydrodashboards.bokeh.widgets import search_period_widget, time_figure_widget
import copy

from datetime import timedelta

NBR_SERIES = 4
LIM_EVENTS = 1000000
EMPTY_WARNING = "no time series for selected locations and parameters"


def load_time_series():
    start_time_series_loader()
    update_time_series_view()
    update_time_series_search()


def toggle_renderers_visibility(figs, visible=False):
    for fig in figs:
        for renderer in fig.renderers:
            renderer.visible = visible


def test_load_beeklandstuw():
    # choose theme oppervlaktewater
    filters[0].active = []
    filters[0].active = [0]
    # choose filter stuw
    filters[1].active = [1]

    # choose location beeklandstuw
    locations.active = [0]

    # choose debiet and waterhoogte
    parameters.active = [1, 5]
    load_time_series()

    # check if there are 4 timeseries
    assert len(data.time_series_sets.time_series) == NBR_SERIES
    # check if there are two graphs
    assert len(time_figure_layout.children[0].children)


def test_toggle_visible():
    figs = time_figure_layout.children[0].children
    sources = get_visible_sources(figs)
    assert len(sources) == NBR_SERIES
    assert data.time_series_sets.max_events_visible > 0
    assert data.time_series_sets.max_events_visible <= LIM_EVENTS

    assert not download_time_series.disabled

    toggle_renderers_visibility(figs)
    sources = get_visible_sources(figs)
    toggle_download_button_on_sources(sources)
    assert not sources
    assert data.time_series_sets.max_events_visible == 0
    assert download_time_series.disabled


def test_update_view_period():
    figs = time_figure_layout.children[0].children
    toggle_renderers_visibility(figs, visible=True)
    sources = get_visible_sources(figs)

    old = view_period.value
    old_length = len(sources[0].data["datetime"])
    shift = timedelta(days=5)
    start_date, end_date = view_period.value_as_datetime
    start_date -= shift
    view_period.value = (start_date, end_date)
    new = view_period.value
    assert data.periods.view_start == start_date

    update_on_view_period_value_throttled("value_throttled", old, new)
    assert len(sources[0].data["datetime"]) > old_length

    assert view_x_range.start == data.periods.view_start
    x_start = copy.copy(view_x_range.start)
    view_x_range.start -= shift
    assert view_x_range.start < x_start
    assert view_x_range.start == data.periods.view_start

    search_start = convert_to_datetime(search_period.children[0].value)
    shift = timedelta(days=5)
    search_start -= timedelta(days=5)
    search_period.children[0].value = search_start.strftime("%Y-%m-%d")
    assert data.periods.search_start == search_start


def test_update_history_search_time_series():
    test_load_beeklandstuw()
    df = data.time_series_sets.get_by_label(search_time_series.value).df
    assert search_source.data["datetime"].min() == df.index.min()
    assert search_source.data["datetime"].max() == df.index.max()

    update_on_history_search_time_series()

    assert search_source.data["datetime"].min() < df.index.min()


def test_empty_timeseries():
    # choose theme oppervlaktewater
    filters[0].active = [0]
    # choose filter gemaal
    filters[1].active = [4]

    # choose location abelstok

    id = locations.labels.index("Triplum (KGM071)")
    locations.active = [id]

    # choose debiet
    parameters.active = [0]

    start_time_series_loader()
    update_time_series_view()

    assert not data.time_series_sets.any_active
    assert EMPTY_WARNING in search_time_figure_layout.children[0].text
    assert EMPTY_WARNING in time_figure_layout.children[0].text

    filters[0].active = []


def test_duplicate_locations():
    # choose FC
    filters[0].active = [2]
    # choose two filters with duplicate locations
    filters[1].active = [1, 2]

    # choose location
    locations.active = [7]

    # choose first parameter
    parameters.active = [0]

    # load data
    load_time_series()

    assert not data.locations.app_df.index.has_duplicates
