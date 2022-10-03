# import FEWS API for reading data
from fewspy import Api

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

from hydrodashboards import __version__

# import functions from python modules
from datetime import datetime
import pandas as pd

FEWS_BUGS = dict(qualifier_ids=True)


def _get_propeties(filter_id, filter_name, filter_colors):
    if filter_id in filter_colors.keys():
        line = filter_colors[filter_id]["line"]
        fill = filter_colors[filter_id]["fill"]
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
    def __init__(self, config, logger=None, now: datetime = datetime.now()):
        self.config = config
        self.logger = logger
        # fews properties
        self._fews_api = Api(
            url=self.config.fews_url, ssl_verify=self.config.ssl_verify, logger=logger
        )
        self._fews_qualifiers = self._fews_api.get_qualifiers()
        self._fews_root_parameters = self._fews_api.get_parameters(
            filter_id=self.config.root_filter
        )
        self._fews_root_locations = self._fews_api.get_locations(
            filter_id=self.config.root_filter,
            attributes=self.config.location_attributes,
        )
        self._fews_filters = self._fews_api.get_filters(
            filter_id=self.config.root_filter
        )

        # time properties
        self.now = now
        self.periods = Periods(self.now, history_period=self.config.history_period)

        # data-classes linked to dashboard
        self.filters = Filters.from_fews(
            self._fews_filters, thematic_view=config.thematic_view
        )
        self.locations = Locations.from_fews(
            self._fews_root_locations, attributes=self.config.location_attributes
        )
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

        ## function used to bypass FEWS_BUGS["qualifier_ids"]
        def include_header(i):
            parameter_id = concat_fews_parameter_ids(
                i.header.parameter_id, i.header.qualifier_id
            )
            return parameter_id in self.parameters.value

        only_headers = False
        thinning = None
        if request_type == "headers":
            only_headers = True
            parallel = False
            (
                location_ids,
                parameter_ids,
                qualifier_ids,
            ) = self._fews_locators_from_indices(indices)
            # start_time = self.periods.search_start
            start_time = self.periods.search_end
            end_time = self.periods.search_end
            # included as there is a bug in qualifier_ids requests
            if FEWS_BUGS["qualifier_ids"]:
                qualifier_ids = None
        elif request_type == "search":
            parallel = self.config.fews_parallel
            thinning = self._get_thinning(selection="search")
            (
                location_ids,
                parameter_ids,
                qualifier_ids,
            ) = self._fews_locators_from_indices(indices)
            start_time = self.periods.search_start
            end_time = self.periods.search_end
        elif request_type == "view":
            parallel = self.config.fews_parallel
            thinning = self._get_thinning()
            time_series = self.time_series_sets.select_view(self.periods)
            location_ids, parameter_ids, qualifier_ids = self._fews_locators_from_ts(
                time_series
            )
            start_time = self.periods.view_start
            end_time = self.periods.view_end
        elif request_type == "history":
            parallel = self.config.fews_parallel
            time_series = self.time_series_sets.select_incomplete()
            location_ids, parameter_ids, qualifier_ids = self._fews_locators_from_ts(
                time_series
            )
            start_time = self.periods.search_start
            end_time = self.periods.search_end

        result = self._fews_api.get_time_series(
            filter_id=self.config.root_filter,
            location_ids=location_ids,
            parameter_ids=parameter_ids,
            qualifier_ids=qualifier_ids,
            start_time=start_time,
            end_time=end_time,
            thinning=thinning,
            only_headers=only_headers,
            parallel=parallel,
        )
        # included as there is a bug in qualifier_ids requests
        if (request_type == "headers") & FEWS_BUGS["qualifier_ids"]:
            result.time_series = [i for i in result.time_series if include_header(i)]

        return result

    def _properties_from_fews_ts_headers(self, fews_time_series):
        def property_generator(header):
            parameter = concat_fews_parameter_ids(
                header.parameter_id, header.qualifier_id
            )
            parameter_name = next(
                i[1] for i in self.parameters.options if i[0] == parameter
            )
            location_name = self.locations.locations.at[header.location_id, "name"]
            label = f"{location_name} {parameter_name}"

            # prepare tags
            xy = ",".join(self.locations.locations.loc[header.location_id, ["x", "y"]])
            if header.qualifier_id is None:
                qualifiers_tag = ""
            else:
                qualifiers_tag = ",".join(header.qualifier_id)
            unit_tag = self.parameters._fews_parameters.at[
                header.parameter_id, "display_unit"
            ]
            tags = [
                header.location_id,
                location_name,
                xy,
                header.parameter_id,
                qualifiers_tag,
                unit_tag,
            ]

            return dict(
                location=header.location_id,
                parameter=parameter,
                parameter_name=parameter_name,
                units=header.units,
                label=label,
                tags=tags,
            )

        return [property_generator(i.header) for i in fews_time_series]

    def _update_ts_from_fews_ts_set(self, fews_ts_set, complete=False):
        def erasing_data(new, old):
            if old.empty:
                return False
            elif new.empty:
                return True

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
        search_period_days = self.periods.search_period.days
        max_events_loaded = self.time_series_sets.max_events_loaded
        max_events_visible = self.time_series_sets.max_events_visible

        if html_type == "list":
            html = (
                f"Geselecteerd:<br>"
                f"<ul><li>locaties: {locations} (max 10)</li>"
                f"<li>parameters: {parameters}</li></ul>"
                f"Tijdseries:<br>"
                f"<ul><li>geladen: {time_series_active}</li>"
                f"<li>cache: {time_series_cache}</li>"
                f"<li>max tijdstappen: {max_events_visible}/{max_events_loaded} (zichtbaar/geladen)</li></ul>"
            )
        elif html_type == "table":
            html = (
                f"Versie: {__version__} | "
                f"Locaties: {locations} (max 10) | "
                f"Parameters: {parameters} | "
                f"Tijdseries: {time_series_active} | "
                f"Tijdseries cache: {time_series_cache} | "
                f"Zoekperiode: {search_period_days} dagen | "
                f"Max tijdstappen: {max_events_visible}/{max_events_loaded} (zichtbaar/geladen)"
            )

        return html

    def update_on_filter_select(self, selected: list):
        """
        Update data-class on selected filter

        Args:
            selected (list): List with selected filter ids or indices.

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
            df = df.loc[~df["parameter_ids"].isin(self.config.exclude_pars)]
            return df

        all_locations = []
        all_parameters = []

        if self.config.filter_type == "MultiSelect":
            values = selected
        elif self.config.filter_type == "CheckBoxGroup":
            values = self.filters.values_by_actives(selected)

        for filter_id in values:
            filter_data = self.filters.get_filter(filter_id)
            filter_name = self.filters.get_name(filter_id, filter_data)

            # get locations and parameters from sub-filter
            if filter_id not in filter_data.cache.keys():  # add to cache if
                if filter_id in self.config.headers_full_history:
                    start_time = self.periods.search_start
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
                properties = _get_propeties(
                    filter_id, filter_name, self.config.filter_colors
                )
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
        self.locations.set_value(values)

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
        self.time_series_sets.set_visible(indices=indices)

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

        # finalize time_series_sets with search_start and search_end
        self.time_series_sets.set_search_period(*self.periods.search_dates)

    def threshold_groups(self, time_series_groups):
        threshold_groups = {i: {} for i in list(self.parameters.get_groups().values())}

        def _get_label_and_value(df, threshold):
            df[i["attribute"]] = df[i["attribute"]].astype(float)
            df = df[df[i["attribute"]].notna()]
            if len(df) > 0:
                value = df[i["attribute"]].to_list()
                label = [f"{threshold['name']} {i}" for i in df["name"]]
                color = threshold["color"]
                line_width = threshold["line_width"]

                return dict(
                    label=label, value=value, color=color, line_width=line_width
                )
            else:
                return {}

        for k, v in threshold_groups.items():
            thresholds = [
                i for i in self.config.thresholds if i["parameter_group"] == k
            ]
            if thresholds:
                location_ids = [i.location for i in time_series_groups[k]]
                for i in thresholds:
                    df = self.locations.locations.loc[location_ids]
                    threshold = _get_label_and_value(df, i)
                    if threshold:
                        v[i["name"]] = threshold

        return threshold_groups
