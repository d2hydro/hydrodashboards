from hydrodashboards import bokeh
from config import wik_config

# %% here we overwrite the default (WAM) config with WIK
wik_config()

# %% now we import main (will be initialized for WIK)
from hydrodashboards.bokeh.main import config, filters, data


def test_config():
    assert config.title == "WIK Dashboard"
