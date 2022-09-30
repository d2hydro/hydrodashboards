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
themes_filter = filters[0]
filtes_filter = filters[1]
themes_filter.active = [1]

# %% choose filter peilbuis
themes_filter.active = [0]

# %% choose themes grondwater and oppervlaktewater
themes_filter.active = [0, 1]
