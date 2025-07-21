import datetime
import os
from pathlib import Path

from bokeh_helpers.logger import add_file_handler, get_logger, set_default_logconfig

MAP_LOG = {"1": "DEBUG", "0": "INFO"}


def get_bokeh_logger(app_file: Path, log_dir: Path | None = None, level="INFO"):
    """Create a logger for the Bokeh app

    Parameters
    ----------
    app_file : Path
        app-file to generate log-file for. Usually main.py
    log_dir : Path | None, optional
        log-dir to store file in. If None, a log_dir will be
          created next to the app-directory., by default None
    level : str, optional
        logger log-level, by default "INFO"

    """
    # get level from environment
    log_flag = os.getenv("DEBUG")
    if log_flag is not None:
        level = MAP_LOG[log_flag]

    # make sure app_file is Path
    if not isinstance(app_file, Path):
        app_file = Path(app_file)

    # define log-dir in same dir as app-dir
    if log_dir is None:
        app_name = app_file.parent.name
        log_dir = app_file.parents[2].joinpath("logs", app_name)
    log_dir.mkdir(exist_ok=True, parents=True)

    log_file = log_dir.joinpath(f"info_{datetime.datetime.now().strftime('%Y-%m-%d')}.log")
    set_default_logconfig(level_root=level)
    logger_root = get_logger(name="root")
    add_file_handler(logger_root, filepath=log_file, rotate=True)

    logger = get_logger(
        name="app",
        level=level,
    )

    logger.debug(f"initialized logger with level {level}")

    return logger
