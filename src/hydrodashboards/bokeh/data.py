# import FEWS API for reading data
from fewspy import Api

# import dashboard configuration
try:
    from config import (
        EXCLUDE_PARS,
        FEWS_URL,
        FILTER_COLORS,
        HEADERS_FULL_HISTORY,
        HISTORY_PERIOD,
        ROOT_FILTER,
        SSL_VERIFY,
    )
except ModuleNotFoundError:
    from hydrodashboards.bokeh.config import (
        EXCLUDE_PARS,
        FEWS_URL,
        FILTER_COLORS,
        HEADERS_FULL_HISTORY,
        HISTORY_PERIOD,
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

# import utilities
from hydrodashboards.datamodel.utils import (
    split_parameter_id_to_fews,
    concat_fews_parameter_ids,
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
    def __init__(self, logger=None, now: datetime = datetime.now()):
        self.logger = logger
        # fews properties
        self._fews_api = Api(url=FEWS_URL, ssl_verify=SSL_VERIFY, logger=logger)
        self._fews_qualifiers = self._fews_api.get_qualifiers()
        self._fews_root_parameters = self._fews_api.get_parameters(
            filter_id=ROOT_FILTER
        )
        self._fews_root_locations = self._fews_api.get_locations(filter_id=ROOT_FILTER)
        self._fews_filters = self._fews_api.get_filters(filter_id=ROOT_FILTER)

        # time properties
        self.now = now
        self.periods = Periods(self.now, history_period=HISTORY_PERIOD)

        # data-classes linked to dashboard
        self.filters = Filters.from_fews(self._fews_filters)
        self.locations = Locations.from_fews(self._fews_root_locations)
        self.parameters = Parameters.from_fews(
            pi_parameters=self._fews_root_parameters,
            pi_qualifiers=self._fews_qualifiers,
        )

        self.time_series_sets = TimeSeriesSets()

    """

    Section with FEWS API helper functions

    """

    def _fews_locators_from_generator(self, generator):
        """Returns location_ids, parameter_ids and qualifier_ids from list"""
        location_ids, parameter_ids, qualifier_ids = list(map(list, zip(*generator)))
        location_ids = list(set(location_ids))
        parameter_ids = list(set(parameter_ids))
        qualifier_ids = [list(i) for i in set(map(tuple, qualifier_ids))]
        return location_ids, parameter_ids, qualifier_ids

    def _fews_locators_from_indices(self, indices):
        generator = [[i[0], *split_parameter_id_to_fews(i[1])] for i in indices]
        return self._fews_locators_from_generator(generator)

    def _fews_locators_from_ts(self, time_series):
        generator = [
            [i.location, *split_parameter_id_to_fews(i.parameter)] for i in time_series
        ]
        return self._fews_locators_from_generator(generator)

    def _get_thinning(self, width=1500, selection="view"):
        if selection == "view":
            period = self.periods.view_period
        elif selection == "search":
            period = self.periods.search_period
        return int(period.total_seconds() * 1000 / width)

    def _get_fews_ts(self, indices=None, request_type="headers"):
        only_headers = False
        thinning = None
        if request_type == "headers":
            only_headers = True
            (
                location_ids,
                parameter_ids,
                qualifier_ids,
            ) = self._fews_locators_from_indices(indices)
            start_time = self.periods.history_start
            end_time = self.periods.now
        elif request_type == "search":
            thinning = self._get_thinning(selection="search")
            (
                location_ids,
                parameter_ids,
                qualifier_ids,
            ) = self._fews_locators_from_indices(indices)
            start_time = self.periods.search_start
            end_time = self.periods.search_end
        elif request_type == "view":
            thinning = self._get_thinning()
            time_series = self.time_series_sets.select_view(self.periods)
            location_ids, parameter_ids, qualifier_ids = self._fews_locators_from_ts(
                time_series
            )
            start_time = self.periods.view_start
            end_time = self.periods.view_end
        elif request_type == "history":
            time_series = self.time_series_sets.select_incomplete()
            location_ids, parameter_ids, qualifier_ids = self._fews_locators_from_ts(
                time_series
            )
            start_time = self.periods.search_start
            end_time = self.periods.search_end

        return self._fews_api.get_time_series(
            filter_id=ROOT_FILTER,
            location_ids=location_ids,
            parameter_ids=parameter_ids,
            qualifier_ids=qualifier_ids,
            start_time=start_time,
            end_time=end_time,
            thinning=thinning,
            only_headers=only_headers,
        )

    def _properties_from_fews_ts_headers(self, fews_time_series):
        def property_generator(header):
            parameter = concat_fews_parameter_ids(
                header.parameter_id, header.qualifier_id
            )
            parameter_name = next(
                i[1] for i in self.parameters.options if i[0] == parameter
            )
            location_name = self.locations.locations.loc[header.location_id]["name"]
            label = f"{location_name} {parameter_name}"
            return dict(location=header.location_id,
                        parameter=parameter,
                        parameter_name=parameter_name,
                        label=label)

        return [property_generator(i.header) for i in fews_time_series]

    def _update_ts_from_fews_ts_set(self, fews_ts_set, complete=False):
        def erasing_data(new, old):
            if old.empty:
                return False
            elif new.empty:
                return True
#            else:
#                return (new.index[0] > old.index[0]) and (new.index[-1] < old.index[-1])

        if not fews_ts_set.empty:
            for fews_ts in fews_ts_set.time_series:
                location_id = fews_ts.header.location_id
                parameter_id = concat_fews_parameter_ids(
                    fews_ts.header.parameter_id, fews_ts.header.qualifier_id
                )
                ts_idx = list(self.time_series_sets.indices).index(
                    (location_id, parameter_id)
                )
                ts_select = self.time_series_sets.time_series[ts_idx]
                if not erasing_data(fews_ts.events, ts_select.df):
                    ts_select.df = fews_ts.events
                    ts_select.complete = complete
                    ts_select.empty = fews_ts.events.empty
                    ts_select.start_datetime = fews_ts.header.start_date
                    ts_select.end_datetime = fews_ts.header.end_date

    """

    Section with functions called in app callbacks

    """

    def app_status(self, html_type="table"):
        locations = len(self.locations.value)
        parameters = len(self.parameters.value)
        time_series_active = self.time_series_sets.active_length
        time_series_cache = len(self.time_series_sets)

        if html_type == "list":
            html = (
                f"Geselecteerd:<br>"
                f"<ul><li>locaties: {locations} (max 10)</li>"
                f"<li>parameters: {parameters}</li></ul>"
                f"Tijdseries:<br>"
                f"<ul><li>geladen: {time_series_active}</li>"
                f"<li>cache: {time_series_cache}</li></ul>"
            )
        elif html_type == "table":
            html = ('<table style="width:100%">'
                    "<tr>"
                    f"<td>locaties: {locations} (max 10)</td>"
                    f"<td>parameters: {parameters}</td>"
                    f"<td>tijdseries: {time_series_active}</td>"
                    f"<td>tijdseries cache: {time_series_cache}</td>"
                    "<tr>"
                    "</table>"
                    )

        return html

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

    def extend_time_series(self, search_datetime, insert=True):
        print(f"extend timeseries from {search_datetime} insert: {insert}")

    def update_time_series_search(self):
        if self.time_series_sets.select_incomplete():
            fews_ts_set = self._get_fews_ts(request_type="history")
            self._update_ts_from_fews_ts_set(fews_ts_set, complete=True)

    def update_time_series(self):
        """
        Updates time_series when button is clicked.

        Returns:
            TYPE: DESCRIPTION.

        """

        # get headers and initalize time series
        indices = self.locations.max_time_series_indices(self.parameters.value)
        fews_ts_set = self._get_fews_ts(indices=indices, request_type="headers")
        properties = self._properties_from_fews_ts_headers(fews_ts_set.time_series)
        self.time_series_sets.append_from_dict(properties)
        self.time_series_sets.set_active(indices)

        # set data for search time_series
        first_active = self.time_series_sets.first_active
        if not first_active.within_period(period=self.periods, selection="search"):
            fews_ts_set = self._get_fews_ts(
                indices=[first_active.index], request_type="search"
            )

            self._update_ts_from_fews_ts_set(fews_ts_set)

        # set data for view time_series
        if self.time_series_sets.select_view(self.periods):
            fews_ts_set = self._get_fews_ts(request_type="view")

            self._update_ts_from_fews_ts_set(fews_ts_set)

        #self.update_time_series_history()
        #print(self.time_series_sets.time_series)
      