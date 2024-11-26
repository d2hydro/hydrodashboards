#%%
from hydrodashboards.bokeh.main import (
    filters,
    parameters,
    locations,
    start_time_series_loader,
    update_time_series_view,
    data,
    search_period,
    view_period,
    view_x_range_as_datetime,
    update_on_view_period_value_throttled,
    update_time_series_sources,
    time_series_sources,
    view_x_range,
    search_x_range,
    sources,
    config,
    map_figure_widget,
    map_figure
)
from datetime import datetime


def load_data():
    start_time_series_loader()
    update_time_series_view()


# choose theme
filters[0].active = [0]
# choose filter
filters[1].active = [0]

# choose location
locations.active = [0]

# choose debiet
parameters.active = [1]

# set view period on available period
data.periods.view_start = datetime(2022,5,1)

# # load data
load_data()

# 
# update_time_series_sources()
view_period.value = (1729987200000, 1732579200000)

view_x_range.start, view_x_range.end = (
    data.periods.view_start,
    data.periods.view_end,
)

update_time_series_sources()

