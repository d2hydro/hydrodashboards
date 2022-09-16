from typing import List
from .models import Filter
from dataclasses import dataclass, field

MAX_FILTER_LEN = 5
SIZING_MODE = "stretch_width"


@dataclass
class LocationsFilter(Filter):
    id: str = None
    cache: dict = field(default_factory=dict)
        
@dataclass
class Filters:
    filters: List[LocationsFilter] = field(default_factory=list)

    @classmethod
    def from_fews(cls, pi_filters: dict = None):
        def _pi_to_dict(fews_filter: dict) -> Filter:
            title = f'{fews_filter["name"]}'
            value = []
            if "child" in fews_filter.keys():
                options = [(i["id"], i["name"]) for i in fews_filter["child"]]
            else:
                options = []
            return LocationsFilter(
                id=fews_filter["id"], title=title, value=value, options=options
            )

        children = pi_filters[0]["child"]

        return cls(filters=[_pi_to_dict(i) for i in children])

    def get_filter(self, id):
        return next((i for i in self.filters if id in [j[0] for j in i.options]), None)

    def get_name(self, filter_id, locations_filter):
        options = locations_filter.options
        return next((i[1] for i in options if i[0] == filter_id), None)

    @property
    def values(self):
        values = [[j[0] for j in i.options] for i in self.filters]
        return [j for i in values for j in i]

    @property
    def labels(self):
        labels = [[j[1] for j in i.options] for i in self.filters]
        return [j for i in labels for j in i]
