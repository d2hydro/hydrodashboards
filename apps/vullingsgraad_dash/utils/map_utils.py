# utils/map_utils.py
"""
Hulpfuncties voor kaartlogica (Leaflet-bounds, peilgebiedstijl, kleuren en data-extractie).
Deze module bevat geen Dash-specifieke onderdelen en kan in meerdere apps worden hergebruikt.
"""

import pandas as pd
from functools import lru_cache
from utils.style import vullingsgraad_classes, vulling_mm_classes


# ========= Kaartberekeningen =========
def bounds_to_map(xmin, ymin, xmax, ymax):
    """
    Zet shapefile-bounds om naar Leaflet-bounds en een kaartcentrum.
    Vergroot de view iets zodat de gebruiker context heeft.
    """
    dx, dy = xmax - xmin, ymax - ymin
    return [[ymin, xmin], [ymax + dy, xmin - 4 * dx]], [ymin + dy / 2, xmax - dx / 2]


def get_default_mpn_selection(df_locs_mpn, default_pgb):
    """
    Bepaal standaard meetpunten die horen bij het geselecteerde peilgebied.
    """
    if default_pgb is not None and "peilgebied_combi_attr" in df_locs_mpn.columns:
        return (
            df_locs_mpn.loc[
                df_locs_mpn["peilgebied_combi_attr"].astype(str) == str(default_pgb),
                "peilgebied_combi_attr",
            ]
            .astype(str)
            .dropna()
            .unique()
            .tolist()
        )
    return []


# ========= Kleurfuncties =========
def _pick_color(val, classes):
    """Kies een kleur op basis van een waarde en kleurklassen."""
    if pd.isna(val):
        return "gray"
    for low, high, color in classes:
        if low <= val < high:
            return color
    return classes[-1][2]


def kleur_bij_vullingsgraad(val, vullingsgraad_classes):
    return _pick_color(val, vullingsgraad_classes)


def kleur_bij_vulling(val, vulling_mm_classes):
    return _pick_color(val, vulling_mm_classes)


# ========= Kaartstijl per tijdstap =========
@lru_cache(maxsize=128)
def get_kaartdata_for_datetime(time_series_cache, dt, kaartvariabele):
    dt = pd.to_datetime(dt).to_pydatetime()

    if kaartvariabele == "vullingsgraad":
        df = time_series_cache.get_time_series(
            "VullingsgraadOutput", "vullingsgraad", start_time=dt, end_time=dt
        )
        kleur_fn = lambda v: kleur_bij_vullingsgraad(v, vullingsgraad_classes)
    else:
        df = time_series_cache.get_time_series(
            "VullingsgraadOutput", "vulling_mm", start_time=dt, end_time=dt
        )
        kleur_fn = lambda v: kleur_bij_vulling(v, vulling_mm_classes)

    df = df.loc[dt].reset_index()
    ids, vals = df["location_id"].to_list(), df[dt].to_list()
    return {
        loc: {
            "fillColor": kleur_fn(val),
            "color": "#666",
            "weight": 0.3,
            "fillOpacity": 1,
        }
        for loc, val in zip(ids, vals)
    }





