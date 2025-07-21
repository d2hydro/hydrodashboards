import datetime
import numbers
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd
from bokeh.models import BoxAnnotation, DatetimeTickFormatter
from bokeh.plotting import figure


def xaxis_date_formatter():
    """Format datetime on timeseries figures based on different zoom levels."""
    return DatetimeTickFormatter(
        years="%Y\n", months="%Y-%m\n", days="%Y-%m-%d\n%H:%M", hourmin="\n%H:%M", hours="\n%H:%M", minutes="\n%H:%M"
    )


def apply_default_toolbar(fig: figure):
    """Default toolbar, hide without logo."""
    fig.toolbar.autohide = True
    fig.toolbar.logo = None


def add_box_annotations(fig: figure, kwargs: Union[list, dict], palette: list[str]):
    """Add box annotations to a figure.

    Parameters
    ----------
    fig (bokeh.plotting.figure):
    kwargs (list, dict):
        kwargs to the BoxAnnotation
    palette (list[str])
        Extend the kwargs with a pallete of colors. Should be same length as kwargs.


    Example
    -------
    fig = figure()
    kwargs = [
        {"top": 25},
        {"bottom": 25, "top": 50},
        {"bottom": 50, "top": 75},
        {"bottom": 75},
    ],
    palette = ["green", "yellow", "orange", "red"]
    """
    if isinstance(kwargs, dict):
        kwargs = [kwargs]

    for idx, kwarg in enumerate(kwargs):
        if palette:
            kwarg["fill_color"] = palette[idx]
        fig.add_layout(BoxAnnotation(level="underlay", **kwarg))


@dataclass
class FeatherTimeseries:
    """FeatherTimeseries can be read as pivot table.
    This will return.

    Parameters
    ----------
    name (str):
        shortname, description
    file_path (Path):
        path to file..
    value_col (str):
        Name of column that holds the values
    int_factor (int, None):
        When provided, multiply floats and turn into int.
        e.g. wlvl in mNAP with a precision of 3 decimals, when multiplied will
        give integers in mmNAP.
    """

    name: str
    file_path: Path
    value_col: str
    int_factor: int = None
    _df: pd.DataFrame = None

    def to_dict(self):
        return {
            "file_path": self.file_path,
            "value_col": self.value_col,
            "int_factor": self.int_factor,
        }

    @property
    def df(self):
        if self._df is None:
            # _df = pd.read_feather(self.file_path, dtype_backend="pyarrow")[["datetime", "location_id", "value"]]
            # FIXME met de dtype_backend="pyarrow" gaat onderstaande .tz_localize(None) niet goed.
            #
            _df = pd.read_feather(self.file_path)[["datetime", "location_id", self.value_col]]

            # This localizing is a bit of a pain.
            # Bokeh doesnt support tz aware x-axes. Even when the tz is set to Amsterdam,
            # The figure would still plot in UTC. We therefore set it to Ams and then
            # localize to None, pretending that the Ams time is actually in UTC.
            _df["datetime"] = _df["datetime"].dt.tz_localize("UTC")
            _df["datetime"] = _df["datetime"].dt.tz_convert("Europe/Amsterdam")
            _df["datetime"] = _df["datetime"].dt.tz_localize(None)
            # _df["datetime"] = _df["datetime"].dt.tz_localize("Europe/Amsterdam")
            _df["datetime"] = _df["datetime"].dt.tz_localize("UTC")
            # _df["datetime"] = _df["datetime"].dt.tz_convert("Europe/Amsterdam")

            # pivot_location
            if self.int_factor is not None:
                _df[self.value_col] = (
                    (_df[self.value_col] * self.int_factor)
                    .fillna(-999999)  # cannot cast to int without filling nans.
                    .astype(int)  # cannot cast to pyarrow int without rounding first
                    .astype("int32[pyarrow]")
                    .replace(-999999, None)
                )
            self._df = _df
        return self._df

    @property
    def last_value_datetime(self):
        return self.df.dropna(subset=["value"]).datetime.max()

    @property
    def first_value_datetime(self):
        return self.df.dropna(subset=["value"]).datetime.min()

    # FIXME int_factor has different name...
    def as_pivot(self, location_ids=[], daily_values=False, statistic=None, value_col="value") -> pd.DataFrame:
        """
        Read feater and pivot the table so that it has one row per location.
        For the value columns it will create pd.Series
        """
        df = self.df[self.df["location_id"].isin(location_ids)]
        if daily_values:
            grouper = df.set_index("datetime").groupby([pd.Grouper(freq="D"), "location_id"])
            if statistic == "mean":
                df = grouper.mean().reset_index(names=["datetime", "location_id"])
            if statistic == "max":
                df = grouper.max().reset_index(names=["datetime", "location_id"])
        df_agg = df.groupby("location_id").agg(pd.Series)

        df2 = df_agg.apply(lambda row: self.add_nodata_to_timeseries(row, daily_values, value_col), axis=1)
        return df2

    @staticmethod
    def add_nodata_to_timeseries(row, daily_values=False, value_col="value"):
        """Add nodata to timeseries so that the lines are not plotted
        on bokeh when there is no data.

        When there are large gaps, only the first value is filled with NaN
        bokeh then stops drawing the line.
        """
        # Define the interval in minutes
        if daily_values:
            freq = "1d"
        else:
            freq = "15min"

        df_row = pd.DataFrame({"datetime": row["datetime"], "value": row[value_col]})

        # Create a complete range of timestamps with the given interval
        start_time = min(df_row["datetime"])
        end_time = max(df_row["datetime"])
        # complete_range = pd.date_range(start=start_time, end=end_time, freq=freq, tz="Europe/Amsterdam")
        complete_range = pd.date_range(start=start_time, end=end_time, freq=freq, tz="UTC")

        # Merge the complete range with the original DataFrame
        complete_df = pd.DataFrame(
            {"datetime": complete_range},
            dtype=df_row.dtypes["datetime"],
        )
        merged_df = pd.merge(complete_df, df_row, on="datetime", how="left")

        # Fill only the first missing value and get all the rows that have data
        # Filter the filled df with these rows.
        yesdata_rows = merged_df["value"].ffill(limit=1).notna()
        filled_df = merged_df[yesdata_rows]

        row["datetime"] = filled_df["datetime"].values
        row["value"] = filled_df["value"].values
        return row

    def at_timestep(self, date_time, df_locs, loc_id_col):
        """Get values for all locations a a specified timestep"""
        values_df = self.df[self.df.datetime == date_time].groupby("location_id").max()

        df_locs_values = pd.merge(
            df_locs[loc_id_col], values_df[self.value_col], left_on=loc_id_col, right_index=True, how="left"
        )
        value_col = df_locs_values[self.value_col]

        # # When selecting outside available time period the None values were interpreted as 0.
        # # By make it NaN it shows as a grey dot correctly.
        df_locs_values[df_locs_values[self.value_col].isna()] = np.nan
        # # Instead of NaN values show a '-' on the hover.
        hover_col = value_col.astype(object).fillna("-")

        return value_col, hover_col


def to_miliseconds(value: Union[int, datetime.datetime]):
    if isinstance(value, datetime.datetime):
        return value.timestamp() * 1000
    elif isinstance(value, numbers.Number):
        return value
    else:
        raise ValueError(f"{value} is not a numbers.Number nor datetime.datetime object")
