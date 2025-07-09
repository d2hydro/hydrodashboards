# %%
import dash
from dash import html, dcc
import dash_leaflet as dl
from pathlib import Path
from flask import send_file
import plotly.express as px
import pandas as pd
from dash_resizable_panels import PanelGroup, Panel, PanelResizeHandle

# WMTS-service URL en laagnaam
wmts_url = "https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0"
layer_name = "Actueel_orthoHR"  # Laagnaam voor de actuele 8cm RGB luchtfoto

# Dash-applicatie
app = dash.Dash(__name__)
data_dir = Path(__file__).parent.joinpath("data")


# Routes to serve the GeoJSON files
@app.server.route("/geojson/<filename>")
def serve_geojson(filename):
    filepath = data_dir / filename
    if filepath.exists():
        return send_file(filepath, mimetype="application/json")
    return {"error": "File not found"}, 404


# Dummy time series
df = pd.date_range("2023-01-01", periods=100, freq="D").to_frame(
    index=False, name="date"
)
df["value"] = (df.index**1.5) % 50

fig = px.line(df, x="date", y="value", title="Dummy Time Series")

app.layout = html.Div(
    [
        PanelGroup(
            id="panel-group",
            children=[
                Panel(
                    id="map-panel",
                    children=[
                        dl.Map(
                            center=[52.1, 5.1],
                            zoom=13,
                            style={
                                "width": "100%",
                                "maxWidth": "1000px",
                                "height": "100%",
                            },
                            children=[
                                dl.TileLayer(
                                    url="https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0/Actueel_orthoHR/EPSG:3857/{z}/{x}/{y}.jpeg",
                                    attribution="&copy; <a href='https://www.pdok.nl/'>PDOK</a>",
                                    tileSize=256,
                                ),
                                dl.GeoJSON(
                                    url="/geojson/points.geojson",
                                    id="points",
                                    zoomToBounds=True,
                                ),
                            ],
                        )
                    ],
                ),
                PanelResizeHandle(
                    html.Div(
                        style={
                            "backgroundColor": "grey",
                            "height": "100%",
                            "width": "5px",
                        }
                    )
                ),
                Panel(
                    id="graph-panel",
                    children=[
                        html.Div(
                            style={
                                "flex": "1",
                                "height": "100%",
                                "minWidth": "800px",
                            },
                            children=[dcc.Graph(figure=fig, style={"height": "100%"})],
                        ),
                    ],
                ),
            ],
            direction="horizontal",
        )
    ],
    style={"height": "100vh"},
)

if __name__ == "__main__":
    app.run(debug=True)
