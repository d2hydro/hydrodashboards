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
    search_source
)
from bokeh.plotting import Figure

def load_data():
    start_time_series_loader()
    update_time_series_view()
    update_time_series_search()


# choose theme oppervlaktewater
filters[0].active = [0]
# choose meetpunt
filters[1].active = [4]

# choose location

locations.active =  [1,12]

# choose debiet 
parameters.active = [0,1,2,3]

#time_figure_layout.children[0].children[0]
load_data()

for idx in [0, -1]:
    assert data.time_series_sets.get_by_label(search_source.name).df.index.values[idx] == search_source.data["datetime"][idx]
