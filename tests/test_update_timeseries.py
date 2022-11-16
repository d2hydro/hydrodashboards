from hydrodashboards.bokeh.main import (
    filters,
    parameters,
    locations,
    data,
    search_time_series,
    search_period,
    search_source,
    start_time_series_loader,
    update_time_series_view,
    update_time_series_search,
    time_figure_layout,
    get_visible_sources,
    toggle_download_button_on_sources,
    download_time_series,
    update_on_view_period_value_throttled,
    view_period,
    view_x_range,
    search_period,
    search_time_figure_layout,
    convert_to_datetime,
    update_on_history_search_time_series
)

from hydrodashboards.bokeh.widgets import search_period_widget, time_figure_widget
import copy

from datetime import timedelta

NBR_SERIES = 4
LIM_EVENTS = 1000000


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

# %%
test_load_beeklandstuw()
data.periods.search_start
# %%
update_on_history_search_time_series()

