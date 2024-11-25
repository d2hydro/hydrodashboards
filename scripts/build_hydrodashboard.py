#!/usr/bin/env python3
from pathlib import Path
import shutil
import fewspy
import hydrodashboards
from hydrodashboards.bokeh.config import Config
from hydrodashboards.build_css_templates import map_opt
from hydrodashboards.build_html_templates import thresholds_button
import argparse
import sys
from typing import Union, Optional

VIRTUAL_ENV = Path(sys.executable).parent.as_posix()
HYDRODASHBOARDS_DIR = Path(hydrodashboards.__file__).parent
CONFIG_FILE = Path(hydrodashboards.__file__).parent.joinpath("bokeh", "config.json")
VERSION = hydrodashboards.__version__

cmd_activate =r"""rem setting environment to python installation
SET VIRTUAL_ENV={virtual_env}
SET PATH=%VIRTUAL_ENV%;%VIRTUAL_ENV%\Library\mingw-w64\bin;%VIRTUAL_ENV%\Library\usr\bin;%VIRTUAL_ENV%\Library\bin;%VIRTUAL_ENV%\Scripts;%VIRTUAL_ENV%\bin;%PATH%
SET PROJ_LIB=%VIRTUAL_ENV%\Library\share\proj
"""

def main():
    args = get_args()
    bokeh(
        app_dir=args.app_dir,
        config_file=args.config_file,
        css_file=args.css_file,
        virtual_env=args.virtual_env,
        app_port=args.app_port,
        bokeh_secret_key=args.bokeh_secret_key
    )


def reverse_bokeh_select(virtual_env: Union[str, Path]):

    # strings to replace
    original = 't||s?t&&!s?"append":!t&&s?"intersect":t&&s?"subtract"'
    new = 't||s?!t&&s?"append":t&&!s?"intersect":t&&s?"subtract"'

    # path to bokeh_min_js
    bokeh_min_js = Path(virtual_env).joinpath(
        r"Lib\site-packages\bokeh\server\static\js\bokeh.min.js"
    )

    # rename to backup
    bokeh_min_js_backup = Path(str(bokeh_min_js) + ".backup")
    bokeh_min_js.rename(bokeh_min_js_backup)

    # read backup, replace string and write to bokeh_min_js
    bokeh_min_js.write_text(bokeh_min_js_backup.read_text().replace(original, new))


def copy_environment(virtual_env: Union[str, Path], reverse_bokeh_select=True):
    virtual_env = Path(virtual_env)

    if virtual_env.exists():
        shutil.rmtree(virtual_env)

    print(f"copying {VIRTUAL_ENV} to {virtual_env}")
    shutil.copytree(VIRTUAL_ENV, virtual_env)

    if reverse_bokeh_select:
        reverse_bokeh_select(virtual_env)


def bokeh(
    app_dir: Optional[str | Path],
    config_file: Optional[str | Path] = None,
    css_file: Optional[str | Path] = None,
    virtual_env: Optional[str | Path] = None,
    bokeh_secret_key: Optional[str] = None,
    app_port: int = 5003,
):
    """
    Build a Bokeh dashboard

    Args:
        app_dir (Union[str, Path]): Directory where the app should be build
        config_file (Union[str, Path], optional): config.json with app-configuration that
            will be copied to app_dir/config.json. If None the default-file will be
            copied. Defaults to None.
        css_file (Union[str, Path], optional): css-file with app-specific CSS.
            If None the default-file will be copied. Defaults to None.
        virtual_env (Union[str, Path], optional): Specification of the
            Python-environment in which the app will be launched. If None, the app will
            use the environment where this function is running. Defaults to None.
        app_port (int, optional): Port to use for the Bokeh-app. Defaults to 5003.

    Returns:
        None.

    """

    # % remove and create directory
    app_dir = Path(app_dir)

    if app_dir.exists():
        shutil.rmtree(app_dir)

    app_dir.mkdir(parents=True)

    # %% copy config-file
    if config_file is None:
        config_file = CONFIG_FILE
    else:
        config_file = Path(config_file)

    config_json = app_dir.joinpath("config.json")
    config_json.write_text(config_file.read_text())

    config = Config.from_json(config_json)
    
    # %% copy config-file
    if config_file is None:
        config_file = CONFIG_FILE
    else:
        config_file = Path(config_file)

    config_json = app_dir.joinpath("config.json")
    config_json.write_text(config_file.read_text())
    # %% provide template
    templates_dir = app_dir / "templates"
    templates_dir.mkdir()

    template_html = HYDRODASHBOARDS_DIR.joinpath(
        "bokeh", "templates", "index.html"
    )

    html = template_html.read_text()
    html = html.replace("{{app}}", f"{app_dir.name}")
    if config.thresholds:
        html = html.replace("{{thresholds_button}}", thresholds_button)
    else:
        html = html.replace("{{thresholds_button}}", "")

    index_html = templates_dir / "index.html"
    index_html.write_text(html)

    # %% provide statics
    static_dir = app_dir / "static"

    css_dir = static_dir / "css"
    css_dir.mkdir(parents=True)
    templates_css_dir = HYDRODASHBOARDS_DIR.joinpath("bokeh", "static", "css")
    template_css = templates_css_dir / "base.css"
    base_css = css_dir / "base.css"

    # map_options_height = int(200 + 18 * len(config.map_overlays))
    # map_options_left = int(55 + 6.5 * max([len(i) for i in config.map_overlays.keys()]))
    # map_options_width = int(map_options_left - 10)
    base_css.write_text(
        template_css.read_text()
        .replace("{{app}}", f"{app_dir.name}")
        )

    
    app_css_str = None

    # read from supplied css-file
    if css_file is not None:
        css_file = Path(css_file)
        if css_file.exists():
            css_file = None
            print(f"css_file {css_file} does not exists (ignored)")          
    
    # read from default in repos
    if css_file is None:
        css_file = templates_css_dir / f"{app_dir.name}.css"
        if not css_file.exists():
            print(f"css_file {css_file} does not exists in template-dir, we'll copy wam.css")   
            css_file = templates_css_dir / "wam.css"
    app_css_str = css_file.read_text()

    # write app-css to app directory
    app_css = css_dir / "custom.css"
    app_css.write_text(app_css_str)


    # write data-json to app directory
    data_json = css_dir / "data.json"
    data_json.write_text((templates_css_dir / "data.json").read_text())

    # write icons
    icons_dir = static_dir / "icons"
    icons_src_dir = HYDRODASHBOARDS_DIR.joinpath("bokeh", "static", "icons")
    shutil.copytree(icons_src_dir, icons_dir)

    # write js-directory
    js_dir = static_dir / "js"
    js_src_dir = HYDRODASHBOARDS_DIR.joinpath("bokeh", "static", "js")
    shutil.copytree(js_src_dir, js_dir)

    # %% copy fewspy to local-folder
    fewspy_src = Path(fewspy.__file__).parent
    fewspy_dir = app_dir / "fewspy"
    shutil.copytree(fewspy_src, fewspy_dir)

    # %% copy hydrodashboards to local-folder
    datamodel_src = HYDRODASHBOARDS_DIR.joinpath("datamodel")
    datamodel_dir = app_dir.joinpath("hydrodashboards", "datamodel")
    shutil.copytree(datamodel_src, datamodel_dir)

    # %% provide hydrodashboards folder
    bokeh_src = HYDRODASHBOARDS_DIR.joinpath("bokeh")
    hydrodashboards_dir = app_dir / "hydrodashboards"
    bokeh_dir = hydrodashboards_dir / "bokeh"

    # copy contents of widgets-folder
    shutil.copytree(bokeh_src / "widgets", bokeh_dir / "widgets")

    # copy contents of datamodel folder to correct location
    for src in list(bokeh_src.glob("*.*")):
        dst = None
        if src.name in [
                "data.py",
                "main.py",
                "theme.yaml",
                "config.py",
                "build_cache.py",
                "time_series_cache.py",
                "log_utils.py",
                "pid_utils.py",
                "__init__.py"]:
            dst = app_dir.joinpath(src.name)
        else:
            dst = bokeh_dir.joinpath(src.name)

        if dst is not None:
            dst.write_text(src.read_text())

    # copy __init__.py
    hydrodashboards_dir.joinpath("__init__.py").write_text(f'__version__ = "{VERSION}"')


    # %% write serve_bokeh.bat
    if virtual_env is None:
        virtual_env = VIRTUAL_ENV

    activate_env = cmd_activate.format(virtual_env=virtual_env)
    
    if bokeh_secret_key is not None:
        activate_env += f"""
rem set bokeh secret key
set BOKEH_SECRET_KEY="{bokeh_secret_key}"
set BOKEH_SIGN_SESSIONS=true"""

    app_dir.parent.joinpath("serve_hydrodashboard.bat").write_text(f"""{activate_env}

rem serve {app_dir.name}
python.exe serve_hydrodashboard.py -app_dir {app_dir.name}
""")
    
    app_dir.parent.joinpath("test_app.bat").write_text(f"""{activate_env}

rem serve {app_dir.name}
bokeh serve {app_dir.name}
""")
    

    app_dir.parent.joinpath("build_cache.bat").write_text(f"""{activate_env}

rem build cache
chdir ./{app_dir.name}
python build_cache.py
chdir ../
""")

    app_dir.parent.joinpath("update_timeseries_cache.bat").write_text(f"""{activate_env}

rem update time series cache
chdir ./{app_dir.name}
python time_series_cache.py
chdir ../
""")
# %% serve_hydrodashboard.py
    scripts_dir = Path(virtual_env) / "scripts"
    import sys
    sys.path.append(str(scripts_dir))    
    import serve_hydrodashboard
    serve_hydrodashboard_py = Path(serve_hydrodashboard.__file__)
    app_dir.parent.joinpath("serve_hydrodashboard.py").write_text(
        serve_hydrodashboard_py.read_text()
        )

def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="""
        Build your Bokeh dashboard.
        """
    )

    parser.add_argument(
        "-app_dir",
        required=True,
        help="A directory where the app will be build",
    )
    parser.add_argument(
        "-config_file",
        help="config.json with app configuration. If not supplied, it will be taken from the repository",
        default=None,
    )
    parser.add_argument(
        "-css_file",
        help="custom css-file for your application",
        default=None,
    )
    parser.add_argument(
        "-bokeh_secret_key",
        help="bokeh-secret-key. If provided all sessions will be externally signed",
        default=None,
    )
    parser.add_argument(
        "-virtual_env",
        help="Python environment to use for starting up the app. If not supplied it will use the current environment",
        default=None,
    )
    parser.add_argument(
        "-app_port",
        help="Port to serve the app. Default is 5003",
        type=int,
        default=5003,
    )

    return parser.parse_args()


if __name__ == "__main__":
    main()
