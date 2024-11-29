from pathlib import Path
from hydrodashboards import bokeh

TEST_DIR = Path(__file__).parents[1]
DATA_DIR = TEST_DIR / "data"


def hhnk_lokaal_config():
    bokeh.set_config_json(DATA_DIR / "hhnk_lokaal_config.json")
    bokeh.delete_cache()


def hhnk_online_config():
    bokeh.set_config_json(DATA_DIR / "hhnk_online_config.json")
    bokeh.delete_cache()
