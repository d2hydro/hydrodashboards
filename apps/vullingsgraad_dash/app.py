#%%
import dash
from dash import html, dcc, Output, Input, State
import dash_leaflet as dl
import pandas as pd
import pyarrow.dataset as ds
from read import read_peilgebieden
from dash_extensions.javascript import assign
from pyproj import Transformer
from dash.exceptions import PreventUpdate

# ==============================
# 0. App-initialisatie
# ==============================
app = dash.Dash(__name__)

# ==============================
# 1. RD-bbox naar WGS84
# ==============================
xmin, ymin, xmax, ymax = 100500, 486900, 150150, 577550
transformer = Transformer.from_crs(28992, 4326, always_xy=True)
lon_sw, lat_sw = transformer.transform(xmin, ymin)
lon_ne, lat_ne = transformer.transform(xmax, ymax)
leaflet_bounds = [[lat_sw, lon_sw], [lat_ne, lon_ne]]

# ==============================
# 2. Peilgebieden inladen + standaardstijl
# ==============================
geojson_data, options = read_peilgebieden(
    file_path="d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/peilgebieden_cso_combi.shp",
    code_col="CODE",
    columns=["naam", "streefpeil", "inundatiepeil", "berging_bij_inundatiepeil", "peil_bij_nul_berging"],
)
for feat in geojson_data["features"]:
    feat["properties"]["style"] = {
        "fillColor": "gray",
        "color": "#666",
        "weight": 0.3,
        "fillOpacity": 0.3
    }

# Maak nette dropdown-opties
location_options = []
seen = set()
for opt in options:
    lbl = opt.get("label")
    val = opt.get("value")
    if lbl and val and val not in seen:
        seen.add(val)
        location_options.append({"label": f"{lbl} ({val})", "value": val})

# ==============================
# 3. Tijdserie inladen (Arrow)
# ==============================
ds_ = ds.dataset(
    "d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/vullingsgraad.arrow",
    format="feather"
)
full_df = ds_.to_table(columns=["datetime", "location_id", "value"]).to_pandas()
full_df["datetime"] = pd.to_datetime(full_df["datetime"])

# ==============================
# 4. Unieke tijdstippen + indexmap
# ==============================
unique_datetimes = sorted(full_df["datetime"].dt.floor("min").unique())
datum_to_index = {i: pd.Timestamp(dt) for i, dt in enumerate(unique_datetimes)}

# ==============================
# 5. Kleurfunctie
# ==============================
def kleur_bij_vullingsgraad(val):
    if pd.isna(val):
        return "gray"
    if val < 25:   return "green"
    if val < 50:   return "yellow"
    if val < 75:   return "orange"
    return "red"

# ==============================
# 6. Style-cache voor performance
# ==============================
style_cache = {}
def build_stylemap_for_datetime(dt: pd.Timestamp):
    key = dt.isoformat()
    if key in style_cache:
        return style_cache[key]
    grp = full_df[full_df["datetime"].dt.floor("min") == dt]
    stylemap = {
        loc: {
            "fillColor": kleur_bij_vullingsgraad(val),
            "color": "#666", "weight": 0.3, "fillOpacity": 1,
            "vullingsgraad": val 
        }
        for loc, val in zip(grp["location_id"], grp["value"])
    }
    style_cache[key] = stylemap
    return stylemap

# Pre-warm cache (eerste 20 tijdstippen)
for dt in unique_datetimes[:20]:
    build_stylemap_for_datetime(pd.Timestamp(dt))

# ==============================
# 7. Startwaarden
# ==============================
default_index = 0
default_dt = datum_to_index[default_index]
initial_stylemap = build_stylemap_for_datetime(default_dt)
initial_label = default_dt.strftime("%Y-%m-%d %H:%M")

# ==============================
# 8. JS-functie: highlight geselecteerd peilgebied
# ==============================
style_handle = assign("""
function(feature, context){
    const stylemap = context.hideout || {};
    const loc = feature.properties.location_id;
    const sel = context.selected;
    let base = stylemap[loc] || feature.properties.style;
    if(sel && loc === sel){
        base = {...base, weight:3, color:'yellow'};
    }
    return base;
}
""")

# ==============================
# 9. Layout: dropdown, kaart, slider, info
# ==============================
app.layout = html.Div([
    html.Div(
        dcc.Dropdown(
            id="pgb-dropdown",
            options=location_options,
            placeholder="Selecteer peilgebied",
            clearable=True,
            style={"width": "350px"},
        ),
        style={"position": "absolute", "top": "10px", "left": "10px", "zIndex": 1002}
    ),
    dl.Map(
        center=[(lat_sw + lat_ne) / 2, (lon_sw + lon_ne) / 2],
        bounds=leaflet_bounds,
        style={"height": "100vh", "width": "100%"},
        preferCanvas=True,
        children=[
            dl.TileLayer(),
            dl.GeoJSON(
                id="geojson-pgb",
                data=geojson_data,
                hideout=initial_stylemap,
                options=dict(
                    style=style_handle,
                    interactive=True,
                    bubblingMouseEvents=True
                ),
                hoverStyle=dict(
                    weight=2,
                    color="yellow",
                    dashArray=""
                ),
                children=[dl.Tooltip(id="geojson-tooltip", sticky=True)],
                eventHandlers=dict(
                    click=assign("""
                        function(e){
                            return e.target.feature.properties;
                        }
                    """)
                )
            ),
        ]
    ),
    html.Div(id="hover-info", style={
        "position": "absolute", "bottom": "10px", "left": "10px",
        "background": "white", "padding": "5px", "borderRadius": "5px", "zIndex": 1001
    }),
    html.Div([
        html.Button("Play ▶️", id="play-button", n_clicks=0),
        html.Button("Pause ⏸️", id="pause-button", n_clicks=0),
        html.Div(
            dcc.Slider(
                id="tijdslider",
                min=0, max=len(unique_datetimes) - 1, step=1,
                value=default_index,
                updatemode="mouseup",
                included=True,
                tooltip={"placement": "bottom", "always_visible": False},
                marks=None
            ),
            style={"width": "50vw"}
        ),
        html.Div(initial_label, id="datum-label", style={"whiteSpace": "nowrap", "fontWeight": "bold"}),
        dcc.Interval(id="interval", interval=1000, disabled=True),
    ], style={
        "position": "absolute", "bottom": "10px", "left": "10px",
        "background": "rgba(255,255,255,0.9)", "padding": "8px",
        "borderRadius": "6px", "zIndex": 1000,
        "display": "flex", "alignItems": "center", "gap": "12px"
    }),
    html.Div(id="click-output", style={
        "position": "absolute", "top": "50px", "right": "10px", "zIndex": 1001,
        "background": "white", "padding": "5px", "borderRadius": "5px"
    }),
])

# ==============================
# 10. Play/Pause: toggling interval
# ==============================
@app.callback(
    Output("interval", "disabled"),
    Input("play-button", "n_clicks"),
    Input("pause-button", "n_clicks"),
)
def toggle_interval(play, pause):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    btn = ctx.triggered[0]["prop_id"].split(".")[0]
    return False if btn == "play-button" else True

# ==============================
# 11. Automatisch slider opschuiven
# ==============================
@app.callback(
    Output("tijdslider", "value"),
    Input("interval", "n_intervals"),
    State("interval", "disabled"),
    State("tijdslider", "value"),
)
def advance_slider(n, disabled, current):
    if disabled or current is None:
        raise PreventUpdate
    return (current + 1) % len(unique_datetimes)

# ==============================
# 12. Update kaartstyle/label/opties bij tijd of selectie
# ==============================
@app.callback(
    Output("geojson-pgb", "hideout"),
    Output("datum-label", "children"),
    Output("geojson-pgb", "options"),
    Input("tijdslider", "value"),
    Input("pgb-dropdown", "value"),
)
def update_stylemap(idx, sel):
    if idx is None or int(idx) not in datum_to_index:
        raise PreventUpdate
    dt = datum_to_index[int(idx)]
    stylemap = build_stylemap_for_datetime(dt)
    label = dt.strftime("%Y-%m-%d %H:%M")
    options = dict(
        style=style_handle,
        selected=sel,
        interactive=True,
        bubblingMouseEvents=True
    )
    return stylemap, label, options


# ==============================
# 13. Klik op kaart = selecteer in dropdown
# ==============================
@app.callback(
    Output("pgb-dropdown", "value"),
    Input("geojson-pgb", "clickData")
)
def select_dropdown_on_click(clickData):
    if not clickData or "properties" not in clickData:
        raise PreventUpdate
    return clickData["properties"]["location_id"]

# ==============================
# 14. Tooltip-tekst bij hover
# ==============================
@app.callback(
    Output("geojson-tooltip", "children"),
    Input("geojson-pgb", "hoverData"),
    State("tijdslider", "value")
)
def update_tooltip(feature, idx):
    if not feature or "properties" not in feature:
        return ""
    props = feature["properties"]
    code = props.get("location_id", "")
    naam = props.get("naam", "")
    dt = datum_to_index[int(idx)]
    vg = style_cache.get(dt.isoformat(), {}).get(code, {}).get("vullingsgraad")
    vg_text = f"{vg:.1f} %" if vg is not None else "n.b."
    return f"naam: {naam} (code: {code}) — {vg_text}"

# ==============================
# Start de app
# ==============================
if __name__ == "__main__":
    app.run(debug=True)
