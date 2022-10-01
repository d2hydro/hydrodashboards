from hydrodashboards.build_dashboard import bokeh
import hydrodashboards
from pathlib import Path


hydrodashboards_dir = Path(hydrodashboards.__file__).parent
config_json = hydrodashboards_dir.joinpath("bokeh", "config.json")


def test_build_app(tmp_path):
    bokeh(tmp_path, config_file=config_json)
    assert tmp_path.joinpath("main.py").exists()
