#%%
import dash
from dash import dcc, html, Output, Input
import dash_leaflet as dl
import geopandas as gpd
import pandas as pd
from datetime import datetime

# === Lees data in
df = pd.read_feather(
    "d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/peilgebieden_cso_combi_4326.arrow"
)
df["geometry"] = gpd.GeoSeries.from_wkt(df["geometry"])
gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")

# === Lees tijdserie (vullingsgraad) in ===
vulling_df = pd.read_feather("d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data/vullingsgraad.arrow")
vulling_df["datetime"] = pd.to_datetime(vulling_df["datetime"])
unique_datetimes = sorted(vulling_df["datetime"].dt.floor("d").unique())
datum_to_index = {i: dt for i, dt in enumerate(unique_datetimes)}

# === Functie om kleur te bepalen ===
def kleur_bij_vullingsgraad(val):
    if val is None or pd.isna(val):
        return "gray"
    elif val < 25:
        return "green"
    elif val < 50:
        return "yellow"
    elif val < 75:
        return "orange"
    else:
        return "red"

# === Bouw GeoJSON uit geopandas + vullingsgraad ===
def make_geojson(selected_date):
    df_sel = vulling_df[vulling_df["datetime"].dt.floor("d") == selected_date]
    merged = gdf.merge(df_sel, on="location_id", how="left")

    features = []
    for _, row in merged.iterrows():
        kleur = kleur_bij_vullingsgraad(row.get("value", None))
        features.append({
            "type": "Feature",
            "geometry": row["geometry"].__geo_interface__,
            "properties": {
                "location_id": row["location_id"],
                "naam": row["naam"],
                "vullingsgraad": row.get("value", None),
                "style": {
                    "fillColor": kleur,
                    "color": "black",
                    "weight": 1,
                    "fillOpacity": 0.7,
                },
            },
        })
    return {"type": "FeatureCollection", "features": features}

# === Dash App layout ===
app = dash.Dash(__name__)
app.layout = html.Div([
    html.H3("Peilgebiedenkaart met vullingsgraad"),

    dcc.Slider(
        id="tijdslider",
        min=0,
        max=len(unique_datetimes) - 1,
        step=1,
        value=len(unique_datetimes) - 1,
        marks={i: dt.strftime("%Y-%m-%d") for i, dt in datum_to_index.items()},
        tooltip={"placement": "bottom", "always_visible": True},
    ),

    dl.Map(center=[52.4, 5.3], zoom=9, style={'height': '70vh', 'width': '100%'}, children=[
        dl.TileLayer(),
        dl.GeoJSON(id="geojson-pgb", zoomToBounds=True),
    ]),

    html.Div(id="click-output", style={"marginTop": "1rem", "fontWeight": "bold"})
])

# === Update GeoJSON bij slider ===
@app.callback(
    Output("geojson-pgb", "data"),
    Input("tijdslider", "value")
)
def update_geojson(date_index):
    selected_date = datum_to_index[date_index]
    return make_geojson(selected_date)

# === Klik op een peilgebied ===
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
    app.run_server(debug=True)
