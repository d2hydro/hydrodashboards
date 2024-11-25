from dataclasses import dataclass, field
from pathlib import Path
import json
from datetime import time

MAX_GRAPH_COUNT = 4
DEFAULT_SAMPLE_CONFIG = {"method": "random_sample", "max_samples": 20000}
TIME_PROPERTIES = ["cache_rebuild_time"]


@dataclass
class Config:
    bounds: list
    filter_dimensions: list
    fews_url: str
    log_dir: Path
    root_filter: str
    title: str
    cache_rebuild_time: time = field(default_factory=time)
    cache_filters: list = field(default_factory=list)
    cache_time_series_update_interval_min: int = None
    disclaimer_file: Path = None
    exclude_pars: list = field(default_factory=list)
    fews_parallel: bool = False
    filter_colors: dict = field(default_factory=dict)
    graph_count: int = 2
    headers_full_history: list = field(default_factory=list)
    history_period: int = 3650
    language: str = "dutch"
    map_overlays: dict = field(default_factory=dict)
    ports: list = field(default_factory=dict)
    ssl_verify: bool = False
    thematic_view: bool = False
    thresholds: list = field(default_factory=list)
    time_series_sampling: dict = field(default_factory=None)
    vertical_datum: str = "NAP"
    remove_duplicates: bool = False

    def __post_init__(self):
        if self.disclaimer_file is not None:
            self.disclaimer_file = Path(self.disclaimer_file)
            if not self.disclaimer_file.is_absolute():
                self.disclaimer_file = (
                    Path(__file__)
                    .parent.joinpath(self.disclaimer_file)
                    .absolute()
                    .resolve()
                )
            if not self.disclaimer_file.exists():
                raise FileNotFoundError(f"{self.disclaimer_file} does not exist")
        self.graph_count = min(self.graph_count, MAX_GRAPH_COUNT)
        if not self.ports:
            self.ports = [5003]

    @staticmethod
    def __deserialize_values(config_dict):
        for i in TIME_PROPERTIES:
            if i in config_dict.keys():
                if config_dict[i] is not None:
                    config_dict[i] = time.fromisoformat(config_dict[i])
        return config_dict

    @staticmethod
    def __serialize_values(config_dict):
        for i in TIME_PROPERTIES:
            if i in config_dict.keys():
                if config_dict[i] is not None:
                    config_dict[i] = config_dict[i].isoformat()
        return config_dict

    @classmethod
    def from_json(cls, config_json: Path = Path("config.json")):
        config_json = Path(config_json)
        config_dict = cls.__deserialize_values(json.loads(config_json.read_text()))
        return cls(**config_dict)

    @property
    def location_attributes(self):
        return [i["attribute"] for i in self.thresholds]

    @property
    def filter_css_heights(self):
        def _height(i):
            px = 22
            if i["items"] > 1:
                px += 22
                px += (i["items"] - 2) * 18
            if i["long_names"]:
                px += 8
            return px

        return [_height(i) for i in self.filter_dimensions]

    @property
    def filter_selector(self):
        return "active"

    def to_json(self, config_json):
        config_json = Path(config_json)
        config_dict = self.__serialize_values(self.__dict__)
        config_json.write_text(json.dumps(config_dict, sort_keys=True, indent=4))
