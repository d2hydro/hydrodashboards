from pathlib import Path
from hydrodashboards import bokeh

TEST_DIR = Path(__file__).parents[1]
DATA_DIR = TEST_DIR / "data"
WIK_CONFIG_JSON = DATA_DIR / "wik_config.json"
WAM_CONFIG_JSON = DATA_DIR / "wam_config.json"


# %% here we overwrite the default (WAM) config with WIK
def set_config(config_file):
    bokeh.set_config_json(config_file)
    bokeh.delete_cache()

def wik_config():
    set_config(WIK_CONFIG_JSON)

def wam_config():
    set_config(WAM_CONFIG_JSON)
