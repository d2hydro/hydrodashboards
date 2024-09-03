try:
    import data
    from config import Config
    from log_utils import import_logger
except ImportError:
    from hydrodashboards.bokeh import data
    from hydrodashboards.bokeh.config import Config
    from hydrodashboards.bokeh.log_utils import import_logger

import argparse
from datetime import datetime

from pathlib import Path


logger = import_logger(log_file="build_cache.log")
CONFIG_JSON = Path(data.__file__).parent.joinpath("config.json")


def main():
    args = get_args()
    rebuild_cache(config_file=args.config_file)


def rebuild_cache(config_file):
    config = Config.from_json(config_file)
    now = datetime.now()
    data_model = data.Data(logger=logger, now=now, config=config)
    logger.info("delete cache (if exists)")
    data_model.delete_cache()
    logger.info("build new cache")
    data_model.build_cache()


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="""
        Build cache for your Bokeh dashboard.
        """
    )

    parser.add_argument(
        "-config_file",
        help="config.json with app configuration. If not supplied, it will take the config.json in the same directory as data.py.",
        default=CONFIG_JSON,
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
