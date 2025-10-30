# %%
"""
Dash-app voor visualisatie van vullingsgraad, vulling en waterstand per peilgebied.

Belangrijkste onderdelen:
- Kaart (dash-leaflet) met peilgebieden en meetpunten (mpn).
- Tijdsanimatie (slider + play/pause).
- Interactieve grafiek met drempels/streefpeil en selectie van meetpunt.

Data komt uit:
- Shapefile peilgebieden (via read_peilgebieden).
- Arrow met meetpunten (via read_mpn_locs).
- TimeSeriesCache (fewspy.cache.TimeSeriesCache).
"""

# ========== IMPORTS ==========
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


# ========== SETTINGS ==========
# Zet IMPORTANT_LOG op True als je kerninteracties in stdout wilt zien.
IMPORTANT_LOG = True

def log(*args, **kwargs):
    """Conditional logger for important user interactions."""
    if IMPORTANT_LOG:
        print(*args, **kwargs)


# ========== PADEN / APP INIT ==========
app_dir = Path(__file__).parent
data_dir = app_dir.parent / "data"
assets_dir = app_dir / "assets"

app = dash.Dash(__name__, assets_folder=str(assets_dir))

# eenvoudige in-memory cache voor figuur-skeletten etc.
cache = Cache(
    app.server,
    config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 3600},
)


def timed_callback(f):
    """
    Decorator om de looptijd van callbacks te meten.
    Laat op dit moment niets zien, maar eenvoudig in te schakelen voor profiling.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        result = f(*args, **kwargs)
        _ = time.perf_counter() - t0  # duur wordt niet meer gelogd
        return result

    return wrapper


def bounds_to_map(xmin, ymin, xmax, ymax):
    """
    Maak Leaflet-bounds + center op basis van shapefile extent.

    We nemen een ruime bbox zodat alles mooi in beeld is.
    Returns:
        bounds  ( [[south,west],[north,east]] )
        center  ( [lat,lon] )
    """
    dx = xmax - xmin
    dy = ymax - ymin
    return [[ymin, xmin], [ymax + dy, xmin - 4 * dx]], [ymin + dy / 2, xmax - dx / 2]


# ========== DATA LADEN ==========
geojson_data, location_options, bounds = read_peilgebieden(
    file_path=(data_dir / "peilgebieden_cso_combi.shp").as_posix(),
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

# meetpuntlocaties (Point features)
df_locs_mpn = read_mpn_locs(data_dir / "mpn_locations.arrow")

# timeseries-cache met alle tijdreeksen
time_series_cache = TimeSeriesCache.from_manifest_file(
    data_dir / "time_series" / "manifest.json"
)

# gedeelde tijdas
all_datetimes = [pd.Timestamp(ts) for ts in time_series_cache.common_time_axis]

# dropdownopties voor kaartvariabele
kaartvariabelen = [
    {"label": "vullingsgraad [%]", "value": "vullingsgraad"},
    {"label": "vulling [mm]", "value": "vulling"},
]


# ========== CONSTANTEN / KLEURSCHALEN ==========
# Klassen voor vullingsgraad in procenten
VULLINGSGRAAD_CLASSES = [
    (0, 25, "rgba(120,200,120,1.0)"),
    (25, 50, "rgba(255,255,100,1.0)"),
    (50, 75, "rgba(255,200,100,1.0)"),
    (75, 100, "rgba(255,100,100,1.0)"),
]

# Klassen voor absolute vulling in mm
VULLING_MM_CLASSES = [
    (0, 10, "rgba(255,255,255,1.0)"),
    (10, 20, "rgba(180,211,231,1.0)"),
    (20, 30, "rgba(114,178,215,1.0)"),
    (30, 40, "rgba(62,145,196,1.0)"),
    (40, 60, "rgba(28,95,165,1.0)"),
]


def _pick_color(val, classes):
    """
    Geef een kleur-RGBA string voor een waarde 'val' op basis van klassen.
    Fallback:
    - NaN => grijs
    - boven hoogste klasse => hoogste kleur
    """
    if pd.isna(val):
        return "gray"
    for low, high, color in classes:
        if low <= val < high:
            return color
    return classes[-1][2]


def kleur_bij_vullingsgraad(val):
    """Mapping vullingsgraad [%] -> fillColor."""
    return _pick_color(val, VULLINGSGRAAD_CLASSES)


def kleur_bij_vulling(val):
    """Mapping vulling [mm] -> fillColor."""
    return _pick_color(val, VULLING_MM_CLASSES)


# ========== DYNAMIC STYLE FUN VOOR DE KAART ==========
# Deze functie draait client-side (JavaScript in de browser) om polygonen te stylen
# op basis van 'hideout' en selectie.
style_handle = assign(
    """
function(feature, context){
    const stylemap = context.hideout || {};
    const loc = feature.properties.location_id;
    const sel = context.selected;

    let base = stylemap[loc] || feature.properties.style || {};

    // basisstijl
    base = {
        ...base,
        color: base.color || "rgba(15,23,42,0.35)",
        weight: 1,
        fillOpacity: base.fillOpacity !== undefined ? base.fillOpacity : 0.7
    };

    // highlight geselecteerd peilgebied
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
"""
)

# default states bij opstart
default_index = len(all_datetimes) - 1
default_dt = all_datetimes[default_index]
default_pgb = location_options[0]["value"] if location_options else None
initial_label = default_dt.strftime("%Y-%m-%d %H:%M")
initial_kaartvariabele = "vullingsgraad"

# standaard subset zichtbaar aan meetpunten (alleen die in het actieve peilgebied)
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


@lru_cache(maxsize=128)
def get_kaartdata_for_datetime(dt, kaartvariabele):
    """
    Bouw een dict met stijl-informatie per peilgebied voor een bepaalde timestamp.
    Dit gaat in 'hideout' van de GeoJSON laag.
    Keys = location_id, value = dict(color, fillColor, etc).
    """
    dt = pd.to_datetime(dt).to_pydatetime()

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

    # get_time_series output bevat een multiindex (time, location_id, ...).
    # We pakken de rij op deze tijdstap en resetten voor makkelijke kolomnamen.
    df = df.loc[dt].reset_index()
    ids = df["location_id"].to_list()
    vals = df[dt].to_list()

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


# hideout voor eerste render van kaart
initial_stylemap = get_kaartdata_for_datetime(default_dt, initial_kaartvariabele)

# opties voor de GeoJSON laag
initial_options = {
    "style": style_handle,
    "selected": default_pgb,
    "interactive": True,
    "bubblingMouseEvents": True,
}

# lege figuur voor placeholder rechts
EMPTY_FIG = go.Figure()
EMPTY_FIG.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=0, r=0, t=0, b=0),
    xaxis=dict(visible=False),
    yaxis=dict(visible=False),
    showlegend=False,
)


# ========== LAYOUT CSS (inline styles als dicts) ==========
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


# ========== APP LAYOUT ==========
app.layout = html.Div(
    style=page_wrapper_style,
    children=[
        # ---------------- LINKER KOLOM (Kaart + controls) ----------------
        html.Div(
            style=left_col_style,
            children=[
                # Kaart
                dl.Map(
                    center=map_center,
                    zoom=10,
                    bounds=map_bounds,
                    style={"height": "100%", "width": "100%"},
                    preferCanvas=True,
                    children=[
                        dl.TileLayer(),
                        # Peilgebieden
                        dl.GeoJSON(
                            id="geojson-pgb",
                            data=geojson_data,
                            hideout=initial_stylemap,
                            options=initial_options,
                            eventHandlers={
                                # Klik op polygon => stuur feature.properties terug
                                "click": assign(
                                    "function(e){return e?.target?.feature?.properties||{};}"
                                )
                            },
                        ),
                        # Meetpunten (circleMarkers, geen standaard Leaflet Marker)
                        dl.GeoJSON(
                            id="marker-mpn",
                            data=json.loads(df_locs_mpn.to_json()),
                            filter=assign(
                                """
                                function(feature, context){
                                    // toon alleen geldige Points, én alleen
                                    // als die bij het geselecteerde peilgebied horen
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
                                        // circleMarker ipv default Leaflet Marker
                                        const naam = feature?.properties?.naam || "meetpunt";
                                        const locId = feature?.properties?.location_id
                                            || feature?.properties?.id
                                            || "(onbekend id)";

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
                                # Klik op meetpunt => stuur props + lat/lng
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
                        # Highlight-layer (gouden cirkel rond geselecteerd meetpunt)
                        dl.LayerGroup(id="mpn-click-layer"),
                    ],
                ),

                # Controlsbox linksboven (kaartvariabele + keuze peilgebied)
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

                # Tijdslider + play/pause onderin de kaart
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
                                # kleine "sparkline" grafiek boven de slider
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

                # Interval voor autoplay
                dcc.Interval(id="interval", interval=1000, disabled=True),

                # Semi-transparante overlay bij laden
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

                # Stores voor click state
                dcc.Store(id="clicked-mpn-store", data=None),
                dcc.Store(id="clicked-trace-store", data=None),
            ],
        ),

        # ---------------- RECHTER KOLOM (Grafiek + info) ----------------
        html.Div(
            style=right_col_style,
            children=[
                dcc.Store(id="combined-fig-store"),
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


# ========== CALLBACKS ==========

@app.callback(
    Output("page-loader", "style"),
    [Input("combined-fig-store", "data"), Input("geojson-pgb", "hideout")],
    prevent_initial_call=True,
)
def hide_page_loader(fig_dict, stylemap):
    """
    Verberg de loading-overlay zodra:
    - we de basisfiguur rechts hebben opgebouwd
    - en de kaart al een stylemap heeft.
    """
    if not fig_dict or not stylemap:
        raise PreventUpdate
    return {"display": "none"}


@app.callback(
    Output("clicked-mpn-store", "data"),
    Input("marker-mpn", "clickData"),
    prevent_initial_call=True,
)
def store_clicked_mpn(cd):
    """
    Sla de laatst aangeklikte meetpunt-info op (locatie_id, coords).
    """
    # We loggen hier niet; highlight_selected_point doet al logging.
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
    """
    Laat een 'gouden' marker + popup zien op het geselecteerde meetpunt.
    Bronnen van selectie:
    - klik op meetpunt in kaart
    - klik op trace in de grafiek
    - wisselen van peilgebied reset de highlight
    """
    from dash import callback_context as ctx

    # Nieuwe selectie van peilgebied -> highlight weg
    if ctx.triggered and ctx.triggered[0]["prop_id"].startswith("pgb-dropdown"):
        log(f"[HIGHLIGHT RESET] nieuw peilgebied: {selected_pgb}")
        return []

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    sel_id = None
    naam = None
    lat = None
    lng = None

    if trigger_id == "clicked-trace-store":
        # gebruiker klikte in de grafiek op een trace met meta == location_id
        sel_id = clicked_trace_id
        log(f"[HIGHLIGHT SOURCE] grafiek-click -> {sel_id}")

    elif trigger_id == "clicked-mpn-store":
        # gebruiker klikte op een mpn-markering op de kaart
        if not mpn_clickdata:
            raise PreventUpdate
        props = mpn_clickdata.get("properties", {}) or {}
        sel_id = props.get("location_id") or props.get("id")
        naam = props.get("naam") or "meetpunt"
        lat = mpn_clickdata.get("lat")
        lng = mpn_clickdata.get("lng")
        log(f"[HIGHLIGHT SOURCE] kaart-click -> {sel_id}")

    else:
        # fallback: gebruik wat we hebben (bij redraw, slider-move, etc.)
        if clicked_trace_id:
            sel_id = clicked_trace_id
        elif mpn_clickdata:
            props = mpn_clickdata.get("properties", {}) or {}
            sel_id = props.get("location_id") or props.get("id")
            naam = props.get("naam") or "meetpunt"
            lat = mpn_clickdata.get("lat")
            lng = mpn_clickdata.get("lng")

        if sel_id:
            log(f"[HIGHLIGHT RESTORE] {sel_id}")

    # niks geselecteerd? -> geen highlight
    if not sel_id:
        return []

    # als we geen lat/lng uit clickData hebben, kijk het meetpunt op in df_locs_mpn
    if lat is None or lng is None:
        row = df_locs_mpn.loc[df_locs_mpn["location_id"] == sel_id]
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
            return []

        if naam is None and "naam" in row.columns:
            naam = row["naam"].iloc[0]
        if naam is None:
            naam = sel_id

    # highlight marker (gouden cirkel + popup met naam/id)
    marker = dl.CircleMarker(
        center=[lat, lng],
        radius=7,
        color="#b28900",
        weight=2,
        fillColor="#ffe680",
        fillOpacity=0.9,
        children=[
            # geen Tooltip hier => geen hover-ID spam
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
    """
    Op elke wijziging in:
    - tijdslider,
    - geselecteerd peilgebied,
    - kaartvariabele,
    herbereken:
      - kleur per polygon (hideout),
      - label bij de tijd,
      - en geef door welk polygon geselecteerd is.
    """
    if idx is None or not sel or not var:
        raise PreventUpdate

    dt = all_datetimes[int(idx)]

    stylemap = get_kaartdata_for_datetime(dt, var)
    label = dt.strftime("%Y-%m-%d %H:%M")
    options = {
        "style": style_handle,
        "selected": sel,
        "interactive": True,
        "bubblingMouseEvents": True,
    }

    return stylemap, label, options


@app.callback(
    Output("pgb-dropdown", "value"),
    Input("geojson-pgb", "clickData"),
    prevent_initial_call=True,
)
def select_dropdown_on_click(clickData):
    """
    Klik op een polygon in de kaart -> zet dat peilgebied in de dropdown.
    """
    loc = clickData["properties"]["location_id"]
    log(f"[SELECT PGB] peilgebied gekozen: {loc}")
    return loc


# --------- GROTE GRAFIEK BOUWEN (zonder cursor/highlight) ---------
@app.callback(
    Output("combined-fig-store", "data"),
    [Input("pgb-dropdown", "value"), Input("kaartvariabele-dropdown", "value")],
)
@timed_callback
def build_combined_figure(sel, var):
    """
    Bouw het 'basisfiguur' voor het geselecteerde peilgebied:
    - subplot1: vullingsgraad [%] + gekleurde risicobanden
    - subplot2: vulling [mm] + drempels (overlast/inundatie/nulpeil)
    - subplot3: waterstand (peilgebied + individuele meetpunten)
      incl. streefpeil-lijn

    Slaat resultaat op in dcc.Store (combined-fig-store). Cursor en highlight
    worden later in een aparte callback toegevoegd.
    """
    if not sel:
        raise PreventUpdate

    # cache-key per peilgebied
    ckey = f"combined_v3_{sel}"

    # 1. Probeer uit cache
    fig = None
    try:
        if hasattr(cache, "cache") and cache.cache is not None:
            cached = cache.get(ckey)
            if cached is not None:
                fig = go.Figure(cached)
                log(f"[FIG] cache hit voor peilgebied {sel}")
    except Exception:
        pass

    # 2. Zo niet: alles nieuw opbouwen
    if fig is None:
        log(f"[FIG] build nieuw figuur voor peilgebied {sel}")

        # --- tijdseries ophalen
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

        # alle meetpunten binnen dit peilgebied
        mpn_ids = df_locs_mpn.loc[
            df_locs_mpn["peilgebied_combi_attr"] == sel, "location_id"
        ].tolist()
        df_mpn = time_series_cache.get_time_series(
            filter_id="PeilgebiedWaterstandMeetpunt",
            parameter_id="H.meting",
            location_ids=mpn_ids,
        )

        # eigenschappen/drempels van dit peilgebied (uit de GeoJSON properties)
        pgb_props = {}
        for feat in geojson_data["features"]:
            if feat["properties"].get("location_id") == sel:
                pgb_props = feat["properties"] or {}
                break

        # --- figure skeleton met 3 rijen
        fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.06,
            subplot_titles=[
                "Vullingsgraad [%]",
                "Vulling [mm]",
                "Waterstand [mNAP]",
            ],
        )

        # ===== Subplot 1: VULLINGSGRAAD [%] =====
        x0_1 = df_vg.index.min()
        x1_1 = df_vg.index.max()

        # Achtergrondbanden per klasse
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
                row=1,
                col=1,
            )

        # Vullingsgraad-lijn
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
            row=1,
            col=1,
        )

        # ===== Subplot 2: VULLING [mm] =====
        # fallback tijd-as als df_vul leeg is
        if df_vul is not None and not df_vul.empty:
            x0_2 = df_vul.index.min()
            x1_2 = df_vul.index.max()
        else:
            x0_2 = df_vg.index.min()
            x1_2 = df_vg.index.max()

        if df_vul is not None and not df_vul.empty:
            series_vul = df_vul[df_vul.columns[0]]
            max_vulling_val = series_vul.max()
        else:
            series_vul = pd.Series(dtype=float)
            max_vulling_val = float("nan")

        has_vulling_data = pd.notna(max_vulling_val)

        # Gekleurde banden (0-10,10-20,...) en evt >60 mm stuk
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
                    row=2,
                    col=1,
                )

            if has_vulling_data:
                axis_top = max(60, math.ceil(float(max_vulling_val) / 10.0) * 10)
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
                        row=2,
                        col=1,
                    )

        # Lijn met vulling [mm]
        fig.add_trace(
            go.Scatter(
                x=(
                    df_vul.index.to_list()
                    if df_vul is not None and not df_vul.empty
                    else []
                ),
                y=(
                    df_vul[df_vul.columns[0]].to_list()
                    if df_vul is not None and not df_vul.empty
                    else []
                ),
                mode="lines",
                line=dict(color="#1e40af", width=3),
                hovertemplate=(
                    "tijd: %{x|%Y-%m-%d %H:%M}<br>"
                    "vulling: %{y:.1f} mm<extra></extra>"
                ),
                showlegend=False,
                name="vulling_lijn",
            ),
            row=2,
            col=1,
        )

        # --- horizontale drempels in subplot 2 ---
        # Kies tijdas voor de labels/drempels
        if df_vul is not None and not df_vul.empty:
            x_vals_berg = df_vul.index.to_list()
        elif df_vg is not None and not df_vg.empty:
            x_vals_berg = df_vg.index.to_list()
        elif df_pgb is not None and not df_pgb.empty:
            x_vals_berg = df_pgb.index.to_list()
        elif df_mpn is not None and not df_mpn.empty:
            x_vals_berg = df_mpn.index.to_list()
        else:
            x_vals_berg = []

        overlast_line_y = pgb_props.get("berging_bij_inundatiepeil")
        inundatiepeil_val = pgb_props.get("inundatiepeil")
        nulpeil_val = pgb_props.get("peil_bij_nul_berging")

        # conversie naar mm (berging-lijnen staan als meters waterpeil t.o.v. NAP)
        inundatiepeil_line_y = (
            inundatiepeil_val * 10 if inundatiepeil_val is not None else None
        )
        nulpeil_line_y = (nulpeil_val * 10 if nulpeil_val is not None else None)

        def add_hline_with_label(x_vals, yval, kleur, tekst):
            """Voeg horizontale drempel-lijn (=dot) + label toe op subplot 2."""
            if not x_vals:
                return
            if yval is None or pd.isna(yval):
                return

            # horizontale lijn
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
                row=2,
                col=1,
            )

            # label naast lijn
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

        add_hline_with_label(x_vals_berg, overlast_line_y, "red", "overlast")
        add_hline_with_label(
            x_vals_berg, inundatiepeil_line_y, "red", "inundatiepeil"
        )
        add_hline_with_label(x_vals_berg, nulpeil_line_y, "green", "nulpeil")

        # ===== Subplot 3: WATERSTAND [mNAP] =====
        # individuele meetpunten (grijs)
        for location_id in df_mpn.columns.get_level_values("location_id"):
            naam = df_locs_mpn.loc[
                df_locs_mpn.location_id == location_id, "naam"
            ].iat[0]

            fig.add_trace(
                go.Scatter(
                    x=df_mpn.index,
                    y=df_mpn[location_id].iloc[:, 0].to_numpy(),
                    mode="lines",
                    line=dict(color="rgba(100,116,139,0.4)", width=2),
                    meta=location_id,  # belangrijk voor highlight
                    hovertemplate=(
                        "tijd: %{x|%Y-%m-%d %H:%M}<br>"
                        "waterstand: %{y:.3f} mNAP<br>"
                        f"naam: {naam}<br>"
                        "location_id: %{meta}<extra></extra>"
                    ),
                    showlegend=False,
                    name=f"mpn_{location_id}",
                ),
                row=3,
                col=1,
            )

        # peilgebied-lijn (blauw)
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
                row=3,
                col=1,
            )

        # streefpeil horizontale lijn + label
        streefpeil = pgb_props.get("streefpeil")
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
                        hovertext=[
                            f"Streefpeil: {y_val:.2f} mNAP"
                        ]
                        * len(x_vals_ws),
                        showlegend=False,
                    ),
                    row=3,
                    col=1,
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

        # ===== AS-INSTELLINGEN & LAYOUT =====

        # y-as vullingsgraad met vaste schaal (0-100%)
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

        # y-as vulling [mm] autoschaal
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

        # y-as waterstand [mNAP] autoschaal
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

        # x-as instellingen
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

        # algemene layout
        fig.update_layout(
            uirevision=sel,  # zorg dat zoom/position niet reset bij hover etc.
            margin=dict(l=40, r=10, t=60, b=40),
            plot_bgcolor="white",
            hovermode="closest",
            font=dict(size=13),
            showlegend=False,
        )

        # lege trace die later gebruikt wordt als highlight-overlay
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
            row=3,
            col=1,
        )

        # naar cache schrijven
        try:
            if hasattr(cache, "cache") and cache.cache is not None:
                cache.set(ckey, fig.to_dict())
        except Exception:
            pass

    return fig.to_dict()


# --------- CURSORLIJN + HIGHLIGHT TOEVOEGEN AAN FIGUUR ---------
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
    """
    Neem de basisfiguur uit combined-fig-store en voeg toe:
    - verticale cursorlijn (op huidige tijdslider-index)
    - highlight van geselecteerde meetpunt (gouden lijn)
    """
    if fig_dict is None or idx is None:
        raise PreventUpdate

    fig = go.Figure(fig_dict)
    current_dt = all_datetimes[int(idx)]

    # bepalen wie er geselecteerd is
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
        # gebruik laatste bekende selectie
        sel_id = (
            selected_trace_id
            or (
                selected_mpn
                and selected_mpn.get("properties", {})
                and selected_mpn["properties"].get("location_id")
            )
        )

    # Eerst alle meetpunt-traces dimmen qua kleur/width. Highlight de gekozen.
    # Belangrijk: we gaan GEEN .opacity meer aanpassen -> dit houdt lijnen leesbaar,
    # ook terwijl je de cursorlijn sleept.
    x_sel, y_sel = [], []
    selected_trace_idx = None

    for i_tr, tr in enumerate(fig.data):
        meta_val = getattr(tr, "meta", None)
        if meta_val:
            # default dim
            tr.line.color = "rgba(100,116,139,0.25)"
            tr.line.width = 2

            # highlight gekozen trace
            if sel_id and meta_val == sel_id:
                tr.line.color = "rgba(251,191,36,1)"
                tr.line.width = 4
                selected_trace_idx = i_tr
                x_sel = list(tr.x)
                y_sel = list(tr.y)

    # Zet de geselecteerde trace helemaal bovenop in de render-volgorde
    if selected_trace_idx is not None:
        data_list = list(fig.data)
        sel_trace = data_list.pop(selected_trace_idx)
        data_list.append(sel_trace)
        fig.data = tuple(data_list)

    # Vul de __highlight__-trace met dezelfde x/y van de geselecteerde meetpunt-trace
    hl_idx = None
    for i in range(len(fig.data) - 1, -1, -1):
        if getattr(fig.data[i], "name", None) == "__highlight__":
            hl_idx = i
            break

    if hl_idx is not None:
        fig.data[hl_idx].x = x_sel
        fig.data[hl_idx].y = y_sel

        data_list = list(fig.data)
        hl_trace = data_list.pop(hl_idx)
        data_list.append(hl_trace)
        fig.data = tuple(data_list)

    # Maak cursorlijnen (halo + kern) voor alle subplots
    cursor_shapes = []
    core_col = "rgba(180,190,210,1.0)"   # dunne kern
    halo_col = "rgba(180,190,210,0.12)"  # brede halo

    # brede halo-lijn
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

    # dunne kernlijn
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
    """
    Kleine grafiek boven de tijdslider:
    toont dezelfde variabele als op de kaart (vulling of vullingsgraad)
    over de hele tijdas. Plus een verticale marker bij de huidige index.
    """
    if not sel:
        raise PreventUpdate

    parameter_id = "vullingsgraad" if var == "vullingsgraad" else "vulling_mm"

    try:
        df = time_series_cache.get_time_series(
            filter_id="VullingsgraadOutput",
            parameter_id=parameter_id,
            location_ids=[sel],
        )
    except Exception:
        df = pd.DataFrame()

    if df is not None and not df.empty:
        series = df.iloc[:, 0]
        # Map alle tijdstappen naar waardes voor consistente x (= index 0..N)
        vals = [series.get(ts, None) for ts in all_datetimes]
    else:
        vals = [None] * len(all_datetimes)

    idx0 = int(idx) if idx is not None else 0

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
        xaxis=dict(
            visible=False,
            range=[0, len(all_datetimes) - 1],
            fixedrange=True,
        ),
        yaxis=dict(visible=False, fixedrange=True),
    )
    return mini


@app.callback(
    Output("playpause-button", "children"),
    Input("is-playing", "data"),
)
def set_playpause(is_playing):
    """Knoptekst: Play of Pause."""
    return "⏸️ Pause" if is_playing else "▶️ Play"


@app.callback(
    Output("is-playing", "data"),
    Input("playpause-button", "n_clicks"),
    State("is-playing", "data"),
    prevent_initial_call=True,
)
def toggle_playpause(n, playing):
    """
    Toggle de animatie-state. Wordt gebruikt om interval aan/uit te zetten.
    """
    return not playing if n else playing


@app.callback(
    Output("interval", "disabled"),
    Input("is-playing", "data"),
)
def toggle_interval(playing):
    """Interval draait alleen als we 'aan het afspelen' zijn."""
    return not playing


@app.callback(
    Output("clicked-trace-store", "data"),
    Input("combined-graph", "clickData"),
    State("combined-graph", "figure"),
    prevent_initial_call=True,
)
def remember_clicked_trace(graph_click, current_fig_dict):
    """
    Als je in de grafiek klikt op een meetpunt-trace (sub-plot 3),
    onthoud dan welke location_id (trace.meta).
    Dat gebruiken we om kaart-highlight te syncen.
    """
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
    if sel_id is None:
        raise PreventUpdate

    log(f"[CLICK GRAPH] trace geselecteerd: {sel_id}")
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
def update_slider_from_interval_or_drag(
    n_intervals, relayoutData, disabled, current_idx
):
    """
    Twee manieren waarop de slider kan bewegen:
    1. Autoplay: interval tikt door -> volgende index
    2. Gebruiker sleept de cursorlijn in de grote grafiek
       (via drag van 'shapes'), en we zoeken dichtstbijzijnde timestep.
    """
    ctx = dash.callback_context

    if not ctx.triggered:
        raise PreventUpdate

    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # (1) autoplay vooruit
    if trigger_id == "interval":
        if disabled or current_idx is None:
            raise PreventUpdate
        new_idx = (int(current_idx) + 1) % len(all_datetimes)
        log(f"[TIME STEP] autoplay -> idx {new_idx}")
        return new_idx

    # (2) cursor-drag in grafiek
    if trigger_id == "combined-graph":
        if not relayoutData:
            raise PreventUpdate

        # zoek nieuwe x-positie van de cursorlijn uit relayoutData
        new_x_val = None
        for k, v in relayoutData.items():
            if k.startswith("shapes[") and (
                k.endswith("].x0") or k.endswith("].x1")
            ):
                new_x_val = v
                break

        if new_x_val is None:
            raise PreventUpdate

        try:
            ts = pd.to_datetime(new_x_val)
        except Exception:
            raise PreventUpdate

        # zoek dichtstbijzijnde index in all_datetimes
        pos = bisect.bisect_left(all_datetimes, ts)

        if pos <= 0:
            nearest = 0
        elif pos >= len(all_datetimes):
            nearest = len(all_datetimes) - 1
        else:
            before = all_datetimes[pos - 1]
            after = all_datetimes[pos]
            nearest = pos if (after - ts) <= (ts - before) else (pos - 1)

        if current_idx is not None and int(current_idx) == nearest:
            raise PreventUpdate

        log(f"[TIME STEP] drag -> idx {nearest} (≈ {ts})")
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
    """
    Toon alleen meetpunten die horen bij het geselecteerde peilgebied.
    Dit sturen we als 'hideout' naar de GeoJSON-laag met de cirkelmarkertjes.
    """
    if not selected_location_id:
        return []

    if "peilgebied_combi_attr" not in df_locs_mpn.columns:
        return []

    mask = (
        df_locs_mpn["peilgebied_combi_attr"].astype(str)
        == str(selected_location_id)
    )
    points = df_locs_mpn[mask]
    if points.empty:
        return []

    hideout_list = (
        points["peilgebied_combi_attr"]
        .astype(str)
        .dropna()
        .unique()
        .tolist()
    )
    return hideout_list


# ========== MAIN ==========
if __name__ == "__main__":
    app.title = "Vullingsgraad"
    app.run(port=5005, debug=True)
