# %%
import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
from bokeh_helpers.fews_api.get_data import GetTimeseries

logger = logging.getLogger(__name__)
# globals
CONFIG_JSON = Path(__file__).parent.joinpath("config.json")
DATA_DIR = Path(__file__).parent / "data"

# definition of time-series cache per filter and parameter-id
SERIES_CACHE = {
    "vullingsgraad": {"filter_id": "VullingsgraadOutput", "parameter_id": "vullingsgraad"},
    "vulling": {"filter_id": "VullingsgraadOutput", "parameter_id": "vulling_mm"},
    "waterstand_pgb": {"filter_id": "PeilgebiedWaterstandOutput", "parameter_id": "WATHTE [m][NAP][OW]"},
    "waterstand_meetpunt": {"filter_id": "PeilgebiedWaterstandMeetpunt", "parameter_id": "WATHTE [m][NAP][OW]"},
}


class GetData:
    def __init__(self, days=40, rebuild=False):
        """Parse arguments to get_data.get_data function."""
        logger.info(days)
        logger.info(rebuild)

        get_timeseries = GetTimeseries(data_dir=DATA_DIR, config_json=CONFIG_JSON)

        # Get locations
        file = DATA_DIR / "mpn_locations.arrow"
        if rebuild or (not file.exists()):
            locations_df_raw = get_timeseries.fews_api.get_locations(
                filter_id="PeilgebiedWaterstandMeetpunt", attributes=["peilgebied_combi_attr"]
            )

            locations_df = locations_df_raw[
                locations_df_raw["peilgebied_combi_attr"].notna()
            ]  # Select only relevant locations
            cols = [i for i in locations_df.columns if i not in ["geometry", "lat", "lon", "z"]]
            pd.DataFrame(locations_df[cols]).to_feather(file)

        # Get parameters
        file = DATA_DIR / "parameters.arrow"
        if rebuild or (not file.exists()):
            parameters_df = get_timeseries.fews_api.get_parameters(filter_id="Vullingsgraad")
            parameters_df.to_feather(file)

        # Get timeseries
        get_timeseries.get_timeseries(series_cache=SERIES_CACHE, days=days, rebuild=rebuild)

    @classmethod
    def from_args(cls, args=None):
        parser = argparse.ArgumentParser(description="Data download from FEWS-API to arrow-files")
        parser.add_argument(
            "--days", type=int, help="days from now of history to download (from now)", required=False, default=40
        )
        parser.add_argument(
            "--rebuild", action=argparse.BooleanOptionalAction, help="rebuild data cache from scratch", default=False
        )
        args = parser.parse_args()
        return cls(days=args.days, rebuild=args.rebuild)


# %%
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Parse command-line arguments
        data = GetData.from_args()
    else:
        days = 1
        rebuild = False
        # Use default arguments
        data = GetData(days=days, rebuild=rebuild)
