from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class Config:
    log_dir: Path
    title: str
    bounds: list
    fews_url: str
    root_filter: str
    filter_dimensions: dict
    filter_type: str = "MultiSelect"
    language: str = "dutch"
    thresholds: list = field(default_factory=list)
    filter_colors: dict = field(default_factory=dict)
    map_overlays: dict = field(default_factory=dict)
    exclude_pars: list = field(default_factory=list)
    headers_full_history: list = field(default_factory=list)
    ssl_verify: bool = False
    thematic_view: bool = False
    history_period: int = 3650

    @classmethod
    def from_json(cls, config_json: Path = Path("config.json")):
        config_json = Path(config_json)
        config_dict = json.loads(config_json.read_text())
        return cls(**config_dict)

    @property
    def location_attributes(self):
        return [i["attribute"] for i in self.thresholds]

    @property
    def filter_height(self):
        if self.thematic_view:
            height = 240
        else:
            filters = self.filter_dimensions["filters"]
            children = self.filter_dimensions["child_filters"]
            height = 61 * filters + (children - filters) * 17
        return height

    @property
    def filter_selector(self):
        if self.filter_type == "MultiSelect":
            return "value"
        elif self.filter_type == "CheckBoxGroup":
            return "active"
