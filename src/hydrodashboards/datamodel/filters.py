from typing import List
from .models import BaseModel, Filter
from bokeh.models import MultiSelect
from bokeh.layouts import column

MAX_FILTER_LEN = 5
SIZING_MODE = "stretch_width"


class Filters(BaseModel):
    filters: List[Filter]
    bokeh: List[MultiSelect] = None

    @classmethod
    def from_fews(cls, pi_filters: dict = None, dashboard="bokeh"):
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

    def to_bokeh(self) -> List[MultiSelect]:

        if self.bokeh is None:
            bokeh_filters = column(
                [
                    i.to_multi_select(sizing_mode=SIZING_MODE, max_filter_len=MAX_FILTER_LEN)
                    for i in self.filters
                ],
                name="filters",
                sizing_mode=SIZING_MODE,
            )

            self.bokeh = bokeh_filters

        return self.bokeh
