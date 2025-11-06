#%%
"""
🌊 Vullingsgraad app
"""

from pathlib import Path
import os
import logging
import pandas as pd
from dash import Dash, Input, Output, State, html
from dash.exceptions import PreventUpdate
from flask_caching import Cache

# ==== Projectmodules ====
from utils.data_loader import load_all_data
from utils.generate_styles import ensure_assets_css
from utils.style import(
    kaartvariabelen,
    vullingsgraad_classes,
    vulling_mm_classes,
    style_handle,
    page_wrapper_style,
    left_col_style,
    right_col_style,
    loader_style,
)
from components.share_url import ShareURL
from components.map.dropdowns import DropdownControls
from components.map.map_controller import MapWithControls
from components.combined_graph.combined_graph_controller import CombinedGraph
from components.video_graph.video_graph_controller import TimeControls



# ========================================================================
# 🏗️ App setup
# ========================================================================
def create_app():
    """Initialiseer Dash-app en cache."""
    app_dir = Path(__file__).parent
    data_dir = app_dir / "data"
    assets_dir = app_dir / "assets"

    app = Dash(__name__, assets_folder=str(assets_dir), suppress_callback_exceptions=True)
    cache = Cache(app.server, config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 3600})
    return app, cache, data_dir, assets_dir


app, cache, data_dir, assets_dir = create_app()


# ========================================================================
# 🧠 Logging
# ========================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logging.info("🚀 HydroDashboard wordt gestart...")

# ========================================================================
# 💅 CSS assets genereren
# ========================================================================

ensure_assets_css(Path(__file__).parent / "assets")
logging.info("🎨 CSS-bestanden gecontroleerd of aangemaakt in ./assets")

# ========================================================================
# 📂 Data laden
# ========================================================================
data = load_all_data(data_dir)

geojson_data = data["geojson_data"]
location_options = data["location_options"]
bounds = data["bounds"]
df_locs_mpn = data["df_locs_mpn"]
time_series_cache = data["time_series_cache"]
all_datetimes = data["all_datetimes"]
default_index = data["default_index"]
default_dt = data["default_dt"]
default_pgb = data["default_pgb"]
initial_kaartvariabele = data["initial_kaartvariabele"]
map_bounds = data["map_bounds"]
map_center = data["map_center"]
initial_stylemap = data["initial_stylemap"]
dd_locs_mpn_default = data["dd_locs_mpn_default"]

logging.info(
    f"✅ Data geladen: {len(location_options)} peilgebieden, "
    f"{len(df_locs_mpn)} meetpunten, {len(all_datetimes)} tijdstappen."
)


# ========================================================================
# 🧱 Componenten
# ========================================================================

share_url = ShareURL(
    mapping={
        "peilgebied": ("pgb-dropdown", "value"),
        "tijdindex": ("tijdslider", "value"),
        "kaartvariabele": ("kaartvariabele-dropdown", "value"),
    },
    assets_folder=assets_dir,
    block_control_update=["peilgebied", "tijdindex", "kaartvariabele"],
)


dropdowns = DropdownControls(
    location_options, kaartvariabelen, default_pgb, initial_kaartvariabele, share_url
)

initial_options = {
    "style": style_handle,
    "selected": default_pgb,
    "interactive": True,
    "bubblingMouseEvents": True,
}

map_component = MapWithControls(
    geojson_data=geojson_data,
    df_locs_mpn=df_locs_mpn,
    dd_locs_mpn_default=dd_locs_mpn_default,
    map_center=map_center,
    map_bounds=map_bounds,
    style_handle=style_handle,
    initial_stylemap=initial_stylemap,
    initial_options=initial_options,
    all_datetimes=all_datetimes,         
    time_series_cache=time_series_cache, 
)


combined_graph = CombinedGraph(
    df_locs_mpn=df_locs_mpn,
    geojson_data=geojson_data,
    cache=cache,
    time_series_cache=time_series_cache,
    all_datetimes=all_datetimes,
    vullingsgraad_classes=vullingsgraad_classes,
    vulling_classes=vulling_mm_classes,
)

time_controls = TimeControls(all_datetimes, default_index, time_series_cache)


# ========================================================================
# 🎨 Layout
# ========================================================================
def build_layout():
    return html.Div(
        style=page_wrapper_style,
        children=[
            html.Div(
                style=left_col_style,
                children=[
                    dropdowns.layout,
                    map_component.layout,
                    time_controls.layout,
                ],
            ),
            html.Div(id="page-loader", style=loader_style),
            html.Div(style=right_col_style, children=[combined_graph.layout]),
        ],
    )


app.layout = build_layout()


# ========================================================================
# 🔗 Callback-registratie
# ========================================================================
share_url.register_callbacks(app)
dropdowns.register_callbacks(app)
map_component.register_callbacks(app)
time_controls.register_callbacks(app)
combined_graph.register_callbacks(app)


# ========================================================================
# ⚙️ callbacks
# ========================================================================
@app.callback(
    Output("page-loader", "style"),
    [Input("combined-fig-store", "data"), Input("geojson-pgb", "hideout")],
    prevent_initial_call=True,
)
def hide_page_loader(fig_dict, stylemap):
    """Verberg de overlay zodra kaart en grafiek geladen zijn."""
    if not fig_dict or not stylemap:
        raise PreventUpdate
    return {"display": "none"}


# ========================================================================
# 🚀 Run
# ========================================================================
if __name__ == "__main__":
    app.title = "Vullingsgraad"
    port = int(os.getenv("PORT", 5005))
    logging.info(f"🌍 App draaien op http://127.0.0.1:{port}")
    app.run(port=port, debug=True)  