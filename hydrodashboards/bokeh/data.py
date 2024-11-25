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
from bokeh.palettes import Category20_20
from datetime import datetime, timedelta
import numpy as np
import itertools
from operator import itemgetter
import pandas as pd

from hydrodashboards.datamodel.cache import Cache, delete_all_cache
from hydrodashboards.datamodel.time_series import KEY

FEWS_BUGS = dict(qualifier_ids=True)
COLOR_CYCLE = itertools.cycle(Category20_20)


def _get_propeties(filter_id, filter_name, filter_colors):
    if filter_id in filter_colors.keys():
        line = filter_colors[filter_id]["line"]
        fill = filter_colors[filter_id]["fill"]
    else:
        line = next(COLOR_CYCLE)
        fill = next(COLOR_CYCLE)

    return {
        "line_color": line,
        "nonselection_line_color": line,
        "fill_color": fill,
        "non_selection_fill_color": fill,
        "label": filter_name,
    }


def to_datetime(date):
    """
    Converts a numpy datetime64 object to a python datetime object
    Input:
      date - a np.datetime64 object
    Output:
      DATE - a python datetime object
    """
    timestamp = (date - np.datetime64("1970-01-01T00:00:00")) / np.timedelta64(1, "s")
    return datetime.utcfromtimestamp(timestamp)


class Data:
    def __init__(self, config, logger=None, now: datetime = datetime.now()):
        self.config = config
        self.logger = logger

        # fews properties
        self._fews_api = None
        self._fews_qualifiers = None
        self._fews_root_parameters = None
        self._fews_root_locations = None
        self._fews_filters = None
        self._root_cache = Cache(sub_dir="root")
        self._init_fews_api()

        # time properties
        self.now = now
        self.periods = Periods(self.now, history_period_days=self.config.history_period)

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

    def _init_fews_api(self):
        self._fews_api = Api(
            url=self.config.fews_url,
            ssl_verify=self.config.ssl_verify,
            logger=self.logger,
        )

        # get root qualifiers
        if self._root_cache.exists("_fews_qualifiers"):
            self.logger.info("reading FEWS-qualifiers from cache")
            self._fews_qualifiers = self._root_cache.data["_fews_qualifiers"]
        else:
            self._fews_qualifiers = self._fews_api.get_qualifiers()
            self._root_cache.set_data(self._fews_qualifiers, "_fews_qualifiers")

        # get root parameters
        if self._root_cache.exists("_fews_root_parameters"):
            self.logger.info("reading FEWS-parameters from cache")
            self._fews_root_parameters = self._root_cache.data["_fews_root_parameters"]
        else:
            self._fews_root_parameters = self._fews_api.get_parameters(
                filter_id=self.config.root_filter
            )
            self._root_cache.set_data(
                self._fews_root_parameters, "_fews_root_parameters"
            )

        # get root locations
        if self._root_cache.exists("_fews_root_locations"):
            self.logger.info("reading FEWS-locations from cache")
            self._fews_root_locations = self._root_cache.data["_fews_root_locations"]
        else:
            self._fews_root_locations = self._fews_api.get_locations(
                filter_id=self.config.root_filter,
                attributes=self.config.location_attributes,
                remove_duplicates=self.config.remove_duplicates
            )
            self._root_cache.set_data(self._fews_root_locations, "_fews_root_locations")

        # get root filters
        if self._root_cache.exists("_fews_filters"):
            self.logger.info("reading FEWS-filters from cache")
            self._fews_filters = self._root_cache.data["_fews_filters"]
        else:
            self._fews_filters = self._fews_api.get_filters(
                filter_id=self.config.root_filter
            )
            self._root_cache.set_data(self._fews_filters, "_fews_filters")

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
        elif selection == "full_history":
            period = self.periods.history_period
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
        elif request_type == "full_history":
            parallel = self.config.fews_parallel
            thinning = self._get_thinning(selection="full_history")
            (
                location_ids,
                parameter_ids,
                qualifier_ids,
            ) = self._fews_locators_from_indices(indices)
            start_time = self.periods.history_start
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
                self.locations.get_parent_name(header.location_id),
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
                if (location_id, parameter_id) in self.time_series_sets.indices:
                    ts_idx = self.time_series_sets.indices.index(
                        (location_id, parameter_id)
                    )
                    ts_select = self.time_series_sets.time_series[ts_idx]
                    if not erasing_data(fews_ts.events, ts_select.df):
                        ts_select.df = fews_ts.events
                        ts_select.complete = complete
                        ts_select.empty = fews_ts.events.empty
                        ts_select.start_datetime = fews_ts.header.start_date
                        ts_select.end_datetime = fews_ts.header.end_date

    def _get_df_from_fews_ts_set(self, fews_ts_set, location_id, parameter_id):
        for fews_ts in fews_ts_set.time_series:
            header = fews_ts.header
            if (header.location_id == location_id) and (
                concat_fews_parameter_ids(
                    fews_ts.header.parameter_id, fews_ts.header.qualifier_id
                )
                == parameter_id
            ):
                return fews_ts.events

    """

    Section with functions handling cache

    """

    def delete_cache(self):
        self.logger.info("deleting cache")
        for i in self.filters.filters:
            i.cache.delete_cache()
        self.locations.sets.delete_cache()
        self._root_cache.delete_cache()
        # delete_all_cache()

    def build_cache(self):
        self.logger.info("building cache")
        self._init_fews_api()
        filter_ids = self.filters.values
        for filter_id in filter_ids:
            filter_data = self.filters.get_filter(filter_id)
            self.cache_filter(filter_data, filter_id)

    def cache_filter(self, filter_data, filter_id):
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
                location_name = self.locations.locations.at[location_id, "name"]
                parameter_id = self.parameters.id_from_ts_header(i)
                parameter_name = self.parameters.name_from_ts_header(i)

                return (
                    location_id,
                    location_name,
                    child_id,
                    parameter_id,
                    parameter_name,
                )
            else:
                return [None for i in range(5)]

        def _pi_headers_to_df(pi_headers):
            data = [_get_from_header(i.header) for i in pi_headers.time_series]

            df = pd.DataFrame.from_records(
                data=data,
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

        filter_name = self.filters.get_name(filter_id, filter_data)
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

        # drop headers without a location_id that is retrieve by get_locations
        if headers_df["location_id"].isna().any():
            self.logger.warning(f"filter id:name {filter_id}:{filter_name} contains location is not returned by get_locations")
            headers_df.dropna(subset="location_id", inplace=True)

        # drop headers with location_names that are not defined
        if headers_df["location_name"].isna().any():
            no_names = headers_df[headers_df["location_name"].isna()]["location_id"].to_list()
            self.logger.warning(f"filter id:name {filter_id}:{filter_name} contains location_ids without location_name that are removed: {no_names}")
            headers_df.dropna(subset="location_name", inplace=True)

        locations = self.locations.options_from_headers_df(headers_df)
        parameters = self.parameters.options_from_headers_df(headers_df)
        filter_data.cache.set_data(
            {
                "locations": locations,
                "parameters": parameters,
            },
            filter_id,
        )

        # if not yet in sets, add it there too
        if not self.locations.sets.exists(filter_id):
            properties = _get_propeties(
                filter_id, filter_name, self.config.filter_colors
            )
            self.locations.add_to_sets(filter_id, headers_df, properties)
        return locations, parameters

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

    def update_on_filter_select(self, selected: list, actives=True):
        """
        Update data-class on selected filter

        Args:
            selected (list): List with selected filter ids or indices.

        Returns:
            None.

        """

        all_locations = []
        all_parameters = []

        if actives:
            values = self.filters.values_by_actives(selected)
        else:
            values = selected

        for filter_id in values:
            filter_data = self.filters.get_filter(filter_id)

            # get locations and parameters from sub-filter
            if not filter_data.cache.exists(filter_id):  # add to cache if
                locations, parameters = self.cache_filter(filter_data, filter_id)

            else:
                filter_data = self.filters.get_filter(filter_id)
                locations, parameters = filter_data.cache.data[filter_id].values()

            # add locations and parameters to list
            all_locations = list(set(all_locations + locations))
            all_parameters = sorted(
                list(set(all_parameters + parameters)), key=itemgetter(1)
            )

        # update locations and parameter filter data
        self.locations.update_from_options(all_locations)
        self.parameters.update_from_options(all_parameters)

        # update map_locations
        self.locations.update_map_locations(values)

        # limit parameters by selected location
        self.update_on_locations_select(self.locations.value)

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
        self.parameters.limit_options_on_search_input()
        self.parameters.clean_value()

    def update_history_time_series_search(self, search_time_series_label):
        search_time_series = self.time_series_sets.get_by_label(
            search_time_series_label
        )

        # try to get the time-series from cache
        cache_key = KEY.format(
            location=search_time_series.location, parameter=search_time_series.parameter
        )
        if self.time_series_sets.cache.exists(cache_key):
            time_series = self.time_series_sets.cache.get_data(cache_key)
            df = time_series.df
        # if we can't, we get the full history from FEWS
        else:
            time_series_index = (
                search_time_series.location,
                search_time_series.parameter,
            )
            fews_ts_set = self._get_fews_ts(
                indices=[time_series_index], request_type="full_history"
            )
            df = self._get_df_from_fews_ts_set(fews_ts_set, *time_series_index)

        return df

    def get_history_period(self, datetime_array):
        if len(datetime_array) == 0:
            return (self.periods.search_start, self.periods.search_end)
        else:
            return (
                to_datetime(datetime_array.min()),
                to_datetime(datetime_array.max()) + timedelta(hours=12),
            )

    def update_time_series_from_cache(self, indices):
        """Update the time_series_sets.time_series from cache if existing."""
        for index in indices:
            # self.logger.info("trying to update from cache")
            if self.time_series_sets.exists(index):
                self.time_series_sets.remove(index)
            # self.logger.info(f"cache file found for {index[0]}, {index[1]}")
            self.time_series_sets.append_from_cache(
                *index, self.periods.search_start, self.periods.search_end
            )
            # self.logger.info(f"new cache length: {len(self.time_series_sets)}")

    def clean_time_series_within_period(self, period, selection="search"):
        self.time_series_sets.time_series = [
            i
            for i in self.time_series_sets.time_series
            if i.within_period(period, selection=selection)
        ]

    def get_time_series_headers(self, indices=None, ignore_cache=False):
        # get headers and initalize time series
        if indices is None:
            indices = self.locations.max_time_series_indices(self.parameters.value)
        if not ignore_cache:
            self.update_time_series_from_cache(indices)

        self.clean_time_series_within_period(self.periods, selection="search")
        self.logger.info(
            f"amount of time-series in memory {len(self.time_series_sets)}"
        )

        # indices should not exist in memory
        fews_indices = [i for i in indices if not self.time_series_sets.exists(i)]

        # we try to append new time-series from FEWS
        if fews_indices:
            self.logger.info(f"fews request for {fews_indices}")
            fews_ts_set = self._get_fews_ts(
                indices=fews_indices, request_type="headers"
            )
            properties = self._properties_from_fews_ts_headers(fews_ts_set.time_series)
            self.time_series_sets.append_from_dict(properties)

    def update_time_series(self, ignore_cache=False):
        """Updates time_series when button is clicked."""

        indices = self.locations.max_time_series_indices(self.parameters.value)
        self.get_time_series_headers(indices=indices, ignore_cache=ignore_cache)

        self.time_series_sets.set_active(indices)
        self.time_series_sets.set_visible(indices=indices)

        if self.time_series_sets.select_incomplete():
            fews_ts_set = self._get_fews_ts(request_type="history")
            self._update_ts_from_fews_ts_set(fews_ts_set, complete=True)

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
