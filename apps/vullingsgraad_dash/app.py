# %%

import dash
from dash import html, dcc, Output, Input, State, callback_context
import dash_leaflet as dl
import pandas as pd
import pyarrow.dataset as ds
from read import read_peilgebieden
from dash_extensions.javascript import assign
from pyproj import Transformer

# --- 0) App setup ---
app = dash.Dash(__name__)

# --- 1) RD‑bbox → WGS84 ---
xmin, ymin, xmax, ymax = 100500, 486900, 150150, 577550
transformer = Transformer.from_crs(28992, 4326, always_xy=True)
lon_sw, lat_sw = transformer.transform(xmin, ymin)
lon_ne, lat_ne = transformer.transform(xmax, ymax)
leaflet_bounds = [[lat_sw, lon_sw], [lat_ne, lon_ne]]

# --- 2) Laad peilgebieden (1×) ---
location_geojson, location_options = read_peilgebieden(
    file_path="d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/peilgebieden_cso_combi.shp",
    code_col="CODE",
    columns=["naam"],
)
for feat in location_geojson["features"]:
    feat["properties"]["style"] = {
        "fillColor": "gray",
        "color": "#666",
        "weight": 0.3,
        "fillOpacity": 0.3,
    }

# Bouw dropdown‑options uit de namen (zonder duplicaten)

# %%
# --- 3) Laad tijdserie en indexmap ---
ds_ = ds.dataset(
    "d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/vullingsgraad.arrow",
    format="feather",
)
full_df = ds_.to_table(columns=["datetime", "location_id", "value"]).to_pandas()
full_df["datetime"] = pd.to_datetime(full_df["datetime"])
unique_datetimes = sorted(full_df["datetime"].dt.floor("min").unique())
datum_to_index = {i: pd.Timestamp(dt) for i, dt in enumerate(unique_datetimes)}


# --- 4) Kleurfunctie & style‑cache ---
def kleur_bij_vullingsgraad(val):
    if pd.isna(val):
        return "gray"
    if val < 25:
        return "green"
    if val < 50:
        return "yellow"
    if val < 75:
        return "orange"
    return "red"


style_cache = {}


def build_stylemap_for_datetime(dt: pd.Timestamp):
    key = dt.isoformat()
    if key not in style_cache:
        grp = full_df[full_df["datetime"].dt.floor("min") == dt]
        style_cache[key] = {
            loc: {
                "fillColor": kleur_bij_vullingsgraad(val),
                "color": "#666",
                "weight": 0.3,
                "fillOpacity": 1,
            }
            for loc, val in zip(grp["location_id"], grp["value"])
        }
    return style_cache[key]


# Warm de eerste 20 timestamps even op
for dt in unique_datetimes[:20]:
    build_stylemap_for_datetime(pd.Timestamp(dt))

# --- 5) Initieel timestamp & hideout ---
default_idx = 0
default_dt = datum_to_index[default_idx]
initial_colors = build_stylemap_for_datetime(default_dt)
initial_label = default_dt.strftime("%Y-%m-%d %H:%M")

# --- 6) JS‑assign voor hideout + selected polygon stijl ---
style_handle = assign("""
    function(feature, context){
        const colors = context.hideout.colors || {};
        const selected = context.hideout.selected;
        const loc = feature.properties.location_id;
        const base = feature.properties.style;
        const style = colors[loc] || base;
        if(selected && selected === loc){
            style.weight = 3;
            style.color = 'blue';
        }
        return style;
    }
""")

# --- 7) Layout: één enkele Div met vier kinderen ---
app.layout = html.Div(
    [
        # 1) Dropdown linksboven
        html.Div(
            dcc.Dropdown(
                id="pgb-dropdown",
                options=[i["value"] for i in location_options],
                placeholder="Selecteer peilgebied",
                clearable=True,
                style={"width": "250px"},
            ),
            style={
                "position": "absolute",
                "top": "10px",
                "left": "10px",
                "zIndex": "1002",
            },
        ),
        # 2) Full‑screen kaart
        dl.Map(
            center=[(lat_sw + lat_ne) / 2, (lon_sw + lon_ne) / 2],
            bounds=leaflet_bounds,
            style={"height": "100vh", "width": "100%"},
            children=[
                dl.TileLayer(),
                dl.GeoJSON(
                    id="geojson-pgb",
                    data=location_geojson,
                    hideout={"colors": initial_colors, "selected": None},
                    options=dict(style=style_handle),
                ),
            ],
        ),
        # 3) Play/Pause + Slider + Label onderin
        html.Div(
            [
                html.Button("Play ▶️", id="play-button", n_clicks=0),
                html.Button("Pause ⏸️", id="pause-button", n_clicks=0),
                html.Div(
                    dcc.Slider(
                        id="tijdslider",
                        min=0,
                        max=len(unique_datetimes) - 1,
                        step=1,
                        value=default_idx,
                        updatemode="mouseup",
                        tooltip={"placement": "bottom", "always_visible": False},
                    ),
                    style={"width": "50vw", "margin": "0 10px"},
                ),
                html.Div(
                    initial_label,
                    id="datum-label",
                    style={"whiteSpace": "nowrap", "fontWeight": "bold"},
                ),
            ],
            style={
                "position": "absolute",
                "bottom": "10px",
                "left": "10px",
                "background": "rgba(255,255,255,0.9)",
                "padding": "8px",
                "borderRadius": "6px",
                "zIndex": "1000",
                "display": "flex",
                "alignItems": "center",
                "gap": "12px",
            },
        ),
        # 4) Interval (onzichtbaar)
        dcc.Interval(id="interval", interval=1000, disabled=True),
        # 5) Klik‑info / dropdown‑info
        html.Div(
            id="click-output",
            style={
                "position": "absolute",
                "top": "10px",
                "right": "10px",
                "zIndex": "1001",
                "background": "white",
                "padding": "5px",
                "borderRadius": "5px",
            },
        ),
    ]
)


# --- 8) Enkele callback voor Play/Pause, slider, kaart‑update én dropdown selectie ---
@app.callback(
    Output("interval", "disabled"),
    Output("tijdslider", "value"),
    Output("geojson-pgb", "hideout"),
    Output("datum-label", "children"),
    Output("click-output", "children"),
    Input("play-button", "n_clicks"),
    Input("pause-button", "n_clicks"),
    Input("interval", "n_intervals"),
    Input("tijdslider", "value"),
    Input("pgb-dropdown", "value"),
    State("interval", "disabled"),
    State("pgb-dropdown", "value"),
)
def drive(play, pause, n_int, slider_val, dropdown_val, disabled, selected_val):
    ctx = callback_context
    # Toggle play/pause
    if ctx.triggered and ctx.triggered[0]["prop_id"].startswith("play-button"):
        disabled = False
    if ctx.triggered and ctx.triggered[0]["prop_id"].startswith("pause-button"):
        disabled = True
    # Advance slider if playing
    if (
        ctx.triggered
        and ctx.triggered[0]["prop_id"] == "interval.n_intervals"
        and not disabled
    ):
        slider_val = (slider_val + 1) % len(unique_datetimes)
    # Determine timestamp & stylemap
    dt = datum_to_index[int(slider_val)]
    stylemap = build_stylemap_for_datetime(dt)
    hideout = {"colors": stylemap, "selected": dropdown_val}
    label = dt.strftime("%Y-%m-%d %H:%M")
    # Klik‑info of dropdown‑info
    if ctx.triggered and ctx.triggered[0]["prop_id"] == "geojson-pgb.click_feature":
        # (indien je deze mogelijkheid nog wilt ondersteunen)
        info = "Klik op peilgebied…"
    else:
        # Toon dropdown‑selectie
        name = next(
            (opt["label"] for opt in location_options if opt["value"] == dropdown_val),
            None,
        )
        info = f"Selected: {name}" if name else "Selecteer een peilgebied"
    return disabled, slider_val, hideout, label, info


if __name__ == "__main__":
    app.run(debug=True)
