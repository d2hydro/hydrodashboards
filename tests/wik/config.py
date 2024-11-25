from pathlib import Path
from hydrodashboards import bokeh

TEST_DIR = Path(__file__).parents[1]
DATA_DIR = TEST_DIR / "data"
WIK_CONFIG_JSON = DATA_DIR / "wik_config.json"
WAM_CONFIG_JSON = DATA_DIR / "wam_config.json"


# %% here we overwrite the default (WAM) config with WIK


def wik_config():
    bokeh.set_config_json(WIK_CONFIG_JSON)
    bokeh.delete_cache()


def wam_config():
    bokeh.set_config_json(WAM_CONFIG_JSON)
    bokeh.delete_cache()
