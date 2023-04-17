try:
    from main import data, filters, locations, parameters, search_period
    from log_utils import import_logger
except ImportError:
    from hydrodashboards.bokeh.main import (
        data,
        filters,
        locations,
        parameters,
        search_period,
    )
    from hydrodashboards.bokeh.log_utils import import_logger

logger = import_logger(log_file="time_series_cache.log")


def load_time_series():
    data.get_time_series_headers()
    data.update_time_series()


search_start = data.periods.history_start.strftime("%Y-%m-%d")
logger.info(f"downloading data from {search_start}")
search_period.children[0].value = search_start
for filter_id in data.config.cache_filters:
    logger.info(f"filter id: {filter_id}")
    main_filter_index = data.filters.get_filter_index(filter_id)
    main_filter = data.filters.get_filter(filter_id)
    sub_filter_index = next(
        (idx for idx, i in enumerate(main_filter.options) if i[0] == filter_id), None
    )
    filters[main_filter_index].active = [sub_filter_index]
    for location_idx, location_name in enumerate(locations.labels):
        logger.info(
            f"caching location: {location_name} ({location_idx +1}/{len(locations.labels)})"
        )
        locations.active = [location_idx]
        parameters.active = [i for i, _ in enumerate(parameters.labels)]
        load_time_series()

        for time_series in data.time_series_sets.time_series:
            time_series.to_cache()
        data.time_series_sets.time_series = []
