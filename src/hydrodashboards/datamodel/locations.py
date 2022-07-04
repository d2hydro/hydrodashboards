from hydrodashboards.bokeh.language import locations_title
from hydrodashboards.datamodel.models import Filter
from fewspy.time_series import TimeSeries
import geopandas as gpd
from dataclasses import dataclass

COLUMNS = [
    "id",
    "name",
    "x",
    "y",
    "parent_id",
    "geometry",
]
EMPTY_SET = gpd.GeoDataFrame(columns=COLUMNS).set_index("id")


@dataclass
class Locations(Filter):
    locations: gpd.GeoDataFrame = EMPTY_SET

    def __post_init__(self):
        self.title = locations_title[self.language]
        self.name = "locations"

    @classmethod
    def from_fews(cls, pi_locations: gpd.GeoDataFrame = None, language="dutch"):
        df = pi_locations.rename(
            columns={"short_name": "name", "parent_location_id": "parent_id"}
        )
        df.index.name = "id"
        df.drop(columns=[i for i in df.columns if i not in COLUMNS], inplace=True)
        return cls(language=language, locations=df)

    def update_from_pi_headers(self, pi_headers: TimeSeries):
        if not pi_headers.empty:
            locations = set([i.header.location_id for i in pi_headers.time_series])
            series = self.locations[self.locations["parent_id"].isna()]["name"]
            series = series[series.index.isin(locations)]
            # update options and values
        options = list(zip(series.index, series.values))
        options.sort(key=lambda a: a[1])
        values = [i[0] for i in options]
        self.options = self.bokeh.options = options
        self.value = self.bokeh.value = values
        return locations
