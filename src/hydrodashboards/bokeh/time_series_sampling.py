from pandas import DataFrame
from hydrodashboards.bokeh import time_series_sampling


def sample_df(df: DataFrame, time_series_sampling_config: dict) -> dict:
    """
    samples based on a time series sample config dictionary

    Args:
        time_series_sampling_config (dict): Time Series sampling conig

    Returns:
        DataFrame: Sampled DataFrame

    """

    function = getattr(time_series_sampling,
                       time_series_sampling_config["method"])
    time_series_sampling_config.pop("method")

    return function(**time_series_sampling_config)


def random_sample(df: DataFrame, max_sample: int = 20000) -> DataFrame:
    """
    Takes a random sample from a pandas dataframe

    Args:
        df (pd.DataFrame): Input DataFrame
        max_sample (int): min sample size. Defaults to 20000

    Returns:
        DataFrame: Sampled DataFrame

    """
    return df.sample(min(len(df), max_sample)).sort_index()
