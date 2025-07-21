"""
This file is shared by:
 - https://github.com/HHNK/hhnk-wis-dashboards/blob/main/bokeh-helpers/bokeh_helpers/logger.py
 - https://github.com/HHNK/hhnk-research-tools/blob/main/hhnk_research_tools/logger.py

These functions allow for adding logging to the console.
This is applied by default in the __init__ of hhnk_research_tools. So when it is imported
in a project, the logging will be set according to these rules.
"""

import logging
import sys
from logging import config

# from logging import *  # noqa: F401,F403 # type: ignore
from logging.handlers import RotatingFileHandler
from os import PathLike
from pathlib import Path
from typing import Any, Literal, Optional, Union

LOGFORMAT = "%(asctime)s|%(levelname)-8s| %(name)s:%(lineno)-4d| %(message)s"  # default logformat
DATEFMT_STREAM = "%H:%M:%S"  # default dateformat for console logger
DATEFMT_FILE = "%Y-%m-%d %H:%M:%S"  # default dateformat for file logger
LOG_LEVEL = Literal["WARNING", "DEBUG", "INFO"]


def get_logconfig_dict(
    level_root: LOG_LEVEL = "WARNING",
    level_dict: Optional[dict[LOG_LEVEL, list[str]]] = None,
    log_filepath: Optional[Union[str, PathLike]] = None,
) -> dict[str, Any]:
    """Make a dict for the logging.

    Parameters
    ----------
    level_root : Literal["WARNING", "DEBUG", "INFO"], optional
        Default log level, warnings are printed to console. By default "WARNING"
    level_dict : Optional[dict[Literal["WARNING", "DEBUG", "INFO"], list[str]]], optional
        e.g. {"INFO" : ['hhnk_research_tools','hhnk_threedi_tools']}
        Apply a different loglevel for these packages. by default None
    log_filepath : Optional[Union[str, PathLike]], optional
        Option to write a log_filepath. By default None
    """

    logconfig_dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "loggers": {
            "": {  # root logger
                "level": level_root,
                "handlers": [
                    "debug_console_handler",
                ],
            },
        },
        "handlers": {
            "null": {
                "class": "logging.NullHandler",
            },
            "debug_console_handler": {
                "level": "NOTSET",
                "formatter": "time_level_name",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
            "stderr": {
                "level": "ERROR",
                "formatter": "time_level_name",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
        },
        "formatters": {
            "time_level_name": {
                "format": LOGFORMAT,
                "datefmt": DATEFMT_STREAM,
            },
        },
    }

    # Apply a different loglevel for these packages.
    if level_dict:
        for loglevel, level_list in level_dict.items():
            if not isinstance(level_list, list):
                raise TypeError("Level_dict should provide lists.")

            for pkg in level_list:
                logconfig_dict["loggers"][pkg] = {
                    "level": loglevel,
                }

    if log_filepath:
        # Not possible to add a default filepath because it would always create this file,
        # even when nothing is being written to it.
        logconfig_dict["handlers"]["info_rotating_file_handler"] = {
            "level": "INFO",
            "formatter": "time_level_name",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "when": "D",
            "backupCount": 7,
            "filename": log_filepath,
        }
    return logconfig_dict


def set_default_logconfig(
    level_root: LOG_LEVEL = "WARNING",
    level_dict: Optional[dict[LOG_LEVEL, list[str]]] = None,
    log_filepath: Optional[Union[str, PathLike]] = None,
):
    """Use this to set the default config, which will log to the console.

    Parameters
    ----------
    level_root : Literal["WARNING", "DEBUG", "INFO"], optional
        Default log level, warnings are printed to console. By default "WARNING"
    level_dict : Optional[dict[Literal["WARNING", "DEBUG", "INFO"], list[str]]], optional
        e.g. {"INFO" : ['hhnk_research_tools','hhnk_threedi_tools']}
        Apply a different loglevel for these packages. by default None
    log_filepath : Optional[Union[str, PathLike]], optional
        Option to write a log_filepath. By default None

    Examples
    --------
    In the __init__.py of hrt the hrt logger is initiated. We only need logging.GetLogger to add
    loggers to functions and classes. Same can be done for other packages.
    Use this in functions:

    import hhnk_research_tools as hrt
    logger = hrt.logging.get_logger(name=__name__, level='INFO')

    Example changing the default behaviour:
    hrt.logging.set_default_logconfig(
        level_root="WARNING",
        level_dict={
            "DEBUG": ["__main__"],
            "INFO": ["hhnk_research_tools", "hhnk_threedi_tools"],
            "WARNING": ['fiona', 'rasterio']
        },
    )
    """
    log_config = get_logconfig_dict(level_root=level_root, level_dict=level_dict, log_filepath=log_filepath)

    config.dictConfig(log_config)


def add_file_handler(
    logger: logging.Logger,
    filepath: Union[str, Path],
    filemode: Literal["w", "a"] = "a",
    filelevel: Optional[int] = None,
    fmt: str = LOGFORMAT,
    datefmt: str = DATEFMT_FILE,
    maxBytes: int = 10 * 1024 * 1024,
    backupCount: int = 5,
    rotate: bool = False,
    logfilter: Optional[logging.Filter] = None,
):
    """Add a filehandler to the logger. Removes the filehandler when it is already present

    Parameters
    ----------
    logger : logging.Logger
        logger to append file-logger to
    filepath : Union[str, Path]
        filepath to write logs to.
    filemode : Literal["w", "a"], optional
        file write-mode, 'w' is write, 'a' is append. by default "a"
    filelevel : Optional[int], optional
        logging Level, by default None
    fmt : str, optional
        default is "%(asctime)s|%(levelname)-8s| %(name)s:%(lineno)-4d| %(message)s"
    datefmt : str, optional
        str, default is "%H:%M:%S"
        Change the default dateformatter to e.g. "%Y-%m-%d %H:%M:%S"
    maxBytes : int, optional
        max length in bytes of log-file, by default 10*1024*1024
    backupCount : int, optional
        logger backup count, by default 5
    rotate : bool, optional
        rotating file handler, by default False
    logfilter : Optional[logging.Filter], optional
        optional logging filter, by default None
    """

    # Remove filehandler when already present
    for handler in logger.handlers:
        if isinstance(handler, (logging.FileHandler, RotatingFileHandler)):
            if Path(handler.stream.name) == filepath:
                logger.removeHandler(handler)
                logger.debug("Removed existing FileHandler, logger probably imported multiple times")

    # TODO  add test that filemode is doing the correct thing
    if not rotate:
        file_handler = logging.FileHandler(str(filepath), mode=filemode)
    else:
        # TODO filemode 'w' doesnt seem to reset file on RotatingFileHandler
        file_handler = RotatingFileHandler(str(filepath), mode=filemode, maxBytes=maxBytes, backupCount=backupCount)

    # This formatter includes longdate.
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
    file_handler.setFormatter(formatter)

    # Set level of filehandler, can be different from logger.
    if filelevel is None:
        filelevel = logger.level
    file_handler.setLevel(filelevel)

    if logfilter:
        file_handler.addFilter(logfilter)
        logger.debug("Added filter to FileHandler")

    logger.addHandler(file_handler)


def _add_or_update_streamhandler_format(logger, fmt, datefmt, propagate: bool = True):
    """Add a StreamHandler with the given formatter to the logger.
    If the logger has no handlers, create a new one

    propagate : bool, default is True
        True: Make formatting changes to the root logger.
        False: Detach the logger from the root and add the handler to
            that specific logger. If not detached (propagate=False), the logger
            will still inherit the handlers from the root logger. Resulting in
            multiple handlers.
    """

    if propagate:
        logger = logging.getLogger()
    else:
        logger.propagate = False

    handler_updated = False
    # Check if the logger already has a StreamHandler with the correct formatter
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            # Update the formatter if the StreamHandler is found
            handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
            logger.debug("Updated StreamHandler formatter")

            handler_updated = True

    if handler_updated:
        return

    # If no matching StreamHandler was found, add a new one
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    logger.addHandler(stream_handler)
    logger.debug("Added new StreamHandler with formatter")


def get_logger(
    name: str,
    level: Optional[str] = None,
    fmt: str = LOGFORMAT,
    datefmt: str = DATEFMT_STREAM,
    propagate: bool = True,
    filepath: Optional[Path] = None,
    **kwargs,
) -> logging.Logger:
    """
    Name should default to __name__, so the logger is linked to the correct file

    When using in a (sub)class, dont use this function. The logger will inherit the settings.
    Use:
        self.logger = hrt.logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    Othwerise:
        logger = hrt.logging.get_logger(name=__name__, level='INFO')

    The names of loggers can be replaced here as well. This creates a shorter logmessage.
    e.g. "hhnk_research_tools" -> "hrt"

    Parameters
    ----------
    name : str
        Default use
        name = __name__
    level : Optional[str], default is None
        Only use this when debugging. Otherwise make the logger inherit the level from the config.
        When None it will use the default from get_logconfig_dict.
    filepath : Optional[Path], default is None
        Path to filehandler.
        When None no filehandler will be used (unless inherited from parents)
    fmt : str, default is "%(asctime)s|%(levelname)-8s| %(name)s:%(lineno)-4d| %(message)s"
        Formatting of logmessage
    datefmt : str, default is "%H:%M:%S"
        Change the default dateformatter to e.g. "%Y-%m-%d %H:%M:%S"
    propagate : bool, default is True
        True: Make formatting changes to the root logger.
        False: Detach the logger from the root and add the handler to
            that specific logger. If not detached (propagate=False), the logger
            will still inherit the handlers from the root logger. Resulting in
            multiple handlers.
    **kwargs
        These arguments will be passed to add_file_handler
    """
    # Rename long names with shorter ones
    replacements = {
        "hhnk_research_tools": "hrt",
        "hhnk_threedi_tools": "htt",
    }

    for old, new in replacements.items():
        name = name.replace(old, new)

    logger = logging.getLogger(name)

    # Change log level
    if level is not None:
        logger.setLevel(level)

    # Change log format or datefmt
    if (fmt != LOGFORMAT) or (datefmt != DATEFMT_STREAM):
        _add_or_update_streamhandler_format(logger, fmt=fmt, datefmt=datefmt, propagate=propagate)

    if filepath:
        add_file_handler(logger=logger, filepath=filepath, **kwargs)

    return logger
