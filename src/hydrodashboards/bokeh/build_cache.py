#!/usr/bin/env python3
try:
    import data
    from config import Config
except ImportError:
    from hydrodashboards.bokeh import data
    from hydrodashboards.bokeh.config import Config

import argparse
from datetime import datetime
import logging
from pathlib import Path

CONFIG_JSON = Path(data.__file__).parent.joinpath("config.json")
logger = logging.getLogger(__name__)


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
