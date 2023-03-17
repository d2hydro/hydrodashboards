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
                                        time_figure_layout) # noqa E:402


def test_y_range_start():
    filters[0].active = [0]
    locations.active = [0, 1]
    parameters.active = [0]
    search_period.children[0].value = "2014-01-01"
    start_time_series_loader()
    update_time_series_view()

    assert time_figure_layout.children[0].children[0].y_range.start == 0
