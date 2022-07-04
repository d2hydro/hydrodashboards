from fewspy import Api
from config import FEWS_URL, SSL_VERIFY, ROOT_FILTER, FIRST_DATE, INIT_TIMEDELTA
from hydrodashboards.datamodel.filters import Filters
from hydrodashboards.datamodel.locations import Locations
from hydrodashboards.datamodel.parameters import Parameters
from hydrodashboards.datamodel.search_period import SearchPeriod
from hydrodashboards.datamodel.placeholders import (
    UpdateGraph,
    MapFigure,
    MapOptions,
    Status,
    TimeFigure,
    SelectSearchTimeSeries,
    DownloadSearchTimeSeries,
    ViewPeriod,
    SearchTimeFigure)
from dataclasses import dataclass
from datetime import datetime
# set api


@dataclass
class Data:
    # help properties for internal use in class
    _fews_api = Api(url=FEWS_URL, ssl_verify=SSL_VERIFY)
    _fews_qualifiers = _fews_api.get_qualifiers()
    _fews_root_parameters = _fews_api.get_parameters(filter_id=ROOT_FILTER)
    _fews_root_locations = _fews_api.get_locations(filter_id=ROOT_FILTER)
    _fews_filters = _fews_api.get_filters(filter_id=ROOT_FILTER)

    # time properties
    now = datetime.now()

    # properties matching dashboard layout
    filters = Filters.from_fews(_fews_filters)
    locations = Locations.from_fews(_fews_root_locations)
    parameters = Parameters.from_fews(
        pi_parameters=_fews_root_parameters,
        pi_qualifiers=_fews_qualifiers
    )
    search_period = SearchPeriod(min_date=FIRST_DATE,
                                 start_date=now - INIT_TIMEDELTA,
                                 end_date=now)
    update_graph = UpdateGraph()
    map_figure = MapFigure()
    map_options = MapOptions()
    status = Status()
    time_figure = TimeFigure()
    select_search_time_series = SelectSearchTimeSeries()
    download_search_time_series = DownloadSearchTimeSeries()
    view_period = ViewPeriod()
    search_time_figure = SearchTimeFigure()
