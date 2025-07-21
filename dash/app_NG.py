#%%
import json, pathlib 
import dash
from dash_extensions.enrich import DashProxy, Output, Input, State, dcc, html
import dash_leaflet as dl
from dash_extensions.javascript import assign
from dash.exceptions import PreventUpdate
import pandas as pd
import pyarrow.feather as feather
from ribasim import Model

file_dir = pathlib.Path(__file__).parent
model_path = file_dir / "data/HollandsNoorderkwartier_parameterized_2025_6_8/ribasim.toml"
model = Model.read(model_path)

# ───────────────────────────────────────────────────────────────────────────────
# DATA
gdf_pumps = model.pump.node.df.copy().to_crs(epsg=4326).reset_index()
gdf_pumps["node_id"] = gdf_pumps["node_id"].astype(str)
gdf_pumps["name"] = gdf_pumps.get("name", gdf_pumps["node_id"])
if model.pump.static.df is not None and "flow_rate" in model.pump.static.df.columns:
    flow_df = model.pump.static.df[["node_id", "flow_rate"]].copy()
    flow_df["node_id"] = flow_df["node_id"].astype(str)
    flow_df["flow_rate"] = flow_df["flow_rate"].round(2)
    gdf_pumps = gdf_pumps.merge(flow_df, on="node_id", how="left")
else:
    gdf_pumps["flow_rate"] = pd.NA

gdf_basin_nodes = model.basin.node.df.copy().to_crs(epsg=4326).reset_index()
gdf_basin_nodes["node_id"] = gdf_basin_nodes["node_id"].astype(str)
gdf_basin_nodes["name"] = gdf_basin_nodes.get("name", gdf_basin_nodes["node_id"])

gdf_links = model.link.df.copy().to_crs(epsg=4326).reset_index()
gdf_links["meta_categorie"] = gdf_links.get("meta_categorie", pd.NA)
links_geojson = json.loads(gdf_links.to_json())

gdf_basin_area = model.basin.area.df.copy().to_crs(epsg=4326).reset_index()
gdf_basin_area["node_id"] = gdf_basin_area["node_id"].astype(str)
gdf_basin_area["name"] = gdf_basin_area.get("name", gdf_basin_area["node_id"])
if model.basin.static.df is not None and "meta_streefpeil" in model.basin.static.df.columns:
    meta_df = model.basin.static.df[["node_id", "meta_streefpeil"]].copy()
    meta_df["node_id"] = meta_df["node_id"].astype(str)
    gdf_basin_area = gdf_basin_area.merge(meta_df, on="node_id", how="left")

basin_area_geojson = json.loads(gdf_basin_area.to_json())
pumps_geojson = json.loads(gdf_pumps.to_json())
basin_nodes_geojson = json.loads(gdf_basin_nodes.to_json())

basin_style = assign("""
function(feature, ctx) {
    const precip = ctx.hideout.precip || {};
    const value = precip[feature.properties.node_id] || 0;
    let color = 'white';
    if (value > 10) color = '#08306b';
    else if (value > 5) color = '#2171b5';
    else if (value > 1) color = '#6baed6';
    else if (value > 0) color = '#c6dbef';
    return {fillColor: color, color: 'grey', weight: 1, fillOpacity: 0.8};
}
""")

pump_style = assign("""function(feature, ctx){ const sel = ctx.hideout.pumps || []; const z = ctx.hideout.zoom || 10; const scale = z < 9 ? 0.4 : z < 11 ? 0.7 : 1.0; const selected = sel.includes(feature.properties.node_id); const radius = selected ? 6 * scale : 4 * scale; const color = selected ? 'red' : 'green'; return {color: color, fillColor: color, radius: radius}; }""")
basin_node_style = assign("""
function(feature, ctx){
    const sel = ctx.hideout.basin_nodes || [];
    const z = ctx.hideout.zoom || 10;
    const scale = z < 9 ? 0.6 : z < 11 ? 0.9 : 1.2;
    const selected = sel.includes(feature.properties.node_id);
    const radius = selected ? 8 * scale : 6 * scale;
    const color = selected ? 'yellow' : 'blue';
    return {color: color, fillColor: color, radius: radius};
}
""")
link_style = assign("""function(feature, ctx)
    { const selected = ctx.hideout.selected_link === feature.properties.link_id; 
    const cat = feature.properties.meta_categorie || ""; 
    const color = selected ? "yellow" : (cat.toLowerCase() === "hoofdwater" ? "#003366" : "#66ccff"); const weight = selected ? 5 : (cat.toLowerCase() === "hoofdwater" ? 4 : 4); return {color: color, weight: weight}; }""")
# ───────────────────────────────────────────────────────────────────────────────
# RESULTAATDATA
arrow_path = file_dir / "data/HollandsNoorderkwartier_parameterized_2025_6_8/results/basin.arrow"
df_basin_result = feather.read_feather(arrow_path)
df_basin_result["node_id"] = df_basin_result["node_id"].astype(str)
df_basin_result["time"] = pd.to_datetime(df_basin_result["time"])

# Maak tijdserie voor visualisatie
unique_times = df_basin_result["time"].sort_values().unique()
precipitation_series = {
    str(t): df_basin_result[df_basin_result["time"] == t].set_index("node_id")["precipitation"].to_dict()
    for t in unique_times
}

flow_arrow_path = file_dir / "data/HollandsNoorderkwartier_parameterized_2025_6_8/results/flow.arrow"
df_link_result = feather.read_feather(flow_arrow_path)
df_link_result["link_id"] = df_link_result["link_id"].astype(int)
df_link_result["time"] = pd.to_datetime(df_link_result["time"])

# ───────────────────────────────────────────────────────────────────────────────
# LAYOUT
app = DashProxy()


app.layout = html.Div(style={"height": "95vh", "display": "flex", "flexDirection": "column"}, children=[
    html.Div(style={"flex": "1", "display": "flex", "flexDirection": "row"}, children=[
        html.Div(style={"flex": "1", "position": "relative"}, children=[
            dl.Map(id="map", center=[52.75, 4.9], 
                   zoom=10, style={"height": "100%"}, 
                   children=[
                dl.TileLayer(),

                # Pane met lage zIndex voor neerslag-laag
                dl.Pane(name="precipitationPane", style={"zIndex": 210}),
                dl.Pane(name="basinNodePane", style={"zIndex": 9999}),
                dl.Pane(name="linkPane", style={"zIndex": 220}),

                dl.GeoJSON(
                    id="geojson-basins",
                    data=basin_area_geojson,
                    hideout={"basins": []},
                    style=basin_style,
                    options={"interactive": False},
                    pane="precipitationPane"
                ),

                dl.GeoJSON(
                    id="geojson-links",
                    data=links_geojson,
                    style=link_style,
                    options={"interactive": True},
                    hideout={"selected_link": None},
                    pane="linkPane"
                ),

                dl.GeoJSON(
                    id="geojson-pumps",
                    data=pumps_geojson,
                    hideout={"pumps": [], "zoom": 10},
                    style=pump_style,
                    pointToLayer=assign("function(feature, latlng){return L.circleMarker(latlng,{fillOpacity:0.8});}"),
                    options={"interactive": True},
                ),

                dl.GeoJSON(
                    id="geojson-basin-nodes",
                    data=basin_nodes_geojson,
                    hideout={"basin_nodes": [], "zoom": 10},
                    style=basin_node_style,
                    pointToLayer=assign("function(feature, latlng){return L.circleMarker(latlng,{fillOpacity:0.8});}"),
                    options={"interactive": True},
                    pane="basinNodePane"
                ),
            ]),

            html.Div(style={"position": "absolute", "top": "10px", "left": "10px", "width": "320px", "background": "rgba(255,255,255,0.9)", "padding": "15px", "borderRadius": "6px", "boxShadow": "0 2px 8px rgba(0,0,0,0.3)", "zIndex": "1000"}, children=[
                html.H4("Selecteer Pompen"),
                dcc.Dropdown(id="pump-dropdown", options=[{"label": row["name"], "value": row["node_id"]} for _, row in gdf_pumps.iterrows()], value=[], multi=True),
                html.H4("Selecteer Basins"),
                dcc.Dropdown(id="bas-dropdown", options=[{"label": row["name"], "value": row["node_id"]} for _, row in gdf_basin_area.iterrows()], value=[], multi=True),
            ]),

            html.Div(style={"position": "absolute", "bottom": "20px", "left": "10px", "zIndex": "1000", "background": "rgba(255,255,255,0.8)", "padding": "10px", "borderRadius": "5px"}, children=[
                html.Div("Legenda: Neerslag (mm/u)"),
                html.Div(style={"height": "10px", "width": "200px", "background": "linear-gradient(to right, white, #c6dbef, #6baed6, #2171b5, #08306b)"}),
                html.Br(),
                dcc.Slider(id="time-slider", min=0, max=len(unique_times)-1, step=1, value=0, tooltip={"always_visible": True}),
                html.Button("Play", id="play-button"),
                html.Button("Pause", id="pause-button"),
                dcc.Interval(id="play-interval", interval=1000, n_intervals=0, disabled=True)
            ])
        ]),

        html.Div(style={"flex": "0 0 35%", "padding": "10px"}, children=[
            dcc.Graph(id="basin-timeseries", style={"height": "30vh"}),
            dcc.Graph(id="basin-level", style={"height": "30vh"}),
            dcc.Graph(id="link-flow", style={"height": "30vh"}),
            dcc.Store(id="sel-pumps", data=[]),
            dcc.Store(id="sel-basins", data=[]),
            dcc.Store(id="selected-link", data=None),
            dcc.Store(id="precipitation-data", data=precipitation_series)
        ])
    ])
])

# ───────────────────────────────────────────────────────────────────────────────
@app.callback(
    Output("geojson-basins", "hideout"),
    Output("time-slider", "value"),
    Input("play-interval", "n_intervals"),
    State("precipitation-data", "data"),
    State("time-slider", "value")
)
def update_precip_hideout(n, precip_data, index):
    times = list(precip_data.keys())
    if index >= len(times):
        return dash.no_update, 0
    t = times[index]
    values = precip_data[t]
    return {"basins": [], "precip": values}, index + 1

@app.callback(
    Output("play-interval", "disabled"),
    Input("play-button", "n_clicks"),
    Input("pause-button", "n_clicks"),
    prevent_initial_call=True
)
def toggle_play(play, pause):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    return ctx.triggered[0]["prop_id"].split(".")[0] != "play-button"

def store_selected_link(cd):
    if not cd or "properties" not in cd or "link_id" not in cd["properties"]:
        raise PreventUpdate
    return cd["properties"]["link_id"]

@app.callback(
    Output("selected-link", "data"),
    Input("geojson-links", "clickData")
)
def store_selected_link(cd):
    if not cd or "properties" not in cd or "link_id" not in cd["properties"]:
        raise PreventUpdate
    return cd["properties"]["link_id"]

@app.callback(
    Output("geojson-links", "hideout"),
    Input("selected-link", "data")
)
def update_link_hideout(selected_link):
    return {"selected_link": selected_link}

@app.callback(
    Output("link-flow", "figure"),
    Input("geojson-links", "clickData")
)
def update_link_graph(cd):
    if not cd or "properties" not in cd or "link_id" not in cd["properties"]:
        raise PreventUpdate
    link_id = int(cd["properties"]["link_id"])
    df_sel = df_link_result[df_link_result["link_id"] == link_id]
    if df_sel.empty:
        raise PreventUpdate
    return {
        "data": [{"x": df_sel["time"], "y": df_sel["flow_rate"], "type": "scatter", "name": f"Flow {link_id}"}],
        "layout": {"title": f"Flow over link {link_id}", "xaxis": {"title": "Tijd"}, "yaxis": {"title": "Debiet (m³/s)"}, "margin": {"l": 60, "r": 10, "t": 40, "b": 40}},
    }


@app.callback(
    Output("pump-dropdown", "value"),
    Input("geojson-pumps", "clickData"),
    State("pump-dropdown", "value")
)
def update_selected_pumps(feature, current_selection):
    if not feature or "properties" not in feature:
        raise PreventUpdate
    node_id = feature["properties"]["node_id"]
    current_selection = current_selection or []
    if node_id in current_selection:
        # Deselecteer bij opnieuw klikken
        return [nid for nid in current_selection if nid != node_id]
    else:
        # Voeg toe aan selectie
        return current_selection + [node_id]
    
@app.callback(
    Output("geojson-pumps", "hideout"),
    Input("pump-dropdown", "value"),
    State("geojson-pumps", "hideout")
)
def update_pump_hideout(selected, current_hideout):
    return {"pumps": selected, "zoom": current_hideout.get("zoom", 10)}


@app.callback(
    Output("basin-timeseries", "figure"),
    Output("basin-level", "figure"),
    Output("geojson-basin-nodes", "hideout"),
    Input("geojson-basin-nodes", "clickData"),
    State("geojson-basin-nodes", "hideout")
)
def update_basin_graphs(cd, current_hideout):
    if not cd or "properties" not in cd or "node_id" not in cd["properties"]:
        raise PreventUpdate
    node_id = str(cd["properties"]["node_id"])
    df_sel = df_basin_result[df_basin_result["node_id"] == node_id]
    if df_sel.empty:
        raise PreventUpdate
    meta_streefpeil = gdf_basin_area.set_index("node_id").get("meta_streefpeil", {}).get(node_id, None)
    fig_fluxes = {
        "data": [
            {"x": df_sel["time"], "y": df_sel["precipitation"], "type": "scatter", "name": "Precipitation"},
            {"x": df_sel["time"], "y": df_sel["drainage"], "type": "scatter", "name": "Drainage"},
            {"x": df_sel["time"], "y": df_sel["inflow_rate"], "type": "scatter", "name": "Inflow"},
            {"x": df_sel["time"], "y": df_sel["outflow_rate"], "type": "scatter", "name": "Outflow"},
            {"x": df_sel["time"], "y": df_sel["storage_rate"], "type": "scatter", "name": "Storage rate"},
        ],
        "layout": {"title": f"Tijdreeks Debieten Basin {node_id}", "xaxis": {"title": "Tijd"}, "yaxis": {"title": "Debiet (m³/s)"}, "margin": {"l": 60, "r": 10, "t": 40, "b": 40}},
    }
    level_trace = {"x": df_sel["time"], "y": df_sel["level"], "type": "scatter", "name": "Waterstand"}
    traces = [level_trace]
    if meta_streefpeil is not None:
        traces.append({"x": df_sel["time"], "y": [meta_streefpeil]*len(df_sel), "type": "scatter", "name": "Streefpeil", "line": {"dash": "dash"}})
    fig_level = {"data": traces, "layout": {"title": f"Waterstand Basin {node_id}", "xaxis": {"title": "Tijd"}, "yaxis": {"title": "Waterstand (m+NAP)"}, "margin": {"l": 60, "r": 10, "t": 40, "b": 40}}}

    current_sel = current_hideout.get("basin_nodes", [])
    updated_sel = [node_id] if node_id not in current_sel else []
    new_hideout = {"basin_nodes": updated_sel, "zoom": 10}
    return fig_fluxes, fig_level, new_hideout

if __name__ == "__main__":
    app.run(debug=True)