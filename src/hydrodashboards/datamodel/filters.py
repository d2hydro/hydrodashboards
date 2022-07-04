from typing import List
from .models import Filter
from bokeh.models import MultiSelect
from bokeh.layouts import column
from dataclasses import dataclass, field

MAX_FILTER_LEN = 5
SIZING_MODE = "stretch_width"


@dataclass
class Filters:
    filters: List[Filter] = field(default_factory=list)
    _bokeh: column = None

    @classmethod
    def from_fews(cls, pi_filters: dict = None):
        def _pi_to_dict(fews_filter: dict) -> Filter:
            title = f'{fews_filter["name"]}'
            value = []
            if "child" in fews_filter.keys():
                options = [(i["id"], i["name"]) for i in fews_filter["child"]]
            else:
                options = []
            return Filter(title=title, value=value, options=options)

        children = pi_filters[0]["child"]

        return cls(filters=[_pi_to_dict(i) for i in children])

    @property
    def bokeh(self) -> column:
        if self._bokeh is None:
            self._bokeh = column(
                [
                    i.bokeh
                    for i in self.filters
                ],
                name="filters",
                sizing_mode=SIZING_MODE,
            )
        return self._bokeh
