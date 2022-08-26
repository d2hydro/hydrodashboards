from pathlib import Path
import shutil
import fewspy
import hydrodashboards
import sys
from typing import Union
VIRTUAL_ENV = Path(sys.executable).parent.as_posix()
HYDRODASHBOARDS_DIR = Path(hydrodashboards.__file__).parent
CONFIG_FILE = Path(hydrodashboards.__file__).parent.joinpath("bokeh", "config.py")

app_dir = r"d:/projecten/D2108.Dashboard_WAM/01.app/20220814/wam"
virtual_env = None
app_port = 5003
config_file = r"d:\repositories\hydrodashboards\src\hydrodashboards\bokeh\config.py"

def copy_environment(virtual_env: Union[str, Path] = None):
    virtual_env = Path(virtual_env)
    
    if virtual_env.exists():
        shutil.rmtree(virtual_env)

    print(f"copying {VIRTUAL_ENV} to {VIRTUAL_ENV}")
    shutil.copytree(VIRTUAL_ENV, virtual_env)


def bokeh(app_dir: Union[str, Path],
          title: str,
          config_file: Union[str, Path] = None,
          virtual_env: Union[str, Path] = None,
          app_port: int = 5003):
    """
    Build a Bokeh dashboard

    Args:
        app_dir (Union[str, Path]): Directory where the app should be build
        config_file (Union[str, Path], optional): config.py with app-configuration that
            will be copied to app_dir/config.py. If None the default-file will be
            copied. Defaults to None.
        virtual_env (Union[str, Path], optional): Specification of the
            Python-environment in which the app will be launched. If None, the app will
            use the environment where this function is running. Defaults to None.
        app_port (int, optional): Port to use for the Bokeh-app. Defaults to 5003.

    Returns:
        None.

    """

    # %% remove and create directory
    app_dir = Path(app_dir)

    if app_dir.exists():
        shutil.rmtree(app_dir)

    app_dir.mkdir(parents=True)

    # %% provide template
    templates_dir = app_dir / "templates"
    templates_dir.mkdir()

    template_html = HYDRODASHBOARDS_DIR.joinpath("bokeh", "templates", "index.html")
    index_html = templates_dir / "index.html"
    index_html.write_text(
        template_html.read_text().replace("/bokeh/", f"/{app_dir.name}/")
        )

    # %% provide statics
    static_dir = app_dir / "static"

    css_dir = static_dir / "css"
    css_dir.mkdir(parents=True)
    template_css = HYDRODASHBOARDS_DIR.joinpath("bokeh", "static", "css", "styles.css")
    styles_css = css_dir / "styles.css"
    styles_css.write_text(
        template_css.read_text().replace("/bokeh/", f"/{app_dir.name}/")
        )

    icons_dir = static_dir / "icons"
    icons_src_dir = HYDRODASHBOARDS_DIR.joinpath("bokeh", "static", "icons")
    shutil.copytree(icons_src_dir, icons_dir)

    js_dir = static_dir / "js"
    js_src_dir = HYDRODASHBOARDS_DIR.joinpath("bokeh", "static", "js")
    shutil.copytree(js_src_dir, js_dir)

    # %% provide fewspy folder
    fewspy_src = Path(fewspy.__file__).parent
    fewspy_dir = app_dir / "fewspy"
    shutil.copytree(fewspy_src, fewspy_dir)

    # %% provide hydrodashboards folder
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
        if src.name in ["data.py", "main.py", "theme.yaml"]:
            dst = app_dir.joinpath(src.name)
        elif src.name != "config.py":
            dst = bokeh_dir.joinpath(src.name)

        if dst is not None:
            dst.write_text(src.read_text())

    # copy __init__.py
    hydrodashboards_dir.joinpath("__init__.py").write_text(
        Path(hydrodashboards.__file__).read_text())

    # %% copy config-file
    if config_file is None:
        config_file = CONFIG_FILE
    else:
        config_file = Path(config_file)

    app_dir.joinpath("config.py").write_text(config_file.read_text())

    # %% write serve_bokeh.bat
    if virtual_env is None:
        virtual_env = VIRTUAL_ENV

    app_dir.parent.joinpath("serve_bokeh.bat").write_text(
        rf"""rem setting environment to python installation
        SET VIRTUAL_ENV={virtual_env}
        SET PATH=%VIRTUAL_ENV%;%VIRTUAL_ENV%\Library\mingw-w64\bin;%VIRTUAL_ENV%\Library\usr\bin;%VIRTUAL_ENV%\Library\bin;%VIRTUAL_ENV%\Scripts;%VIRTUAL_ENV%\bin;%PATH%
        SET PROJ_LIB=%VIRTUAL_ENV%\Library\share\proj
        
        rem serve {app_dir.name}
        bokeh serve {app_dir.name} --port {app_port}
        """
        )
