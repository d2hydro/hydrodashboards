from hydrodashboards import bokeh
from datetime import datetime
from bokeh.plotting import figure
from bokeh.io import show
from bokeh.models import ColumnDataSource,FuncTickFormatter

from hydrodashboards.bokeh.widgets.time_figure_widget import DT_JS_FORMAT
from time import time

# %% here we overwrite the default (WAM) config with WIK
AAM_CONFIG_JSON = r"..\tests\data\wik_config.json"
bokeh.set_config_json(AAM_CONFIG_JSON)
bokeh.delete_cache()

def load_time_series():
    data.get_time_series_headers()
    data.update_time_series_search()

# %% now we import main (will be initialized for WIK)
from hydrodashboards.bokeh.main import (data,
                                        filters,
                                        locations,
                                        parameters,
                                        search_period,
                                        start_time_series_loader,
                                        update_time_series_view,
                                        update_time_series_search
                                        )

search_start = data.periods.history_start.strftime("%Y-%m-%d")
print(f"downloading data from {search_start}")
search_period.children[0].value = search_start
filter_id = data.config.cache_filters[0]

main_filter_index = data.filters.get_filter_index(filter_id)
main_filter = data.filters.get_filter(filter_id)
sub_filter_index = next(
    (idx for idx, i in enumerate(main_filter.options) if i[0] == filter_id),
    None
    )
filters[main_filter_index].active = [sub_filter_index]
locations.active = [0]
parameters.active = [0]
load_time_series()

time_series = data.time_series_sets.time_series[0]

# %%
tic = time()
pickle_path = time_series.cache.cache_dir / f"{time_series.key}.pickle"
time_series.to_cache()


key = time_series.key

print(f"to pickle {time() - tic:.2f} seconds")
tic = time()
hdf_path = time_series.cache.cache_dir / f"{time_series.key}.hdf"
time_series.df.to_hdf(hdf_path, time_series.key)
print(f"to hdf {time() - tic:.2f} seconds")

# filters[main_filter_index].active = [sub_filter_index]
# for idx, location in enumerate(locations.labels):
#     print(f"caching data for {location} ({idx+1}/{len(locations.labels)})")
#     tic = time()
#     locations.active = [idx]
#     parameters.active = [idx for idx, i in enumerate(parameters.labels)]
#     load_time_series()
#     print(f" loaded in {time() - tic:.2f} seconds")
#     tic = time()
#     for time_series in data.time_series_sets.time_series:
#         if not time_series.cache.exists(time_series.key):
#             time_series.to_cache()
#     print(f" saved in {time() - tic:.2f} seconds")
#     data.time_series_sets.time_series = []
