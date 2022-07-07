from fewspy import Api
from hydrodashboards.datamodel.filters import Filters
from hydrodashboards.bokeh.data import Data
import pandas as pd
from datetime import datetime
import numpy as np
ROOT_FILTER = "WDB"
OPTIONS = [
    ("WDB_OW_KGM", "Gemaal"),
    ("WDB_OW_KST", "Stuw"),
    ("WDB_OW_INL", "Inlaat"),
    ("WDB_OW_KSL", "Sluis"),
    ("WDB_OW_MPN", "Meetpunt"),
]
TITLES = ["Oppervlaktewater", "Grondwater", "Fysisch/Chemisch", "Meteorologie"]

api = Api(
    url="https://www.hydrobase.nl/fews/nzv/FewsWebServices/rest/fewspiservice/v1/",
    ssl_verify=False,
)
EXCLUDE_PARS = ["Dummy"]

data = Data()

# select one filter
filter_ids = ["WDB_OW_KGM"]
data.update_on_filter_select(filter_ids)

# add another filter
filter_ids = ["WDB_OW_KGM", "WDB_ML_KNMI"]
data.update_on_filter_select(filter_ids)

# select locations
values = ["NL34.HL.KGM003", "KNMI_235"]
data.update_on_locations_select(values)

# select parameters
values = ["Q [m3/s] [NVT] [OW] * validatie", "NEERSG [mm] [NVT] [LT]", "WATHTE [m] [NAP] [OW] * validatie"]
data.parameters.value = values


# update timeseries
data.update_time_series()

#%% new code!
from hydrodashboards.datamodel.utils import split_parameter_id_to_fews
self = data
times_series = self.time_series_sets.time_series
