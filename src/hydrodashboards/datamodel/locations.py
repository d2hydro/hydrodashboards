from hydrodashboards.bokeh.language import locations_title
from hydrodashboards.datamodel.models import Filter
from hydrodashboards.datamodel.cache import Cache
from fewspy.time_series import TimeSeries
import geopandas as gpd
import pandas as pd
from dataclasses import dataclass
from typing import List
import itertools

COLUMNS = [
    "id",
    "name",
    "x",
    "y",
    "parent_id",
    "geometry",
]
EMPTY_SET = gpd.GeoDataFrame(columns=COLUMNS).set_index("id")
MAP_LOCATIONS = {
    i: []
    for i in [
        "x",
        "y",
        "id",
        "name",
        "child_ids",
        "parameter_ids",
        "line_color",
        "fill_color",
        "nonselection_line_color",
        "non_selection_fill_color",
        "label",
    ]
}


@dataclass
class Locations(Filter):
    """Locations-data class for hydrodashboard"""

    locations: gpd.GeoDataFrame = EMPTY_SET
    sets: Cache = Cache(sub_dir="locations", data_frame=True)
    app_df: pd.DataFrame = pd.DataFrame(MAP_LOCATIONS).set_index("id")

    def __post_init__(self):
        self.title = locations_title[self.language]
        self.name = "locations"

    @property
    def map_locations(self):
        map_locations = self.app_df.reset_index().to_dict(orient="list")
        return map_locations

    def max_time_series_indices(self, parameter_values: list) -> List[tuple]:
        """
        Returns the maximum amount of time series indices to be found on selected
        locations and parameters

        Args:
            parameter_values (list): List of parameter values

        Returns:
            List[tuple]: List with (location, parameter) tuples

        """

        def _indices_for_location(location):
            children = list(self.app_df.loc[location]["child_ids"])
            parameters = [
                i
                for i in self.app_df.loc[location]["parameter_ids"]
                if i in parameter_values
            ]

            return list(itertools.product(children, parameters))

        labels_gen = (_indices_for_location(i) for i in self.value)
        return [i for i in itertools.chain(*labels_gen)]

    @classmethod
    def from_fews(cls, pi_locations: gpd.GeoDataFrame, attributes=[], language="dutch"):
        """
        Initalize Locations class from FEWS pi_locations

        Args:
            pi_locations (gpd.GeoDataFrame): FEWS locations
            language (TYPE, optional): Language setting. Defaults to "dutch".

        Returns:
            TYPE: DESCRIPTION.

        """

        df = pi_locations.rename(
            columns={"short_name": "name", "parent_location_id": "parent_id"}
        )
        df.index.name = "id"
        cols = COLUMNS + attributes
        df.drop(columns=[i for i in df.columns if i not in cols], inplace=True)
        return cls(language=language, locations=df)

    def parent_id_from_ts_header(self, header):
        return self.locations.loc[header.location_id]["parent_id"]

    def name_from_ts_header(self, header):
        return self.locations.loc[header.location_id]["name"]

    def get_parent_name(self, location_id):
        if not pd.isna(self.locations.at[location_id, "parent_id"]):
            location_id = self.locations.at[location_id, "parent_id"]
        return self.locations.at[location_id, "name"]

    def from_pi_headers(self, pi_headers: TimeSeries) -> List[tuple]:
        """
        Get all location options from FEWS pi headers

        Args:
            pi_headers (TimeSeries): PI headers

        Returns:
            options (List[tuple]): List with location (id, name) tuples

        """

        if not pi_headers.empty:
            locations = set([i.header.location_id for i in pi_headers.time_series])
            series = self.locations[self.locations["parent_id"].isna()]["name"]
            series = series[series.index.isin(locations)]
            options = list(zip(series.index, series.values))
            options.sort(key=lambda a: a[1])
        else:
            options = []
        return options

    def options_from_headers_df(self, headers_df: pd.DataFrame):
        """
        Update options and values from list of options

        Args:
            headers_df (pd.DataFrame): headers in pandas dataframe

        Returns:
            None.

        """

        options = [
            tuple(i)
            for i in headers_df[["location_id", "location_name"]]
            .drop_duplicates()
            .to_records(index=False)
        ]
        options.sort(key=lambda a: a[1])
        return options

    def add_to_sets(self, filter_id: str, headers_df: pd.DataFrame, properties: dict):
        """
        Add locations to sets

        Args:
            filter_id (str): id of filter value
            headers_df (pd.DataFrame): headers in pandas dataframe
            properties (dict): properties to append to map_locations

        Returns:
            None.

        """

        # create a grouper with parameter_ids and child_ids
        grouper = headers_df.groupby("location_id")
        parameters_series = grouper["parameter_ids"].unique()
        child_series = grouper["child_ids"].unique()

        # create a location set from grouper
        ids = [i for i, _ in grouper]
        df = self.locations.loc[ids]
        df["x"] = df["x"].astype(float)
        df["y"] = df["y"].astype(float)
        df["parameter_ids"] = parameters_series
        df["child_ids"] = child_series
        df.drop(columns=["parent_id", "geometry"], inplace=True)

        # add drawing properties
        for k, v in properties.items():
            df[k] = v

        # append to set
        self.sets.set_data(df, filter_id)

    def update_map_locations(self, filter_ids: List[str]):
        """
        Concat sets of location ids to map locations

        Args:
            filter_ids (List[str]): Filter ids to concat locations for.

        Returns:
            None.

        """

        def _defaults():
            return dict(
                line_color="black",
                fill_color="grey",
                nonselection_line_color="black",
                non_slection_fill_color="grey",
                label="meerdere filters",
            )

        def _flatten_series(series):
            result = series.iloc[0].to_dict()
            result["parameter_ids"] = list(
                set(itertools.chain(*series["parameter_ids"]))
            )
            for k, v in _defaults().items():
                result[k] = v
            return result

        if filter_ids:
            sets = [self.sets.data[i] for i in filter_ids if self.sets.exists(i)]
            df = pd.concat(sets)
            if df.index.has_duplicates:
                duplicates = [i for i in df.index if list(df.index).count(i) > 1]
                new_df = pd.DataFrame.from_dict(
                    {i: _flatten_series(df.loc[i]) for i in duplicates}, orient="index"
                )
                new_df.index.name = "id"
                df = df.loc[[i for i in df.index if i not in duplicates]]
                df = pd.concat([df, new_df])
            self.app_df = df

        else:
            self.app_df = pd.DataFrame(MAP_LOCATIONS).set_index("id")
