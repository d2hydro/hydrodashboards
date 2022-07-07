from typing import List
from dataclasses import dataclass, field


@dataclass
class Filter:
    language: str = "dutch"
    title: str = None
    name: str = None
    options: List[tuple] = field(default_factory=list)
    value: list = field(default_factory=list)
