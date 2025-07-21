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
import plotly.graph_objs as go

app = dash.Dash(__name__)

# ========== Geodata ==============
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

location_options = []
seen = set()
for opt in options:
    lbl = opt.get("label")
    val = opt.get("value")
    if lbl and val and val not in seen:
        seen.add(val)
        location_options.append({"label": f"{lbl} ({val})", "value": val})

ds_ = ds.dataset(
    "d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/vullingsgraad.arrow",
    format="feather"
)
full_df = ds_.to_table(columns=["datetime", "location_id", "value"]).to_pandas()
full_df["datetime"] = pd.to_datetime(full_df["datetime"])

unique_datetimes = sorted(full_df["datetime"].dt.floor("min").unique())
datum_to_index = {i: pd.Timestamp(dt) for i, dt in enumerate(unique_datetimes)}

def kleur_bij_vullingsgraad(val):
    if pd.isna(val):
        return "gray"
    if val < 25:   return "green"
    if val < 50:   return "yellow"
    if val < 75:   return "orange"
    return "red"

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

for dt in unique_datetimes[:20]:
    build_stylemap_for_datetime(pd.Timestamp(dt))

default_index = 0
default_dt = datum_to_index[default_index]
initial_stylemap = build_stylemap_for_datetime(default_dt)
initial_label = default_dt.strftime("%Y-%m-%d %H:%M")

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

kaartvariabelen = [
    {"label": "vullingsgraad [%]", "value": "vullingsgraad"},
]

# ============ LAYOUT ==============
app.layout = html.Div([
    # LINKSBOVEN
    html.Div([
        html.Label([
            "kaartvariabele: ",
            html.Span("?", title="Welke variabele wil je op de kaart tonen?", style={"cursor": "help"})
        ], style={"fontSize": "13px"}),
        dcc.Dropdown(
            id="kaartvariabele-dropdown",
            options=kaartvariabelen,
            value="vullingsgraad",
            clearable=False,
            style={"width": "240px", "marginBottom": "8px"},
        ),
        html.Label([
            "peilgebied: ",
            html.Span("?", title="Selecteer een peilgebied", style={"cursor": "help"})
        ], style={"fontSize": "13px"}),
        dcc.Dropdown(
            id="pgb-dropdown",
            options=location_options,
            placeholder="Selecteer peilgebied",
            clearable=True,
            style={"width": "240px"},
        ),
    ], style={
        "position": "absolute", "top": "10px", "left": "10px", "zIndex": 1002,
        "background": "rgba(220,240,255,1)", "borderRadius": "8px", "padding": "10px"
    }),

    # KAART
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

    # GRAFIEK RECHTSBOVEN
    html.Div(
        dcc.Graph(id="vullingsgraad-grafiek", config={"displayModeBar": False}),
        style={
            "position": "absolute",
            "top": "10px",
            "right": "10px",
            "width": "480px",
            "height": "320px",
            "background": "white",
            "borderRadius": "5px",
            "zIndex": 1100,
            "boxShadow": "0 2px 8px rgba(0,0,0,0.05)",
            "padding": "10px"
        }
    ),

    # HOVER-INFO LINKSONDER (optioneel)
    html.Div(id="hover-info", style={
        "position": "absolute", "bottom": "10px", "left": "10px",
        "background": "white", "padding": "5px", "borderRadius": "5px", "zIndex": 1001
    }),

    # BEDIENINGSBALK ONDERIN
    html.Div([
        dcc.Store(id="is-playing", data=False),
        html.Button(id="playpause-button", n_clicks=0, style={"width": "72px"}),
        html.Div(initial_label, id="datum-label", style={
            "whiteSpace": "nowrap", "fontWeight": "bold", "marginLeft": "0px", "marginRight": "0px"
        }),
        html.Div([
            dcc.Graph(
                id="mini-tijdserie",
                config={"displayModeBar": False},
                style={
                    "height": "50px",
                    "width": "350px",   
                    "position": "absolute",
                    "top": 0,
                    "left": "25px",    
                    "zIndex": 0,
                    "pointerEvents": "none"
                }
            ),
            dcc.Slider(
                id="tijdslider",
                min=0, max=len(unique_datetimes) - 1, step=1,
                value=default_index,
                updatemode="mouseup",
                included=True,
                tooltip={"placement": "bottom", "always_visible": False},
                marks=None
            ),
        ], style={
            "position": "relative",
            "width": "400px",
            "height": "50px",
            "padding": "0px",
            "margin": "0px",
            "display": "inline-block"
        }),
    ], style={
        "position": "absolute", "bottom": "10px", "left": "10px",
        "background": "rgba(255,255,255,0.9)", "padding": "8px",
        "borderRadius": "6px", "zIndex": 1000,
        "display": "flex", "alignItems": "center", "gap": "10px"
    }),

    dcc.Interval(id="interval", interval=1000, disabled=True),

    html.Div(id="click-output", style={
        "position": "absolute", "top": "50px", "right": "10px", "zIndex": 1001,
        "background": "white", "padding": "5px", "borderRadius": "5px"
    }),
])

# ============= CALLBACKS =============

@app.callback(
    Output("playpause-button", "children"),
    Input("is-playing", "data"),
)
def set_playpause_button(is_playing):
    return "⏸️ Pause" if is_playing else "▶️ Play"

@app.callback(
    Output("is-playing", "data"),
    Input("playpause-button", "n_clicks"),
    State("is-playing", "data"),
    prevent_initial_call=True,
)
def toggle_playpause(n_clicks, is_playing):
    return not is_playing if n_clicks else is_playing

@app.callback(
    Output("interval", "disabled"),
    Input("is-playing", "data"),
)
def toggle_interval(is_playing):
    return not is_playing

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

@app.callback(
    Output("pgb-dropdown", "value"),
    Input("geojson-pgb", "clickData")
)
def select_dropdown_on_click(clickData):
    if not clickData or "properties" not in clickData:
        raise PreventUpdate
    return clickData["properties"]["location_id"]

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

@app.callback(
    Output("vullingsgraad-grafiek", "figure"),
    Input("pgb-dropdown", "value"),
)
def update_vullingsgraad_figure(selected_location_id):
    vlakken = [
        dict(y0=0,   y1=25,  color="rgba(120,200,120,0.4)"),
        dict(y0=25,  y1=50,  color="rgba(255,255,100,0.4)"),
        dict(y0=50,  y1=75,  color="rgba(255,200,100,0.4)"),
        dict(y0=75,  y1=100, color="rgba(255,100,100,0.4)"),
    ]
    if not selected_location_id:
        fig = go.Figure()
        for v in vlakken:
            fig.add_shape(
                type="rect", xref="paper", yref="y",
                x0=0, x1=1, y0=v['y0'], y1=v['y1'], fillcolor=v['color'], line_width=0, layer="below"
            )
        fig.update_layout(
            yaxis=dict(range=[0, 100], title="vullingsgraad [%]"),
            title="Selecteer een peilgebied voor de vullingsgraad",
            margin=dict(l=30, r=10, t=40, b=30), height=300
        )
        return fig

    df = full_df[full_df["location_id"] == selected_location_id]
    label = next((opt["label"] for opt in location_options if opt["value"] == selected_location_id), selected_location_id)
    fig = go.Figure()
    for v in vlakken:
        fig.add_shape(
            type="rect", xref="paper", yref="y",
            x0=0, x1=1, y0=v['y0'], y1=v['y1'], fillcolor=v['color'], line_width=0, layer="below"
        )
    fig.add_trace(
        go.Scatter(
            x=df["datetime"], y=df["value"],
            mode="lines+markers",
            name="Vullingsgraad",
            line=dict(color="blue", width=2),
            marker=dict(size=4),
        )
    )
    fig.update_layout(
        title=f"Vullingsgraad {label}",
        xaxis_title="Tijd",
        yaxis=dict(range=[0, 100], title="vullingsgraad [%]"),
        margin=dict(l=30, r=10, t=40, b=30),
        height=300,
        plot_bgcolor="white"
    )
    return fig

@app.callback(
    Output("mini-tijdserie", "figure"),
    Input("pgb-dropdown", "value"),
    Input("kaartvariabele-dropdown", "value"),
    Input("tijdslider", "value"),
)
def update_mini_tijdserie(selected_location_id, kaartvariabele, slider_idx):
    # -- Key change: x-as is indices (0..len-1) ipv timestamps, perfect uitgelijnd met slider! --
    if kaartvariabele != "vullingsgraad" or not selected_location_id:
        fig = go.Figure()
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            height=50,
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(
                visible=False,
                range=[0, len(unique_datetimes) - 1],
                fixedrange=True,
                constrain="domain",
                automargin=False,
                showline=False,
                showgrid=False,
                zeroline=False,
                mirror=False,
            ),
            yaxis=dict(
                visible=False,
                range=[0, 100],
                fixedrange=True,
            ),
        )
        return fig

    try:
        idx = int(slider_idx)
        if not (0 <= idx < len(unique_datetimes)):
            raise ValueError
    except Exception:
        fig = go.Figure()
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            height=50,
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(
                visible=False,
                range=[0, len(unique_datetimes) - 1],
                fixedrange=True,
                constrain="domain",
                automargin=False,
                showline=False,
                showgrid=False,
                zeroline=False,
                mirror=False,
            ),
            yaxis=dict(
                visible=False,
                range=[0, 100],
                fixedrange=True,
            ),
        )
        return fig

    # Tijdserie ophalen
    sel_df = full_df[full_df["location_id"] == selected_location_id].copy()
    sel_df["datetime"] = sel_df["datetime"].dt.floor("min")
    serie = pd.Series(sel_df["value"].values, index=sel_df["datetime"])
    values = [serie.get(pd.Timestamp(dt), None) for dt in unique_datetimes]

    # Belangrijk: x = indexen, dus 0, 1, 2, ..., n-1
    fig = go.Figure(go.Scatter(
        x=list(range(len(unique_datetimes))),
        y=values,
        mode="lines",
        line=dict(color="royalblue", width=2),
        hoverinfo="skip",
        showlegend=False,
    ))

    # Verticale marker
    fig.add_vline(x=idx, line_width=2, line_dash="dash", line_color="orange")

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=50,
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            visible=False,
            range=[0, len(unique_datetimes) - 1],
            fixedrange=True,
            constrain="domain",
            automargin=False,
            showline=False,
            showgrid=False,
            zeroline=False,
            mirror=False,
        ),
        yaxis=dict(
            visible=False,
            range=[0, 100],
            fixedrange=True,
        ),
    )
    return fig

if __name__ == "__main__":
    app.run(debug=True)
