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


# %% choose theme grondwater
# def test_reupdate_themes_filter():
filters[0].active = [1]

# %% choose filter peilbuis
filters[1].active = [0]

# %% choose themes grondwater and oppervlaktewater
filters[0].active = [0, 1]


# %%
#update_time_series_view()
#update_time_series_search()
