# %%
from pathlib import Path

import geopandas as gpd
import pandas as pd
import json


def get_xs_ys(geometry, as_int=True):
    """Schrijf een polygon ring geometrie om naar twee lijsten; xs met x-coordinaten en ys met y-coordinaten"""
    xs, ys = list(zip(*geometry.coords))
    if as_int:
        return list(map(int, xs)), list(map(int, ys))
    else:
        return list(xs), list(ys)


def read_peilgebieden(
    file_path: str,
    code_col: str = "CODE",
    geometry_precision: float = 0.000006,
    columns: list = ["naam"],
    style: dict | None = None,
) -> pd.DataFrame:
    """schrijf/lees peilgebieden in/uit een arrow-file voor bokeh

    Parameters
    ----------
    file : str | Path
        Verwijzing naar het peilgebiedenbestand
    code_col : str
        kolomnaam die als peilgebied-id ingelezen moet worden
    geometry_precision: float
        precisie waarmee x en y coordinaten moeten worden afgerond
    columns: list
        lijst met kolommen die we willen bewaren
    style: dict, optioneel
        dict met style die moet worden toegevoegd aan de geodataframe

    Returns
    -------
    dict, DataFrame, np.ndarray
        GeoJSON (dict) met peilgebieden, DataFrame met opties en numpy array met bounds
    """

    # make file Path if not already
    file_path = Path(file_path)

    # read arrow-file if exists, otherwise make one.
    arrow_file = file_path.with_suffix(".arrow")

    if arrow_file.exists():
        gdf = gpd.read_feather(arrow_file)  # , dtype_backend="pyarrow")
    else:
        gdf = gpd.read_file(file_path, engine="pyogrio")
        df_csv = pd.read_csv(file_path.with_suffix(".csv"))
        gdf = pd.merge(gdf, df_csv, left_on="CODE", right_on="CODE")
        gdf.rename(
            {
                "NAAM": "naam",
                "STREEFPEIL_ZOMER": "streefpeil",
                "BOVENGRENSPEIL_VULLINGSGRAAD": "inundatiepeil",
                "BERGING_BOVENGRENS_VULLINGSGR": "berging_bij_inundatiepeil",
                "NULPEIL_VULLINGSGRAAD": "peil_bij_nul_berging",
            },
            axis=1,
            inplace=True,
        )
        gdf["geometry"] = gdf.buffer(0.1).buffer(
            -0.1
        )  # Buffer so we get less geoms when exploding
        gdf.to_crs(epsg=4326, inplace=True)
        gdf["geometry"] = gdf.geometry.set_precision(geometry_precision)
        gdf = gdf[[code_col] + columns + ["geometry"]]
        gdf.rename(columns={code_col: "location_id"}, inplace=True)

        gdf.loc[gdf["naam"].isna(), "naam"] = "naamloos"
        # store dataframe
        gdf.to_feather(arrow_file)

    # add style if given
    if style is not None:
        gdf["style"] = [style] * len(gdf)

    # get options
    options_df = gdf[["location_id", "naam"]].copy()
    options_df.rename(columns={"location_id": "value", "naam": "label"}, inplace=True)
    options_df["label"] = options_df["label"] + " (" + options_df["value"] + ")"
    options_df.sort_values(by="label", inplace=True)

    return (
        json.loads(gdf.to_json()),
        options_df.to_dict(orient="records"),
        gdf.total_bounds,
    )


def read_mpn_locs(file_path):
    df = pd.read_feather(file_path)  # ,  dtype_backend="pyarrow")
    gdf = gpd.GeoDataFrame(df, geometry=gpd.GeoSeries.from_xy(df.x, df.y), crs=28992)
    gdf.to_crs(4326, inplace=True)

    gdf.reset_index(drop=False, inplace=True)
    gdf.rename(columns={"short_name": "naam"}, inplace=True)

    return gdf


if __name__ == "__main__":
    DATA_DIR = Path(__file__).parent / "data"
    peilgebieden_gpkg = DATA_DIR / "peilgebieden_union.gpkg"
    peilgebieden_gpkg = DATA_DIR / "peilgebieden_cso_combi.shp"

    file = peilgebieden_gpkg
    code_col = "CODE"
    columns = [
        "naam",
        "streefpeil",
        "inundatiepeil",
        "berging_bij_inundatiepeil",
        "peil_bij_nul_berging",
    ]
    simplify_tolerance = None

    read_peilgebieden(file, code_col, simplify_tolerance, columns)

# %%
