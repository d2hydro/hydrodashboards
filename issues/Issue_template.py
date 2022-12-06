# import all from main that is needed for reproduction
from hydrodashboards.bokeh.main import (
    filters,
    parameters,
    locations,
    data,
    start_time_series_loader,
    update_time_series_view,
    update_time_series_search,
)


# time series loader sequence
def load_data(update_search=True):
    start_time_series_loader()
    update_time_series_view()
    if update_search:
        update_time_series_search()

def find_indices(filter_cls, value):
    values = [i[0] for i in filter_cls.options]
    return [values.index(i) for i in value]

# choose a theme by index
theme_ids = ['WDB_OW']
filters[0].active = find_indices(data.filters.thematic_filters[0], theme_ids)
# choose filter by filter_ids
filter_ids = ['WDB_OW_KGM']
filters[1].active = find_indices(data.filters.thematic_filters[1], filter_ids)

# choose locations by location_ids
location_ids = ['NL34.HL.KGM156', 'NL34.HL.KGM295']
locations.active = find_indices(data.locations, location_ids)

# choose parameter by parameter_ids
parameter_ids = ['Q [m3/s] [NVT] [OW] * productie', 'WATHTE [m] [NAP] [OW] * productie']
parameters.active = find_indices(data.parameters, parameter_ids)

# load data
load_data()

# if un-expected outcome, raise an AssertionError that is to be fixed
assert data.locations.value == location_ids
