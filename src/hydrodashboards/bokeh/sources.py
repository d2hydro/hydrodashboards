from bokeh.models import ColumnDataSource
import numpy as np
import pandas as pd


def time_series_to_source(time_series,
                          start_date_time=None,
                          end_date_time=None,
                          unreliables=False,
                          excluded_date_times=None):
    def _index_mask(index, start_date_time, end_date_time):
        return (index > start_date_time) & (index <= end_date_time)
    df = time_series.df
    if (start_date_time is not None) and (end_date_time is not None):
        df = df.loc[_index_mask(df.index, start_date_time, end_date_time)]
    if excluded_date_times is not None:
        df = df.loc[~df.index.isin(excluded_date_times)]
    if (not unreliables) & ("flag" in df.columns):
        df = pd.DataFrame(df.loc[df["flag"] < 6]["value"])
    source = ColumnDataSource(df)
    source.name = time_series.label
    return source


def locations_source():
    return ColumnDataSource(
        data={
            i: []
            for i in [
                "x",
                "y",
                "id",
                "name",
                "line_color",
                "fill_color",
                "label",
            ]
        },
    )


def time_series_template():
    return ColumnDataSource(data = {i: np.array([]) for i in ["datetime", "value"]})


def view_period_patch_source(data):
    return ColumnDataSource(data = {"x":[data.view_start, data.view_start, data.view_end, data.view_end],
                                    "y": [-10**9, 10**9, 10**9, -10**9]})


def time_series_sources(time_series=[], unreliables=False, active_only=False):
    def _active(i, active_only=active_only):
        if active_only:
            return i.active
        else:
            return True
    return {i.label: time_series_to_source(i, unreliables) for i in time_series if _active(i)}


def update_time_series_sources(sources, time_series=[], unreliables=False):
    for i in time_series:
        source = time_series_to_source(i, unreliables)
        sources[i.label].data.update(source.data)
