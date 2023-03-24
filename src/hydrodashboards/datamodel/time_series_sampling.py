from pandas import DataFrame
from hydrodashboards.datamodel import time_series_sampling
import pandas as pd
from datetime import timedelta


def sample_df(df: DataFrame, sampling_config: dict) -> dict:
    """
    samples based on a time series sample config dictionary

    Args:
        time_series_sampling_config (dict): Time Series sampling config

    Returns:
        DataFrame: Sampled DataFrame

    """

    function = getattr(time_series_sampling, sampling_config["method"])
    kwargs = {k: v for k, v in sampling_config.items() if k != "method"}
    print(f"sample_df init {df}")
    if not df.empty:
        return function(df, **kwargs)
    else:
        return df


def random_sample(df: DataFrame, max_samples: int = 20000) -> DataFrame:
    """
    Takes a random sample from a pandas dataframe

    Args:
        df (pd.DataFrame): Input DataFrame
        max_sample (int): min sample size. Defaults to 20000

    Returns:
        DataFrame: Sampled DataFrame

    """
    print(f"random sample {df}")
    return df.sample(min(len(df), max_samples)).sort_index()


def simplify(df, max_samples: int = 250000, intervals=False) -> DataFrame:
    """
    Simplifies the value-column in a time-series dataframe dataframe

    Args:
        df (pd.DataFrame): Input DataFrame
        max_sample (int): min sample size. Defaults to 20000
        intervals (boolean): min, max time interval. Default false

    Returns:
        DataFrame: Sampled DataFrame

    """

    p = max_samples / len(df)
    print(len(df))
    if len(df) > max_samples:
        # compute slope
        delta_time = (
            df.reset_index()
            .set_index("datetime", drop=False)
            .datetime.diff()
            .dt.total_seconds()
        )
        delta_value = df.value.diff()
        slope = delta_value / delta_time

        # compute percentiles
        max_value = df.value.quantile(q=(1 - p / 8))
        min_value = df.value.quantile(q=p / 8)
        slope_max = slope.quantile(q=(1 - p / 2))
        slope_min = slope.quantile(q=(p / 2))

        # simplified sample
        simplified = df[
            (slope > slope_max)
            | (df.value > max_value)
            | (df.value < min_value)
            | (slope < slope_min)
        ]
        print("0",len(simplified))
        if intervals:
            print("intervals")
            func_idxmax = lambda x: x.idxmax() if not x.empty else pd.NA # noqa
            func_idxmin = lambda x: x.idxmin() if not x.empty else pd.NA # noqa
            func_max = lambda x: x.max() if not x.empty else pd.NA # noqa
            func_min = lambda x: x.min() if not x.empty else pd.NA # noqa

            # regular max and min
            intervals = df.groupby(
                pd.Grouper(freq=timedelta(minutes=1))
                ).value.agg(
                [
                    ("idxmax", func_idxmax),
                    ("idxmin", func_idxmin),
                    ("max", func_max),
                    ("min", func_min),
                ]
            )
            regular_max = (
                intervals.rename
                (columns={"idxmax": "datetime", "max": "value"})
                .dropna()
                .set_index("datetime")[["value"]]
            )
            regular_min = (
                intervals.rename
                (columns={"idxmin": "datetime", "min": "value"})
                .dropna()
                .set_index("datetime")[["value"]]
            )

            # concat in one dataframe
            df_simplified = (
                pd.concat([simplified, regular_max, regular_min])
                .reset_index()
                .drop_duplicates(subset="datetime", keep="last")
                .set_index("datetime")
                .sort_index()
            )
            print("1",len(df_simplified),len(simplified),len(regular_max),len(regular_min))
        else:
            df_simplified = (
                simplified
                .reset_index()
                .drop_duplicates(subset="datetime", keep="last")
                .set_index("datetime")
                .sort_index()
            )
        print(f"simplified {df}")   
        return df_simplified
    else:
        return df
