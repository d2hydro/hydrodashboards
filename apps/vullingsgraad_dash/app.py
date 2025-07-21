#%%
import dash
from dash import dcc, html, Output, Input
import dash_leaflet as dl
import geopandas as gpd
import pandas as pd
from read import read_peilgebieden

# === Lees data in
df = pd.read_feather(
    "d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/peilgebieden_cso_combi_4326.arrow"
)
df["geometry"] = gpd.GeoSeries.from_wkt(df["geometry"])
gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")

def kleur_bij_vullingsgraad(val):
    if val is None:
        return "gray"
    elif val < 25:
        return "green"
    elif val < 50:
        return "yellow"
    elif val < 75:
        return "orange"
    else:
        return "red"


# === Maak GeoJSON data (met 'properties' voor klikinfo)
def gdf_to_geojson(gdf):
    features = []
    for _, row in gdf.iterrows():
        kleur = kleur_bij_vullingsgraad(row.get("vullingsgraad", None))
        features.append({
            "type": "Feature",
            "geometry": row["geometry"].__geo_interface__,
            "properties": {
                "location_id": row["location_id"],
                "naam": row["naam"],
                "vullingsgraad": row.get("vullingsgraad", None),
                "style": {
                    "fillColor": kleur,
                    "color": "black",
                    "weight": 1,
                    "fillOpacity": 0.7,
                }
            }
        })
    return {"type": "FeatureCollection", "features": features}

geojson_data = gdf_to_geojson(gdf)



# === App layout
app = dash.Dash(__name__)
app.layout = html.Div([
    html.H3("Peilgebiedenkaart"),
    dl.Map(center=[52.4, 5.3], zoom=9, style={'height': '70vh', 'width': '100%'}, children=[
        dl.TileLayer(),
        dl.GeoJSON(
            data=geojson_data,
            id="geojson-pgb",
            zoomToBounds=True,
            style=dict(),  # laat leeg: stijl zit al in elk feature via properties["style"]
        )
    ]),
    html.Div(id="click-output", style={"marginTop": "1rem", "fontWeight": "bold"})
])

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
