#%%
import dash
from dash import html, dcc, Output, Input, State, ALL
import dash_leaflet as dl
import pandas as pd
import pyarrow.dataset as ds
import pyarrow.compute as pc
import pyarrow as pa
from read import read_peilgebieden, read_mpn_locs
from dash_extensions.javascript import assign
from pyproj import Transformer
from dash.exceptions import PreventUpdate
import plotly.graph_objs as go
import time
import sys
from flask_caching import Cache
from plotly.subplots import make_subplots
from functools import wraps, lru_cache
from copy import deepcopy

app = dash.Dash(__name__)

# === Voeg caching toe ===
cache = Cache(app.server, config={
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 3600
})

def timed_callback(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        result = f(*args, **kwargs)
        dt = time.perf_counter() - t0
        print(f"[TIMING] Callback {f.__name__} duurde {dt:.3f}s")
        return result
    return wrapper

# ========== Geodata laden ==============
timer_start = time.time()
xmin, ymin, xmax, ymax = 100500, 486900, 150150, 577550
transformer = Transformer.from_crs(28992, 4326, always_xy=True)
lon_sw, lat_sw = transformer.transform(xmin, ymin)
lon_ne, lat_ne = transformer.transform(xmax, ymax)
leaflet_bounds = [[lat_sw, lon_sw], [lat_ne, lon_ne]]

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
print("TIJD: shapefile/geodata ingelezen in", round(time.time() - timer_start, 2), "s")

location_options = []
seen = set()
for opt in options:
    lbl = opt.get("label")
    val = opt.get("value")
    if lbl and val and val not in seen:
        seen.add(val)
        location_options.append({"label": f"{lbl} ({val})", "value": val})

# ===== Laad Arrow tijdseries, bepaal tijdas =====
ds_vg = ds.dataset("d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/vullingsgraad.arrow", format="feather")
ds_vul = ds.dataset("d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/vulling.arrow", format="feather")
df_locs_mpn = read_mpn_locs("d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/mpn_locations.arrow")
ds_wlvl_mpn = ds.dataset("d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/waterstand_meetpunt.arrow", format="feather")
ds_wlvl_pgb = ds.dataset("d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/waterstand_pgb.arrow", format="feather")

timer_start = time.time()
dt_vg = ds_vg.to_table(columns=["datetime"])
dt_vul = ds_vul.to_table(columns=["datetime"])
all_dt_arrow = pc.unique(pa.concat_tables([dt_vg, dt_vul])["datetime"])
all_datetimes = sorted(pd.to_datetime(all_dt_arrow.to_pylist()))
datum_to_index = {i: dt for i, dt in enumerate(all_datetimes)}
index_to_datum = {pd.Timestamp(dt): i for i, dt in enumerate(all_datetimes)}
print("TIJD: tijdas opgebouwd in", round(time.time() - timer_start, 2), "s")

kaartvariabelen = [
    {"label": "vullingsgraad [%]", "value": "vullingsgraad"},
    {"label": "vulling [mm]", "value": "vulling"},
]

# --------- Kleurfuncties ----------
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

# Kleur voor selectie (overal hetzelfde)
SELECTIE_KLEUR = "#e7e427"  # geel

style_handle = assign(f"""
function(feature, context){{
    const stylemap = context.hideout || {{}};
    const loc = feature.properties.location_id;
    const sel = context.selected;
    let base = stylemap[loc] || feature.properties.style;
    if(sel && loc === sel){{
        base = Object.assign({{}}, base, {{weight:3, color:'{SELECTIE_KLEUR}'}})
    }}
    return base;
}}
""")

def_layout = {
    "position": "absolute", "top": "10px", "right": "10px", "bottom": "10px",
    "width": "480px", "height": "calc(100vh - 32px)",
    "background": "white", "borderRadius": "5px",
    "zIndex": 1100, "boxShadow": "0 2px 8px rgba(0,0,0,0.05)",
    "padding": "10px", "display": "flex",
    "flexDirection": "column", "gap": "10px", "minHeight": 0
}

default_index = 0
default_dt = datum_to_index[default_index]
initial_label = default_dt.strftime("%Y-%m-%d %H:%M")
initial_stylemap = {}

# ========== Layout ==========
app.layout = html.Div([
    dcc.Store(id="selected-mpn-id"),
    # Besturing dropdowns
    html.Div([
        html.Label(["kaartvariabele: ", html.Span("?", title="Welke variabele...", style={"cursor": "help"})], style={"fontSize": "13px"}),
        dcc.Dropdown(id="kaartvariabele-dropdown", options=kaartvariabelen, value="vullingsgraad", clearable=False, style={"width": "240px", "marginBottom": "8px"}),
        html.Label(["peilgebied: ", html.Span("?", title="Selecteer peilgebied", style={"cursor": "help"})], style={"fontSize": "13px"}),
        dcc.Dropdown(id="pgb-dropdown", options=location_options, placeholder="Selecteer peilgebied", clearable=True, style={"width": "240px"}),
    ], style={"position":"absolute","top":"10px","left":"10px","zIndex":1002,"background":"rgba(220,240,255,1)","borderRadius":"8px","padding":"10px"}),

    # Kaart
    dl.Map(center=[(lat_sw+lat_ne)/2,(lon_sw+lon_ne)/2], bounds=leaflet_bounds, style={"height":"100vh","width":"100%"}, preferCanvas=True, children=[
        dl.TileLayer(), 
        dl.LayerGroup(id="marker-mpn"),
        dl.GeoJSON(id="geojson-pgb", data=geojson_data, hideout=initial_stylemap,
                   options={"style":style_handle,"interactive":True,"bubblingMouseEvents":True},
                   hoverStyle={"weight":2,"color":SELECTIE_KLEUR,"dashArray":""},
                   children=[dl.Tooltip(id="geojson-tooltip")],
                   eventHandlers={"click": assign("function(e){return e?.target?.feature?.properties||{};}")}
        )
    ]),

    # Grote grafiekpaneel (laadspinner alleen om deze grafiek)
    html.Div([
        dcc.Loading(
            id="graph-loading",
            type="circle",
            color="#e7e427",
            children=[
                dcc.Graph(
                    id="combined-graph",
                    config={"displayModeBar":True, "scrollZoom":True},
                    style={"height": "100%", "minHeight": 0}
                )
            ]
        )
    ], style=def_layout),

    # Mini-tijdserie + tijdslider (los van grote grafiek)
    html.Div([
        dcc.Store(id="is-playing", data=False), 
        html.Button(id="playpause-button", n_clicks=0, style={"width":"72px"}),
        html.Div(initial_label, id="datum-label", style={"fontWeight":"bold"}),
        html.Div([
            dcc.Graph(id="mini-tijdserie", config={"displayModeBar":False},
                style={"height":"50px","width":"350px","position":"absolute","top":0,"left":"25px","pointerEvents":"none"}),
            dcc.Slider(id="tijdslider", min=0, max=len(all_datetimes)-1, value=default_index, updatemode="mouseup")
        ], style={"position":"relative","width":"400px","height":"50px","display":"inline-block"})
    ], style={"position":"absolute","bottom":"10px","left":"10px","background":"rgba(255,255,255,0.9)","padding":"8px","borderRadius":"6px","zIndex":1000,"display":"flex","gap":"10px","alignItems":"center"}),
    dcc.Interval(id="interval", interval=1000, disabled=True), 
    html.Div(id="click-output")
])

# ============= CALLBACKS =============

@lru_cache(maxsize=128)
def get_kaartdata_for_datetime(dt, kaartvariabele):
    dt = pd.Timestamp(dt)
    arrow_dt = pa.scalar(dt)
    if kaartvariabele == "vullingsgraad":
        tb = ds_vg.to_table(filter=(ds.field('datetime')==arrow_dt), columns=["location_id","value"])         
        kleur_fn = kleur_bij_vullingsgraad
    else:
        tb = ds_vul.to_table(filter=(ds.field('datetime')==arrow_dt), columns=["location_id","value"])         
        kleur_fn = kleur_bij_vulling
    ids = tb["location_id"].to_pylist(); vals = tb["value"].to_pylist()
    return {loc:{"fillColor":kleur_fn(val),"color":"#666","weight":0.3,"fillOpacity":1, kaartvariabele:val} for loc,val in zip(ids,vals)}

@app.callback(
    Output("geojson-pgb","hideout"), Output("datum-label","children"), Output("geojson-pgb","options"),
    Input("tijdslider","value"), Input("pgb-dropdown","value"), Input("kaartvariabele-dropdown","value"),
    prevent_initial_call=True
)
def update_stylemap(idx, sel, var):
    try:
        if idx is None or int(idx) not in datum_to_index or not sel or not var:
            raise PreventUpdate
        dt = datum_to_index[int(idx)]
        stylemap = get_kaartdata_for_datetime(dt, var)
        label = dt.strftime("%Y-%m-%d %H:%M")
        options = {"style":style_handle,"selected":sel,"interactive":True,"bubblingMouseEvents":True}
        return stylemap, label, options
    except PreventUpdate:
        raise
    except Exception as e:
        print(f"[ERROR] update_stylemap: {e}", file=sys.stderr)
        raise PreventUpdate

@app.callback(Output("pgb-dropdown","value"), Input("geojson-pgb","clickData"), prevent_initial_call=True)
def select_dropdown_on_click(clickData): return clickData["properties"]["location_id"]

@app.callback(
    Output("geojson-tooltip","children"), Input("geojson-pgb","hoverData"), State("tijdslider","value"), State("kaartvariabele-dropdown","value"),
    prevent_initial_call=True
)
def update_tooltip(feature, idx, var):
    if not feature: return ""
    props=feature["properties"]; code, naam = props.get("location_id"), props.get("naam")
    dt=datum_to_index[int(idx)]; style=get_kaartdata_for_datetime(dt,var)
    val=style.get(code,{}).get(var)
    txt = f"{val:.1f}%" if val is not None else "n.b."
    return f"naam: {naam} (code: {code}) — {txt}"

# ==== Grote grafiek ====
@app.callback(
    Output("combined-graph", "figure"),
    [Input("pgb-dropdown", "value"),
     Input("kaartvariabele-dropdown", "value"),
     Input("selected-mpn-id", "data")],
    prevent_initial_call=True
)
@timed_callback
def update_combined_graph(sel, var, selected_mpn_id):
    if not sel: raise PreventUpdate
    ckey = f"combined_{sel}_{var}"
    base_fig = cache.get(ckey)
    if base_fig is None:
        # vullingsgraad & vulling data
        tb=ds_vg.to_table(filter=(ds.field('location_id')==sel), columns=["datetime","value"])
        df_vg=pd.DataFrame({"datetime":pd.to_datetime(tb['datetime'].to_pylist()),"vullingsgraad":tb['value'].to_pylist()})
        tb=ds_vul.to_table(filter=(ds.field('location_id')==sel), columns=["datetime","value"])
        df_vul=pd.DataFrame({"datetime":pd.to_datetime(tb['datetime'].to_pylist()),"vulling":tb['value'].to_pylist()})
        tb=ds_wlvl_pgb.to_table(filter=(ds.field('location_id')==sel), columns=["datetime","value"])
        df_pgb=pd.DataFrame({"datetime":pd.to_datetime(tb['datetime'].to_pylist()),"waarde":tb['value'].to_pylist()})
        mpn_ids=df_locs_mpn.loc[df_locs_mpn['peilgebied_combi_attr']==sel,'location_id'].tolist()
        tb_all=ds_wlvl_mpn.to_table(filter=ds.field('location_id').isin(mpn_ids), columns=["location_id","datetime","value"]).to_pandas()
        tb_all['datetime']=pd.to_datetime(tb_all['datetime'])
        base_fig=make_subplots(rows=3,cols=1,shared_xaxes=True,vertical_spacing=0.06,subplot_titles=["Vullingsgraad [%]","Vulling [mm]","Waterstand [mNAP]"])
        base_fig.add_trace(go.Scatter(x=df_vg.datetime,y=df_vg.vullingsgraad, line=dict(color='blue',width=1),showlegend=False),row=1,col=1)
        for y0,y1,colc in [(0,25,'rgba(120,200,120,0.4)'),(25,50,'rgba(255,255,100,0.4)'),(50,75,'rgba(255,200,100,0.4)'),(75,100,'rgba(255,100,100,0.4)')]:
            base_fig.add_shape(type='rect',xref='x1',yref='y1', x0=df_vg.datetime.min(),x1=df_vg.datetime.max(),y0=y0,y1=y1,fillcolor=colc,line_width=0,layer='below',row=1,col=1)
        base_fig.add_trace(go.Scatter(x=df_vul.datetime,y=df_vul.vulling, line=dict(color='royalblue',width=1),showlegend=False),row=2,col=1)
        for y0,y1,colc in [(0,10,'#ffffff'),(10,20,'#b4d3e7'),(20,30,'#72b2d7'),(30,40,'#3e91c4'),(40,60,'#1c5fa5')]:
            base_fig.add_shape(type='rect',xref='x2',yref='y2', x0=df_vul.datetime.min(),x1=df_vul.datetime.max(),y0=y0,y1=y1,fillcolor=colc,line_width=0,layer='below',row=2,col=1)
        for mid, grp in tb_all.groupby('location_id'):
            naam = df_locs_mpn.loc[df_locs_mpn.location_id==mid,'naam'].iat[0]
            base_fig.add_trace(go.Scattergl(
                x=grp.datetime,
                y=grp.value/1000,
                mode='lines',
                line=dict(color='grey', width=1),
                opacity=0.7,
                customdata=[[mid]]*len(grp),
                hovertemplate=f'datum: %{{x|%Y-%m-%d %H:%M}}<br>waarde: %{{y:.3f}}<br>naam: {naam}<extra></extra>',
                showlegend=False
            ), row=3, col=1)
        if not df_pgb.empty:
            base_fig.add_trace(
                go.Scattergl(
                    x=df_pgb.datetime, y=df_pgb.waarde/1000,
                    mode='lines',
                    line=dict(color='royalblue', width=1),
                    hovertemplate='datum: %{x|%Y-%m-%d %H:%M}<br>waarde: %{y:.3f}<br>naam: Peilgebied<extra></extra>',
                    showlegend=False
                ), row=3, col=1
            )
        base_fig.update_yaxes(range=[0,100], fixedrange=True, row=1, col=1)
        base_fig.update_yaxes(range=[0,60], fixedrange=True, row=2, col=1)
        base_fig.update_yaxes(fixedrange=True, row=3, col=1)
        base_fig.update_xaxes(title_text='Tijd', row=3, col=1)
        base_fig.update_layout(
            height=900,
            margin=dict(l=40, r=10, t=60, b=40),
            plot_bgcolor='white',
            hovermode='closest',
            font=dict(size=13),
            showlegend=False
        )
        cache.set(ckey, base_fig)
    fig = deepcopy(base_fig)
    if selected_mpn_id:
        idx_trace = None
        for i, trace in enumerate(fig.data):
            cd = getattr(trace, "customdata", None)
            if cd and len(cd) > 0 and cd[0][0] == selected_mpn_id:
                idx_trace = i
                break
        if idx_trace is not None:
            sel_trace = fig.data[idx_trace]
            fig.add_trace(go.Scattergl(
                x=sel_trace.x,
                y=sel_trace.y,
                mode=sel_trace.mode,
                line=dict(color=SELECTIE_KLEUR, width=2),
                opacity=1,
                customdata=sel_trace.customdata,
                hovertemplate=sel_trace.hovertemplate,
                showlegend=False
            ), row=3, col=1)
    return fig

# ==== Mini tijdserie, los ====
@app.callback(
    Output("mini-tijdserie", "figure"),
    [Input("pgb-dropdown", "value"),
     Input("kaartvariabele-dropdown", "value"),
     Input("tijdslider", "value")]
)
def update_mini_tijdserie(sel, var, idx):
    if not sel:
        raise PreventUpdate
    mkey = f"mini_{sel}_{var}"
    mini = cache.get(mkey)
    if mini is None:
        ds_sel = ds_vg if var == 'vullingsgraad' else ds_vul
        tb = ds_sel.to_table(filter=(ds.field('location_id') == sel), columns=['datetime', 'value'])
        series = pd.Series(tb['value'].to_pylist(), index=pd.to_datetime(tb['datetime'].to_pylist()))
        vals = [series.get(pd.Timestamp(dt), None) for dt in all_datetimes]
        mini = go.Figure(go.Scatter(
            x=list(range(len(all_datetimes))),
            y=vals,
            mode='lines',
            line=dict(width=2),
            hoverinfo='skip',
            showlegend=False
        ))
        cache.set(mkey, mini)
    fig = deepcopy(mini)
    idx0 = int(idx)
    fig.add_vline(x=idx0, line_width=2, line_dash='dash')
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=50,
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False, range=[0, len(all_datetimes)-1], fixedrange=True),
        yaxis=dict(visible=False, fixedrange=True)
    )
    return fig

# Callback voor selectie van lijn in de onderste grafiek (Waterstand) én klik op marker
@app.callback(
    Output("selected-mpn-id", "data"),
    [
        Input("pgb-dropdown", "value"),
        Input("combined-graph", "clickData"),
        Input({"type": "mpn-marker", "index": ALL}, "n_clicks")
    ],
    State("selected-mpn-id", "data"),
    prevent_initial_call=True
)
def set_or_reset_selected_mpn(pgb_val, clickData, marker_clicks, prev_sel):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    trigger = ctx.triggered[0]['prop_id']

    if trigger == "pgb-dropdown.value":
        # Wissel van peilgebied -> altijd deselecteren!
        return None

    # Klik uit grafiek
    if trigger.startswith("combined-graph.clickData"):
        if clickData and "points" in clickData:
            pt = clickData["points"][0]
            customdata = pt.get("customdata")
            if customdata:
                mid = customdata[0]
                # Toggle: opnieuw klikken deselecteert
                if prev_sel == mid:
                    return None
                return mid
        return prev_sel

    # Klik uit marker
    elif "mpn-marker" in trigger:
        import json
        id_part = trigger.split('.')[0]
        marker_id = json.loads(id_part)["index"]
        if prev_sel == marker_id:
            return None
        return marker_id

    raise PreventUpdate

@app.callback(
    Output("marker-mpn", "children"),
    Input("pgb-dropdown", "value"),
    Input("selected-mpn-id", "data"),
)
def update_mpn_markers(selected_location_id, selected_mpn_id):
    if not selected_location_id:
        return []
    points = df_locs_mpn[df_locs_mpn["peilgebied_combi_attr"] == selected_location_id]
    markers = []
    for _, row in points.iterrows():
        lon, lat = transformer.transform(row["x"], row["y"])
        icon = None
        if selected_mpn_id and row["location_id"] == selected_mpn_id:
            icon = {
                "iconUrl": "https://cdn.jsdelivr.net/gh/pointhi/leaflet-color-markers@master/img/marker-icon-yellow.png",
                "iconSize": [35, 56],
                "iconAnchor": [17, 55],
                "popupAnchor": [1, -34],
                "shadowUrl": "https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png",
                "shadowSize": [41, 41]
            }
        markers.append(
            dl.Marker(
                position=[lat, lon],
                icon=icon,
                id={"type": "mpn-marker", "index": row["location_id"]},
                n_clicks=0,
                children=[
                    dl.Tooltip(row["naam"])
                ]
            )
        )
    return markers

@app.callback(Output("playpause-button","children"), Input("is-playing","data"))
def set_playpause(is_playing): return "⏸️ Pause" if is_playing else "▶️ Play"

@app.callback(Output("is-playing","data"), Input("playpause-button","n_clicks"), State("is-playing","data"), prevent_initial_call=True)
def toggle_playpause(n,playing): return not playing if n else playing

@app.callback(Output("interval","disabled"), Input("is-playing","data"))
def toggle_interval(playing): return not playing

@app.callback(Output("tijdslider","value"), Input("interval","n_intervals"), State("interval","disabled"), State("tijdslider","value"))
def advance_slider(n,disabled,current):
    if disabled or current is None: raise PreventUpdate
    return (current+1)%len(all_datetimes)

if __name__ == "__main__":
    app.run(debug=True)
