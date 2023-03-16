from pathlib import Path
from hydrodashboards.datamodel.cache import CACHE_DIR
import shutil

CONFIG_JSON = Path(__file__).parent.joinpath("config.json")


def set_config_json(config_json):
    global CONFIG_JSON

    CONFIG_JSON = Path(config_json).absolute().resolve()


def delete_cache():
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
