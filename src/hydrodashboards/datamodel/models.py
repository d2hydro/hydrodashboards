from pydantic import BaseModel as PydanticBaseModel
from pydantic import validator
from typing import List
from bokeh.models import MultiSelect


class BaseModel(PydanticBaseModel):
    class Config:
        arbitrary_types_allowed = True


class Filter(BaseModel):
    title: str
    options: List[tuple]
    value: list = []
    multi_select: MultiSelect = None

    def to_multi_select(
        self, sizing_mode: str = "stretch_width", max_filter_len: int = 5
    ) -> MultiSelect:
        title = f"{self.title}:"
        multi_select = MultiSelect(title=title, value=self.value, options=self.options)
        multi_select.size = min(len(multi_select.options), max_filter_len)
        multi_select.sizing_mode = sizing_mode
        self.multi_select = multi_select
        return multi_select
