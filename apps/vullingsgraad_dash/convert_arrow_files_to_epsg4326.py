#%%
from pathlib import Path
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely import wkt

DATA_DIR = Path("d:/repositories/hydrodashboards/apps/vullingsgraad_dash/data")
ARROW_FILES = [
    "mpn_locations.arrow",
    "parameters.arrow",
    "peilgebieden_cso_combi.arrow",
    "vulling.arrow",
    "vullingsgraad.arrow",
    "waterstand_meetpunt.arrow",
    "waterstand_pgb.arrow",
]


def convert_xs_ys_to_geometry(df):
    def xs_ys_to_multipolygon(xs, ys):
        polygons = []
        for ring_xs, ring_ys in zip(xs, ys):
            exterior = list(zip(ring_xs[0], ring_ys[0]))
            holes = [list(zip(rx, ry)) for rx, ry in zip(ring_xs[1:], ring_ys[1:])]
            polygons.append(Polygon(exterior, holes))
        return MultiPolygon(polygons)
    return [xs_ys_to_multipolygon(x, y) for x, y in zip(df["xs"], df["ys"])]


def convert_file(file_path: Path):
    df = pd.read_feather(file_path)
    geometry = None

    if {"xs", "ys"}.issubset(df.columns):
        geometry = convert_xs_ys_to_geometry(df)
    elif {"x", "y"}.issubset(df.columns):
        geometry = gpd.points_from_xy(df["x"], df["y"])
    else:
        print(f"⏩ Sla over (geen geometrie): {file_path.name}")
        return

    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:28992")
    gdf = gdf.to_crs("EPSG:4326")

    # Zet geometry om naar WKT voor opslag
    gdf["geometry"] = gdf["geometry"].to_wkt()

    # Sla op als Feather-bestand met geometrie als WKT-string
    output_file = file_path.with_name(file_path.stem + "_4326.arrow")
    gdf.to_feather(output_file)
    print(f"✅ {file_path.name} → {output_file.name}")


def main():
    for fname in ARROW_FILES:
        fpath = DATA_DIR / fname
        if fpath.exists():
            convert_file(fpath)
        else:
            print(f"⚠️  Niet gevonden: {fname}")


if __name__ == "__main__":
    main()
