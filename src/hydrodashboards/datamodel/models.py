from typing import List
from dataclasses import dataclass, field


@dataclass
class Filter:
    language: str = "dutch"
    title: str = None
    name: str = None
    options: List[tuple] = field(default_factory=list)
    _value: list = field(default_factory=list)
    _active: list = field(default_factory=list)

    @property
    def labels(self):
        return [i[1] for i in self.options]

    @property
    def value(self):
        if self._value:
            return self._value
        else:
            return [self.options[i][0] for i in self._active]

    @property
    def active(self):
        if self._active:
            return self._active
        else:
            ids = [i[0] for i in self.options]
            return [ids.find(i) for i in self._value]

    def get_values_by_actives(self, actives):
        return [self.options[i][0] for i in actives]

    def set_value(self, value):
        self._value = value

    def set_active(self, active):
        self._active = active
