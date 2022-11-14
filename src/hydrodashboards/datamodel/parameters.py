from hydrodashboards.bokeh.language import parameters_title
from hydrodashboards.datamodel.models import Filter
import pandas as pd
from dataclasses import dataclass, field
from typing import List
from .utils import (
    concat_fews_parameter_names,
    concat_fews_parameter_ids,
    split_parameter_id_to_fews,
)


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
        return concat_fews_parameter_ids(header.parameter_id, header.qualifier_id)

    def name_from_ts_header(self, header):
        parameter_id = header.parameter_id
        parameter_name = self._fews_parameters.at[parameter_id, "name"]
        if header.qualifier_id is not None:
            qualifier_names = [
                self._fews_qualifiers.at[i, "name"] for i in header.qualifier_id
            ]
        else:
            qualifier_names = None
        parameter_name = concat_fews_parameter_names(parameter_name, qualifier_names)

        return parameter_name

    def get_groups(self, parameter_source="fews"):
        if parameter_source == "fews":
            groups = {
                i: self._fews_parameters.at[
                    split_parameter_id_to_fews(i)[0], "parameter_group"
                ]
                for i in self.value
            }
        return groups

    def get_y_labels(self, vertical_datum):
        parameter_groups = list(set(self.get_groups().values()))
        if "parameter_group_name" in self._fews_parameters.columns:
            label_column = "parameter_group_name"
        else:
            label_column = "parameter_group"

        def _label(parameter_group):
            row = self._fews_parameters[self._fews_parameters["parameter_group"] == parameter_group].iloc[0]

            label = f"{row[label_column]} [{row.display_unit}]"
            if row.uses_datum:
                label = f"{label} [{vertical_datum}]"
            return label

        return {i: _label(i) for i in parameter_groups}


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
