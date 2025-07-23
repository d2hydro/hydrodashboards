#%%
import dash
from dash import html, dcc, Output, Input, State, ALL, ctx
import dash_leaflet as dl
import pandas as pd
import pyarrow.dataset as ds
from read import read_peilgebieden, read_mpn_locs
from dash_extensions.javascript import assign
from pyproj import Transformer
from dash.exceptions import PreventUpdate
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import time
import sys
from flask_caching import Cache
from functools import wraps, lru_cache

# ------------------------------------------------------------
# Timer helpers
# ------------------------------------------------------------
def timer_print(msg, t0):
    print(f"[TIMER] {msg} - {time.perf_counter() - t0:.3f} s")

def timed_inner(name):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            t0 = time.perf_counter()
            out = f(*args, **kwargs)
            timer_print(f"  --> Binnen {name}", t0)
            return out
        return wrapper
    return decorator

def timed_callback(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        output_ids = get_callback_output_ids()
        print(f"[CALLBACK] {', '.join(output_ids)} triggered by {ctx.triggered_id}")
        result = f(*args, **kwargs)
        dt = time.perf_counter() - t0
        print(f"[TIMING] Callback {f.__name__} duurde {dt:.3f} s")
        return result
    return wrapper

def get_callback_output_ids():
    try:
        v = getattr(ctx, "outputs_list", None)
        if not v:
            return ["?"]
        if isinstance(v, str):
            return [v]
        if isinstance(v, dict):
            return [str(v.get("id", "?"))]
        if isinstance(v, (list, tuple)):
            out = []
            for item in v:
                if isinstance(item, dict):
                    out.append(str(item.get("id", "?")))
                else:
                    out.append(str(item))
            return out if out else ["?"]
        return [str(v)]
    except Exception as e:
        print("Error in get_callback_output_ids:", e)
        return ["?"]

# ------------------------------------------------------------
# App en cache setup
# ------------------------------------------------------------
app = dash.Dash(__name__)

cache = Cache(app.server, config={
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 3600
})

# ------------------------------------------------------------
# Geodata en datasets laden + PREFILTERS
# ------------------------------------------------------------
timer0 = time.perf_counter()
xmin, ymin, xmax, ymax = 100500, 486900, 150150, 577550
transformer = Transformer.from_crs(28992, 4326, always_xy=True)
lon_sw, lat_sw = transformer.transform(xmin, ymin)
lon_ne, lat_ne = transformer.transform(xmax, ymax)
leaflet_bounds = [[lat_sw, lon_sw], [lat_ne, lon_ne]]
timer_print("CRS transformatie (kaart bounds)", timer0)

timer1 = time.perf_counter()
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
    # Zet expliciet location_id!
    if "CODE" in feat["properties"]:
        feat["properties"]["location_id"] = str(feat["properties"]["CODE"])

location_options = []
seen = set()
for opt in options:
    lbl, val = opt.get("label"), opt.get("value")
    if lbl and val and val not in seen:
        seen.add(val)
        location_options.append({"label": f"{lbl} ({val})", "value": str(val)})
timer_print("Dropdown opties opgebouwd", timer1)

VG_DF = ds.dataset("d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/vullingsgraad.arrow", format="feather").to_table().to_pandas()
VG_DF["datetime"] = pd.to_datetime(VG_DF["datetime"])
VUL_DF = ds.dataset("d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/vulling.arrow", format="feather").to_table().to_pandas()
VUL_DF["datetime"] = pd.to_datetime(VUL_DF["datetime"])

LOC_MPN_DF = read_mpn_locs("d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/mpn_locations.arrow")
WLVL_MPN_DF = ds.dataset("d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/waterstand_meetpunt.arrow", format="feather").to_table().to_pandas()
WLVL_PGB_DF = ds.dataset("d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/waterstand_pgb.arrow", format="feather").to_table().to_pandas()
timer_print("Alle Arrow/Feather datasets als pandas ingeladen", timer1)

all_dt_arrow = pd.concat([VG_DF["datetime"], VUL_DF["datetime"]]).drop_duplicates()
all_datetimes = sorted(pd.to_datetime(all_dt_arrow))
datum_to_index = {i: dt for i, dt in enumerate(all_datetimes)}
index_to_datum = {pd.Timestamp(dt): i for i, dt in enumerate(all_datetimes)}

# ===== Prefilter: alles in dicts =====
VG_DF_dict = {k: g.reset_index(drop=True) for k, g in VG_DF.groupby("location_id")}
VUL_DF_dict = {k: g.reset_index(drop=True) for k, g in VUL_DF.groupby("location_id")}
lege_vg_df = pd.DataFrame({"datetime": all_datetimes, "value": [None]*len(all_datetimes)})
lege_vul_df = pd.DataFrame({"datetime": all_datetimes, "value": [None]*len(all_datetimes)})
mpn_per_peilgebied = {k: g.reset_index(drop=True) for k, g in LOC_MPN_DF.groupby("peilgebied_combi_attr")}
wlvl_per_mpn = {k: g.reset_index(drop=True) for k, g in WLVL_MPN_DF.groupby("location_id")}
wlvl_per_pgb = {k: g.reset_index(drop=True) for k, g in WLVL_PGB_DF.groupby("location_id")}

kaartvariabelen = [
    {"label": "vullingsgraad [%]", "value": "vullingsgraad"},
    {"label": "vulling [mm]", "value": "vulling"},
]

# ------------------------------------------------------------
# Kleuren en stijlfuncties
# ------------------------------------------------------------
def kleur_bij_vullingsgraad(val):
    if pd.isna(val): return "gray"
    if val < 25: return "green"
    if val < 50: return "yellow"
    if val < 75: return "orange"
    return "red"

def kleur_bij_vulling(val):
    if pd.isna(val): return "gray"
    if val < 10:  return "#eff3ff"
    if val < 20:  return "#bdd7e7"
    if val < 30:  return "#6baed6"
    if val < 40:  return "#3182bd"
    return "#08519c"

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

def get_marker_icon(selected=False):
    url = "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/"
    icon_url = url + ("marker-icon-yellow.png" if selected else "marker-icon-blue.png")
    return {
        "iconUrl": icon_url,
        "iconSize": [25, 41],
        "iconAnchor": [12, 41],
        "popupAnchor": [1, -34],
        "shadowUrl": url + "marker-shadow.png",
        "shadowSize": [41, 41]
    }

def_layout = {
    "position": "absolute", "top": "10px", "right": "10px", "bottom": "10px",
    "width": "480px", "height": "calc(100vh - 32px)",
    "background": "white", "borderRadius": "5px",
    "zIndex": 1100, "boxShadow": "0 2px 8px rgba(0,0,0,0.05)",
    "padding": "10px", "display": "flex",
    "flexDirection": "column", "gap": "10px", "minHeight": 0
}

# ---------- DEFAULTS VOOR DIRECTE INIT ------------
default_index = 0
default_dt = datum_to_index[default_index]
default_var = "vullingsgraad"
default_pgb = location_options[0]["value"]
initial_label = default_dt.strftime("%Y-%m-%d %H:%M")

# ---------------------------------------------------

# ------------------------------------------------------------
# Layout
# ------------------------------------------------------------
app.layout = html.Div([
    html.Div([
        html.Label([
            "kaartvariabele: ",
            html.Span("?", title="Welke variabele wordt als kleur getoond op de kaart.", style={"cursor": "help"})
        ], style={"fontSize": "13px"}),
        dcc.Dropdown(
            id="kaartvariabele-dropdown",
            options=kaartvariabelen,
            value=default_var,
            clearable=False,
            style={"width": "240px", "marginBottom": "8px"}
        ),
        dcc.Store(id="hovered-trace", data=None),
        dcc.Store(id="selected-mpn-id", data=None),
        html.Label([
            "peilgebied: ",
            html.Span("?", title="Selecteer peilgebied", style={"cursor": "help"})
        ], style={"fontSize": "13px"}),
        dcc.Dropdown(
            id="pgb-dropdown",
            options=location_options,
            value=default_pgb,   # <-- Default selection!
            placeholder="Selecteer peilgebied",
            clearable=True,
            style={"width": "240px"}
        )
    ], style={
        "position": "absolute", "top": "10px", "left": "10px", "zIndex": 1002,
        "background": "rgba(220,240,255,1)", "borderRadius": "8px", "padding": "10px"
    }),

    html.Div([
        dcc.Loading(
            id="graph-loading",
            type="circle",
            children=[
                dcc.Graph(
                    id="combined-graph",
                    config={"displayModeBar": True, "scrollZoom": True},
                    style={"height": "100%", "minHeight": 0}
                )
            ],
            color="#e7e427",
            fullscreen=False
        )
    ], style=def_layout),

    dl.Map(
        center=[(lat_sw + lat_ne) / 2, (lon_sw + lon_ne) / 2],
        bounds=leaflet_bounds,
        style={"height": "100vh", "width": "100%"},
        preferCanvas=True,
        children=[
            dl.TileLayer(),
            dl.LayerGroup(id="marker-mpn"),
            dl.GeoJSON(
                id="geojson-pgb",
                data=geojson_data,
                options={
                    "style": style_handle,
                    "interactive": True,
                    "bubblingMouseEvents": True,
                    "selected": default_pgb,  # <-- Default selected!
                },
                hoverStyle={"weight": 2, "color": "yellow", "dashArray": ""},
                children=[dl.Tooltip(id="geojson-tooltip")],
                eventHandlers={"click": assign("function(e){return e?.target?.feature?.properties||{};}")}
            ),
        ]
    ),

    html.Div([
        dcc.Store(id="is-playing", data=False),
        html.Button(id="playpause-button", n_clicks=0, style={"width": "72px"}),
        html.Div(initial_label, id="datum-label", style={"fontWeight": "bold"}),
        html.Div([
            dcc.Graph(
                id="mini-tijdserie", config={"displayModeBar": False},
                style={"height": "50px", "width": "350px", "position": "absolute", "top": 0, "left": "25px", "pointerEvents": "none"}
            ),
            dcc.Slider(
                id="tijdslider",
                min=0, max=len(all_datetimes) - 1, value=default_index, updatemode="mouseup"
            )
        ], style={"position": "relative", "width": "400px", "height": "50px", "display": "inline-block"})
    ],
        style={
            "position": "absolute", "bottom": "10px", "left": "10px",
            "background": "rgba(255,255,255,0.9)", "padding": "8px",
            "borderRadius": "6px", "zIndex": 1000,
            "display": "flex", "gap": "10px", "alignItems": "center"
        }
    ),

    dcc.Interval(id="interval", interval=1000, disabled=True),
    html.Div(id="click-output"),
])

# ------------------------------------------------------------
# Callbacks (ALLES via dict lookups!)
# ------------------------------------------------------------

@lru_cache(maxsize=128)
@timed_inner("get_kaartdata_for_datetime")
def get_kaartdata_for_datetime(dt, kaartvariabele):
    dt = pd.Timestamp(dt)
    if kaartvariabele == "vullingsgraad":
        data_dict = VG_DF_dict
        kleur_fn = kleur_bij_vullingsgraad
    else:
        data_dict = VUL_DF_dict
        kleur_fn = kleur_bij_vulling
    return {
        loc: {
            "fillColor": kleur_fn(
                df.loc[df["datetime"] == dt, "value"].iloc[0]
            ) if not df.empty and (df["datetime"] == dt).any() else "gray",
            "color": "#666", "weight": 0.3, "fillOpacity": 1,
            kaartvariabele: df.loc[df["datetime"] == dt, "value"].iloc[0]
                if not df.empty and (df["datetime"] == dt).any() else None
        }
        for loc, df in data_dict.items()
    }

@app.callback(
    Output("geojson-pgb", "hideout"),
    Output("datum-label", "children"),
    Output("geojson-pgb", "options"),
    Input("tijdslider", "value"),
    Input("pgb-dropdown", "value"),
    Input("kaartvariabele-dropdown", "value"),
    # GEEN prevent_initial_call=True hier!
)
def update_stylemap(idx, sel, var):
    t0 = time.perf_counter()
    if idx is None or int(idx) not in datum_to_index or not sel or not var:
        raise PreventUpdate
    dt = datum_to_index[int(idx)]
    stylemap = get_kaartdata_for_datetime(dt, var)
    label = dt.strftime("%Y-%m-%d %H:%M")
    options = {"style": style_handle, "selected": sel, "interactive": True, "bubblingMouseEvents": True}
    timer_print("update_stylemap callback", t0)
    return stylemap, label, options

@app.callback(
    Output("pgb-dropdown", "value"),
    Input("geojson-pgb", "clickData"),
    prevent_initial_call=True
)
def select_dropdown_on_click(clickData):
    if not clickData or "properties" not in clickData or "location_id" not in clickData["properties"]:
        raise PreventUpdate
    return clickData["properties"]["location_id"]

@app.callback(
    Output("geojson-tooltip", "children"),
    Input("geojson-pgb", "hoverData"),
    State("tijdslider", "value"),
    State("kaartvariabele-dropdown", "value"),
    prevent_initial_call=True
)
def update_tooltip(feature, idx, var):
    if not feature:
        return ""
    props = feature["properties"]
    code, naam = props.get("location_id"), props.get("naam")
    dt = datum_to_index[int(idx)]
    style = get_kaartdata_for_datetime(dt, var)
    val = style.get(code, {}).get(var)
    txt = f"{val:.1f}%" if val is not None else "n.b."
    return f"naam: {naam} (code: {code}) — {txt}"

@app.callback(
    Output("combined-graph", "figure"),
    Input("pgb-dropdown", "value"),
    Input("kaartvariabele-dropdown", "value"),
    Input("selected-mpn-id", "data"),
    prevent_initial_call=True
)
@timed_callback
def update_and_highlight_combined(sel, var, selected_mpn_id):
    t0 = time.perf_counter()
    if not sel:
        raise PreventUpdate
    ckey = f"combined_{sel}_{selected_mpn_id}"
    fig = cache.get(ckey)
    if fig is not None:
        print(f"CACHE HIT combined for {sel} / {selected_mpn_id}")
        timer_print("update_and_highlight_combined totaal", t0)
        return fig
    print(f"CACHE MISS combined for {sel} / {selected_mpn_id}")

    df_vg = VG_DF_dict.get(sel, lege_vg_df)
    df_vul = VUL_DF_dict.get(sel, lege_vul_df)
    df_pgb = wlvl_per_pgb.get(sel, pd.DataFrame(columns=["datetime", "value"]))
    mpn_ids = mpn_per_peilgebied.get(sel, pd.DataFrame(columns=["location_id"]))["location_id"].tolist()
    traces = []
    if selected_mpn_id and selected_mpn_id in wlvl_per_mpn:
        for mid in mpn_ids:
            if mid == selected_mpn_id: continue
            grp = wlvl_per_mpn.get(mid, pd.DataFrame(columns=["datetime", "value"]))
            naam = LOC_MPN_DF.loc[LOC_MPN_DF.location_id == mid, 'naam'].iat[0] if not LOC_MPN_DF.empty else ""
            traces.append(go.Scattergl(x=grp["datetime"], y=grp["value"]/1000, mode='lines',
                line=dict(color='grey', width=1), opacity=0.7,
                hovertemplate=f'datum: %{{x|%Y-%m-%d %H:%M}}<br>waarde: %{{y:.3f}}<br>naam: {naam}<extra></extra>'))
        if not df_pgb.empty:
            traces.append(go.Scattergl(
                x=df_pgb["datetime"], y=df_pgb["value"]/1000, mode='lines',
                line=dict(color='royalblue', width=3),
                name=f"Meetpunt {naam}",
                hovertemplate='datum: %{x|%Y-%m-%d %H:%M}<br>waarde: %{y:.3f}<br>naam: Peilgebied<extra></extra>'
            ))
        grp = wlvl_per_mpn.get(selected_mpn_id, pd.DataFrame(columns=["datetime", "value"]))
        if not grp.empty:
            naam = LOC_MPN_DF.loc[LOC_MPN_DF.location_id == selected_mpn_id, 'naam'].iat[0]
            traces.append(go.Scattergl(
                x=grp["datetime"], y=grp["value"]/1000, mode='lines',
                line=dict(color='#e7e427', width=3), opacity=1,
                hovertemplate=f'datum: %{{x|%Y-%m-%d %H:%M}}<br>waarde: %{{y:.3f}}<br>naam: {naam}<extra></extra>'
            ))
    else:
        for mid in mpn_ids:
            grp = wlvl_per_mpn.get(mid, pd.DataFrame(columns=["datetime", "value"]))
            naam = LOC_MPN_DF.loc[LOC_MPN_DF.location_id == mid, 'naam'].iat[0] if not LOC_MPN_DF.empty else ""
            traces.append(go.Scattergl(x=grp["datetime"], y=grp["value"]/1000, mode='lines',
                line=dict(color='grey', width=1), opacity=0.7,
                hovertemplate=f'datum: %{{x|%Y-%m-%d %H:%M}}<br>waarde: %{{y:.3f}}<br>naam: {naam}<extra></extra>'))
        if not df_pgb.empty:
            traces.append(go.Scattergl(
                x=df_pgb["datetime"], y=df_pgb["value"]/1000, mode='lines',
                line=dict(color='royalblue', width=3),
                hovertemplate='datum: %{x|%Y-%m-%d %H:%M}<br>waarde: %{y:.3f}<br>naam: Peilgebied<extra></extra>'
            ))

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
        subplot_titles=["Vullingsgraad [%]", "Vulling [mm]", "Waterstand [mNAP]"]
    )

    # BOVENSTE GRAFIEK MET ACHTERGRONDKLEUREN
    fig.add_trace(go.Scatter(
        x=df_vg["datetime"], y=df_vg["value"], line=dict(color='blue', width=2), showlegend=False
    ), row=1, col=1)
    for y0, y1, colc in [
        (0, 25, 'rgba(120,200,120,0.4)'),
        (25, 50, 'rgba(255,255,100,0.4)'),
        (50, 75, 'rgba(255,200,100,0.4)'),
        (75, 100, 'rgba(255,100,100,0.4)')
    ]:
        fig.add_shape(type='rect', xref='x1', yref='y1',
                      x0=df_vg["datetime"].min(), x1=df_vg["datetime"].max(),
                      y0=y0, y1=y1, fillcolor=colc, line_width=0, layer='below', row=1, col=1)

    # TWEEDE GRAFIEK MET ACHTERGRONDKLEUREN
    fig.add_trace(go.Scatter(
        x=df_vul["datetime"], y=df_vul["value"], line=dict(color='royalblue', width=2), showlegend=False
    ), row=2, col=1)
    for y0, y1, colc in [
        (0, 10, '#ffffff'),
        (10, 20, '#b4d3e7'),
        (20, 30, '#72b2d7'),
        (30, 40, '#3e91c4'),
        (40, 60, '#1c5fa5')
    ]:
        fig.add_shape(type='rect', xref='x2', yref='y2',
                      x0=df_vul["datetime"].min(), x1=df_vul["datetime"].max(),
                      y0=y0, y1=y1, fillcolor=colc, line_width=0, layer='below', row=2, col=1)

    # DERDE GRAFIEK: WATERSTAND MEETPUNTEN
    for tr in traces:
        fig.add_trace(tr, row=3, col=1)

    fig.update_layout(
        height=900, margin=dict(l=40, r=10, t=60, b=40), plot_bgcolor='white',
        hovermode='closest', font=dict(size=13), showlegend=False
    )
    cache.set(ckey, fig)
    timer_print("update_and_highlight_combined totaal", t0)
    return fig

@app.callback(
    Output("mini-tijdserie", "figure"),
    Input("pgb-dropdown", "value"),
    Input("kaartvariabele-dropdown", "value"),
    Input("tijdslider", "value"),
    prevent_initial_call=True
)
@timed_callback

def update_mini_timeseries(sel, var, idx):
    t0 = time.perf_counter()
    if not sel:
        raise PreventUpdate
    mkey = f"mini_{sel}_{var}"
    mini = cache.get(mkey)
    
    if mini is None:
        ds_sel = VG_DF_dict if var == 'vullingsgraad' else VUL_DF_dict
        df = ds_sel.get(sel, lege_vg_df if var == "vullingsgraad" else lege_vul_df)
        all_datetimes_dt = pd.to_datetime(all_datetimes)
        if isinstance(df, pd.DataFrame) and not df.empty and "datetime" in df.columns:
            df["datetime"] = pd.to_datetime(df["datetime"])
            all_datetimes_dt = pd.to_datetime(all_datetimes)
            df = df.drop_duplicates(subset=["datetime"])
            df = df.set_index("datetime").reindex(all_datetimes_dt).reset_index()
        else:
            df = pd.DataFrame({
                "datetime": pd.to_datetime(all_datetimes),
                "value": [np.nan] * len(all_datetimes)
            })
        vals = df["value"].tolist()
        idx0 = int(idx)
        mini = go.Figure(go.Scatter(
            x=list(range(len(all_datetimes))),
            y=vals, mode='lines', line=dict(width=2),
            hoverinfo='skip', showlegend=False
        ))
        mini.add_vline(x=idx0, line_width=2, line_dash='dash')
        mini.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=50, plot_bgcolor='rgba(0,0,0,0)',
                           xaxis=dict(visible=False, range=[0, len(all_datetimes) - 1], fixedrange=True),
                           yaxis=dict(visible=False, fixedrange=True))
        cache.set(mkey, mini)
    timer_print("update_mini_timeseries totaal", t0)
    return mini


@app.callback(
    Output("marker-mpn", "children"),
    Input("pgb-dropdown", "value"),
    Input("selected-mpn-id", "data"),
)
def update_mpn_markers(selected_location_id, selected_mpn_id):
    t0 = time.perf_counter()
    if not selected_location_id:
        timer_print("update_mpn_markers callback (geen selectie)", t0)
        raise PreventUpdate
    points = mpn_per_peilgebied.get(selected_location_id)
    if points is None or points.empty:
        timer_print("update_mpn_markers callback (geen punten)", t0)
        return []
    coords = transformer.transform(points["x"].values, points["y"].values)
    lons, lats = coords if isinstance(coords, tuple) else (coords[0], coords[1])
    selected_str = str(selected_mpn_id) if selected_mpn_id is not None else None
    markers = [
        dl.Marker(
            id={'type': 'mpn-marker', 'index': row.location_id},
            position=[lat, lon],
            n_clicks=0,
            icon=get_marker_icon(str(row.location_id) == selected_str),
            children=[
                dl.Tooltip(row.naam),
                dl.Popup(f"{row.naam} ({row.location_id})")
            ]
        )
        for row, lat, lon in zip(points.itertuples(index=False), lats, lons)
    ]
    timer_print("update_mpn_markers callback", t0)
    return markers

@app.callback(
    Output("selected-mpn-id", "data"),
    Input({'type': 'mpn-marker', 'index': ALL}, "n_clicks"),
    Input("pgb-dropdown", "value"),
    State("selected-mpn-id", "data"),
    prevent_initial_call=True
)
def set_or_reset_selected_mpn(marker_clicks, pgb_value, prev_selected):
    t0 = time.perf_counter()
    trig = ctx.triggered_id
    if trig == "pgb-dropdown" and prev_selected is None:
        raise PreventUpdate
    if isinstance(trig, dict) and trig.get("type") == "mpn-marker":
        mpn_id = trig["index"]
        points = mpn_per_peilgebied.get(pgb_value, pd.DataFrame(columns=["location_id"]))
        marker_ids = points["location_id"].tolist()
        if mpn_id in marker_ids:
            i = marker_ids.index(mpn_id)
            if marker_clicks[i] > 0:
                if prev_selected == mpn_id:
                    timer_print("set_or_reset_selected_mpn callback (deselect)", t0)
                    return None
                timer_print("set_or_reset_selected_mpn callback (select)", t0)
                return mpn_id
    timer_print("set_or_reset_selected_mpn callback (PreventUpdate)", t0)
    raise PreventUpdate

@app.callback(Output("playpause-button", "children"), Input("is-playing", "data"))
def set_playpause(is_playing):
    return "⏸️ Pause" if is_playing else "▶️ Play"

@app.callback(
    Output("is-playing", "data"),
    Input("playpause-button", "n_clicks"),
    State("is-playing", "data"),
    prevent_initial_call=True
)
def toggle_playpause(n, playing):
    return not playing if n else playing

@app.callback(Output("interval", "disabled"), Input("is-playing", "data"))
def toggle_interval(playing):
    return not playing

@app.callback(
    Output("tijdslider", "value"),
    Input("interval", "n_intervals"),
    State("interval", "disabled"),
    State("tijdslider", "value")
)
def advance_slider(n, disabled, current):
    if disabled or current is None:
        raise PreventUpdate
    return (current + 1) % len(all_datetimes)

#Lijnen grafiek oplichten vai plotly.js

app.clientside_callback(
    """
    function(hoverData) {
            var dashDiv = document.getElementById('combined-graph');
            if (!dashDiv) return window.dash_clientside.no_update;
            var graphDiv = dashDiv.querySelector('.js-plotly-plot');
            if (!graphDiv || !graphDiv.data) return window.dash_clientside.no_update;

            let n_top = 0, n_mid = 1;
            let highlight = -1;
            if (hoverData && hoverData.points && hoverData.points.length > 0) {
                let curveNumber = hoverData.points[0].curveNumber;
                if (curveNumber >= n_top + n_mid) highlight = curveNumber;
            }

            let n = graphDiv.data.length;
            let colors = [], widths = [];
            for (let i = 0; i < n; i++) {
                if (i < n_top + n_mid) {
                    colors.push(null);
                    widths.push(2);
                } else if (i === highlight) {
                    colors.push('#ffd700');
                    widths.push(2);
                } else {
                    colors.push('grey');
                    widths.push(1);
                }
            }
            Plotly.restyle(graphDiv, {'line.color': colors, 'line.width': widths});

            // Lijn naar voren halen:
            // (alleen als highlight geldig en nog niet bovenop)
            if (highlight >= n_top + n_mid && highlight !== n - 1) {
                // Verplaats de trace naar het einde
                Plotly.moveTraces(graphDiv, highlight, n - 1);
            }

            return window.dash_clientside.no_update;
    }
    """,
    Output("hovered-trace", "data"),
    Input("combined-graph", "hoverData"),
)


# ------------------------------------------------------------
# Run
# ------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
