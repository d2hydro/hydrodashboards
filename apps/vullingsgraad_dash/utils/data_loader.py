"""
📦 data_loader.py
-----------------
Centrale module voor het inladen van shapefiles, Arrow-data en tijdreeksen
voor de HydroDashboard – Vullingsgraad Viewer.
"""

from pathlib import Path
import pandas as pd
from fewspy.cache import TimeSeriesCache
from utils.readers import read_peilgebieden, read_mpn_locs
from utils.map_utils import get_kaartdata_for_datetime, bounds_to_map, get_default_mpn_selection


def load_all_data(data_dir: Path):
    """
    Laadt alle benodigde data voor de Vullingsgraad-app in één stap.

    Parameters
    ----------
    data_dir : Path
        Pad naar de /data map binnen de app-directory.

    Returns
    -------
    dict
        Dictionary met:
        - geojson_data
        - location_options
        - bounds
        - df_locs_mpn
        - time_series_cache
        - all_datetimes
        - default_index
        - default_dt
        - default_pgb
        - map_bounds
        - map_center
        - initial_kaartvariabele
        - initial_stylemap
        - dd_locs_mpn_default
    """

    # === 1️⃣ Peilgebieden inladen ===
    shp_path = (data_dir / "peilgebieden_cso_combi.shp").as_posix()
    geojson_data, location_options, bounds = read_peilgebieden(
        shp_path,
        code_col="CODE",
        columns=[
            "naam",
            "streefpeil",
            "inundatiepeil",
            "berging_bij_inundatiepeil",
            "peil_bij_nul_berging",
        ],
        style={"fillColor": "gray", "color": "#666", "weight": 0.3, "fillOpacity": 1},
    )

    # === 2️⃣ Meetpunten inladen ===
    df_locs_mpn = read_mpn_locs(data_dir / "mpn_locations.arrow")

    # === 3️⃣ Tijdreeks-cache ===
    ts_cache = TimeSeriesCache.from_manifest_file(data_dir / "time_series" / "manifest.json")

    # === 4️⃣ Tijden & defaults ===
    all_datetimes = [pd.Timestamp(ts) for ts in ts_cache.common_time_axis]
    default_index = len(all_datetimes) - 1
    default_dt = all_datetimes[default_index]
    default_pgb = location_options[0]["value"] if location_options else None
    initial_kaartvariabele = "vullingsgraad"

    # === 5️⃣ Extra helpers ===
    map_bounds, map_center = bounds_to_map(*bounds)
    dd_locs_mpn_default = get_default_mpn_selection(df_locs_mpn, default_pgb)
    initial_stylemap = get_kaartdata_for_datetime(ts_cache, default_dt, initial_kaartvariabele)

    # === 6️⃣ Resultaat als dictionary ===
    return {
        "geojson_data": geojson_data,
        "location_options": location_options,
        "bounds": bounds,
        "df_locs_mpn": df_locs_mpn,
        "time_series_cache": ts_cache,
        "all_datetimes": all_datetimes,
        "default_index": default_index,
        "default_dt": default_dt,
        "default_pgb": default_pgb,
        "initial_kaartvariabele": initial_kaartvariabele,
        "map_bounds": map_bounds,
        "map_center": map_center,
        "initial_stylemap": initial_stylemap,
        "dd_locs_mpn_default": dd_locs_mpn_default,
    }
