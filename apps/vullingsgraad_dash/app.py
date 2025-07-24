# %%
import sys
import time
from functools import lru_cache, wraps

import dash
import dash_leaflet as dl
import pandas as pd
import plotly.graph_objs as go
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
from dash import Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate
from dash_extensions.javascript import assign
from flask_caching import Cache
from plotly.subplots import make_subplots
from read import read_mpn_locs, read_peilgebieden

app = dash.Dash(__name__)

# === caching
cache = Cache(
    app.server, config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 3600}
)

def timed_callback(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        result = f(*args, **kwargs)
        dt = time.perf_counter() - t0
        print(f"[TIMING] Callback {f.__name__} duurde {dt:.3f} s")
        return result

    return wrapper

def bounds_to_map(xmin, ymin, xmax, ymax):
    dx = xmax - xmin
    dy = ymax - ymin
    map_bounds = [[ymin, xmin], [ymax, xmin + 2 * dx]]
    map_center = [ymin + dy / 2, xmax + dx / 2]
    return map_bounds, map_center

# ========== Geodata laden ==============
timer_start = time.time()

# inlezen peilgebieden (GeoJSON) Locatie opties (DataFrame) en map bounds (numpy array) uit peilgebieden
geojson_data, location_options, bounds = read_peilgebieden(
    file_path="d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/peilgebieden_cso_combi.shp",
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
        "fillOpacity": 0.3,
    },
)

# transformmeren van bounds uit peilgebieden naar map bounds en centrum
map_bounds, map_center = bounds_to_map(*bounds)

print("TIJD: shapefile/geodata ingelezen in", round(time.time() - timer_start, 2), "s")

# ===== Laad Arrow tijdseries, bepaal tijdas =====
ds_vg = ds.dataset(
    "d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/vullingsgraad.arrow",
    format="feather",
)
ds_vul = ds.dataset(
    "d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/vulling.arrow",
    format="feather",
)
df_locs_mpn = read_mpn_locs(
    "d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/mpn_locations.arrow"
)
ds_wlvl_mpn = ds.dataset(
    "d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/waterstand_meetpunt.arrow",
    format="feather",
)
ds_wlvl_pgb = ds.dataset(
    "d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/waterstand_pgb.arrow",
    format="feather",
)

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

# ========== Kleurfuncties ==========
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

def kleur_bij_vulling(val):
    if pd.isna(val):
        return "gray"
    if val < 10:
        return "#eff3ff"
    if val < 20:
        return "#bdd7e7"
    if val < 30:
        return "#6baed6"
    if val < 40:
        return "#3182bd"
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

def_layout = {
    "position": "absolute",
    "top": "10px",
    "right": "10px",
    "bottom": "10px",
    "width": "50%",
    "height": "calc(100vh - 32px)",
    "background": "white",
    "borderRadius": "5px",
    "zIndex": 1100,
    "boxShadow": "0 2px 8px rgba(0,0,0,0.05)",
    "padding": "10px",
    "display": "flex",
    "flexDirection": "column",
    "gap": "10px",
    "minHeight": 0,
}

# ===== Standaardkeuzes bij opstarten =====
default_index = 0  # eerste tijdstap
default_dt = datum_to_index[default_index]
default_pgb = location_options[0]["value"] if location_options else None
initial_label = default_dt.strftime("%Y-%m-%d %H:%M")
initial_kaartvariabele = "vullingsgraad"

@lru_cache(maxsize=128)
def get_kaartdata_for_datetime(dt, kaartvariabele):
    dt = pd.Timestamp(dt)
    arrow_dt = pa.scalar(dt)
    if kaartvariabele == "vullingsgraad":
        tb = ds_vg.to_table(
            filter=(ds.field("datetime") == arrow_dt), columns=["location_id", "value"]
        )
        kleur_fn = kleur_bij_vullingsgraad
    else:
        tb = ds_vul.to_table(
            filter=(ds.field("datetime") == arrow_dt), columns=["location_id", "value"]
        )
        kleur_fn = kleur_bij_vulling
    ids = tb["location_id"].to_pylist()
    vals = tb["value"].to_pylist()
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

# ========== Layout ==========
app.layout = html.Div(
    [
        html.Div(
            [
                html.Label(
                    [
                        "kaartvariabele: ",
                        html.Span(
                            "?", title="Welke variabele...", style={"cursor": "help"}
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
                            "?", title="Selecteer peilgebied", style={"cursor": "help"}
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
            },
        ),
        dl.Map(
            center=map_center,
            zoom=10,
            bounds=map_bounds,
            style={"height": "100vh", "width": "100%"},
            preferCanvas=True,
            children=[
                dl.TileLayer(),
                dl.LayerGroup(id="marker-mpn"),
                dl.GeoJSON(
                    id="geojson-pgb",
                    data=geojson_data,
                    hideout=initial_stylemap,
                    options=initial_options,
                    hoverStyle={"weight": 2, "color": "yellow", "dashArray": ""},
                    children=[dl.Tooltip(id="geojson-tooltip")],
                    eventHandlers={
                        "click": assign(
                            "function(e){return e?.target?.feature?.properties||{};}"
                        )
                    },
                ),
            ],
        ),
        html.Div(
            [
                dcc.Loading(
                    id="graph-loading",
                    type="circle",
                    children=[
                        dcc.Graph(
                            id="combined-graph",
                            config={"displayModeBar": True, "scrollZoom": True},
                            style={"height": "100%", "minHeight": 0},
                        )
                    ],
                    color="#e7e427",
                    fullscreen=False,
                )
            ],
            style=def_layout,
        ),
        # MINI-TIJDSERIE LOS, BUITEN DE LOADER:
        html.Div(
            [
                dcc.Store(id="is-playing", data=False),
                html.Button(id="playpause-button", n_clicks=0, style={"width": "72px"}),
                html.Div(initial_label, id="datum-label", style={"fontWeight": "bold"}),
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
            },
        ),
        dcc.Interval(id="interval", interval=1000, disabled=True),
        html.Div(id="click-output"),
    ]
)

# ============= CALLBACKS =============
@lru_cache(maxsize=128)
def get_kaartdata_for_datetime(dt, kaartvariabele):
    dt = pd.Timestamp(dt)
    arrow_dt = pa.scalar(dt)
    if kaartvariabele == "vullingsgraad":
        tb = ds_vg.to_table(
            filter=(ds.field("datetime") == arrow_dt), columns=["location_id", "value"]
        )
        kleur_fn = kleur_bij_vullingsgraad
    else:
        tb = ds_vul.to_table(
            filter=(ds.field("datetime") == arrow_dt), columns=["location_id", "value"]
        )
        kleur_fn = kleur_bij_vulling
    ids = tb["location_id"].to_pylist()
    vals = tb["value"].to_pylist()
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
    try:
        if idx is None or int(idx) not in datum_to_index or not sel or not var:
            raise PreventUpdate
        dt = datum_to_index[int(idx)]
        stylemap = get_kaartdata_for_datetime(dt, var)
        label = dt.strftime("%Y-%m-%d %H:%M")
        options = {
            "style": style_handle,
            "selected": sel,
            "interactive": True,
            "bubblingMouseEvents": True,
        }
        return stylemap, label, options
    except PreventUpdate:
        raise
    except Exception as e:
        print(f"[ERROR] update_stylemap: {e}", file=sys.stderr)
        raise PreventUpdate

@app.callback(
    Output("pgb-dropdown", "value"),
    Input("geojson-pgb", "clickData"),
    prevent_initial_call=True,
)
def select_dropdown_on_click(clickData):
    return clickData["properties"]["location_id"]

@app.callback(
    Output("geojson-tooltip", "children"),
    Input("geojson-pgb", "hoverData"),
    State("tijdslider", "value"),
    State("kaartvariabele-dropdown", "value"),
    prevent_initial_call=True,
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

# ========= Grote grafiek los, mini los =========
@app.callback(
    Output("combined-graph", "figure"),
    [
        Input("pgb-dropdown", "value"),
        Input("kaartvariabele-dropdown", "value"),
    ],
)
@timed_callback
def update_combined_graph(sel, var):
    if not sel:
        raise PreventUpdate
    ckey = f"combined_{sel}"
    fig = cache.get(ckey)
    if fig is None:
        # vullingsgraad & vulling data
        tb = ds_vg.to_table(
            filter=(ds.field("location_id") == sel), columns=["datetime", "value"]
        )
        df_vg = pd.DataFrame(
            {
                "datetime": pd.to_datetime(tb["datetime"].to_pylist()),
                "vullingsgraad": tb["value"].to_pylist(),
            }
        )
        tb = ds_vul.to_table(
            filter=(ds.field("location_id") == sel), columns=["datetime", "value"]
        )
        df_vul = pd.DataFrame(
            {
                "datetime": pd.to_datetime(tb["datetime"].to_pylist()),
                "vulling": tb["value"].to_pylist(),
            }
        )
        tb = ds_wlvl_pgb.to_table(
            filter=(ds.field("location_id") == sel), columns=["datetime", "value"]
        )
        df_pgb = pd.DataFrame(
            {
                "datetime": pd.to_datetime(tb["datetime"].to_pylist()),
                "waarde": tb["value"].to_pylist(),
            }
        )
        # meetpunt data
        mpn_ids = df_locs_mpn.loc[
            df_locs_mpn["peilgebied_combi_attr"] == sel, "location_id"
        ].tolist()
        tb_all = ds_wlvl_mpn.to_table(
            filter=ds.field("location_id").isin(mpn_ids),
            columns=["location_id", "datetime", "value"],
        ).to_pandas()
        tb_all["datetime"] = pd.to_datetime(tb_all["datetime"])
        fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.06,
            subplot_titles=["Vullingsgraad [%]", "Vulling [mm]", "Waterstand [mNAP]"],
        )
        # tekens
        fig.add_trace(
            go.Scatter(
                x=df_vg.datetime,
                y=df_vg.vullingsgraad,
                line=dict(color="blue", width=2),
                showlegend=False,
            ),
            row=1,
            col=1,
        )
        for y0, y1, colc in [
            (0, 25, "rgba(120,200,120,0.4)"),
            (25, 50, "rgba(255,255,100,0.4)"),
            (50, 75, "rgba(255,200,100,0.4)"),
            (75, 100, "rgba(255,100,100,0.4)"),
        ]:
            fig.add_shape(
                type="rect",
                xref="x1",
                yref="y1",
                x0=df_vg.datetime.min(),
                x1=df_vg.datetime.max(),
                y0=y0,
                y1=y1,
                fillcolor=colc,
                line_width=0,
                layer="below",
                row=1,
                col=1,
            )
        fig.add_trace(
            go.Scatter(
                x=df_vul.datetime,
                y=df_vul.vulling,
                line=dict(color="royalblue", width=2),
                showlegend=False,
            ),
            row=2,
            col=1,
        )
        for y0, y1, colc in [
            (0, 10, "#ffffff"),
            (10, 20, "#b4d3e7"),
            (20, 30, "#72b2d7"),
            (30, 40, "#3e91c4"),
            (40, 60, "#1c5fa5"),
        ]:
            fig.add_shape(
                type="rect",
                xref="x2",
                yref="y2",
                x0=df_vul.datetime.min(),
                x1=df_vul.datetime.max(),
                y0=y0,
                y1=y1,
                fillcolor=colc,
                line_width=0,
                layer="below",
                row=2,
                col=1,
            )
        for mid, grp in tb_all.groupby("location_id"):
            naam = df_locs_mpn.loc[df_locs_mpn.location_id == mid, "naam"].iat[0]
            fig.add_trace(
                go.Scatter(
                    x=grp.datetime,
                    y=grp.value / 1000,
                    mode="lines",
                    line=dict(color="grey", width=1),
                    opacity=0.7,
                    hovertemplate="datum: %{x|%Y-%m-%d %H:%M}<br>waarde: %{y:.3f}<br>naam: "
                    + naam
                    + "<extra></extra>",
                    showlegend=False,
                ),
                row=3,
                col=1,
            )
        if not df_pgb.empty:
            fig.add_trace(
                go.Scatter(
                    x=df_pgb.datetime,
                    y=df_pgb.waarde / 1000,
                    mode="lines",
                    line=dict(color="royalblue", width=3),
                    hovertemplate="datum: %{x|%Y-%m-%d %H:%M}<br>waarde: %{y:.3f}<br>naam: Peilgebied<extra></extra>",
                    showlegend=False,
                ),
                row=3,
                col=1,
            )
        # ==== STREEFPEIL TOEVOEGEN ====
        # Zoek streefpeil op in geojson_data
        streefpeil = None
        for feat in geojson_data["features"]:
            if feat["properties"].get("location_id") == sel:
                streefpeil = feat["properties"].get("streefpeil")
                break
        # Voeg streefpeil-lijn toe als laatste trace, label aan de linkerkant
        if streefpeil is not None and pd.notnull(streefpeil):
            if not df_pgb.empty:
                x_vals = list(df_pgb["datetime"])
            else:
                x_vals = list(tb_all["datetime"].unique())
                x_vals.sort()
            if x_vals:
                y_val = streefpeil / 1000
                fig.add_trace(
                    go.Scatter(
                        x=x_vals,
                        y=[y_val] * len(x_vals),
                        mode="lines",
                        line=dict(dash="dash", color="orange", width=2),
                        name="Streefpeil",
                        hoverinfo="text",
                        hovertext=[f"Streefpeil: {y_val:.2f} mNAP"] * len(x_vals),
                        showlegend=False,
                    ),
                    row=3,
                    col=1,
                )
                fig.add_annotation(
                    x=x_vals[0],
                    y=y_val,
                    xref="x3",
                    yref="y3",
                    text="streefpeil",
                    font=dict(color="orange", size=13),
                    showarrow=False,
                    xanchor="left",
                    yanchor="bottom",
                    align="left",
                    bgcolor="rgba(255,255,255,0.7)",
                    borderpad=2,
                )
        fig.update_yaxes(range=[0, 100], fixedrange=True, row=1, col=1)
        fig.update_yaxes(range=[0, 60], fixedrange=True, row=2, col=1)
        fig.update_yaxes(fixedrange=True, row=3, col=1)
        fig.update_xaxes(title_text="Tijd", row=3, col=1)
        fig.update_layout(
            height=900,
            margin=dict(l=40, r=10, t=60, b=40),
            plot_bgcolor="white",
            hovermode="closest",
            font=dict(size=13),
            showlegend=False,
        )
        cache.set(ckey, fig)
        print(f"CACHE MISS combined for {sel}")
    else:
        print(f"CACHE HIT combined for {sel}")
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
    if not sel:
        raise PreventUpdate
    mkey = f"mini_{sel}_{var}"
    mini = cache.get(mkey)
    ds_sel = ds_vg if var == "vullingsgraad" else ds_vul
    tb = ds_sel.to_table(
        filter=(ds.field("location_id") == sel), columns=["datetime", "value"]
    )
    series = pd.Series(
        tb["value"].to_pylist(), index=pd.to_datetime(tb["datetime"].to_pylist())
    )
    vals = [series.get(pd.Timestamp(dt), None) for dt in all_datetimes]
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
    mini.add_vline(x=idx0, line_width=2, line_dash="dash")
    mini.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=50,
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False, range=[0, len(all_datetimes) - 1], fixedrange=True),
        yaxis=dict(visible=False, fixedrange=True),
    )
    return mini

@app.callback(Output("playpause-button", "children"), Input("is-playing", "data"))
def set_playpause(is_playing):
    return "⏸️ Pause" if is_playing else "▶️ Play"

@app.callback(
    Output("is-playing", "data"),
    Input("playpause-button", "n_clicks"),
    State("is-playing", "data"),
    prevent_initial_call=True,
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
    State("tijdslider", "value"),
)
def advance_slider(n, disabled, current):
    if disabled or current is None:
        raise PreventUpdate
    return (current + 1) % len(all_datetimes)

@app.callback(
    Output("marker-mpn", "children"),
    Input("pgb-dropdown", "value"),
)
def update_mpn_markers(selected_location_id):
    if not selected_location_id:
        return []
    points = df_locs_mpn[df_locs_mpn["peilgebied_combi_attr"] == selected_location_id]
    markers = [
        dl.Marker(
            position=[i.geometry.y, i.geometry.x],
            children=[dl.Tooltip(i.naam), dl.Popup(f"{i.naam} ({i.location_id})")],
        )
        for i in points.itertuples()
    ]
    return markers

if __name__ == "__main__":
    app.run(debug=True)
