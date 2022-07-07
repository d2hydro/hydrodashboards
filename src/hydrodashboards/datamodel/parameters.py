from hydrodashboards.bokeh.language import parameters_title
from hydrodashboards.datamodel.models import Filter
import pandas as pd
from dataclasses import dataclass, field
from typing import List
from .utils import concat_fews_parameter_names, concat_fews_parameter_ids

@dataclass
class Parameters(Filter):
    _fews_parameters: pd.DataFrame = pd.DataFrame()
    _fews_qualifiers: pd.DataFrame = pd.DataFrame()
    _options: List[tuple] = field(default_factory=list)

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

    def id_from_ts_header(self, header):
        parameter_id = header.parameter_id
        if header.qualifier_id is not None:
            qualifier_ids = header.qualifier_id
            parameter_id = concat_fews_parameter_ids(parameter_id, qualifier_ids)
        return parameter_id

    def name_from_ts_header(self, header):
        parameter_id = header.parameter_id
        parameter_name = self._fews_parameters.loc[parameter_id]["name"]
        if header.qualifier_id is not None:
            qualifier_names = [
                self._fews_qualifiers.loc[i]["name"] for i in header.qualifier_id
            ]
            parameter_name = concat_fews_parameter_ids(parameter_name, qualifier_names)

        return parameter_name

    def clean_value(self):
        values = [i[0] for i in self.options]
        self.value = [i for i in self.value if i in values]

    def update_from_options(self, options: List[tuple], reinit=True):
        self._options = options
        if reinit:
            self.options = self._options
        self.clean_value()

    def options_from_headers_df(self, headers_df: pd.DataFrame):
        """
        Update options and values from list of options

        Args:
            headers_df (pd.DataFrame): headers in pandas dataframe

        Returns:
            None.

        """

        options = [
            tuple(i)
            for i in headers_df[["parameter_ids", "parameter_names"]]
            .drop_duplicates()
            .to_records(index=False)
        ]
        options.sort(key=lambda a: a[1])
        return options
