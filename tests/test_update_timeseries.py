from hydrodashboards.bokeh.main import (
    filters,
    parameters,
    locations,
    data,
    start_time_series_loader,
    update_time_series_view,
    update_time_series_search,
    time_figure_layout,
    get_visible_sources,
    toggle_download_button_on_sources,
    download_time_series,
)

NBR_SERIES = 4
LIM_EVENTS = 1000000


def toggle_renderers_visibility(figs, visible=False):
    for fig in figs:
        for renderer in fig.renderers:
            renderer.visible = visible


def test_load_abelstok():
    # choose theme oppervlaktewater
    filters[0].active = [0]
    # choose filter gemaal
    filters[1].active = [1]

    # choose location abelstok
    locations.active = [0]

    # choose debiet and waterhoogte
    parameters.active = [1, 5]
    start_time_series_loader()
    update_time_series_view()
    update_time_series_search()
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
