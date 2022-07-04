from bokeh.models import MultiSelect
from hydrodashboards.bokeh.language import parameters_title
from hydrodashboards.datamodel.models import Filter
from fewspy.time_series import TimeSeries
import geopandas as gpd
import pandas as pd
from typing import List
from dataclasses import dataclass, field


@dataclass
class Parameters(Filter):
    _fews_parameters: pd.DataFrame = pd.DataFrame()
    _fews_qualifiers: pd.DataFrame = pd.DataFrame()

    def __post_init__(self):
        self.title = parameters_title[self.language]
        self.name = "parameters"

    @classmethod
    def from_fews(
        cls,
        pi_parameters: pd.DataFrame = pd.DataFrame(),
        pi_qualifiers: pd.DataFrame = pd.DataFrame(),
        language="dutch",
    ):
        return cls(
            language=language,
            _fews_parameters=pi_parameters,
            _fews_qualifiers=pi_qualifiers,
        )

    def update_from_pi_headers(self, pi_headers: TimeSeries, exclude_pars: list = []):
        def _concat_options(header, exclude_pars=[]):
            parameter_id = header.parameter_id
            parameter_name = self._fews_parameters.loc[parameter_id]["name"]
            if header.qualifier_id is not None:
                parameter_id = f"{parameter_id} * {'*'.join(header.qualifier_id)}"
                qualifier_names = [
                    self._fews_qualifiers.loc[i]["name"] for i in header.qualifier_id
                ]
                parameter_name = f"{parameter_name} ({' '.join(qualifier_names)})"

            return parameter_id, parameter_name

        options = list(set([_concat_options(i.header) for i in pi_headers.time_series]))
        options = [i for i in options if i[0] not in exclude_pars]
        options.sort(key=lambda a: a[1])
        values = [i[0] for i in options]

        # update options and values
        self.options = self.bokeh.options = options
        self.value = self.bokeh.value = [i for i in self.value if i in values]
        return options
