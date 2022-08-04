from bokeh.models import ColumnDataSource
import numpy as np

def _make_ts_cds(i, unreliables=False):
    df = i.df
    if not unreliables:
        df = df.loc[df["flag"] < 6]
    return ColumnDataSource(df)


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
    return ColumnDataSource(data = {i: np.array([]) for i in ["datetime", "value", "flag"]})


def view_period_patch_source(data):
    return ColumnDataSource(data = {"x":[data.view_start, data.view_start, data.view_end, data.view_end],
                                    "y": [-10**9, 10**9, 10**9, -10**9]})


def time_series_sources(time_series=[], unreliables=False, active_only=False):
    def _active(i, active_only=active_only):
        if active_only:
            return i.active
        else:
            return True
    return {i.label: _make_ts_cds(i, unreliables) for i in time_series if _active(i)}


def update_time_series_sources(sources, time_series=[], unreliables=False):
    for i in time_series:
        source = _make_ts_cds(i, unreliables)
        sources[i.label].data.update(source.data)
