import argparse
import os
import schedule
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import shutil
import time
import atexit

# the minimum files expected to load all modules
APP_FILES = [
    "__init__.py",
    "config.json",
    "config.py",
    "main.py",
    "data.py",
    "pid_utils.py",
    "log_utils.py",
    "time_series_cache.py"
    ]


def is_bokeh_app(app_path):
    """Check if supplied path contains all required modules."""
    is_app = False
    if app_path.is_dir():
        is_app = all((app_path.joinpath(i).exists() for i in APP_FILES))
    return is_app

def start_applications(config):
    """Start bokeh applications at given ports."""
    from log_utils import LOG_DIR
    from pid_utils import write_pid_file
    for port in config.ports:
        process = subprocess.Popen([
            "bokeh",
            "serve",
            config.app_name,
            "--port",
            str(port)
            ])  
        write_pid_file(LOG_DIR / f"bokeh_{port}.pid", pid=process.pid)

def restart_applications(config, rebuild_time_series=True):
    """Restart application after rebuilding cache."""
    from pid_utils import terminate_bokeh
    from log_utils import import_logger
    import data

    # terminate all bokeh applications
    terminate_bokeh()

    # rebuild cache
    logger = import_logger(log_file="build_cache.log")
    data_model = data.Data(
        logger=logger,
        now=datetime.now(),
        config=config)
    logger.info("delete cache (if exists)")
    data_model.delete_cache()
    time_series_cache = data_model.time_series_sets.cache.cache_dir
    if rebuild_time_series:
        if time_series_cache.exists():
            shutil.rmtree(time_series_cache)
    logger.info("build new cache")
    data_model.build_cache()

    # restart bokeh applications
    start_applications(config)
    
    # build time-series cache
    update_timeseries_cache()

def update_timeseries_cache():
    """Update time-series cache."""
    from time_series_cache import update_idle, warning, update_cache
    
    if update_idle():
        update_cache()
    else:
        print("bezig!")
        warning()

def main():
    args = get_args()
    app_path = Path(args.app_dir).absolute().resolve()
    
    if is_bokeh_app(app_path):
        
        

        # import local modules
        sys.path.insert(0, str(app_path))
        from config import Config
        from log_utils import LOG_DIR
        from pid_utils import write, terminate_bokeh

        atexit.register(terminate_bokeh)
        pid_file = LOG_DIR / "serve_hydrodashboards.pid"
        write(pid_file)

        # launch hydrodashboards
        os.chdir(app_path.parent)
        config = Config.from_json(app_path / "config.json")
        config.app_name = app_path.name
        restart_applications(config, rebuild_time_series=False)

        # schedule reboot
        restart_time = config.cache_rebuild_time.strftime("%H:%M")
        schedule.every().day.at(restart_time).do(
            restart_applications,
            config=config
            )

        # schedule time_series_cache_update
        interval = config.cache_time_series_update_interval_min 
        if interval is not None:
            print("init time_series_cache")
            schedule.every(interval).minutes.do(update_timeseries_cache)

        while True:
            schedule.run_pending()
            time.sleep(1)

def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="""
        Serve your hydrodashboard.
        """
    )

    parser.add_argument(
        "-app_dir",
        required=True,
        help="directory of the application (contains main.py, config.json, etc)"
    )

    return parser.parse_args()

if __name__ == "__main__":
    main()
