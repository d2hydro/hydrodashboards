from typing import List
from hydrodashboards.datamodel.models import Filter
from hydrodashboards.datamodel.cache import Cache
from dataclasses import dataclass, field


MAX_FILTER_LEN = 5
SIZING_MODE = "stretch_width"


@dataclass
class TimeSeriesFilter(Filter):
    id: str = None
    cache: Cache = field(default_factory=Cache(sub_dir="filters"))


@dataclass
class Filters:
    filters: List[TimeSeriesFilter] = field(default_factory=list)
    thematic_view: bool = False
    thematic_filters: List[TimeSeriesFilter] = field(default_factory=list)

    def __post_init__(self):
        if self.thematic_view:
            self.thematic_filters = self.generate_thematic_filters()

    @classmethod
    def from_fews(cls, pi_filters: dict = None, thematic_view=False):
        def _pi_to_dict(fews_filter: dict) -> Filter:
            title = f'{fews_filter["name"]}'
            value = []
            if "child" in fews_filter.keys():
                options = [(i["id"], i["name"]) for i in fews_filter["child"]]
            else:
                options = []
            return TimeSeriesFilter(
                id=fews_filter["id"], title=title, value=value, options=options
            )

        children = pi_filters[0]["child"]

        return cls(
            filters=[_pi_to_dict(i) for i in children], thematic_view=thematic_view
        )

    def generate_thematic_filters(self):
        theme = {}
        theme["options"] = [(i.id, i.title) for i in self.filters]
        theme["value"] = [i.id for i in self.filters if i.value]
        theme["id"] = "themes"
        theme["title"] = "Thema's"

        filters = {}
        filters["id"] = "filters"
        filters["title"] = "Filters"
        return [TimeSeriesFilter(**theme), TimeSeriesFilter(**filters)]

    def get_filter_options(self, active=None):
        options = [self.filters[i].options for i in active]
        options = [j for i in options for j in i]
        values = [i[0] for i in options]
        labels = [i[1] for i in options]
        return options, values, labels

    def values_by_actives(self, actives):
        if self.thematic_view:
            self.thematic_filters[1].set_active(actives)
            values = self.thematic_filters[1].value
        else:
            for idx, i in enumerate(self.filters):
                i.set_active(actives[idx])
            values = [i.value for i in self.filters]
            values = [j for i in values for j in i]
        return values

    def get_filter(self, id):
        return next((i for i in self.filters if id in [j[0] for j in i.options]), None)

    def get_filter_index(self, id):
        return next(
            (
                idx
                for idx, i in enumerate(self.filters)
                if id in [j[0] for j in i.options]
            ),
            None,
        )

    def get_name(self, filter_id, locations_filter):
        options = locations_filter.options
        return next((i[1] for i in options if i[0] == filter_id), None)

    @property
    def values(self):
        values = [[j[0] for j in i.options] for i in self.filters]
        return [j for i in values for j in i]

    def value(self, thematic_view=True):
        if thematic_view:
            value = self.thematic_filters[1].value
        else:
            values = [i.value for i in self.filters]
            value = [j for i in values for j in i]
        return value
