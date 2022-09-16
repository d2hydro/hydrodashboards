from typing import List
from dataclasses import dataclass, field


@dataclass
class Filter:
    language: str = "dutch"
    title: str = None
    name: str = None
    options: List[tuple] = field(default_factory=list)
    value: list = field(default_factory=list)

    @property
    def labels(self):
        return [i[1] for i in self.options]

    @property
    def active(self):
        ids = [i[0] for i in self.options]
        return [ids.find(i) for i in self.value]
