from hydrodashboards import bokeh

# %% here we overwrite the default (WAM) config with WIK
AAM_CONFIG_JSON = r"data\wik_config.json"

bokeh.set_config_json(AAM_CONFIG_JSON)

# %% now we import main (will be initialized for WIK)
from hydrodashboards.bokeh.main import config, filters, data

def test_config():
    assert config.title == "WIK Dashboard"
