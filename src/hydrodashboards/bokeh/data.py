from fewspy import Api
from config import *
from hydrodashboards.datamodel.filters import Filters
from hydrodashboards.datamodel.locations import Locations
from dataclasses import dataclass

# set api

@dataclass
class Data:
    # help properties for internal use in class
    _fews_api = Api(url=FEWS_URL, ssl_verify=SSL_VERIFY)

    # properties matching dashboard layout
    filters = Filters.from_fews(
        _fews_api.get_filters(filter_id=ROOT_FILTER)
    ).to_bokeh()
    locations = None
    parameters = None
    search_period = None
    update_graph = None
    map_figure = None
    map_options = None
    status = None
    time_figure = None
    select_search_time_series = None
    download_search_time_series = None
    view_period = None
    search_time_figure = None
