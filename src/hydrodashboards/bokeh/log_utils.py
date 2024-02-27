import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).parents[1].joinpath("logs")
LOG_LEVEL = "DEBUG"


def import_logger(log_dir=LOG_DIR, log_file="hydrodashboard.log") -> logging.Logger:
    """
    Make a logger for Bokeh app, including file handler

    Returns:
        logger (logging.Logger): Logger object to be used in Bokeh app.

    """
    log_dir = Path(log_dir)
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir.joinpath(f"{log_file}").resolve()
    logFormatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger(__name__)
    logger.setLevel(getattr(logging, LOG_LEVEL))
    fh = RotatingFileHandler(log_file, maxBytes=1024 * 50, backupCount=1)
    fh = logging.FileHandler(log_file)
    fh.setFormatter(logFormatter)
    logger.addHandler(fh)
    return logger
