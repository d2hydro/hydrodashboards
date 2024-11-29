# %%
from config import hhnk_online_config

# %% here we overwrite the default (WAM) config with WIK
hhnk_online_config()

# %% now we import main (will be initialized for WIK)
from hydrodashboards.bokeh.main import (
    config,
    filters,
    data,
    locations,
    parameters,
    start_time_series_loader,
    update_time_series_view,
)


def load_time_series():
    start_time_series_loader()
    update_time_series_view()


# selecteer filter, locatie en alle parameters
filters[0].active = [0]
locations.active = [0]
parameters.active = [i for i in range(len(parameters.labels))]

load_time_series()

# %%
