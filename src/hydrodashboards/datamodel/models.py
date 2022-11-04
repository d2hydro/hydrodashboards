from typing import List
from dataclasses import dataclass, field


@dataclass
class Filter:
    language: str = "dutch"
    title: str = None
    name: str = None
    options: List[tuple] = field(default_factory=list)
    value: list = field(default_factory=list)
    active: list = field(default_factory=list)

    @property
    def labels(self):
        return [i[1] for i in self.options]

    def get_values_by_actives(self, actives):
        return [self.options[i][0] for i in actives]

    def set_value(self, value):
        self.value = value
        ids = [i[0] for i in self.options]
        self.active = [ids.index(i) for i in value]

    def set_active(self, active):
        self.active = active
        self.value = [self.options[i][0] for i in active]
