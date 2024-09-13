try:
    from main import data, filters, locations, parameters, search_period
    from log_utils import import_logger, LOG_DIR
    import pid_utils
except ImportError:
    from hydrodashboards.bokeh.main import (
        data,
        filters,
        locations,
        parameters,
        search_period,
    )
    from hydrodashboards.bokeh.log_utils import import_logger, LOG_DIR
    from hydrodashboards.bokeh import pid_utils

import pandas as pd
from datetime import datetime

logger = import_logger(log_file="time_series_cache.log")
pid_file_path = LOG_DIR / "time_series_cache.pid"


def load_time_series():
    """Support function for downloading time-series."""
    # data.get_time_series_headers(ignore_cache=True)
    data.update_time_series(ignore_cache=True)


def update_idle():
    """Check if update process is not still running."""
    idle = False

    running_process = pid_utils.read(pid_file_path)
    if running_process is None:
        idle = True
    else:  # if pid-file somehow exists, we check if process indeed runs
        if not pid_utils.running(**running_process):
            idle = True

    return idle


def warning():
    """Logs warning when process is busy."""
    running_process = pid_utils.read(pid_file_path)
    logger.warning(
        f"No update of time-series cache. Terminate process with pid {running_process['pid']} first"
    )


def main():
    """Main function, if update_idle(), then update cache."""
    if update_idle():
        pid_utils.write(pid_file_path)
        update_cache()
        pid_file_path.unlink()
    else:
        warning()


def update_cache():
    # get search_start used as startTime in FEWS-API-call
    search_start = data.periods.history_start.strftime("%Y-%m-%d")
    if data.time_series_sets.cache.cache_dir.exists():
        if any(data.time_series_sets.cache.cache_dir.iterdir()):
            search_start = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"downloading data from {search_start}")
    search_period.children[0].value = search_start

    # iterate over filters to populate cache
    for filter_id in data.config.cache_filters:
        logger.info(f"filter id: {filter_id}")
        main_filter_index = data.filters.get_filter_index(filter_id)
        main_filter = data.filters.get_filter(filter_id)
        sub_filter_index = next(
            (idx for idx, i in enumerate(main_filter.options) if i[0] == filter_id),
            None,
        )
        filters[main_filter_index].active = [sub_filter_index]

        # iterate over locations
        for location_idx, location_name in enumerate(locations.labels):
            logger.info(
                f"caching location: {location_name} ({location_idx +1}/{len(locations.labels)})"
            )
            locations.active = [location_idx]

            # set all locations active
            parameters.active = [i for i, _ in enumerate(parameters.labels)]

            # load all time-series
            load_time_series()

            # store, or update, all timeseries in cache
            for time_series in data.time_series_sets.time_series:
                # update cached time-series if exists
                if data.time_series_sets.cache.exists(time_series.key):
                    df = time_series.df
                    if not df.empty:  # only update existing if new isn't empty
                        time_series = data.time_series_sets.cache.get_data(
                            time_series.key
                        )
                        time_series.df = time_series.df.loc[
                            ~time_series.df.index.isin(df.index)
                        ]
                        time_series.df = pd.concat([time_series.df, df])
                        time_series.to_cache()
                else:  # not yet in cache, so write any way
                    time_series.to_cache()

            # empty in-memory time-series for next iter
            data.time_series_sets.time_series = []


if __name__ == "__main__":
    main()
