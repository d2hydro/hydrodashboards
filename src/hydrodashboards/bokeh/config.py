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
    filter_dimensions: list
    disclaimer_file: Path = None
    fews_parallel: bool = False
    language: str = "dutch"
    thresholds: list = field(default_factory=list)
    filter_colors: dict = field(default_factory=dict)
    map_overlays: dict = field(default_factory=dict)
    exclude_pars: list = field(default_factory=list)
    headers_full_history: list = field(default_factory=list)
    ssl_verify: bool = False
    thematic_view: bool = False
    history_period: int = 3650

    def __post_init__(self):
        if self.disclaimer_file is not None:
            self.disclaimer_file = Path(self.disclaimer_file)
            if not self.disclaimer_file.is_absolute():
                self.disclaimer_file = Path(__file__).parent.joinpath(self.disclaimer_file).absolute().resolve()
            if not self.disclaimer_file.exists():
                raise FileNotFoundError(f"{self.disclaimer_file} does not exist")

    @classmethod
    def from_json(cls, config_json: Path = Path("config.json")):
        config_json = Path(config_json)
        config_dict = json.loads(config_json.read_text())
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
        config_json.write_text(json.dumps(self.__dict__, sort_keys=True, indent=4))
