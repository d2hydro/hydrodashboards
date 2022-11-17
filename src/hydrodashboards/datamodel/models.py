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
    search_input: str = ""

    @property
    def labels(self):
        return [i[1] for i in self.options]

    @property
    def selected_labels(self):
        return [self.labels[i] for i in self.active]

    @property
    def unselected_labels(self):
        return sorted([i for i in self.labels if i not in self.selected_labels])

    @property
    def unselected_options(self):
        return [i for idx, i in enumerate(self.options) if idx not in self.active]

    @property
    def selected_options(self):
        return [self.options[i] for i in self.active]

    def order_options(self, active):
        selected_options = sorted([self.options[i] for i in active], key=lambda x: x[1])
        unselected_options = sorted(
            [i for i in self.options if i not in selected_options], key=lambda x: x[1]
        )
        self.options = selected_options + unselected_options
        self.set_active([i for i in range(len(active))])

    def limit_options_on_search_input(self, search_input=None):
        if search_input is not None:
            self.search_input = search_input
        if len(self.search_input) >= 3:
            limited_options = [
                i for i in self.unselected_options if self.search_input in i[1].lower()
            ]
            self.options = self.selected_options + limited_options
        # else:
        #     self.options = self._options

    def get_values_by_actives(self, actives):
        return [self.options[i][0] for i in actives]

    def set_value(self, value):
        self.value = value
        ids = [i[0] for i in self.options]
        self.active = [ids.index(i) for i in value]

    def set_active(self, active):
        self.active = active
        self.value = [self.options[i][0] for i in active]

    def set_options(self, options):
        values = [i[0] for i in options]
        value = [i for i in self.value if i in values]
        selected_options = sorted(
            [options[values.index(i)] for i in value], key=lambda x: x[1]
        )
        unselected_options = sorted(
            [i for i in options if i not in selected_options], key=lambda x: x[1]
        )
        self.options = selected_options + unselected_options

    def clean_value(self):
        values = [i[0] for i in self.options]
        self.set_value([i for i in self.value if i in values])

    def update_from_options(self, options: List[tuple], limit_string=""):
        options.sort(key=lambda a: a[1])
        self._options = options
        self.set_options(options)
        self.limit_options_on_search_input()
        self.clean_value()
