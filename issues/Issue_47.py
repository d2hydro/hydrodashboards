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
    update_on_view_period_value_throttled,
    view_period,
    view_x_range,
    search_period,
    convert_to_datetime,
)
from bokeh.plotting import Figure


def load_data():
    start_time_series_loader()
    update_time_series_view()
    update_time_series_search()


# choose theme grondwatater
filters[0].active = [1]
# choose filter gemaal
filters[1].active = [0]

# choose location abelstok

locations.active = [0, 1]

# choose debiet
parameters.active = [1]
# time_figure_layout.children[0].children[0]
# load_data()
