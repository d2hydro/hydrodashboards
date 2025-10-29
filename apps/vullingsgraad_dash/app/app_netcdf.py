
# %%
import json
import sys
import time
from functools import lru_cache, wraps
from pathlib import Path
import bisect, math

import dash
import dash_leaflet as dl
import pandas as pd
import plotly.graph_objs as go
from dash import Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate
from dash_extensions.javascript import assign
from fewspy.cache import TimeSeriesCache
from flask_caching import Cache
from plotly.subplots import make_subplots
from read import read_mpn_locs, read_peilgebieden

# ====== PADEN / INIT ======
app_dir = Path(__file__).parent
data_dir = app_dir.parent.joinpath("data")
assets_dir = app_dir / "assets"

app = dash.Dash(__name__, assets_folder=str(assets_dir))

cache = Cache(
    app.server,
    config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 3600},
)

def timed_callback(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        result = f(*args, **kwargs)
        dt = time.perf_counter() - t0
        print(f"[TIMING] {f.__name__} {dt:.3f}s")
        return result
    return wrapper


def bounds_to_map(xmin, ymin, xmax, ymax):
    dx = xmax - xmin
    dy = ymax - ymin
    return [[ymin, xmin], [ymax + dy, xmin - 4 * dx]], [ymin + dy / 2, xmax - dx / 2]


# ====== DATA LADEN ======
t0 = time.time()
geojson_data, location_options, bounds = read_peilgebieden(
    file_path=data_dir.joinpath("peilgebieden_cso_combi.shp").as_posix(),
    code_col="CODE",
    columns=[
        "naam",
        "streefpeil",
        "inundatiepeil",
        "berging_bij_inundatiepeil",
        "peil_bij_nul_berging",
    ],
    style={
        "fillColor": "gray",
        "color": "#666",
        "weight": 0.3,
        "fillOpacity": 1,
    },
)
map_bounds, map_center = bounds_to_map(*bounds)
print("TIJD: shapefile/geodata ingelezen in", round(time.time() - t0, 2), "s")

df_locs_mpn = read_mpn_locs(data_dir.joinpath("mpn_locations.arrow"))

time_series_cache = TimeSeriesCache.from_manifest_file(
    data_dir.joinpath("time_series", "manifest.json")
)

t0 = time.time()
all_datetimes = [pd.Timestamp(i) for i in time_series_cache.common_time_axis]
print("TIJD: tijdas opgebouwd in", round(time.time() - t0, 2), "s")
print("[DEBUG init] aantal timestamps:", len(all_datetimes))
if len(all_datetimes) > 0:
    print("[DEBUG init] eerste timestamp:", all_datetimes[0])
    print("[DEBUG init] laatste  timestamp:", all_datetimes[-1])

kaartvariabelen = [
    {"label": "vullingsgraad [%]", "value": "vullingsgraad"},
    {"label": "vulling [mm]", "value": "vulling"},
]

# ===== CONSTANTE KLEUREN =====
VULLINGSGRAAD_CLASSES = [
    (0, 25,  "rgba(120,200,120,1.0)"),
    (25, 50, "rgba(255,255,100,1.0)"),
    (50, 75, "rgba(255,200,100,1.0)"),
    (75, 100,"rgba(255,100,100,1.0)"),
]

VULLING_MM_CLASSES = [
    (0, 10,  "rgba(255,255,255,1.0)"),
    (10, 20, "rgba(180,211,231,1.0)"),
    (20, 30, "rgba(114,178,215,1.0)"),
    (30, 40, "rgba(62,145,196,1.0)"),
    (40, 60, "rgba(28,95,165,1.0)"),
]

def _pick_color(val, classes):
    if pd.isna(val):
        return "gray"
    for low, high, color in classes:
        if low <= val < high:
            return color
    return classes[-1][2]

def kleur_bij_vullingsgraad(val):
    return _pick_color(val, VULLINGSGRAAD_CLASSES)

def kleur_bij_vulling(val):
    return _pick_color(val, VULLING_MM_CLASSES)


# ====== DYNAMIC STYLE FUN VOOR DE KAART ======
style_handle = assign("""
function(feature, context){
    const stylemap = context.hideout || {};
    const loc = feature.properties.location_id;
    const sel = context.selected;

    let base = stylemap[loc] || feature.properties.style || {};

    base = {
        ...base,
        color: base.color || "rgba(15,23,42,0.35)",
        weight: 1,
        fillOpacity: base.fillOpacity !== undefined ? base.fillOpacity : 0.7
    };

    if (sel && loc === sel) {
        base = {
            ...base,
            weight: 2,
            color: "rgba(251,191,36,0.95)",
            fillOpacity: 0.85
        };
    }

    return base;
}
""")

default_index = len(all_datetimes) - 1
default_dt = all_datetimes[default_index]
default_pgb = location_options[0]["value"] if location_options else None
initial_label = default_dt.strftime("%Y-%m-%d %H:%M")
initial_kaartvariabele = "vullingsgraad"

if default_pgb is not None and "peilgebied_combi_attr" in df_locs_mpn.columns:
    dd_locs_mpn_default = (
        df_locs_mpn.loc[
            df_locs_mpn["peilgebied_combi_attr"].astype(str) == str(default_pgb),
            "peilgebied_combi_attr",
        ]
        .astype(str)
        .dropna()
        .unique()
        .tolist()
    )
else:
    dd_locs_mpn_default = []

print("[DEBUG init] default_pgb:", default_pgb)
print("[DEBUG init] dd_locs_mpn_default:", dd_locs_mpn_default[:5], "...")

@lru_cache(maxsize=128)
def get_kaartdata_for_datetime(dt, kaartvariabele):
    """Geef per peilgebied kleurinfo/waarde op specifieke timestamp."""
    dt = pd.to_datetime(dt).to_pydatetime()
    print(f"[DEBUG kaartdata] build kaartdata voor {dt} var={kaartvariabele}")
    if kaartvariabele == "vullingsgraad":
        df = time_series_cache.get_time_series(
            filter_id="VullingsgraadOutput",
            parameter_id="vullingsgraad",
            start_time=dt,
            end_time=dt,
        )
        kleur_fn = kleur_bij_vullingsgraad
    else:
        df = time_series_cache.get_time_series(
            filter_id="VullingsgraadOutput",
            parameter_id="vulling_mm",
            start_time=dt,
            end_time=dt,
        )
        kleur_fn = kleur_bij_vulling

    print("[DEBUG kaartdata] df shape:", df.shape if hasattr(df, "shape") else "geen df?")
    df = df.loc[dt].reset_index()
    ids = df["location_id"].to_list()
    vals = df[dt].to_list()
    print("[DEBUG kaartdata] first 5 ids:", ids[:5])
    print("[DEBUG kaartdata] first 5 vals:", vals[:5])

    return {
        loc: {
            "fillColor": kleur_fn(val),
            "color": "#666",
            "weight": 0.3,
            "fillOpacity": 1,
            kaartvariabele: val,
        }
        for loc, val in zip(ids, vals)
    }

initial_stylemap = get_kaartdata_for_datetime(default_dt, initial_kaartvariabele)

initial_options = {
    "style": style_handle,
    "selected": default_pgb,
    "interactive": True,
    "bubblingMouseEvents": True,
}

EMPTY_FIG = go.Figure()
EMPTY_FIG.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=0, r=0, t=0, b=0),
    xaxis=dict(visible=False),
    yaxis=dict(visible=False),
    showlegend=False,
)

# ====== LAYOUT STYLES ======

page_wrapper_style = {
    "display": "flex",
    "flexDirection": "row",
    "height": "100vh",
    "width": "100vw",
    "overflow": "hidden",
}

left_col_style = {
    "position": "relative",
    "flex": "1 1 50%",
    "minWidth": 0,
    "minHeight": 0,
    "overflow": "hidden",
    "height": "100vh",
}

right_col_style = {
    "display": "flex",
    "flexDirection": "column",
    "flex": "1 1 50%",
    "height": "100vh",
    "minWidth": 0,
    "minHeight": 0,
    "padding": "0px",
    "boxShadow": "0 2px 8px rgba(0,0,0,0.05)",
    "borderRadius": "5px",
    "backgroundColor": "rgba(255,255,255,0.0)",
    "overflow": "hidden",
}

# ====== APP LAYOUT ======
app.layout = html.Div(
    style=page_wrapper_style,
    children=[
        # ========== LINKER KOLOM ==========
        html.Div(
            style=left_col_style,
            children=[
                dl.Map(
                    center=map_center,
                    zoom=10,
                    bounds=map_bounds,
                    style={"height": "100%", "width": "100%"},
                    preferCanvas=True,
                    children=[
                        dl.TileLayer(),
                        dl.GeoJSON(
                            id="geojson-pgb",
                            data=geojson_data,
                            hideout=initial_stylemap,
                            options=initial_options,
                            eventHandlers={
                                "click": assign(
                                    "function(e){return e?.target?.feature?.properties||{};}"
                                )
                            },
                        ),
                        dl.GeoJSON(
                            id="marker-mpn",
                            data=json.loads(df_locs_mpn.to_json()),
                            filter=assign(
                                """
                                function(feature, context){
                                    const ok = feature && feature.geometry && feature.geometry.type === "Point"
                                        && Array.isArray(feature.geometry.coordinates)
                                        && feature.geometry.coordinates.length === 2
                                        && isFinite(feature.geometry.coordinates[0])
                                        && isFinite(feature.geometry.coordinates[1]);
                                    if (!ok) return false;

                                    const list = context.hideout || [];
                                    const attr = String(feature.properties?.peilgebied_combi_attr);
                                    return Array.isArray(list) && list.includes(attr);
                                }
                                """
                            ),
                            hideout=dd_locs_mpn_default,
                            options={
                                "pane": "markerPane",
                                "onEachFeature": assign(
                                    "function(f, layer){ if(layer && layer.bringToFront){ layer.bringToFront(); } }"
                                ),
                                "pointToLayer": assign(
                                    """
                                    function(feature, latlng){
                                        const naam = feature?.properties?.naam || "meetpunt";
                                        const locId = feature?.properties?.location_id || feature?.properties?.id || "(onbekend id)";

                                        const tooltipHtml = "<b>" + naam + "</b><br/>" + locId;

                                        const marker = L.circleMarker(latlng, {
                                            radius: 5,
                                            fillColor: '#4cc9f0',
                                            color: '#1b4d5e',
                                            weight: 1.5,
                                            opacity: 1,
                                            fillOpacity: 0.9
                                        });

                                        marker.bindTooltip(tooltipHtml, {
                                            permanent: false,
                                            direction: "top",
                                            opacity: 0.95
                                        });

                                        return marker;
                                    }
                                    """
                                ),
                                "bubblingMouseEvents": True,
                            },
                            eventHandlers={
                                "click": assign(
                                    """
                                    function(e){
                                        const layer = e && (e.layer || e.sourceTarget || e.target);
                                        const feat = layer && layer.feature;
                                        const props = (feat && feat.properties) ? feat.properties : {};
                                        const ll = e && e.latlng ? e.latlng : null;
                                        return {
                                            properties: props,
                                            lat: ll?.lat,
                                            lng: ll?.lng
                                        };
                                    }
                                    """
                                )
                            },
                        ),
                        dl.LayerGroup(id="mpn-click-layer"),
                    ],
                ),

                # Controlsbox linksboven
                html.Div(
                    [
                        html.Label(
                            [
                                "kaartvariabele: ",
                                html.Span(
                                    "?",
                                    title="Selecteer de variabele die op de kaart moet worden getoond",
                                    style={"cursor": "help"},
                                ),
                            ],
                            style={"fontSize": "13px"},
                        ),
                        dcc.Dropdown(
                            id="kaartvariabele-dropdown",
                            options=kaartvariabelen,
                            value=initial_kaartvariabele,
                            clearable=False,
                            style={"width": "240px", "marginBottom": "8px"},
                        ),
                        html.Label(
                            [
                                "peilgebied: ",
                                html.Span(
                                    "?",
                                    title="Selecteer een peilgebied waarvoor de grafieken moeten worden getoond",
                                    style={"cursor": "help"},
                                ),
                            ],
                            style={"fontSize": "13px"},
                        ),
                        dcc.Dropdown(
                            id="pgb-dropdown",
                            options=location_options,
                            value=default_pgb,
                            placeholder="Selecteer peilgebied",
                            clearable=True,
                            style={"width": "240px"},
                        ),
                    ],
                    style={
                        "position": "absolute",
                        "top": "10px",
                        "left": "10px",
                        "zIndex": 1002,
                        "background": "rgba(220,240,255,1)",
                        "borderRadius": "8px",
                        "padding": "10px",
                        "boxShadow": "0 2px 8px rgba(0,0,0,0.15)",
                    },
                ),

                # Slider + play/pause onderin kaart
                html.Div(
                    [
                        html.Button(
                            id="playpause-button",
                            n_clicks=0,
                            style={"width": "72px"},
                        ),
                        dcc.Store(id="is-playing", data=False),

                        html.Div(
                            initial_label,
                            id="datum-label",
                            style={"fontWeight": "bold"},
                        ),

                        html.Div(
                            [
                                dcc.Graph(
                                    id="mini-tijdserie",
                                    config={"displayModeBar": False},
                                    style={
                                        "height": "50px",
                                        "width": "350px",
                                        "position": "absolute",
                                        "top": 0,
                                        "left": "25px",
                                        "pointerEvents": "none",
                                    },
                                ),
                                dcc.Slider(
                                    id="tijdslider",
                                    min=0,
                                    max=len(all_datetimes) - 1,
                                    value=default_index,
                                    marks=None,
                                    updatemode="mouseup",
                                ),
                            ],
                            style={
                                "position": "relative",
                                "width": "400px",
                                "height": "50px",
                                "display": "inline-block",
                            },
                        ),
                    ],
                    style={
                        "position": "absolute",
                        "bottom": "10px",
                        "left": "10px",
                        "background": "rgba(255,255,255,0.9)",
                        "padding": "8px",
                        "borderRadius": "6px",
                        "zIndex": 1000,
                        "display": "flex",
                        "gap": "10px",
                        "alignItems": "center",
                        "boxShadow": "0 2px 8px rgba(0,0,0,0.15)",
                    },
                ),

                dcc.Interval(id="interval", interval=1000, disabled=True),

                # overlay loader
                html.Div(
                    id="page-loader",
                    children=html.Div(
                        className="loader-inner",
                        children=[
                            html.Div(className="spinner-ring"),
                            html.Div("kaart en data loading", className="loader-text"),
                        ],
                    ),
                    style={
                        "display": "block",
                        "position": "absolute",
                        "top": 0,
                        "left": 0,
                        "right": 0,
                        "bottom": 0,
                        "backgroundColor": "rgba(255,255,255,0.6)",
                        "backdropFilter": "blur(2px)",
                        "zIndex": 2000,
                        "alignItems": "center",
                        "justifyContent": "center",
                        "display": "flex",
                        "flexDirection": "column",
                        "fontSize": "14px",
                        "fontWeight": "500",
                        "color": "#0f172a",
                    },
                ),

                # stores
                dcc.Store(id="clicked-mpn-store", data=None),
                dcc.Store(id="clicked-trace-store", data=None),
            ],
        ),

        # ========== RECHTER KOLOM ==========
        html.Div(
            style=right_col_style,
            children=[
                dcc.Store(id="combined-fig-store"),

                dcc.Loading(
                    id="loading-combined",
                    type="default",
                    style={
                        "flex": "1 1 auto",
                        "minHeight": 0,
                        "minWidth": 0,
                        "display": "flex",
                        "flexDirection": "column",
                        "overflow": "hidden",
                    },
                    children=[
                        dcc.Graph(
                            id="combined-graph",
                            figure=EMPTY_FIG,
                            config={
                                "displayModeBar": True,
                                "scrollZoom": True,
                                "displaylogo": False,
                                "modeBarButtonsToRemove": ["toImage"],
                                "edits": {"shapePosition": True},
                                "responsive": True,
                            },
                            style={
                                "flex": "1 1 auto",
                                "minHeight": 0,
                                "minWidth": 0,
                                "margin": "10px",
                                "height": "96vh",
                                "width": "48vw",
                                "overflow": "hidden",
                            },
                        ),
                    ],
                ),

                html.Div(
                    id="click-output",
                    style={
                        "fontSize": "12px",
                        "color": "#475569",
                        "paddingTop": "4px",
                        "minHeight": "0px",
                        "lineHeight": "1.2",
                        "overflow": "hidden",
                        "textOverflow": "ellipsis",
                        "whiteSpace": "nowrap",
                    },
                ),
            ],
        ),
    ],
)

# ====== CALLBACKS ======

@app.callback(
    Output("page-loader", "style"),
    [Input("combined-fig-store", "data"), Input("geojson-pgb", "hideout")],
    prevent_initial_call=True,
)
def hide_page_loader(fig_dict, stylemap):
    if not fig_dict or not stylemap:
        raise PreventUpdate
    return {"display": "none"}


@app.callback(
    Output("clicked-mpn-store", "data"),
    Input("marker-mpn", "clickData"),
    prevent_initial_call=True,
)
def store_clicked_mpn(cd):
    print("[DEBUG clicked-mpn-store] storing clickData:", cd)
    return cd


@app.callback(
    Output("mpn-click-layer", "children"),
    [
        Input("clicked-mpn-store", "data"),
        Input("clicked-trace-store", "data"),
        Input("pgb-dropdown", "value"),
    ],
)
def highlight_selected_point(mpn_clickdata, clicked_trace_id, selected_pgb):
    from dash import callback_context as ctx
    print("[DEBUG highlight_selected_point] trigger:", ctx.triggered)
    print("[DEBUG highlight_selected_point] mpn_clickdata:", mpn_clickdata)
    print("[DEBUG highlight_selected_point] clicked_trace_id:", clicked_trace_id)
    print("[DEBUG highlight_selected_point] selected_pgb:", selected_pgb)

    # Nieuwe selectie van peilgebied -> highlight weg
    if ctx.triggered and ctx.triggered[0]["prop_id"].startswith("pgb-dropdown"):
        print("[DEBUG highlight_selected_point] reset because pgb-dropdown changed")
        return []

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    sel_id = None
    naam = None
    lat = None
    lng = None

    if trigger_id == "clicked-trace-store":
        sel_id = clicked_trace_id
    elif trigger_id == "clicked-mpn-store":
        if not mpn_clickdata:
            raise PreventUpdate
        props = mpn_clickdata.get("properties", {}) or {}
        sel_id = props.get("location_id") or props.get("id")
        naam = props.get("naam") or "meetpunt"
        lat = mpn_clickdata.get("lat")
        lng = mpn_clickdata.get("lng")
    else:
        if clicked_trace_id:
            sel_id = clicked_trace_id
        elif mpn_clickdata:
            props = mpn_clickdata.get("properties", {}) or {}
            sel_id = props.get("location_id") or props.get("id")
            naam = props.get("naam") or "meetpunt"
            lat = mpn_clickdata.get("lat")
            lng = mpn_clickdata.get("lng")

    print("[DEBUG highlight_selected_point] resolved sel_id:", sel_id, "lat/lng:", lat, lng, "naam:", naam)

    if not sel_id:
        return []

    # lookup coord als nodig
    if lat is None or lng is None:
        row = df_locs_mpn.loc[df_locs_mpn["location_id"] == sel_id]
        print("[DEBUG highlight_selected_point] lookup row empty?", row.empty)
        if row.empty:
            return []

        if {"lat", "lng"}.issubset(row.columns):
            lat = row["lat"].iloc[0]
            lng = row["lng"].iloc[0]
        elif {"lat", "lon"}.issubset(row.columns):
            lat = row["lat"].iloc[0]
            lng = row["lon"].iloc[0]
        elif "geometry" in row.columns:
            geom = row["geometry"].iloc[0]
            lat = geom.y
            lng = geom.x
        else:
            print("[DEBUG highlight_selected_point] no coords in row columns", row.columns)
            return []

        if naam is None and "naam" in row.columns:
            naam = row["naam"].iloc[0]
        if naam is None:
            naam = sel_id

    print("[DEBUG highlight_selected_point] final marker lat/lng:", lat, lng)

    marker = dl.CircleMarker(
        center=[lat, lng],
        radius=7,
        color="#b28900",
        weight=2,
        fillColor="#ffe680",
        fillOpacity=0.9,
        children=[
            dl.Tooltip(sel_id),
            dl.Popup(
                html.Div(
                    [
                        html.B(
                            naam,
                            style={"color": "#0f172a", "fontWeight": "600"},
                        ),
                        html.Br(),
                        html.Span(
                            f"ID: {sel_id}",
                            style={"color": "#475569", "fontSize": "12px"},
                        ),
                    ],
                    style={"minWidth": "140px", "maxWidth": "200px"},
                ),
                autoPan=True,
                closeOnClick=False,
            ),
        ],
    )

    return [marker]


@app.callback(
    Output("geojson-pgb", "hideout"),
    Output("datum-label", "children"),
    Output("geojson-pgb", "options"),
    Input("tijdslider", "value"),
    Input("pgb-dropdown", "value"),
    Input("kaartvariabele-dropdown", "value"),
    prevent_initial_call=True,
)
def update_stylemap(idx, sel, var):
    print(f"[DEBUG update_stylemap] idx={idx}, sel={sel}, var={var}")
    if idx is None or not sel or not var:
        raise PreventUpdate
    dt = all_datetimes[int(idx)]
    print("[DEBUG update_stylemap] dt chosen:", dt)
    stylemap = get_kaartdata_for_datetime(dt, var)
    label = dt.strftime("%Y-%m-%d %H:%M")
    options = {
        "style": style_handle,
        "selected": sel,
        "interactive": True,
        "bubblingMouseEvents": True,
    }
    print("[DEBUG update_stylemap] stylemap keys sample:", list(stylemap.keys())[:5])
    return stylemap, label, options


@app.callback(
    Output("pgb-dropdown", "value"),
    Input("geojson-pgb", "clickData"),
    prevent_initial_call=True,
)
def select_dropdown_on_click(clickData):
    print("[DEBUG select_dropdown_on_click] clickData:", clickData)
    return clickData["properties"]["location_id"]


# ===== Grote grafiek -> opgeslagen basisfiguur =====
@app.callback(
    Output("combined-fig-store", "data"),
    [Input("pgb-dropdown", "value"),
     Input("kaartvariabele-dropdown", "value")],
)
@timed_callback
def build_combined_figure(sel, var):
    # NOTE: bumped cache key to v3 so we always see debug prints when switching pgb
    if not sel:
        print("[DEBUG build_combined_figure] geen sel -> PreventUpdate")
        raise PreventUpdate

    ckey = f"combined_v3_{sel}"
    print(f"[DEBUG build_combined_figure] START sel={sel} var={var} cachekey={ckey}")

    # probeer cache
    fig = None
    try:
        if hasattr(cache, "cache") and cache.cache is not None:
            cached = cache.get(ckey)
            if cached is not None:
                print("[DEBUG build_combined_figure] cache HIT")
                fig = go.Figure(cached)
    except Exception as e:
        print(f"[CACHE WARN] cache.get('{ckey}'): {e}")

    if fig is None:
        print("[DEBUG build_combined_figure] cache MISS -> data ophalen")

        # ===== data ophalen =====
        df_vg = time_series_cache.get_time_series(
            filter_id="VullingsgraadOutput",
            parameter_id="vullingsgraad",
            location_ids=[sel],
        )
        df_vul = time_series_cache.get_time_series(
            filter_id="VullingsgraadOutput",
            parameter_id="vulling_mm",
            location_ids=[sel],
        )
        df_pgb = time_series_cache.get_time_series(
            filter_id="PeilgebiedWaterstandOutput",
            parameter_id="H.meting",
            location_ids=[sel],
        )
        mpn_ids = df_locs_mpn.loc[
            df_locs_mpn["peilgebied_combi_attr"] == sel,
            "location_id"
        ].tolist()
        df_mpn = time_series_cache.get_time_series(
            filter_id="PeilgebiedWaterstandMeetpunt",
            parameter_id="H.meting",
            location_ids=mpn_ids,
        )

        print("[DEBUG build_combined_figure] df_vg shape:", df_vg.shape if hasattr(df_vg,"shape") else None)
        print("[DEBUG build_combined_figure] df_vul shape:", df_vul.shape if hasattr(df_vul,"shape") else None)
        print("[DEBUG build_combined_figure] df_pgb shape:", df_pgb.shape if hasattr(df_pgb,"shape") else None)
        print("[DEBUG build_combined_figure] df_mpn shape:", df_mpn.shape if hasattr(df_mpn,"shape") else None)
        print("[DEBUG build_combined_figure] mpn_ids:", mpn_ids)

        # haal eigenschappen van dit peilgebied (voor drempels)
        pgb_props = {}
        for feat in geojson_data["features"]:
            if feat["properties"].get("location_id") == sel:
                pgb_props = feat["properties"] or {}
                break

        print("[DEBUG build_combined_figure] pgb_props:", pgb_props)

        # ===== figure skeleton =====
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.06,
            subplot_titles=["Vullingsgraad [%]", "Vulling [mm]", "Waterstand [mNAP]"],
        )

        # -------------------------------------------------
        # 1. VULLINGSGRAAD [%] (row=1)
        # -------------------------------------------------
        x0_1 = df_vg.index.min()
        x1_1 = df_vg.index.max()
        print("[DEBUG build_combined_figure] vullingsgraad x0_1,x1_1:", x0_1, x1_1)

        # achtergrondbanden
        for low, high, color in VULLINGSGRAAD_CLASSES:
            fig.add_trace(
                go.Scatter(
                    x=[x0_1, x1_1, x1_1, x0_1],
                    y=[low, low, high, high],
                    mode="none",
                    fill="toself",
                    fillcolor=color.replace("1.0", "0.75"),
                    line=dict(width=0),
                    hoverinfo="skip",
                    showlegend=False,
                    name="band_vg",
                ),
                row=1, col=1,
            )

        # lijn vullingsgraad
        fig.add_trace(
            go.Scatter(
                x=df_vg.index.to_list(),
                y=df_vg[df_vg.columns[0]].to_list(),
                mode="lines",
                line=dict(color="#1e40af", width=3),
                hovertemplate=(
                    "tijd: %{x|%Y-%m-%d %H:%M}<br>"
                    "vullingsgraad: %{y:.1f}%<extra></extra>"
                ),
                showlegend=False,
                name="vullingsgraad_lijn",
            ),
            row=1, col=1,
        )

        # -------------------------------------------------
        # 2. VULLING [mm] (row=2)
        # -------------------------------------------------
        # fallback x0_2/x1_2 op df_vg als df_vul leeg is
        if df_vul is not None and not df_vul.empty:
            x0_2 = df_vul.index.min()
            x1_2 = df_vul.index.max()
        else:
            x0_2 = df_vg.index.min()
            x1_2 = df_vg.index.max()

        print("[DEBUG build_combined_figure] vulling x0_2,x1_2:", x0_2, x1_2)

        if df_vul is not None and not df_vul.empty:
            series_vul = df_vul[df_vul.columns[0]]
            max_vulling_val = series_vul.max()
        else:
            series_vul = pd.Series(dtype=float)
            max_vulling_val = float("nan")

        print("[DEBUG build_combined_figure] max_vulling_val:", max_vulling_val)

        has_vulling_data = pd.notna(max_vulling_val)

        # standaardbanden
        if x0_2 is not None and x1_2 is not None:
            for low, high, color in VULLING_MM_CLASSES:
                fig.add_trace(
                    go.Scatter(
                        x=[x0_2, x1_2, x1_2, x0_2],
                        y=[low, low, high, high],
                        mode="none",
                        fill="toself",
                        fillcolor=color.replace("1.0", "0.75"),
                        line=dict(width=0),
                        hoverinfo="skip",
                        showlegend=False,
                        name="band_vul",
                    ),
                    row=2, col=1,
                )

            if has_vulling_data:
                axis_top = max(60, math.ceil(float(max_vulling_val) / 10.0) * 10)
                print("[DEBUG build_combined_figure] axis_top:", axis_top)
                if axis_top > 60:
                    _, _, dark_blue = VULLING_MM_CLASSES[-1]
                    fig.add_trace(
                        go.Scatter(
                            x=[x0_2, x1_2, x1_2, x0_2],
                            y=[60, 60, axis_top, axis_top],
                            mode="none",
                            fill="toself",
                            fillcolor=dark_blue.replace("1.0", "0.75"),
                            line=dict(width=0),
                            hoverinfo="skip",
                            showlegend=False,
                            name="band_vul_hi",
                        ),
                        row=2, col=1,
                    )

        # blauwe lijn vulling
        fig.add_trace(
            go.Scatter(
                x=df_vul.index.to_list() if df_vul is not None and not df_vul.empty else [],
                y=df_vul[df_vul.columns[0]].to_list() if df_vul is not None and not df_vul.empty else [],
                mode="lines",
                line=dict(color="#1e40af", width=3),
                hovertemplate=(
                    "tijd: %{x|%Y-%m-%d %H:%M}<br>"
                    "vulling: %{y:.1f} mm<extra></extra>"
                ),
                showlegend=False,
                name="vulling_lijn",
            ),
            row=2, col=1,
        )

        # -------- horizontale drempels subplot 2 --------
        # kies tijdas
        if df_vul is not None and not df_vul.empty:
            x_vals_berg = df_vul.index.to_list()
            x_src = "df_vul"
        elif df_vg is not None and not df_vg.empty:
            x_vals_berg = df_vg.index.to_list()
            x_src = "df_vg"
        elif df_pgb is not None and not df_pgb.empty:
            x_vals_berg = df_pgb.index.to_list()
            x_src = "df_pgb"
        elif df_mpn is not None and not df_mpn.empty:
            x_vals_berg = df_mpn.index.to_list()
            x_src = "df_mpn"
        else:
            x_vals_berg = []
            x_src = "none"

        print("[DEBUG build_combined_figure] x_vals_berg source:", x_src,
              "len:", len(x_vals_berg))

        overlast_line_y = pgb_props.get("berging_bij_inundatiepeil")
        inundatiepeil_val = pgb_props.get("inundatiepeil")
        nulpeil_val = pgb_props.get("peil_bij_nul_berging")

        inundatiepeil_line_y = (inundatiepeil_val * 10) if inundatiepeil_val is not None else None
        nulpeil_line_y = (nulpeil_val * 10) if nulpeil_val is not None else None

        print("[DEBUG build_combined_figure] overlast_line_y:", overlast_line_y)
        print("[DEBUG build_combined_figure] inundatiepeil_line_y:", inundatiepeil_line_y)
        print("[DEBUG build_combined_figure] nulpeil_line_y:", nulpeil_line_y)

        def add_hline_with_label(x_vals, yval, kleur, tekst):
            if not x_vals:
                print(f"[DEBUG add_hline_with_label] {tekst}: geen x_vals -> skip")
                return
            if yval is None or pd.isna(yval):
                print(f"[DEBUG add_hline_with_label] {tekst}: yval None -> skip")
                return

            print(f"[DEBUG add_hline_with_label] ADD {tekst} y={yval} kleur={kleur}")
            print(f"[DEBUG add_hline_with_label] tijdsrange {x_vals[0]} -> {x_vals[-1]}")

            # lijn
            fig.add_trace(
                go.Scatter(
                    x=[x_vals[0], x_vals[-1]],
                    y=[yval, yval],
                    mode="lines",
                    line=dict(color=kleur, width=2, dash="dot"),
                    hoverinfo="skip",
                    showlegend=False,
                    name=f"{tekst}_hline",
                ),
                row=2, col=1,
            )
            # label
            fig.add_annotation(
                x=x_vals[0],
                y=yval,
                xref="x2",
                yref="y2",
                text=tekst,
                font=dict(color=kleur, size=12),
                showarrow=False,
                xanchor="left",
                yanchor="bottom",
                align="left",
                bgcolor="rgba(255,255,255,0.7)",
                borderpad=2,
            )

        add_hline_with_label(x_vals_berg, overlast_line_y,      "red",   "overlast")
        add_hline_with_label(x_vals_berg, inundatiepeil_line_y, "red",   "inundatiepeil")
        add_hline_with_label(x_vals_berg, nulpeil_line_y,       "green", "nulpeil")

        # -------------------------------------------------
        # 3. WATERSTAND [mNAP] (row=3)
        # -------------------------------------------------
        for location_id in df_mpn.columns.get_level_values("location_id"):
            naam = df_locs_mpn.loc[
                df_locs_mpn.location_id == location_id,
                "naam"
            ].iat[0]

            fig.add_trace(
                go.Scatter(
                    x=df_mpn.index,
                    y=df_mpn[location_id].iloc[:, 0].to_numpy(),
                    mode="lines",
                    line=dict(color="rgba(100,116,139,0.4)", width=2),
                    meta=location_id,
                    hovertemplate=(
                        "tijd: %{x|%Y-%m-%d %H:%M}<br>"
                        "waterstand: %{y:.3f} mNAP<br>"
                        f"naam: {naam}<br>"
                        "location_id: %{meta}<extra></extra>"
                    ),
                    showlegend=False,
                    name=f"mpn_{location_id}",
                ),
                row=3, col=1,
            )

        if not df_pgb.empty:
            fig.add_trace(
                go.Scatter(
                    x=df_pgb.index,
                    y=df_pgb.iloc[:, 0].to_numpy(),
                    mode="lines",
                    line=dict(color="#1e40af", width=3),
                    hovertemplate=(
                        "tijd: %{x|%Y-%m-%d %H:%M}<br>"
                        "peilgebied: %{y:.3f} mNAP<extra></extra>"
                    ),
                    showlegend=False,
                    name="peilgebied",
                ),
                row=3, col=1,
            )

        streefpeil = pgb_props.get("streefpeil")
        print("[DEBUG build_combined_figure] streefpeil:", streefpeil)
        if streefpeil is not None and pd.notnull(streefpeil):
            if not df_pgb.empty:
                x_vals_ws = list(df_pgb.index)
            else:
                x_vals_ws = sorted(list(df_mpn.index.unique()))

            if x_vals_ws:
                y_val = streefpeil
                fig.add_trace(
                    go.Scatter(
                        x=x_vals_ws,
                        y=[y_val] * len(x_vals_ws),
                        mode="lines",
                        line=dict(dash="dash", color="#facc15", width=2),
                        name="Streefpeil",
                        hoverinfo="text",
                        hovertext=[f"Streefpeil: {y_val:.2f} mNAP"] * len(x_vals_ws),
                        showlegend=False,
                    ),
                    row=3, col=1,
                )

                fig.add_annotation(
                    x=x_vals_ws[0],
                    y=y_val,
                    xref="x3",
                    yref="y3",
                    text="streefpeil",
                    font=dict(color="#facc15", size=13),
                    showarrow=False,
                    xanchor="left",
                    yanchor="bottom",
                    align="left",
                    bgcolor="rgba(255,255,255,0.7)",
                    borderpad=2,
                )

        # -------------------------------------------------
        # ASSEN + GRID
        # -------------------------------------------------

        # y-as vullingsgraad (vaste ticks)
        fig.update_yaxes(
            range=[0, 100],
            tickformat=".0f",
            fixedrange=True,
            tickmode="array",
            tickvals=[25, 50, 75, 100],
            ticktext=["25", "50", "75", "100"],
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            gridwidth=1,
            zeroline=False,
            row=1,
            col=1,
        )

        # y-as vulling (autoschaal)
        fig.update_yaxes(
            fixedrange=False,
            tickformat=".0f",
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            gridwidth=1,
            zeroline=False,
            row=2,
            col=1,
        )

        # y-as waterstand (autoschaal)
        fig.update_yaxes(
            fixedrange=False,
            tickformat=".2f",
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            gridwidth=1,
            zeroline=False,
            row=3,
            col=1,
            automargin=False,
        )

        # x-assen
        fig.update_xaxes(
            title_text="Tijd",
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            gridwidth=1,
            zeroline=False,
            row=3,
            col=1,
        )

        x_min = df_vg.index.min()
        x_max = df_vg.index.max()
        print("[DEBUG build_combined_figure] x-range final:", x_min, x_max)
        for r in [1, 2, 3]:
            fig.update_xaxes(
                range=[x_min, x_max],
                automargin=False,
                showgrid=True,
                gridcolor="rgba(0,0,0,0.08)",
                gridwidth=1,
                zeroline=False,
                row=r,
                col=1,
            )

        # layout algemeen
        fig.update_layout(
            uirevision=sel,
            margin=dict(l=40, r=10, t=60, b=40),
            plot_bgcolor="white",
            hovermode="closest",
            font=dict(size=13),
            showlegend=False,
        )

        # lege highlight-trace voor geselecteerde mpn
        fig.add_trace(
            go.Scatter(
                x=[],
                y=[],
                mode="lines",
                line=dict(color="rgba(251,191,36,1)", width=4),
                hoverinfo="skip",
                name="__highlight__",
                showlegend=False,
            ),
            row=3, col=1,
        )

        # cache proberen te vullen
        try:
            if hasattr(cache, "cache") and cache.cache is not None:
                cache.set(ckey, fig.to_dict())
        except Exception as e:
            print(f"[CACHE WARN] cache.set('{ckey}'): {e}")
        print(f"[CACHE MISS] built fig for {sel}")
    else:
        print(f"[CACHE HIT] reuse fig for {sel}")

    return fig.to_dict()


# ===== finale figuur (cursor + highlight) =====
@app.callback(
    Output("combined-graph", "figure"),
    [
        Input("combined-fig-store", "data"),
        Input("tijdslider", "value"),
        Input("marker-mpn", "clickData"),
        Input("clicked-trace-store", "data"),
    ],
)
def add_vline_and_highlight(fig_dict, idx, selected_mpn, selected_trace_id):
    if fig_dict is None or idx is None:
        raise PreventUpdate

    fig = go.Figure(fig_dict)

    current_dt = all_datetimes[int(idx)]

    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
    if trigger_id == "clicked-trace-store":
        sel_id = selected_trace_id
    elif trigger_id == "marker-mpn":
        sel_id = (
            selected_mpn
            and selected_mpn.get("properties", {})
            and selected_mpn["properties"].get("location_id")
        )
    else:
        sel_id = (
            selected_trace_id
            or (
                selected_mpn
                and selected_mpn.get("properties", {})
                and selected_mpn["properties"].get("location_id")
            )
        )

    print("[DEBUG add_vline_and_highlight] trigger_id:", trigger_id)
    print("[DEBUG add_vline_and_highlight] sel_id:", sel_id)
    print("[DEBUG add_vline_and_highlight] idx/time:", idx, current_dt)

    # dim alle mpn-traces, highlight de gekozen
    x_sel, y_sel = [], []
    selected_trace_idx = None

    for i_tr, tr in enumerate(fig.data):
        meta_val = getattr(tr, "meta", None)
        if meta_val:
            # dim standaard
            tr.line.color = "rgba(100,116,139,0.25)"
            tr.line.width = 2
            tr.opacity = 1.0

            if sel_id and meta_val == sel_id:
                print("[DEBUG add_vline_and_highlight] highlight trace index", i_tr, "meta", meta_val)
                tr.line.color = "rgba(251,191,36,1)"
                tr.line.width = 4
                tr.opacity = 1.0
                selected_trace_idx = i_tr
                x_sel = list(tr.x)
                y_sel = list(tr.y)

    # gekozen mpn-trace bovenop
    if selected_trace_idx is not None:
        data_list = list(fig.data)
        sel_trace = data_list.pop(selected_trace_idx)
        data_list.append(sel_trace)
        fig.data = tuple(data_list)

    # highlight overlay-trace vullen en bovenop leggen
    hl_idx = None
    for i in range(len(fig.data) - 1, -1, -1):
        if getattr(fig.data[i], "name", None) == "__highlight__":
            hl_idx = i
            break

    print("[DEBUG add_vline_and_highlight] hl_idx:", hl_idx)

    if hl_idx is not None:
        fig.data[hl_idx].x = x_sel
        fig.data[hl_idx].y = y_sel

        data_list = list(fig.data)
        hl_trace = data_list.pop(hl_idx)
        data_list.append(hl_trace)
        fig.data = tuple(data_list)

    # cursor shapes
    cursor_shapes = []
    core_col = "rgba(180,190,210,1.0)"   # dunne kernlijn
    halo_col = "rgba(180,190,210,0.12)"  # brede halo

    # Halo
    for xref in ["x1", "x2", "x3"]:
        cursor_shapes.append(
            go.layout.Shape(
                type="line",
                x0=current_dt,
                x1=current_dt,
                y0=0,
                y1=1,
                xref=xref,
                yref="paper",
                line=dict(
                    color=halo_col,
                    width=6,
                ),
                layer="above",
            )
        )

    # Kern
    for xref in ["x1", "x2", "x3"]:
        cursor_shapes.append(
            go.layout.Shape(
                type="line",
                x0=current_dt,
                x1=current_dt,
                y0=0,
                y1=1,
                xref=xref,
                yref="paper",
                line=dict(
                    color=core_col,
                    width=2,
                ),
                layer="above",
            )
        )

    fig.layout.shapes = tuple(cursor_shapes)

    return fig


@app.callback(
    Output("mini-tijdserie", "figure"),
    [
        Input("pgb-dropdown", "value"),
        Input("kaartvariabele-dropdown", "value"),
        Input("tijdslider", "value"),
    ],
)
def update_mini_graph(sel, var, idx):
    print("[DEBUG update_mini_graph] sel, var, idx:", sel, var, idx)
    if not sel:
        raise PreventUpdate

    parameter_id = "vullingsgraad" if var == "vullingsgraad" else "vulling_mm"

    try:
        df = time_series_cache.get_time_series(
            filter_id="VullingsgraadOutput",
            parameter_id=parameter_id,
            location_ids=[sel],
        )
    except Exception as e:
        print("[DEBUG update_mini_graph] error get_time_series:", e)
        df = pd.DataFrame()

    if df is not None and not df.empty:
        series = df.iloc[:, 0]
        vals = [series.get(ts, None) for ts in all_datetimes]
    else:
        vals = [None] * len(all_datetimes)

    idx0 = int(idx) if idx is not None else 0
    print("[DEBUG update_mini_graph] idx0:", idx0, "vals_sample:", vals[idx0:idx0+3])

    mini = go.Figure(
        go.Scatter(
            x=list(range(len(all_datetimes))),
            y=vals,
            mode="lines",
            line=dict(width=2),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    mini.add_vline(x=idx0, line_width=2, line_dash="dash", line_color="#bbbbbb")
    mini.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=50,
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False, range=[0, len(all_datetimes) - 1], fixedrange=True),
        yaxis=dict(visible=False, fixedrange=True),
    )
    return mini


@app.callback(
    Output("playpause-button", "children"),
    Input("is-playing", "data"),
)
def set_playpause(is_playing):
    return "⏸️ Pause" if is_playing else "▶️ Play"


@app.callback(
    Output("is-playing", "data"),
    Input("playpause-button", "n_clicks"),
    State("is-playing", "data"),
    prevent_initial_call=True,
)
def toggle_playpause(n, playing):
    print("[DEBUG toggle_playpause] clicked n:", n, "was playing:", playing)
    return not playing if n else playing


@app.callback(
    Output("interval", "disabled"),
    Input("is-playing", "data"),
)
def toggle_interval(playing):
    print("[DEBUG toggle_interval] playing:", playing)
    return not playing


@app.callback(
    Output("clicked-trace-store", "data"),
    Input("combined-graph", "clickData"),
    State("combined-graph", "figure"),
    prevent_initial_call=True,
)
def remember_clicked_trace(graph_click, current_fig_dict):
    print("[DEBUG remember_clicked_trace] graph_click:", graph_click)
    if (
        graph_click is None
        or current_fig_dict is None
        or "points" not in graph_click
        or not graph_click["points"]
        or "curveNumber" not in graph_click["points"][0]
    ):
        raise PreventUpdate

    fig = go.Figure(current_fig_dict)
    point = graph_click["points"][0]
    trace = fig.data[point["curveNumber"]]
    sel_id = getattr(trace, "meta", None)
    print("[DEBUG remember_clicked_trace] selected meta:", sel_id)
    if sel_id is None:
        raise PreventUpdate
    return sel_id


@app.callback(
    Output("tijdslider", "value"),
    [
        Input("interval", "n_intervals"),
        Input("combined-graph", "relayoutData"),
    ],
    [
        State("interval", "disabled"),
        State("tijdslider", "value"),
    ],
)
def update_slider_from_interval_or_drag(n_intervals, relayoutData, disabled, current_idx):
    ctx = dash.callback_context
    print("[DEBUG update_slider] trigger:", ctx.triggered)
    print("[DEBUG update_slider] relayoutData:", relayoutData)
    print("[DEBUG update_slider] disabled:", disabled, "current_idx:", current_idx)

    if not ctx.triggered:
        raise PreventUpdate

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # autoplay vooruit
    if trigger_id == "interval":
        if disabled or current_idx is None:
            raise PreventUpdate
        new_idx = (int(current_idx) + 1) % len(all_datetimes)
        print("[DEBUG update_slider] autoplay ->", new_idx)
        return new_idx

    # cursor-drag
    if trigger_id == "combined-graph":
        if not relayoutData:
            raise PreventUpdate

        new_x_val = None
        for k, v in relayoutData.items():
            if k.startswith("shapes[") and (k.endswith("].x0") or k.endswith("].x1")):
                new_x_val = v
                break

        print("[DEBUG update_slider] drag new_x_val:", new_x_val)

        if new_x_val is None:
            raise PreventUpdate

        try:
            ts = pd.to_datetime(new_x_val)
        except Exception as e:
            print("[DEBUG update_slider] cannot parse ts:", e)
            raise PreventUpdate

        pos = bisect.bisect_left(all_datetimes, ts)

        if pos <= 0:
            nearest = 0
        elif pos >= len(all_datetimes):
            nearest = len(all_datetimes) - 1
        else:
            before = all_datetimes[pos - 1]
            after = all_datetimes[pos]
            nearest = pos if (after - ts) <= (ts - before) else (pos - 1)

        print("[DEBUG update_slider] nearest index:", nearest)

        if current_idx is not None and int(current_idx) == nearest:
            raise PreventUpdate

        return nearest

    raise PreventUpdate


@app.callback(
    Output("marker-mpn", "hideout"),
    [
        Input("pgb-dropdown", "value"),
        Input("kaartvariabele-dropdown", "value"),
    ],
)
def update_mpn_markers(selected_location_id, _var):
    print("[DEBUG update_mpn_markers] selected_location_id:", selected_location_id)
    if not selected_location_id:
        return []

    if "peilgebied_combi_attr" not in df_locs_mpn.columns:
        print("[DEBUG update_mpn_markers] kolom peilgebied_combi_attr ontbreekt")
        return []

    mask = df_locs_mpn["peilgebied_combi_attr"].astype(str) == str(selected_location_id)
    points = df_locs_mpn[mask]
    print("[DEBUG update_mpn_markers] aantal punten:", len(points))
    if points.empty:
        return []
    hideout_list = (
        points["peilgebied_combi_attr"]
        .astype(str)
        .dropna()
        .unique()
        .tolist()
    )
    print("[DEBUG update_mpn_markers] hideout_list:", hideout_list)
    return hideout_list


if __name__ == "__main__":
    app.title = "Vullingsgraad"
    app.run(port=5005, debug=True)
