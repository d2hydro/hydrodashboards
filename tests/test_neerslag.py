from hydrodashboards import bokeh

# %% here we overwrite the default (WAM) config with WIK
AAM_CONFIG_JSON = r"data\wik_config.json"
bokeh.set_config_json(AAM_CONFIG_JSON)
bokeh.delete_cache()

# %% now we import main (will be initialized for WIK)
from hydrodashboards.bokeh.main import (filters,
                                        locations,
                                        parameters,
                                        search_period,
                                        start_time_series_loader,
                                        update_time_series_view,
                                        update_time_series_search,
                                        search_time_series,
                                        time_figure_layout,
                                        search_time_figure_layout) # noqa E:402


def test_y_range_start():
    filters[0].active = [0]
    locations.active = [0, 1]
    parameters.active = [0]
    search_period.children[0].value = "2014-01-01"
    start_time_series_loader()
    update_time_series_view()

    assert time_figure_layout.children[0].children[0].y_range.start == 0

    filters[0].active = []


def test_scaling_search_fig():
    filters[0].active = [0]  # select Keten.Neerslag
    locations.active = [0, 1]  # select 't Heufke & 't Staal
    parameters.active = [0]  # select Neerslag (gecalibreerde radar)
    search_period.children[0].value = "2017-03-01"
    start_time_series_loader()
    update_time_series_view()
    update_time_series_search()

    assert search_time_figure_layout.children[0].y_range.end == search_time_figure_layout.children[0].renderers[1].data_source.data["value"].max()

    search_time_series.value = search_time_series.options[1]

    assert search_time_figure_layout.children[0].y_range.end == search_time_figure_layout.children[0].renderers[1].data_source.data["value"].max()

    filters[0].active = []
