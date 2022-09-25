from fewspy import Api
from hydrodashboards.datamodel.filters import Filters
from hydrodashboards.bokeh.data import Data
from hydrodashboards.bokeh.config import Config
from hydrodashboards.bokeh import sources
import pandas as pd
from datetime import datetime
import numpy as np
from hydrodashboards.bokeh.log_utils import import_logger
from pathlib import Path

from hydrodashboards.bokeh.main import *

# select one filter
filter_ids = ["WDB_OW_KGM"]
data.update_on_filter_select(filter_ids)


# select locations
location_ids = ["NL34.HL.KGM156"]
data.update_on_locations_select(location_ids)

# select parameters
parameter_ids = ["Q [m3/s] [NVT] [OW] * productie", "WATHTE [m] [NAP] [OW] * productie"]
data.parameters.value = parameter_ids

# update timeseries
update_time_series_view()
update_time_series_search()