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
    language: str = "dutch"
    filter_colors: dict = field(default_factory=dict)
    map_overlays: dict = field(default_factory=dict)
    exclude_pars: list = field(default_factory=list)
    headers_full_history: list = field(default_factory=list)
    ssl_verify: bool = False
    history_period: int = 3650

    @classmethod
    def from_json(cls, config_json: Path = Path("config.json")):
        config_json = Path(config_json)
        config_dict = json.loads(config_json.read_text())
        return cls(**config_dict)
