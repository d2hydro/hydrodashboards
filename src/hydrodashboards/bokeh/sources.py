from bokeh.models import ColumnDataSource, CustomJS
import numpy as np
import pandas as pd

locations_source_js = """
if (window.MenuEvents && typeof window.MenuEvents.onLocationsDataChanged === 'function') {
    window.MenuEvents.onLocationsDataChanged();
}
"""


def thresholds_to_source(thresholds):
    value = [[i] * 2 for i in thresholds["value"]]
    datetime = [
        np.array(["1900-01-01T00:00:00", "2100-01-01T00:00:00"], dtype="datetime64")
        for i in value
    ]
    label = np.array(thresholds["label"])
    return ColumnDataSource(data={"datetime": datetime, "value": value, "label": label})


def _index_mask(index, start_date_time, end_date_time):
    return (index > start_date_time) & (index <= end_date_time)


def df_to_source(
    df,
    start_date_time=None,
    end_date_time=None,
    excluded_date_times=None,
    unreliables=False,
    sample=True
):
    if (start_date_time is not None) and (end_date_time is not None):
        df = df.loc[_index_mask(df.index, start_date_time, end_date_time)]
    if excluded_date_times is not None:
        df = df.loc[~df.index.isin(excluded_date_times)]
    if (not unreliables) & ("flag" in df.columns):
        df = pd.DataFrame(df.loc[df["flag"] < 6]["value"])

    # To Do (Neeltje): advanced sampling preserving peaks and depressions
    if sample:
        df = df.sample(min(len(df), 2000)).sort_index()
    # end of improvements
    return ColumnDataSource(df)


def time_series_to_source(
    time_series,
    start_date_time=None,
    end_date_time=None,
    unreliables=False,
    excluded_date_times=None,
    sample=True
):

    source = df_to_source(
        time_series.df,
        start_date_time=start_date_time,
        end_date_time=end_date_time,
        unreliables=unreliables,
        excluded_date_times=excluded_date_times,
        sample=sample
    )
    source.name = time_series.label
    source.tags = time_series.tags
    return source


def locations_source():
    source = ColumnDataSource(
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

    source.js_on_change("data", CustomJS(args=dict(), code=locations_source_js))

    return source


def time_series_template():
    return ColumnDataSource(data={i: np.array([]) for i in ["datetime", "value"]})


def view_period_patch_source(data):
    return ColumnDataSource(
        data={
            "x": [data.view_start, data.view_start, data.view_end, data.view_end],
            "y": [-(10**9), 10**9, 10**9, -(10**9)],
        }
    )


def time_series_sources(time_series=[], unreliables=False, active_only=False, sample=False):
    def _active(i, active_only=active_only):
        if active_only:
            return i.active
        else:
            return True

    return {
        i.label: time_series_to_source(i, unreliables, sample=sample)
        for i in time_series
        if _active(i)
    }


def update_time_series_sources(sources, time_series=[], unreliables=False, sample=True):
    for i in time_series:
        source = time_series_to_source(i, unreliables, sample=sample)
        sources[i.label].data.update(source.data)
