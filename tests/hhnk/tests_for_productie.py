#%%
from config import hhnk_config

# %% here we overwrite the default (WAM) config with WIK
hhnk_config()

# %% now we import main (will be initialized for WIK)
from hydrodashboards.bokeh.main import config, filters, data, locations, parameters

# %% select gemalen
def test_select_gemalen():
    filters[0].active = [0]
    assert len(locations.labels) == 475