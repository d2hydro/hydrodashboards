from hydrodashboards import bokeh
from hydrodashboards.datamodel.time_series_sampling import simplify

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
parameters.active = [0, 1]
load_time_series()

for time_series in data.time_series_sets.time_series:
    print(time_series.key)
    time_series.df = time_series.df.loc[time_series.df.flag < 6]
    _df = simplify(time_series.df, max_samples=100, intervals=True)
    _df.loc[_df.flag.isna(), "flag"] = 0
    time_series.df = _df
    time_series.to_cache()
