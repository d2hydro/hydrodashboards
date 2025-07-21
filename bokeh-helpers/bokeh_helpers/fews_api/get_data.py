# %%
import datetime
from dataclasses import dataclass
from pathlib import Path

import fewspy
import pandas as pd

from bokeh_helpers.fews_api.api_config import ApiConfig


def ts_to_df(ts):
    """Flatten fewspy TimeSeries to pandas dataframe"""
    df = ts.events[["value"]]
    df.loc[:, "location_id"] = ts.header.location_id
    df.rename(columns={"value": ts.header.parameter_id}, inplace=True)
    df.reset_index(inplace=True)
    return df


@dataclass
class GetTimeseries:
    """Get data from FEWS API."""

    data_dir: Path
    config_json: Path

    def __post_init__(self):
        config = ApiConfig.from_json(self.config_json)
        self.fews_api = fewspy.Api(config.fews_url)

        if not self.data_dir.exists():
            self.data_dir.mkdir(exist_ok=True)

    def _write_log(self, days, rebuild):
        """Write log with last edit time and used params.
        Append to last log with a max of 1000 rows.
        """
        file = self.data_dir / "update.log"
        if file.exists():
            if len(file.read_text().split("\n")) > 1000:  # Remove file if too many rows
                file.unlink()
        with file.open("a") as f:
            f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}___days: {days} -- rebuild: {rebuild}\n")

    def get_timeseries(self, series_cache, days=40, rebuild=False):
        """Get time series"""
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(days=days)

        for k, v in series_cache.items():
            file = self.data_dir.joinpath(f"{k}.arrow")

            # Read cache_file and get new start-time
            if (not rebuild) and file.exists():
                cache_df = pd.read_feather(file)
                if not cache_df.empty:
                    start_time = cache_df.datetime.max().to_pydatetime()
                else:
                    file.unlink()

            # Get timeseries and flatten to df
            tss = self.fews_api.get_time_series(
                filter_id=v["filter_id"],
                parameter_ids=[v["parameter_id"]],
                start_time=start_time,
                end_time=end_time,
            )
            dfs = [ts_to_df(ts) for ts in tss.time_series if not ts.events.empty]
            if dfs:
                df = pd.concat(dfs, ignore_index=True)
                df.rename(columns={v["parameter_id"]: "value"}, inplace=True)

                # Add to cache_df
                if (not rebuild) and file.exists():
                    df = pd.concat([cache_df, df], ignore_index=True)
                    df.drop_duplicates(inplace=True)
                    df.reset_index(inplace=True)

                # Write to feather
                df[["datetime", "value", "location_id"]].to_feather(file)

        self._write_log(days=days, rebuild=rebuild)
