# %%
import dash
from dash import dcc, html, Output, Input
import dash_leaflet as dl
import geopandas as gpd
import pandas as pd
from read import read_peilgebieden
from pathlib import Path
import json

# == DATA
data_dir = Path(__file__).parent.joinpath("data")
geojson_data = read_peilgebieden(
    file_path=data_dir.joinpath("peilgebieden_cso_combi.shp").as_posix(),
    code_col="CODE",
    columns=[
        "naam",
        "streefpeil",
        "inundatiepeil",
        "berging_bij_inundatiepeil",
        "peil_bij_nul_berging",
    ],
)

# === App layout
app = dash.Dash(__name__)
app.layout = html.Div(
    [
        html.H3("Peilgebiedenkaart"),
        dl.Map(
            center=[52.4, 5.3],
            zoom=9,
            style={"height": "70vh", "width": "100%"},
            children=[
                dl.TileLayer(),
                dl.GeoJSON(
                    data=geojson_data,
                    id="geojson-pgb",
                    zoomToBounds=True,
                    style=dict(),  # laat leeg: stijl zit al in elk feature via properties["style"]
                ),
            ],
        ),
        html.Div(id="click-output", style={"marginTop": "1rem", "fontWeight": "bold"}),
    ]
)


# === Callback: klik op een peilgebied
@app.callback(
    Output("click-output", "children"),
    Input("geojson-pgb", "data_click"),
)
def show_click(feature):
    if not feature:
        return "Klik op een peilgebied..."
    props = feature["properties"]
    return f"Geselecteerd: {props['naam']} (code: {props['location_id']}), vullingsgraad: {props.get('vullingsgraad', 'onbekend')}%"


if __name__ == "__main__":
    app.run(debug=True)
