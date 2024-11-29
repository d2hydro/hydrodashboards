from pathlib import Path
from hydrodashboards import bokeh

TEST_DIR = Path(__file__).parents[1]
DATA_DIR = TEST_DIR / "data"
HHNK_CONFIG_JSON = DATA_DIR / "hhnk_config.json"

# %% here we overwrite the default (WAM) config with WIK
def hhnk_config():
    bokeh.set_config_json(HHNK_CONFIG_JSON)
    bokeh.delete_cache()
