# %%
"""
HydroDashboard – Vullingsgraad Viewer
-------------------------------------
"""
# ========= Imports =========
import bisect
import json
import math
import time
from functools import lru_cache, wraps
from pathlib import Path

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


# ========= Settings =========
IMPORTANT_LOG = True
def log(*args, **kwargs):
    """Kleine helper om gerichte debugregels te printen."""
    if IMPORTANT_LOG:
        print(*args, **kwargs)


# ========= Paden / App init =========
app_dir = Path(__file__).parent
data_dir = app_dir.parent / "data"
assets_dir = app_dir / "assets"

app = dash.Dash(__name__, assets_folder=str(assets_dir))

cache = Cache(app.server, config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 3600})


def timed_callback(f):
    """Decorator om runtime van callbacks te meten (nu stil; laat staan voor profileren)."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        result = f(*args, **kwargs)
        _ = time.perf_counter() - t0
        return result
    return wrapper


def bounds_to_map(xmin, ymin, xmax, ymax):
    """Ruime bbox + center afgeleid van shapefile-extent."""
    dx, dy = xmax - xmin, ymax - ymin
    return [[ymin, xmin], [ymax + dy, xmin - 4 * dx]], [ymin + dy / 2, xmax - dx / 2]


# ========= Data laden =========
geojson_data, location_options, bounds = read_peilgebieden(
    file_path=(data_dir / "peilgebieden_cso_combi.shp").as_posix(),
    code_col="CODE",
    columns=["naam", "streefpeil", "inundatiepeil", "berging_bij_inundatiepeil", "peil_bij_nul_berging"],
    style={"fillColor": "gray", "color": "#666", "weight": 0.3, "fillOpacity": 1},
)
map_bounds, map_center = bounds_to_map(*bounds)

df_locs_mpn = read_mpn_locs(data_dir / "mpn_locations.arrow")

time_series_cache = TimeSeriesCache.from_manifest_file(data_dir / "time_series" / "manifest.json")
all_datetimes = [pd.Timestamp(ts) for ts in time_series_cache.common_time_axis]

kaartvariabelen = [
    {"label": "vullingsgraad [%]", "value": "vullingsgraad"},
    {"label": "vulling [mm]", "value": "vulling"},
]


# ========= Kleuren =========
VULLINGSGRAAD_CLASSES = [
    (0, 25, "rgba(120,200,120,1.0)"),
    (25, 50, "rgba(255,255,100,1.0)"),
    (50, 75, "rgba(255,200,100,1.0)"),
    (75, 100, "rgba(255,100,100,1.0)"),
]
VULLING_MM_CLASSES = [
    (0, 10, "rgba(255,255,255,1.0)"),
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


def kleur_bij_vullingsgraad(val): return _pick_color(val, VULLINGSGRAAD_CLASSES)
def kleur_bij_vulling(val):       return _pick_color(val, VULLING_MM_CLASSES)


# ========= Polygon style (clientside) =========
style_handle = assign(
    """
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
    base = {...base, weight: 2, color: "rgba(251,191,36,0.95)", fillOpacity: 0.85};
  }
  return base;
}
"""
)

# ========= Default state =========
default_index = len(all_datetimes) - 1
default_dt = all_datetimes[default_index]
default_pgb = location_options[0]["value"] if location_options else None
initial_label = default_dt.strftime("%Y-%m-%d %H:%M")
initial_kaartvariabele = "vullingsgraad"

if default_pgb is not None and "peilgebied_combi_attr" in df_locs_mpn.columns:
    dd_locs_mpn_default = (
        df_locs_mpn.loc[df_locs_mpn["peilgebied_combi_attr"].astype(str) == str(default_pgb), "peilgebied_combi_attr"]
        .astype(str).dropna().unique().tolist()
    )
else:
    dd_locs_mpn_default = []


@lru_cache(maxsize=128)
def get_kaartdata_for_datetime(dt, kaartvariabele):
    """
    Maak voor één tijdstap een stylemap per peilgebied:
    { location_id: {fillColor, color, weight, fillOpacity, <waarde> } }
    """
    dt = pd.to_datetime(dt).to_pydatetime()
    if kaartvariabele == "vullingsgraad":
        df = time_series_cache.get_time_series("VullingsgraadOutput", "vullingsgraad", start_time=dt, end_time=dt)
        kleur_fn = kleur_bij_vullingsgraad
    else:
        df = time_series_cache.get_time_series("VullingsgraadOutput", "vulling_mm", start_time=dt, end_time=dt)
        kleur_fn = kleur_bij_vulling

    df = df.loc[dt].reset_index()
    ids, vals = df["location_id"].to_list(), df[dt].to_list()

    return {
        loc: {"fillColor": kleur_fn(val), "color": "#666", "weight": 0.3, "fillOpacity": 1, kaartvariabele: val}
        for loc, val in zip(ids, vals)
    }


initial_stylemap = get_kaartdata_for_datetime(default_dt, initial_kaartvariabele)
initial_options = {"style": style_handle, "selected": default_pgb, "interactive": True, "bubblingMouseEvents": True}

EMPTY_FIG = go.Figure()
EMPTY_FIG.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(visible=False), yaxis=dict(visible=False), showlegend=False
)


# ========= Layout styles =========
page_wrapper_style = {"display": "flex", "flexDirection": "row", "height": "100vh", "width": "100vw", "overflow": "hidden"}
left_col_style = {"position": "relative", "flex": "1 1 50%", "minWidth": 0, "minHeight": 0, "overflow": "hidden", "height": "100vh"}
right_col_style = {
    "display": "flex", "flexDirection": "column", "flex": "1 1 50%",
    "height": "100vh", "minWidth": 0, "minHeight": 0, "padding": "0px",
    "boxShadow": "0 2px 8px rgba(0,0,0,0.05)", "borderRadius": "5px", "backgroundColor": "rgba(255,255,255,0.0)",
    "overflow": "hidden",
}


# ========= App layout =========
app.layout = html.Div(
    style=page_wrapper_style,
    children=[
        # --------- Linker kolom: kaart + controls ---------
        html.Div(
            style=left_col_style,
            children=[
                dl.Map(
                    center=map_center, zoom=10, bounds=map_bounds,
                    style={"height": "100%", "width": "100%"}, preferCanvas=False,
                    children=[
                        # Top-pane voor meetpunten 
                        dl.Pane(id="pane-top", name="veryTopPane", style={"zIndex": 650}),
                        dl.TileLayer(),

                        # Peilgebieden
                        dl.GeoJSON(
                            id="geojson-pgb",
                            data=geojson_data,
                            hideout=initial_stylemap,
                            options={**initial_options, "pane": "overlayPane"},
                            eventHandlers={"click": assign("function(e){return e?.target?.feature?.properties||{};}")},
                        ),

                        # Meetpunten (circleMarkers) 
                        dl.GeoJSON(
                            id="marker-mpn",
                            data=json.loads(df_locs_mpn.to_json()),
                            filter=assign(
                                """
                                function(feature, context){
                                  const ho = context.hideout || [];
                                  const allowed = Array.isArray(ho) ? ho : (ho.allowed || []);
                                  const okGeom = feature && feature.geometry && feature.geometry.type === "Point"
                                    && Array.isArray(feature.geometry.coordinates)
                                    && feature.geometry.coordinates.length === 2
                                    && isFinite(feature.geometry.coordinates[0])
                                    && isFinite(feature.geometry.coordinates[1]);
                                  if (!okGeom) return false;
                                  const attr = String(feature.properties?.peilgebied_combi_attr);
                                  return Array.isArray(allowed) && allowed.includes(attr);
                                }
                                """
                            ),
                            hideout=dd_locs_mpn_default,  
                            options={
                                "pane": "veryTopPane",
                                "style": assign(
                                    """
                                    function(feature, context){
                                      const ho = context.hideout || {};
                                      const sel = ho.sel || null;
                                      const locId = feature?.properties?.location_id || feature?.properties?.id || null;

                                      let st = { radius: 5, fillColor: '#4cc9f0', color: '#1b4d5e',
                                                 weight: 1.5, opacity: 1, fillOpacity: 0.9 };

                                      if (sel && locId && String(sel) === String(locId)) {
                                        st = {...st, radius: 7, fillColor: '#fde68a', color: '#d97706', weight: 2};
                                      }
                                      return st;
                                    }
                                    """
                                ),
                                "onEachFeature": assign("function(f, layer){ if(layer?.bringToFront){ layer.bringToFront(); } }"),
                                "pointToLayer": assign(
                                    """
                                    function(feature, latlng){
                                      const naam = feature?.properties?.naam || "meetpunt";
                                      const locId = feature?.properties?.location_id || feature?.properties?.id || "(onbekend id)";
                                      const marker = L.circleMarker(latlng, { pane: 'veryTopPane' });
                                      marker.bindTooltip("<b>"+naam+"</b><br/>"+locId, { permanent:false, direction:'top', opacity:0.95 });
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
                                      return { properties: props, lat: ll?.lat, lng: ll?.lng };
                                    }
                                    """
                                )
                            },
                        ),

                        # Extra highlight (bijv. gouden cirkel)
                        dl.LayerGroup(id="mpn-click-layer", pane="veryTopPane"),
                    ],
                ),

                # Controls (links boven)
                html.Div(
                    [
                        html.Label(["kaartvariabele: ",
                                    html.Span("?", title="Variabele voor kaartkleuren", style={"cursor": "help"})],
                                   style={"fontSize": "13px"}),
                        dcc.Dropdown(id="kaartvariabele-dropdown", options=kaartvariabelen,
                                     value=initial_kaartvariabele, clearable=False,
                                     style={"width": "240px", "marginBottom": "8px"}),

                        html.Label(["peilgebied: ",
                                    html.Span("?", title="Peilgebied voor grafieken", style={"cursor": "help"})],
                                   style={"fontSize": "13px"}),
                        dcc.Dropdown(id="pgb-dropdown", options=location_options, value=default_pgb,
                                     placeholder="Selecteer peilgebied", clearable=True, style={"width": "240px"}),
                    ],
                    style={
                        "position": "absolute", "top": "10px", "left": "10px", "zIndex": 1002,
                        "background": "rgba(220,240,255,1)", "borderRadius": "8px",
                        "padding": "10px", "boxShadow": "0 2px 8px rgba(0,0,0,0.15)",
                    },
                ),

                # Tijdslider + mini-grafiek (onder)
                html.Div(
                    [
                        html.Button(id="playpause-button", n_clicks=0, style={"width": "72px"}),
                        dcc.Store(id="is-playing", data=False),
                        html.Div(initial_label, id="datum-label", style={"fontWeight": "bold"}),
                        html.Div(
                            [
                                dcc.Graph(id="mini-tijdserie", config={"displayModeBar": False},
                                          style={"height": "50px", "width": "350px", "position": "absolute",
                                                 "top": 0, "left": "25px", "pointerEvents": "none"}),
                                dcc.Slider(id="tijdslider", min=0, max=len(all_datetimes) - 1,
                                           value=default_index, marks=None, updatemode="mouseup"),
                            ],
                            style={"position": "relative", "width": "400px", "height": "50px", "display": "inline-block"},
                        ),
                    ],
                    style={
                        "position": "absolute", "bottom": "10px", "left": "10px",
                        "background": "rgba(255,255,255,0.9)", "padding": "8px",
                        "borderRadius": "6px", "zIndex": 1000, "display": "flex",
                        "gap": "10px", "alignItems": "center", "boxShadow": "0 2px 8px rgba(0,0,0,0.15)",
                    },
                ),

                dcc.Interval(id="interval", interval=1000, disabled=True),

                # Semi-transparante overlay bij laden
                html.Div(
                    id="page-loader",
                    children=html.Div(
                        className="loader-inner",
                        children=[html.Div(className="spinner-ring"), html.Div("kaart en data loading", className="loader-text")],
                    ),
                    style={
                        "position": "absolute", "top": 0, "left": 0, "right": 0, "bottom": 0,
                        "backgroundColor": "rgba(255,255,255,0.6)", "backdropFilter": "blur(2px)",
                        "zIndex": 2000, "display": "flex", "alignItems": "center", "justifyContent": "center",
                        "flexDirection": "column", "fontSize": "14px", "fontWeight": "500", "color": "#0f172a",
                    },
                ),

                dcc.Store(id="clicked-mpn-store", data=None),
                dcc.Store(id="clicked-trace-store", data=None),
            ],
        ),

        # --------- Rechter kolom: grafiek ---------
        html.Div(
            style=right_col_style,
            children=[
                dcc.Store(id="combined-fig-store"),
                dcc.Graph(
                    id="combined-graph", figure=EMPTY_FIG,
                    config={"displayModeBar": True, "scrollZoom": True, "displaylogo": False,
                            "modeBarButtonsToRemove": ["toImage"], "edits": {"shapePosition": True}, "responsive": True},
                    style={"flex": "1 1 auto", "minHeight": 0, "minWidth": 0, "margin": "10px",
                           "height": "96vh", "width": "48vw", "overflow": "hidden"},
                ),
            ],
        ),
    ],
)


# ========= Callbacks =========
@app.callback(
    Output("page-loader", "style"),
    [Input("combined-fig-store", "data"), Input("geojson-pgb", "hideout")],
    prevent_initial_call=True,
)
def hide_page_loader(fig_dict, stylemap):
    """Verberg loader zodra figuur en kaart-styles binnen zijn."""
    if not fig_dict or not stylemap:
        raise PreventUpdate
    return {"display": "none"}


@app.callback(Output("clicked-mpn-store", "data"), Input("marker-mpn", "clickData"), prevent_initial_call=True)
def store_clicked_mpn(cd):
    """Onthoud laatst aangeklikte meetpunt (voor sync met grafiek/highlight)."""
    return cd


@app.callback(
    Output("mpn-click-layer", "children"),
    [Input("clicked-mpn-store", "data"), Input("clicked-trace-store", "data"), Input("pgb-dropdown", "value")],
)
def highlight_selected_point(mpn_clickdata, clicked_trace_id, selected_pgb):
    """Plaats een gouden marker op het geselecteerde meetpunt (bron: kaart of grafiek)."""
    from dash import callback_context as ctx

    # Nieuwe peilgebiedselectie -> reset highlight
    if ctx.triggered and ctx.triggered[0]["prop_id"].startswith("pgb-dropdown"):
        log(f"[HIGHLIGHT RESET] nieuw peilgebied: {selected_pgb}")
        return []

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
    sel_id = naam = None
    lat = lng = None

    if trigger_id == "clicked-trace-store":
        sel_id = clicked_trace_id
        log(f"[HIGHLIGHT SOURCE] grafiek-click -> {sel_id}")
    elif trigger_id == "clicked-mpn-store":
        if not mpn_clickdata:
            raise PreventUpdate
        props = mpn_clickdata.get("properties", {}) or {}
        sel_id = props.get("location_id") or props.get("id")
        naam = props.get("naam") or "meetpunt"
        lat, lng = mpn_clickdata.get("lat"), mpn_clickdata.get("lng")
        log(f"[HIGHLIGHT SOURCE] kaart-click -> {sel_id}")
    else:
        # Fallback bij redraw
        if clicked_trace_id:
            sel_id = clicked_trace_id
        elif mpn_clickdata:
            props = mpn_clickdata.get("properties", {}) or {}
            sel_id = props.get("location_id") or props.get("id")
            naam = props.get("naam") or "meetpunt"
            lat, lng = mpn_clickdata.get("lat"), mpn_clickdata.get("lng")
        if sel_id:
            log(f"[HIGHLIGHT RESTORE] {sel_id}")

    if not sel_id:
        return []

    # Bepaal lat/lng indien niet vanuit clickData
    if lat is None or lng is None:
        row = df_locs_mpn.loc[df_locs_mpn["location_id"] == sel_id]
        if row.empty:
            return []
        if {"lat", "lng"}.issubset(row.columns):
            lat, lng = row["lat"].iloc[0], row["lng"].iloc[0]
        elif {"lat", "lon"}.issubset(row.columns):
            lat, lng = row["lat"].iloc[0], row["lon"].iloc[0]
        elif "geometry" in row.columns:
            geom = row["geometry"].iloc[0]
            lat, lng = geom.y, geom.x
        else:
            return []
        if naam is None and "naam" in row.columns:
            naam = row["naam"].iloc[0]

    # Gouden cirkel
    marker = dl.CircleMarker(center=[lat, lng], radius=7, color="#b28900", weight=2, fillColor="#ffe680", fillOpacity=0.9)
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
    """Update polygon-kleuren, geselecteerd peilgebied en het datumlabel."""
    if idx is None or not sel or not var:
        raise PreventUpdate

    dt = all_datetimes[int(idx)]
    stylemap = get_kaartdata_for_datetime(dt, var)
    label = dt.strftime("%Y-%m-%d %H:%M")
    options = {"style": style_handle, "selected": sel, "interactive": True, "bubblingMouseEvents": True}
    return stylemap, label, options


@app.callback(Output("pgb-dropdown", "value"), Input("geojson-pgb", "clickData"), prevent_initial_call=True)
def select_dropdown_on_click(clickData):
    """Klik op polygon => zet location_id in de dropdown."""
    loc = clickData["properties"]["location_id"]
    log(f"[SELECT PGB] peilgebied: {loc}")
    return loc


# --------- Figuur bouwen (zonder cursor/highlight) ---------
@app.callback(Output("combined-fig-store", "data"), [Input("pgb-dropdown", "value"), Input("kaartvariabele-dropdown", "value")])
@timed_callback
def build_combined_figure(sel, _var):
    """
    Bouw basisonderdelen van de 3-subplot figuur:
    1) vullingsgraad [%] + banden
    2) vulling [mm] + drempels
    3) waterstand (peilgebied + mpn) + streefpeil
    """
    if not sel:
        raise PreventUpdate

    ckey = f"combined_v3_{sel}"

    # Probeer cache
    try:
        cached = cache.get(ckey) if getattr(cache, "cache", None) is not None else None
        if cached is not None:
            log(f"[FIG] cache hit {sel}")
            return go.Figure(cached).to_dict()
    except Exception:
        pass

    # Data ophalen
    log(f"[FIG] build {sel}")
    df_vg = time_series_cache.get_time_series("VullingsgraadOutput", "vullingsgraad", location_ids=[sel])
    df_vul = time_series_cache.get_time_series("VullingsgraadOutput", "vulling_mm", location_ids=[sel])
    df_pgb = time_series_cache.get_time_series("PeilgebiedWaterstandOutput", "H.meting", location_ids=[sel])

    mpn_ids = df_locs_mpn.loc[df_locs_mpn["peilgebied_combi_attr"] == sel, "location_id"].tolist()
    df_mpn = time_series_cache.get_time_series("PeilgebiedWaterstandMeetpunt", "H.meting", location_ids=mpn_ids)

    pgb_props = next((f["properties"] for f in geojson_data["features"] if f["properties"].get("location_id") == sel), {})

    # Figuurskelet
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        subplot_titles=["Vullingsgraad [%]", "Vulling [mm]", "Waterstand [mNAP]"])

    # 1) Vullingsgraad
    x0_1, x1_1 = df_vg.index.min(), df_vg.index.max()
    for low, high, color in VULLINGSGRAAD_CLASSES:
        fig.add_trace(
            go.Scatter(x=[x0_1, x1_1, x1_1, x0_1], y=[low, low, high, high],
                       mode="none", fill="toself", fillcolor=color.replace("1.0", "0.75"),
                       line=dict(width=0), hoverinfo="skip", showlegend=False, name="band_vg"),
            row=1, col=1,
        )
    fig.add_trace(
        go.Scatter(
            x=df_vg.index.to_list(), y=df_vg[df_vg.columns[0]].to_list(),
            mode="lines", line=dict(color="#1e40af", width=3),
            hovertemplate="tijd: %{x|%Y-%m-%d %H:%M}<br>vullingsgraad: %{y:.1f}%<extra></extra>",
            showlegend=False, name="vullingsgraad_lijn",
        ),
        row=1, col=1,
    )

    # 2) Vulling
    if df_vul is not None and not df_vul.empty:
        x0_2, x1_2 = df_vul.index.min(), df_vul.index.max()
        series_vul = df_vul[df_vul.columns[0]]
        max_vulling_val = series_vul.max()
    else:
        x0_2, x1_2 = df_vg.index.min(), df_vg.index.max()
        series_vul = pd.Series(dtype=float)
        max_vulling_val = float("nan")
    has_vulling_data = pd.notna(max_vulling_val)

    if x0_2 is not None and x1_2 is not None:
        for low, high, color in VULLING_MM_CLASSES:
            fig.add_trace(
                go.Scatter(x=[x0_2, x1_2, x1_2, x0_2], y=[low, low, high, high],
                           mode="none", fill="toself", fillcolor=color.replace("1.0", "0.75"),
                           line=dict(width=0), hoverinfo="skip", showlegend=False, name="band_vul"),
                row=2, col=1,
            )
        if has_vulling_data:
            axis_top = max(60, math.ceil(float(max_vulling_val) / 10.0) * 10)
            if axis_top > 60:
                _, _, dark_blue = VULLING_MM_CLASSES[-1]
                fig.add_trace(
                    go.Scatter(x=[x0_2, x1_2, x1_2, x0_2], y=[60, 60, axis_top, axis_top],
                               mode="none", fill="toself", fillcolor=dark_blue.replace("1.0", "0.75"),
                               line=dict(width=0), hoverinfo="skip", showlegend=False, name="band_vul_hi"),
                    row=2, col=1,
                )

    fig.add_trace(
        go.Scatter(
            x=(df_vul.index.to_list() if df_vul is not None and not df_vul.empty else []),
            y=(df_vul[df_vul.columns[0]].to_list() if df_vul is not None and not df_vul.empty else []),
            mode="lines", line=dict(color="#1e40af", width=3),
            hovertemplate="tijd: %{x|%Y-%m-%d %H:%M}<br>vulling: %{y:.1f} mm<extra></extra>",
            showlegend=False, name="vulling_lijn",
        ),
        row=2, col=1,
    )

    # Drempels op subplot 2
    if df_vul is not None and not df_vul.empty:
        x_vals_berg = df_vul.index.to_list()
    elif df_vg is not None and not df_vg.empty:
        x_vals_berg = df_vg.index.to_list()
    elif df_pgb is not None and not df_pgb.empty:
        x_vals_berg = df_pgb.index.to_list()
    else:
        x_vals_berg = []

    def add_hline_with_label(x_vals, yval, kleur, tekst):
        if not x_vals or yval is None or pd.isna(yval):
            return
        fig.add_trace(
            go.Scatter(x=[x_vals[0], x_vals[-1]], y=[yval, yval], mode="lines",
                       line=dict(color=kleur, width=2, dash="dot"),
                       hoverinfo="skip", showlegend=False, name=f"{tekst}_hline"),
            row=2, col=1,
        )
        fig.add_annotation(
            x=x_vals[0], y=yval, xref="x2", yref="y2", text=tekst,
            font=dict(color=kleur, size=12), showarrow=False, xanchor="left", yanchor="bottom",
            align="left", bgcolor="rgba(255,255,255,0.7)", borderpad=2,
        )

    overlast_line_y = pgb_props.get("berging_bij_inundatiepeil")
    inundatiepeil_val = pgb_props.get("inundatiepeil")
    nulpeil_val = pgb_props.get("peil_bij_nul_berging")
    inundatiepeil_line_y = (inundatiepeil_val * 10 if inundatiepeil_val is not None else None)
    nulpeil_line_y = (nulpeil_val * 10 if nulpeil_val is not None else None)
    add_hline_with_label(x_vals_berg, overlast_line_y, "red", "overlast")
    add_hline_with_label(x_vals_berg, inundatiepeil_line_y, "red", "inundatiepeil")
    add_hline_with_label(x_vals_berg, nulpeil_line_y, "green", "nulpeil")

    # 3) Waterstand – mpn + peilgebied + streefpeil
    for location_id in df_mpn.columns.get_level_values("location_id"):
        naam = df_locs_mpn.loc[df_locs_mpn.location_id == location_id, "naam"].iat[0]
        fig.add_trace(
            go.Scatter(
                x=df_mpn.index, y=df_mpn[location_id].iloc[:, 0].to_numpy(),
                mode="lines", line=dict(color="rgba(100,116,139,0.4)", width=2),
                meta=location_id,
                hovertemplate=(
                    "tijd: %{{x|%Y-%m-%d %H:%M}}<br>"
                    "waterstand: %{{y:.3f}} mNAP<br>"
                    f"naam: {naam}<br>"
                    "location_id: %{{meta}}<extra></extra>"
                ),
                showlegend=False, name=f"mpn_{location_id}",
            ),
            row=3, col=1,
        )

    if not df_pgb.empty:
        fig.add_trace(
            go.Scatter(
                x=df_pgb.index, y=df_pgb.iloc[:, 0].to_numpy(),
                mode="lines", line=dict(color="#1e40af", width=3),
                hovertemplate="tijd: %{x|%Y-%m-%d %H:%M}<br>peilgebied: %{y:.3f} mNAP<extra></extra>",
                showlegend=False, name="peilgebied",
            ),
            row=3, col=1,
        )

    streefpeil = pgb_props.get("streefpeil")
    if streefpeil is not None and pd.notnull(streefpeil):
        x_vals_ws = list(df_pgb.index) if not df_pgb.empty else sorted(list(df_mpn.index.unique()))
        if x_vals_ws:
            y_val = streefpeil
            fig.add_trace(
                go.Scatter(
                    x=x_vals_ws, y=[y_val] * len(x_vals_ws),
                    mode="lines", line=dict(dash="dash", color="#facc15", width=2),
                    name="Streefpeil", hoverinfo="text",
                    hovertext=[f"Streefpeil: {y_val:.2f} mNAP"] * len(x_vals_ws),
                    showlegend=False,
                ),
                row=3, col=1,
            )
            fig.add_annotation(
                x=x_vals_ws[0], y=y_val, xref="x3", yref="y3", text="streefpeil",
                font=dict(color="#facc15", size=13), showarrow=False,
                xanchor="left", yanchor="bottom", align="left",
                bgcolor="rgba(255,255,255,0.7)", borderpad=2,
            )

    # As- en layoutinstellingen
    fig.update_yaxes(range=[0, 100], tickformat=".0f", fixedrange=True,
                     tickmode="array", tickvals=[25, 50, 75, 100], ticktext=["25", "50", "75", "100"],
                     showgrid=True, gridcolor="rgba(0,0,0,0.08)", gridwidth=1, zeroline=False, row=1, col=1)
    fig.update_yaxes(fixedrange=False, tickformat=".0f", showgrid=True,
                     gridcolor="rgba(0,0,0,0.08)", gridwidth=1, zeroline=False, row=2, col=1)
    fig.update_yaxes(fixedrange=False, tickformat=".2f", showgrid=True,
                     gridcolor="rgba(0,0,0,0.08)", gridwidth=1, zeroline=False, row=3, col=1, automargin=False)

    x_min, x_max = df_vg.index.min(), df_vg.index.max()
    for r in [1, 2, 3]:
        fig.update_xaxes(range=[x_min, x_max], automargin=False, showgrid=True,
                         gridcolor="rgba(0,0,0,0.08)", gridwidth=1, zeroline=False, row=r, col=1)
    fig.update_xaxes(title_text="Tijd", row=3, col=1)

    fig.update_layout(uirevision=sel, margin=dict(l=40, r=10, t=60, b=40),
                      plot_bgcolor="white", hovermode="closest", font=dict(size=13), showlegend=False)

    # Lege highlight-trace (wordt later gevuld)
    fig.add_trace(
        go.Scatter(x=[], y=[], mode="lines", line=dict(color="rgba(251,191,36,1)", width=4),
                   hoverinfo="skip", name="__highlight__", showlegend=False),
        row=3, col=1,
    )

    # Cache
    try:
        if getattr(cache, "cache", None) is not None:
            cache.set(ckey, fig.to_dict())
    except Exception:
        pass

    return fig.to_dict()


# --------- Cursorlijn + highlight invullen ---------
@app.callback(
    Output("combined-graph", "figure"),
    [Input("combined-fig-store", "data"), Input("tijdslider", "value"),
     Input("marker-mpn", "clickData"), Input("clicked-trace-store", "data")],
)
def add_vline_and_highlight(fig_dict, idx, selected_mpn, selected_trace_id):
    """Voeg vline toe en highlight geselecteerde mpn-trace; zet selectie bovenop."""
    if fig_dict is None or idx is None:
        raise PreventUpdate

    fig = go.Figure(fig_dict)
    current_dt = all_datetimes[int(idx)]

    # Bepaal selectiebron
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
    if trigger_id == "clicked-trace-store":
        sel_id = selected_trace_id
    elif trigger_id == "marker-mpn":
        sel_id = (selected_mpn and selected_mpn.get("properties", {}) and selected_mpn["properties"].get("location_id"))
    else:
        sel_id = selected_trace_id or (selected_mpn and selected_mpn.get("properties", {}) and selected_mpn["properties"].get("location_id"))

    # Dimmen + highlighten
    x_sel, y_sel = [], []
    selected_trace_idx = None
    for i_tr, tr in enumerate(fig.data):
        meta_val = getattr(tr, "meta", None)
        if meta_val:
            tr.line.color = "rgba(100,116,139,0.25)"
            tr.line.width = 2
            if sel_id and meta_val == sel_id:
                tr.line.color = "rgba(251,191,36,1)"
                tr.line.width = 4
                selected_trace_idx = i_tr
                x_sel, y_sel = list(tr.x), list(tr.y)

    # Zet geselecteerde trace en highlight helemaal bovenop
    if selected_trace_idx is not None:
        data_list = list(fig.data)
        sel_trace = data_list.pop(selected_trace_idx)
        data_list.append(sel_trace)
        fig.data = tuple(data_list)

    hl_idx = next((i for i in range(len(fig.data) - 1, -1, -1) if getattr(fig.data[i], "name", None) == "__highlight__"), None)
    if hl_idx is not None:
        fig.data[hl_idx].x = x_sel
        fig.data[hl_idx].y = y_sel
        data_list = list(fig.data)
        hl_trace = data_list.pop(hl_idx)
        data_list.append(hl_trace)
        fig.data = tuple(data_list)

    # Cursorlijnen (halo + kern) voor alle subplots
    cursor_shapes = []
    core_col, halo_col = "rgba(180,190,210,1.0)", "rgba(180,190,210,0.12)"
    for xref in ["x1", "x2", "x3"]:
        cursor_shapes.append(go.layout.Shape(type="line", x0=current_dt, x1=current_dt, y0=0, y1=1,
                                             xref=xref, yref="paper", line=dict(color=halo_col, width=6), layer="above"))
    for xref in ["x1", "x2", "x3"]:
        cursor_shapes.append(go.layout.Shape(type="line", x0=current_dt, x1=current_dt, y0=0, y1=1,
                                             xref=xref, yref="paper", line=dict(color=core_col, width=2), layer="above"))
    fig.layout.shapes = tuple(cursor_shapes)
    return fig


@app.callback(
    Output("mini-tijdserie", "figure"),
    [Input("pgb-dropdown", "value"), Input("kaartvariabele-dropdown", "value"), Input("tijdslider", "value")],
)
def update_mini_graph(sel, var, idx):
    """Kleine overzichtsgrafiek boven slider + vline op huidige index."""
    if not sel:
        raise PreventUpdate
    parameter_id = "vullingsgraad" if var == "vullingsgraad" else "vulling_mm"
    try:
        df = time_series_cache.get_time_series("VullingsgraadOutput", parameter_id, location_ids=[sel])
    except Exception:
        df = pd.DataFrame()

    if df is not None and not df.empty:
        series = df.iloc[:, 0]
        vals = [series.get(ts, None) for ts in all_datetimes]
    else:
        vals = [None] * len(all_datetimes)

    idx0 = int(idx) if idx is not None else 0
    mini = go.Figure(go.Scatter(x=list(range(len(all_datetimes))), y=vals, mode="lines", line=dict(width=2),
                                hoverinfo="skip", showlegend=False))
    mini.add_vline(x=idx0, line_width=2, line_dash="dash", line_color="#bbbbbb")
    mini.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=50, plot_bgcolor="rgba(0,0,0,0)",
                       xaxis=dict(visible=False, range=[0, len(all_datetimes) - 1], fixedrange=True),
                       yaxis=dict(visible=False, fixedrange=True))
    return mini


@app.callback(Output("playpause-button", "children"), Input("is-playing", "data"))
def set_playpause(is_playing): return "⏸️ Pause" if is_playing else "▶️ Play"


@app.callback(Output("is-playing", "data"),
              Input("playpause-button", "n_clicks"),
              State("is-playing", "data"), prevent_initial_call=True)
def toggle_playpause(n, playing): return (not playing) if n else playing


@app.callback(Output("interval", "disabled"), Input("is-playing", "data"))
def toggle_interval(playing): return not playing


@app.callback(
    Output("clicked-trace-store", "data"),
    Input("combined-graph", "clickData"),
    State("combined-graph", "figure"),
    prevent_initial_call=True,
)
def remember_clicked_trace(graph_click, current_fig_dict):
    """Klik in grafiek op mpn-lijn => onthoud location_id via trace.meta."""
    if (graph_click is None or current_fig_dict is None
            or "points" not in graph_click or not graph_click["points"]
            or "curveNumber" not in graph_click["points"][0]):
        raise PreventUpdate

    fig = go.Figure(current_fig_dict)
    point = graph_click["points"][0]
    trace = fig.data[point["curveNumber"]]
    sel_id = getattr(trace, "meta", None)
    if sel_id is None:
        raise PreventUpdate
    log(f"[CLICK GRAPH] trace: {sel_id}")
    return sel_id


@app.callback(
    Output("tijdslider", "value"),
    [Input("interval", "n_intervals"), Input("combined-graph", "relayoutData")],
    [State("interval", "disabled"), State("tijdslider", "value")],
)
def update_slider_from_interval_or_drag(n_intervals, relayoutData, disabled, current_idx):
    """
    1) Autoplay via interval -> volgende index.
    2) Drag van vline in grafiek -> dichtstbijzijnde tijdstap.
    """
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger_id == "interval":
        if disabled or current_idx is None:
            raise PreventUpdate
        new_idx = (int(current_idx) + 1) % len(all_datetimes)
        log(f"[TIME STEP] autoplay -> idx {new_idx}")
        return new_idx

    if trigger_id == "combined-graph":
        if not relayoutData:
            raise PreventUpdate
        # Pak x0/x1 uit verplaatste shape
        new_x_val = None
        for k, v in relayoutData.items():
            if k.startswith("shapes[") and (k.endswith("].x0") or k.endswith("].x1")):
                new_x_val = v
                break
        if new_x_val is None:
            raise PreventUpdate
        try:
            ts = pd.to_datetime(new_x_val)
        except Exception:
            raise PreventUpdate

        # Zoek dichtstbijzijnde index
        pos = bisect.bisect_left(all_datetimes, ts)
        if pos <= 0:
            nearest = 0
        elif pos >= len(all_datetimes):
            nearest = len(all_datetimes) - 1
        else:
            before, after = all_datetimes[pos - 1], all_datetimes[pos]
            nearest = pos if (after - ts) <= (ts - before) else (pos - 1)

        if current_idx is not None and int(current_idx) == nearest:
            raise PreventUpdate
        log(f"[TIME STEP] drag -> idx {nearest} (≈ {ts})")
        return nearest

    raise PreventUpdate


# === marker-mpn hideout updaten (allowed + selectie + tick) ===
@app.callback(
    Output("marker-mpn", "hideout"),
    [Input("pgb-dropdown", "value"), Input("tijdslider", "value"),
     Input("clicked-mpn-store", "data"), Input("clicked-trace-store", "data"),
     Input("combined-graph", "relayoutData")],  # blijft Input om re-style te forceren
)
def update_mpn_markers(selected_location_id, idx, mpn_clickdata, clicked_trace_id, _relayoutData):
    """
    Houdt bij:
    - welke meetpunten getoond mogen worden (allowed)
    - welk meetpunt geselecteerd is (sel)
    - een 'tick' zodat de client-side style opnieuw rendert bij tijd of drag
    """
    if not selected_location_id or "peilgebied_combi_attr" not in df_locs_mpn.columns:
        return {"allowed": [], "sel": None, "tick": int(idx) if idx is not None else 0}

    mask = (df_locs_mpn["peilgebied_combi_attr"].astype(str) == str(selected_location_id))
    points = df_locs_mpn[mask]
    allowed = points["peilgebied_combi_attr"].astype(str).dropna().unique().tolist() if not points.empty else []

    sel_id = None
    if clicked_trace_id:
        sel_id = clicked_trace_id
    elif mpn_clickdata and mpn_clickdata.get("properties"):
        sel_id = mpn_clickdata["properties"].get("location_id") or mpn_clickdata["properties"].get("id")

    return {"allowed": allowed, "sel": sel_id, "tick": int(idx) if idx is not None else 0}


# ========= Main =========
if __name__ == "__main__":
    app.title = "Vullingsgraad"
    app.run(port=5005, debug=True)
