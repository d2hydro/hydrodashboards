from pandas import DataFrame
from hydrodashboards.datamodel import time_series_sampling


def sample_df(df: DataFrame, sampling_config: dict) -> dict:
    """
    samples based on a time series sample config dictionary

    Args:
        time_series_sampling_config (dict): Time Series sampling conig

    Returns:
        DataFrame: Sampled DataFrame

    """

    function = getattr(time_series_sampling,
                       sampling_config["method"])
    kwargs = {k: v for k,v in sampling_config.items() if k != "method"}

    return function(df, **kwargs)


def random_sample(df: DataFrame, max_samples: int = 20000) -> DataFrame:
    """
    Takes a random sample from a pandas dataframe

    Args:
        df (pd.DataFrame): Input DataFrame
        max_sample (int): min sample size. Defaults to 20000

    Returns:
        DataFrame: Sampled DataFrame

    """
    return df.sample(min(len(df), max_samples)).sort_index()
