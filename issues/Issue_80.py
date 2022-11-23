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
from datetime import datetime

def load_data():
    start_time_series_loader()
    update_time_series_view()
    update_time_series_search()


# choose theme
filters[0].active = [2]
# choose filter
filters[1].active = [7]

# choose location
locations.active = [1]

# choose debiet
parameters.active = [1]

# set view period on available period
data.periods.view_start = datetime(2022,5,1)

# load data
load_data()
