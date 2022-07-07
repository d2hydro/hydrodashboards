# import FEWS API for reading data
from fewspy import Api

# import dashboard configuration
from hydrodashboards.bokeh.config import (
    EXCLUDE_PARS,
    FEWS_URL,
    FILTER_COLORS,
    FIRST_DATE,
    HEADERS_FULL_HISTORY,
    INIT_TIMEDELTA,
    ROOT_FILTER,
    SSL_VERIFY,
)

# import datamodel components
from hydrodashboards.datamodel import (
    Filters,
    Locations,
    Parameters,
    Periods,
    TimeSeriesSets,
)

from hydrodashboards.datamodel.placeholders import (
    SelectSearchTimeSeries,
    DownloadSearchTimeSeries,
    ViewPeriod,
    SearchTimeFigure,
)


# import functions from python modules
from datetime import datetime
import pandas as pd
import itertools


def _get_propeties(filter_id, filter_name):
    if filter_id in FILTER_COLORS.keys():
        line = FILTER_COLORS[filter_id]["line"]
        fill = FILTER_COLORS[filter_id]["fill"]
    else:
        line = "orange"
        fill = "black"

    return {
        "line_color": line,
        "nonselection_line_color": line,
        "fill_color": fill,
        "non_selection_fill_color": fill,
        "label": filter_name,
    }


class Data:
    def __init__(self, logger=None):
        self.logger = logger
        # help properties for internal use in class
        self._fews_api = Api(url=FEWS_URL, ssl_verify=SSL_VERIFY, logger=logger)
        self._fews_qualifiers = self._fews_api.get_qualifiers()
        self._fews_root_parameters = self._fews_api.get_parameters(
            filter_id=ROOT_FILTER
        )
        self._fews_root_locations = self._fews_api.get_locations(filter_id=ROOT_FILTER)
        self._fews_filters = self._fews_api.get_filters(filter_id=ROOT_FILTER)

        # time properties
        self.now = datetime.now()

        # properties matching dashboard layout
        self.filters = Filters.from_fews(self._fews_filters)
        self.locations = Locations.from_fews(self._fews_root_locations)
        self.parameters = Parameters.from_fews(
            pi_parameters=self._fews_root_parameters,
            pi_qualifiers=self._fews_qualifiers,
        )
        self.periods = Periods(self.now)

        self.time_series_sets = TimeSeriesSets()
        self.select_search_time_series = SelectSearchTimeSeries()
        self.download_search_time_series = DownloadSearchTimeSeries()
        self.view_period = ViewPeriod()
        self.search_time_figure = SearchTimeFigure()

    @property
    def app_status(self):
        locations = len(self.locations.value)
        parameters = len(self.parameters.value)
        time_series = 0

        return (
            f"Geselecteerd:<br>"
            f"<ul><li>locaties: {locations} (max 10)</li>"
            f"<li>parameters: {parameters}</li></ul>"
            f"Tijdseries geladen: {time_series}"
        )

    def update_on_filter_select(self, values: list):
        """
        Update data-class on selected filter

        Args:
            values (list): List with selected filter ids.

        Returns:
            None.

        """

        def _get_from_header(i):
            location_id = self.locations.parent_id_from_ts_header(i)

            # If the location is parent, it has no parent_id. And if the parent has no
            # timeseries the location can not be revealed via the FEWS API. In both
            # cases we use the location_id in the app.
            if pd.isna(location_id) | (
                location_id not in self.locations.locations.index
            ):
                location_id = i.location_id
            if location_id in self.locations.locations.index:
                child_id = i.location_id
                location_name = self.locations.locations.loc[location_id]["name"]
                parameter_id = self.parameters.id_from_ts_header(i)
                parameter_name = self.parameters.name_from_ts_header(i)
                return [
                    location_id,
                    location_name,
                    child_id,
                    parameter_id,
                    parameter_name,
                ]
            else:
                return [None for i in range(5)]

        def _pi_headers_to_df(pi_headers):
            df = pd.DataFrame.from_records(
                data=[_get_from_header(i.header) for i in pi_headers.time_series],
                columns=[
                    "location_id",
                    "location_name",
                    "child_ids",
                    "parameter_ids",
                    "parameter_names",
                ],
            )
            df = df.loc[~df["parameter_ids"].isin(EXCLUDE_PARS)]
            return df

        all_locations = []
        all_parameters = []

        for filter_id in values:
            filter_data = self.filters.get_filter(filter_id)
            filter_name = self.filters.get_name(filter_id, filter_data)

            # get locations and parameters from sub-filter
            if filter_id not in filter_data.cache.keys():  # add to cache if
                if filter_id in HEADERS_FULL_HISTORY:
                    start_time = datetime(1900, 1, 1)
                else:
                    start_time = self.now
                pi_headers = self._fews_api.get_time_series(
                    filter_id=filter_id,
                    start_time=start_time,
                    end_time=self.now,
                    only_headers=True,
                )
                headers_df = _pi_headers_to_df(pi_headers)

                locations = self.locations.options_from_headers_df(headers_df)
                parameters = self.parameters.options_from_headers_df(headers_df)
                filter_data.cache[filter_id] = {
                    "locations": locations,
                    "parameters": parameters,
                }

            else:
                locations, parameters = filter_data.cache[filter_id].values()

            # if not yet in sets, add it there too
            if filter_id not in self.locations.sets.keys():
                properties = _get_propeties(filter_id, filter_name)
                self.locations.add_to_sets(filter_id, headers_df, properties)

            # add locations and parameters to list
            all_locations = list(set(all_locations + locations))
            all_parameters = list(set(all_parameters + parameters))

        # update locations and parameter filter data
        self.locations.update_from_options(all_locations)
        self.parameters.update_from_options(all_parameters)

        # update map_locations
        self.locations.update_map_locations(values)

    def update_on_locations_select(self, values: list):
        """
        Update data-class on selected locations

        Args:
            values (list): List with selected location ids.

        Returns:
            None.

        """

        # update locations.value to values
        self.locations.value = values

        # update parameters to selected values
        if values:
            df = self.locations.app_df.loc[values]
            parameter_ids = df["parameter_ids"].explode().to_list()
            options = [i for i in self.parameters._options if i[0] in parameter_ids]
            options.sort(key=lambda a: a[1])
            self.parameters.options = options
        else:
            self.parameters.options = self.parameters._options

        # clean parameter value to options
        self.parameters.clean_value()

    def update_time_series(self):
        def labels_by_location(location):
            children = list(self.locations.app_df.loc[location]["child_ids"])
            parameters = [
                i
                for i in self.locations.app_df.loc[location]["parameter_ids"]
                if i in self.parameters.value
            ]

            return list(itertools.product(children, parameters))

        def get_labels():
            labels_gen = (labels_by_location(i) for i in self.locations.value)
            return [i for i in itertools.chain(*labels_gen)]

        labels = get_labels()
        self.time_series_sets.append_from_labels(labels)
        self.time_series_sets.set_active(labels)
