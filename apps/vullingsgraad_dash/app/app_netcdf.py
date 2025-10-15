# %%
import sys
import time
import json
from functools import lru_cache, wraps

import dash
import dash_leaflet as dl
import pandas as pd
import plotly.graph_objs as go
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
from pathlib import Path
from dash import Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate
from dash_extensions.javascript import assign
from flask_caching import Cache
from plotly.subplots import make_subplots
from read import read_mpn_locs, read_peilgebieden
from fewspy.cache.manifest import Manifest
from typing import Optional
import xarray as xr
import numpy as np
from datetime import datetime
import threading

# ====== PADEN ======
app_dir = Path(__file__).parent
data_dir = app_dir.parent.joinpath("data")
project_root = app_dir.parents[2]
assets_dir = project_root / "assets"


# # ====== TimeSeriesCache ======
class TimeSeriesCache:
    def __init__(self, manifest: Manifest, last_manifest_mtime: Optional[float] = None):
        self.manifest = manifest
        self.last_manifest_mtime: float | None = last_manifest_mtime
        self._lock = threading.RLock()
        self._datasets: dict[str, xr.Dataset] = {}
        self._common_time_axis: pd.DatetimeIndex | None = None
        self._open_all()  #

    def _key_for(self, path: Path) -> str:
        return f"{path.parent.name}/{path.name}"

    def _get_open_ds(self, filter_id: str, parameter_id: str) -> xr.Dataset:
        entry = self.manifest.get_entry(filter_id=filter_id, parameter_id=parameter_id)
        key = self._key_for(entry.path)
        with self._lock:
            ds = self._datasets.get(key)
        if ds is None:
            # Fallback if not cached
            entry = self.manifest.get_entry(
                filter_id=filter_id, parameter_id=parameter_id
            )
            ds = xr.open_dataset(
                entry.path,
                engine="netcdf4",
                decode_times=True,
                mask_and_scale=True,
                cache=False,
            )
        return ds

    def _open_all(self):
        """Open all datasets and close old datasets"""
        new = {}
        for entry in self.manifest.files:
            key = self._key_for(entry.path)
            dataset = xr.open_dataset(
                entry.path,
                engine="netcdf4",
                decode_times=True,
                mask_and_scale=True,
                cache=False,
            )
            new[key] = dataset
        with self._lock:
            old = self._datasets
            self._datasets = new
        for dataset in old.values():
            try:
                dataset.close()
            except:
                pass

    @property
    def common_time_axis(self) -> pd.DatetimeIndex:
        if not self._datasets:
            raise ValueError(
                "No NetCDF DataSets open in cache. Check manifest-file and run self._open_all()"
            )

        if self._common_time_axis is None:
            # init idx_all
            idx_all: pd.DatetimeIndex | None = None

            # union all time-axis to idx_all
            for dataset in self._datasets.values():
                idx = pd.to_datetime(dataset["time"].values)

                if idx_all is None:
                    idx_all = idx
                else:
                    idx_all = idx_all.union(idx)

            if idx_all is not None:
                self._common_time_axis = idx_all.sort_values()
        return self._common_time_axis

    @classmethod
    def _decode_station_ids(cls, sid: xr.DataArray) -> np.ndarray:
        """
        Retourneert een 1D numpy array met dtype 'U' (unicode) zonder Python-loop.
        Werkt voor:
        - fixed-width bytes: dtype.kind == 'S'
        - unicode strings:   dtype.kind == 'U'
        - object arrays met mix van bytes/str: dtype.kind == 'O'
        """
        vals = sid.values

        # Case 1: fixed-width bytes (b'...') -> vectorized decode
        if vals.dtype.kind == "S":  # e.g. dtype('S20')
            return np.char.decode(vals, "utf-8", "replace")

        # Case 2: al unicode
        if vals.dtype.kind == "U":
            return vals

        # Case 3: object array met mix bytes/str
        if vals.dtype.kind == "O":
            obj = vals
            # mask voor bytes
            is_bytes = np.frompyfunc(lambda x: isinstance(x, (bytes, bytearray)), 1, 1)(
                obj
            ).astype(bool)

            out = np.empty(obj.shape, dtype=object)
            if is_bytes.any():
                # Alleen de bytes-subset in één keer decoden
                out[is_bytes] = np.char.decode(
                    obj[is_bytes].astype("S"), "utf-8", "replace"
                )
            if (~is_bytes).any():
                # Niet-bytes naar str (no-op voor str, netjes voor ints e.d.)
                out[~is_bytes] = obj[~is_bytes].astype(str)
            return out.astype("U")

        # Fallback: veilig naar unicode casten
        return vals.astype("U")

    @classmethod
    def from_manifest_file(cls, path: Path):
        manifest = Manifest.from_file(path)
        manifest.validate_files()
        return cls(manifest=manifest, last_manifest_mtime=path.stat().st_mtime)

    def refresh_if_changed(self, manifest_path: Path) -> bool:
        """Swap DataSets if manifest_json has changed

        Args:
            manifest_path (Path): Path to manifest.json

        Returns:
            bool: True if swapped, else False
        """
        mtime = manifest_path.stat().st_mtime
        if mtime == self.last_manifest_mtime:
            return False
        # read new manifest and validate
        new_manifest = Manifest.from_file(manifest_path)
        try:
            # mount new manifest file
            new_manifest.validate_files()
            self.manifest = new_manifest
            self.last_manifest_mtime = mtime

            # swap to new netcdfs and close old
            self._open_all()

            # reset derived arguments so they will be re-computed
            self._common_time_axis = None
            return True
        except ValueError:  # in case new manifest returns invalid files
            return False

    def get_time_series(
        self,
        filter_id: str,
        parameter_id: str,
        start_time: Optional[datetime | str] = None,
        end_time: Optional[datetime | str] = None,
        location_ids: Optional[list[str]] = None,
    ) -> pd.DataFrame:
        """fetch time series data from NetCDF file based on filter_id and parameter_id

        Args:
            filter_id (str): filter_id
            parameter_id (str): parameter_id
            start_time (Optional[datetime  |  str], optional): start_time Defaults to None.
            end_time (Optional[datetime  |  str], optional): end_time. Defaults to None.
            location_ids (Optional[list[str]], optional): location_ids. Defaults to None.

        Returns:
            pd.DataFrame: DataFrame with datetime index and MultiIndex columns (location_id, parameter_id)
        """
        dataset = self._get_open_ds(filter_id=filter_id, parameter_id=parameter_id)
        da = dataset[parameter_id]

        if "stations" in da.dims and "station_id" in dataset.variables:
            # swap station index for station_id values
            # TODO: bij chache een optie inbouwen om station_ids al als location_id (string) op te slaan
            # TODO: bij cache een optie inbouwen om station_ids te gebruiken i.p.v. stations index
            station_ids = self._decode_station_ids(dataset["station_id"])
            da = da.assign_coords(station_id=("stations", station_ids))
            da = da.swap_dims({"stations": "station_id"})

        # Slice time and location_ids
        slicer = {}
        if (start_time is not None) | (end_time is not None):
            slicer["time"] = slice(start_time, end_time)
        if location_ids is not None:
            slicer["station_id"] = location_ids
        if slicer:
            da = da.sel(**slicer)

        s = da.to_series()
        if "station_id" in s.index.names:
            df = s.unstack("station_id")
        else:
            df = s.unstack("stations")
            df.columns = df.columns.astype(str)

        # MultiIndex-kolommen (station_id, parameter_id)
        df.columns = pd.MultiIndex.from_arrays(
            [df.columns, [parameter_id] * len(df.columns)],
            names=["location_id", "parameter_id"],
        )

        # sort indices
        df.sort_index(inplace=True)
        df.sort_index(inplace=True, axis=1)

        return df


# Initialize Dash and set assets folder explicitly to the project-level assets
app = dash.Dash(__name__, assets_folder=str(assets_dir))

# === caching
cache = Cache(
    app.server, config={"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 3600}
)


def timed_callback(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        result = f(*args, **kwargs)
        dt = time.perf_counter() - t0
        print(f"[TIMING] Callback {f.__name__} duurde {dt:.3f} s")
        return result

    return wrapper


def bounds_to_map(xmin, ymin, xmax, ymax):
    dx = xmax - xmin
    dy = ymax - ymin
    map_bounds = [[ymin, xmin], [ymax, xmin + 2 * dx]]
    map_center = [ymin + dy / 2, xmax + dx / 2]
    return map_bounds, map_center


# ========== Geodata laden ==============
timer_start = time.time()
geojson_data, location_options, bounds = read_peilgebieden(
    file_path=data_dir.joinpath("peilgebieden_cso_combi.shp").as_posix(),
    code_col="CODE",
    columns=[
        "naam",
        "streefpeil",
        "inundatiepeil",
        "berging_bij_inundatiepeil",
        "peil_bij_nul_berging",
    ],
    style={
        "fillColor": "gray",
        "color": "#666",
        "weight": 0.3,
        "fillOpacity": 0.3,
    },
)
map_bounds, map_center = bounds_to_map(*bounds)
print("TIJD: shapefile/geodata ingelezen in", round(time.time() - timer_start, 2), "s")

# ===== Laad Arrow tijdseries, bepaal tijdas =====
ds_vg = ds.dataset(
    data_dir.joinpath("vullingsgraad.arrow"),
    format="feather",
)
ds_vul = ds.dataset(
    data_dir.joinpath("vulling.arrow"),
    format="feather",
)
df_locs_mpn = read_mpn_locs(data_dir.joinpath("mpn_locations.arrow"))
dd_locs_mpn_default = []

ds_wlvl_mpn = ds.dataset(
    data_dir.joinpath("waterstand_meetpunt.arrow"),
    format="feather",
)
ds_wlvl_pgb = ds.dataset(
    data_dir.joinpath("waterstand_pgb.arrow"),
    format="feather",
)

time_series_cache = TimeSeriesCache.from_manifest_file(
    data_dir.joinpath("time_series", "manifest.json")
)

timer_start = time.time()

# TODO: dit verwijderen wanneer time_series_cache.common_time_axis werkt
# dt_vg = ds_vg.to_table(columns=["datetime"])
# dt_vul = ds_vul.to_table(columns=["datetime"])
# all_dt_arrow = pc.unique(pa.concat_tables([dt_vg, dt_vul])["datetime"])
# all_datetimes = sorted(pd.to_datetime(all_dt_arrow.to_pylist()))
all_datetimes = [pd.Timestamp(i) for i in time_series_cache.common_time_axis]
datum_to_index = {i: dt for i, dt in enumerate(all_datetimes)}
print("TIJD: tijdas opgebouwd in", round(time.time() - timer_start, 2), "s")

kaartvariabelen = [
    {"label": "vullingsgraad [%]", "value": "vullingsgraad"},
    {"label": "vulling [mm]", "value": "vulling"},
]


# ========== Kleurfuncties ==========
def kleur_bij_vullingsgraad(val):
    if pd.isna(val):
        return "gray"
    if val < 25:
        return "green"
    if val < 50:
        return "yellow"
    if val < 75:
        return "orange"
    return "red"


def kleur_bij_vulling(val):
    if pd.isna(val):
        return "gray"
    if val < 10:
        return "#eff3ff"
    if val < 20:
        return "#bdd7e7"
    if val < 30:
        return "#6baed6"
    if val < 40:
        return "#3182bd"
    return "#08519c"


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

def_layout = {
    "position": "absolute",
    "top": "10px",
    "right": "10px",
    "bottom": "10px",
    "width": "50%",
    "height": "calc(100vh - 32px)",
    "background": "white",
    "borderRadius": "5px",
    "zIndex": 1100,
    "boxShadow": "0 2px 8px rgba(0,0,0,0.05)",
    "padding": "10px",
    "display": "flex",
    "flexDirection": "column",
    "gap": "10px",
    "minHeight": 0,
}

# ===== Standaardkeuzes bij opstarten =====
default_index = 0
default_dt = all_datetimes[default_index]
default_pgb = location_options[0]["value"] if location_options else None
initial_label = default_dt.strftime("%Y-%m-%d %H:%M")
initial_kaartvariabele = "vullingsgraad"


@lru_cache(maxsize=128)
def get_kaartdata_for_datetime(dt, kaartvariabele):
    dt = pd.to_datetime(dt).to_pydatetime()
    if kaartvariabele == "vullingsgraad":
        df = time_series_cache.get_time_series(
            filter_id="VullingsgraadOutput",
            parameter_id="vullingsgraad",
            start_time=dt,
            end_time=dt,
        )
        kleur_fn = kleur_bij_vullingsgraad
    else:
        df = time_series_cache.get_time_series(
            filter_id="VullingsgraadOutput",
            parameter_id="vulling_mm",
            start_time=dt,
            end_time=dt,
        )
        kleur_fn = kleur_bij_vulling
    df = df.loc[dt].reset_index()
    ids = df["location_id"].to_list()
    vals = df[dt].to_list()
    return {
        loc: {
            "fillColor": kleur_fn(val),
            "color": "#666",
            "weight": 0.3,
            "fillOpacity": 1,
            kaartvariabele: val,
        }
        for loc, val in zip(ids, vals)
    }


initial_stylemap = get_kaartdata_for_datetime(default_dt, initial_kaartvariabele)
initial_options = {
    "style": style_handle,
    "selected": default_pgb,
    "interactive": True,
    "bubblingMouseEvents": True,
}

EMPTY_FIG = go.Figure()
EMPTY_FIG.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=0, r=0, t=0, b=0),
    xaxis=dict(visible=False),
    yaxis=dict(visible=False),
    showlegend=False,
)
# ========== Layout ==========
from dash import html, dcc

app.layout = html.Div(
    [
        # <<< FULLSCREEN OVERLAY SPINNER >>>
        html.Div(
            id="page-loader",
            children=html.Div(className="spinner"),
            style={"display": "block"},
        ),
        # <<< JE HUIDIGE APP-INHOUD >>>
        html.Div(
            [
                html.Div(
                    [
                        html.Label(
                            [
                                "kaartvariabele: ",
                                html.Span(
                                    "?",
                                    title="Selecteer de variabele die op de kaart moet worden getoond",
                                    style={"cursor": "help"},
                                ),
                            ],
                            style={"fontSize": "13px"},
                        ),
                        dcc.Dropdown(
                            id="kaartvariabele-dropdown",
                            options=kaartvariabelen,
                            value=initial_kaartvariabele,
                            clearable=False,
                            style={"width": "240px", "marginBottom": "8px"},
                        ),
                        html.Label(
                            [
                                "peilgebied: ",
                                html.Span(
                                    "?",
                                    title="Selecteer een peilgebied waarvoor de grafieken moeten worden getoond",
                                    style={"cursor": "help"},
                                ),
                            ],
                            style={"fontSize": "13px"},
                        ),
                        dcc.Dropdown(
                            id="pgb-dropdown",
                            options=location_options,
                            value=default_pgb,
                            placeholder="Selecteer peilgebied",
                            clearable=True,
                            style={"width": "240px"},
                        ),
                    ],
                    style={
                        "position": "absolute",
                        "top": "10px",
                        "left": "10px",
                        "zIndex": 1002,
                        "background": "rgba(220,240,255,1)",
                        "borderRadius": "8px",
                        "padding": "10px",
                    },
                ),
                dl.Map(
                    center=map_center,
                    zoom=10,
                    bounds=map_bounds,
                    style={"height": "100vh", "width": "100%"},
                    preferCanvas=True,
                    children=[
                        dl.TileLayer(),
                        dl.GeoJSON(
                            data=json.loads(df_locs_mpn.to_json()),
                            id="marker-mpn",
                            filter=assign(
                                "function(feature, context){return context.hideout.includes(feature.properties.peilgebied_combi_attr);}"
                            ),
                            hideout=dd_locs_mpn_default,
                            eventHandlers={
                                "click": assign(
                                    "function(e){return e?.target?.feature?.properties||{};}"
                                )
                            },
                        ),
                        dl.GeoJSON(
                            id="geojson-pgb",
                            data=geojson_data,
                            hideout=initial_stylemap,
                            options=initial_options,
                            # hoverStyle eventueel weghalen als je helemaal geen hoveraccent wilt
                            # hoverStyle={"weight": 2, "color": "yellow", "dashArray": ""},
                            eventHandlers={
                                "click": assign(
                                    "function(e){return e?.target?.feature?.properties||{};}"
                                )
                            },
                        ),
                    ],
                ),
                html.Div(
                    [
                        dcc.Store(id="combined-fig-store"),
                        # Lokale spinner voor alleen de grote grafiek mag blijven
                        dcc.Loading(
                            id="loading-combined",
                            type="default",
                            children=[
                                dcc.Graph(
                                    id="combined-graph",
                                    figure=EMPTY_FIG,
                                    config={"displayModeBar": True, "scrollZoom": True},
                                    style={"height": "100%", "minHeight": 0},
                                )
                            ],
                        ),
                    ],
                    style=def_layout,
                ),
                html.Div(
                    [
                        dcc.Store(id="is-playing", data=False),
                        html.Button(
                            id="playpause-button", n_clicks=0, style={"width": "72px"}
                        ),
                        html.Div(
                            initial_label,
                            id="datum-label",
                            style={"fontWeight": "bold"},
                        ),
                        html.Div(
                            [
                                dcc.Graph(
                                    id="mini-tijdserie",
                                    config={"displayModeBar": False},
                                    style={
                                        "height": "50px",
                                        "width": "350px",
                                        "position": "absolute",
                                        "top": 0,
                                        "left": "25px",
                                        "pointerEvents": "none",
                                    },
                                ),
                                dcc.Slider(
                                    id="tijdslider",
                                    min=0,
                                    max=len(all_datetimes) - 1,
                                    value=default_index,
                                    updatemode="mouseup",
                                ),
                            ],
                            style={
                                "position": "relative",
                                "width": "400px",
                                "height": "50px",
                                "display": "inline-block",
                            },
                        ),
                    ],
                    style={
                        "position": "absolute",
                        "bottom": "10px",
                        "left": "10px",
                        "background": "rgba(255,255,255,0.9)",
                        "padding": "8px",
                        "borderRadius": "6px",
                        "zIndex": 1000,
                        "display": "flex",
                        "gap": "10px",
                        "alignItems": "center",
                    },
                ),
                dcc.Interval(id="interval", interval=1000, disabled=True),
                html.Div(id="click-output"),
            ]
        ),
    ]
)


# ============= CALLBACKS =============
@app.callback(
    Output("page-loader", "style"),
    [Input("combined-fig-store", "data"), Input("geojson-pgb", "hideout")],
    prevent_initial_call=True,
)
def hide_page_loader(fig_dict, stylemap):
    if not fig_dict or not stylemap:
        raise PreventUpdate
    return {"display": "none"}


@app.callback(
    Output("geojson-pgb", "hideout"),
    Output("datum-label", "children"),
    Output("geojson-pgb", "options"),
    Input("tijdslider", "value"),
    Input("pgb-dropdown", "value"),
    Input("kaartvariabele-dropdown", "value"),
    prevent_initial_call=True,
)
def update_stylemap(idx, sel, var):
    try:
        if idx is None or idx not in all_datetimes or not sel or not var:
            raise PreventUpdate
        dt = all_datetimes[int(idx)]
        stylemap = get_kaartdata_for_datetime(dt, var)
        label = dt.strftime("%Y-%m-%d %H:%M")
        options = {
            "style": style_handle,
            "selected": sel,
            "interactive": True,
            "bubblingMouseEvents": True,
        }
        return stylemap, label, options
    except PreventUpdate:
        raise
    except Exception as e:
        print(f"[ERROR] update_stylemap: {e}", file=sys.stderr)
        raise PreventUpdate


@app.callback(
    Output("pgb-dropdown", "value"),
    Input("geojson-pgb", "clickData"),
    prevent_initial_call=True,
)
def select_dropdown_on_click(clickData):
    return clickData["properties"]["location_id"]


# ========= Grote grafiek: BASIS in Store =========
@app.callback(
    Output("combined-fig-store", "data"),
    [
        Input("pgb-dropdown", "value"),
        Input("kaartvariabele-dropdown", "value"),
    ],
)
@timed_callback
def build_combined_figure(sel, var):
    if not sel:
        raise PreventUpdate
    print(f"selected: {sel}")
    ckey = f"combined_{sel}"
    fig = cache.get(ckey)
    if fig is None:
        df_vg = time_series_cache.get_time_series(
            filter_id="VullingsgraadOutput",
            parameter_id="vullingsgraad",
            location_ids=[sel],
        )
        df_vul = time_series_cache.get_time_series(
            filter_id="VullingsgraadOutput",
            parameter_id="vulling_mm",
            location_ids=[sel],
        )
        df_pgb = time_series_cache.get_time_series(
            filter_id="PeilgebiedWaterstandOutput",
            parameter_id="H.meting",
            location_ids=[sel],
        )
        mpn_ids = df_locs_mpn.loc[
            df_locs_mpn["peilgebied_combi_attr"] == sel, "location_id"
        ].tolist()
        df_mpn = time_series_cache.get_time_series(
            filter_id="PeilgebiedWaterstandMeetpunt",
            parameter_id="H.meting",
            location_ids=mpn_ids,
        )

        # tb_all = ds_wlvl_mpn.to_table(
        #     filter=ds.field("location_id").isin(mpn_ids),
        #     columns=["location_id", "datetime", "value"],
        # ).to_pandas()
        # tb_all["datetime"] = pd.to_datetime(tb_all["datetime"])
        fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.06,
            subplot_titles=["Vullingsgraad [%]", "Vulling [mm]", "Waterstand [mNAP]"],
        )
        fig.add_trace(
            go.Scatter(
                x=df_vg.datetime,
                y=df_vg.vullingsgraad,
                line=dict(color="blue", width=2),
                showlegend=False,
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=[],
                y=[],
                mode="lines",
                line=dict(color="Orange", width=3),
                opacity=1.0,
                hoverinfo="skip",
                showlegend=False,
                name="__highlight__",  # herkenbare naam
            ),
            row=3,
            col=1,
        )
        for y0, y1, colc in [
            (0, 25, "rgba(120,200,120,0.4)"),
            (25, 50, "rgba(255,255,100,0.4)"),
            (50, 75, "rgba(255,200,100,0.4)"),
            (75, 100, "rgba(255,100,100,0.4)"),
        ]:
            fig.add_shape(
                type="rect",
                xref="x1",
                yref="y1",
                x0=df_vg.datetime.min(),
                x1=df_vg.datetime.max(),
                y0=y0,
                y1=y1,
                fillcolor=colc,
                line_width=0,
                layer="below",
                row=1,
                col=1,
            )
        fig.add_trace(
            go.Scatter(
                x=df_vul.datetime,
                y=df_vul.vulling,
                line=dict(color="royalblue", width=2),
                showlegend=False,
            ),
            row=2,
            col=1,
        )
        for y0, y1, colc in [
            (0, 10, "#ffffff"),
            (10, 20, "#b4d3e7"),
            (20, 30, "#72b2d7"),
            (30, 40, "#3e91c4"),
            (40, 60, "#1c5fa5"),
        ]:
            fig.add_shape(
                type="rect",
                xref="x2",
                yref="y2",
                x0=df_vul.datetime.min(),
                x1=df_vul.datetime.max(),
                y0=y0,
                y1=y1,
                fillcolor=colc,
                line_width=0,
                layer="below",
                row=2,
                col=1,
            )
        for location_id in df_mpn.columns.get_level_values("location_id"):
            naam = df_locs_mpn.loc[df_locs_mpn.location_id == location_id, "naam"].iat[
                0
            ]
            fig.add_trace(
                go.Scatter(
                    x=df_mpn.index,
                    y=df_mpn[location_id].to_numpy() / 1000,
                    mode="lines",
                    line=dict(color="grey", width=1),
                    opacity=0.7,
                    meta=location_id,
                    hovertemplate="datum: %{x|%Y-%m-%d %H:%M}<br>waarde: %{y:.3f}<br>naam: "
                    + naam
                    + "<extra></extra>",
                    showlegend=False,
                ),
                row=3,
                col=1,
            )
        if not df_pgb.empty:
            fig.add_trace(
                go.Scatter(
                    x=df_pgb.index,
                    y=df_pgb[df_pgb.columns[0]].to_numpy() / 1000,
                    mode="lines",
                    line=dict(color="royalblue", width=3),
                    hovertemplate="datum: %{x|%Y-%m-%d %H:%M}<br>waarde: %{y:.3f}<br>naam: Peilgebied<extra></extra>",
                    showlegend=False,
                ),
                row=3,
                col=1,
            )
        streefpeil = None
        for feat in geojson_data["features"]:
            if feat["properties"].get("location_id") == sel:
                streefpeil = feat["properties"].get("streefpeil")
                break
        if streefpeil is not None and pd.notnull(streefpeil):
            if not df_pgb.empty:
                x_vals = list(df_pgb.index)
            else:
                x_vals = list(df_mpn.index.unique())
                x_vals.sort()
            if x_vals:
                y_val = streefpeil / 1000
                fig.add_trace(
                    go.Scatter(
                        x=x_vals,
                        y=[y_val] * len(x_vals),
                        mode="lines",
                        line=dict(dash="dash", color="orange", width=2),
                        name="Streefpeil",
                        hoverinfo="text",
                        hovertext=[f"Streefpeil: {y_val:.2f} mNAP"] * len(x_vals),
                        showlegend=False,
                    ),
                    row=3,
                    col=1,
                )
                fig.add_annotation(
                    x=x_vals[0],
                    y=y_val,
                    xref="x3",
                    yref="y3",
                    text="streefpeil",
                    font=dict(color="orange", size=13),
                    showarrow=False,
                    xanchor="left",
                    yanchor="bottom",
                    align="left",
                    bgcolor="rgba(255,255,255,0.7)",
                    borderpad=2,
                )
        fig.update_yaxes(range=[0, 100], fixedrange=True, row=1, col=1)
        fig.update_yaxes(range=[0, 60], fixedrange=True, row=2, col=1)
        fig.update_yaxes(fixedrange=True, row=3, col=1)
        fig.update_xaxes(title_text="Tijd", row=3, col=1)
        fig.update_layout(
            height=900,
            margin=dict(l=40, r=10, t=60, b=40),
            plot_bgcolor="white",
            hovermode="closest",
            font=dict(size=13),
            showlegend=False,
        )
        x_min = df_vg.datetime.min()
        x_max = df_vg.datetime.max()
        for r in [1, 2, 3]:
            fig.update_xaxes(range=[x_min, x_max], row=r, col=1, automargin=True)
        cache.set(ckey, fig)
        print(f"CACHE MISS combined for {sel}")
    else:
        print(f"CACHE HIT combined for {sel}")
    return fig.to_dict()


# ========= Tweede callback: vline toevoegen op figuur =========
@app.callback(
    Output("combined-graph", "figure"),
    [
        Input("combined-fig-store", "data"),
        Input("tijdslider", "value"),
        Input("marker-mpn", "clickData"),
    ],
)
def add_vline_to_combined(fig_dict, idx, selected_mpn):
    if fig_dict is None or idx is None:
        raise PreventUpdate

    fig = go.Figure(fig_dict)

    # vline(s)
    current_dt = all_datetimes[int(idx)]
    for xref in ["x1", "x2", "x3"]:
        fig.add_shape(
            type="line",
            x0=current_dt,
            x1=current_dt,
            y0=0,
            y1=1,
            xref=xref,
            yref="paper",
            line=dict(dash="dot", width=2, color="#bbbbbb"),
            layer="above",
        )

    # 1) alles grauw maken (alle MPN-traces hebben meta == location_id)
    for tr in fig.data:
        if getattr(tr, "meta", None):
            tr.line.color = "#bbbbbb"
            tr.line.width = 2
            tr.opacity = 1.0

    # 2) highlight-trace zoeken (laatste met name == "__highlight__")
    highlight_idx = None
    for i in range(len(fig.data) - 1, -1, -1):
        if getattr(fig.data[i], "name", None) == "__highlight__":
            highlight_idx = i
            break

    # 3) geselecteerde serie in de highlight-trace projecteren
    sel_id = selected_mpn and selected_mpn.get("properties", {}).get("location_id")
    x_sel, y_sel = [], []
    if sel_id:
        for tr in fig.data:
            if getattr(tr, "meta", None) == sel_id:
                x_sel, y_sel = tr.x, tr.y
                break

    if highlight_idx is not None:
        fig.data[highlight_idx].x = x_sel
        fig.data[highlight_idx].y = y_sel
        # optioneel: boven pgb-lijn houden? Zet de highlight-trace helemaal als laatste:
        data = list(fig.data)
        hl = data.pop(highlight_idx)
        data.append(hl)
        fig.data = tuple(data)

    return fig


@app.callback(
    Output("mini-tijdserie", "figure"),
    [
        Input("pgb-dropdown", "value"),
        Input("kaartvariabele-dropdown", "value"),
        Input("tijdslider", "value"),
    ],
)
def update_mini_graph(sel, var, idx):
    if not sel:
        raise PreventUpdate
    if var == "vullingsgraad":
        vals = []
    idx0 = int(idx) if idx is not None else 0
    mini = go.Figure(
        go.Scatter(
            x=[],
            y=vals,
            mode="lines",
            line=dict(width=2),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    mini.add_vline(x=idx0, line_width=2, line_dash="dash", line_color="#bbbbbb")
    mini.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=50,
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False, range=[0, len(all_datetimes) - 1], fixedrange=True),
        yaxis=dict(visible=False, fixedrange=True),
    )
    return mini


@app.callback(Output("playpause-button", "children"), Input("is-playing", "data"))
def set_playpause(is_playing):
    return "⏸️ Pause" if is_playing else "▶️ Play"


@app.callback(
    Output("is-playing", "data"),
    Input("playpause-button", "n_clicks"),
    State("is-playing", "data"),
    prevent_initial_call=True,
)
def toggle_playpause(n, playing):
    return not playing if n else playing


@app.callback(Output("interval", "disabled"), Input("is-playing", "data"))
def toggle_interval(playing):
    return not playing


@app.callback(
    Output("tijdslider", "value"),
    Input("interval", "n_intervals"),
    State("interval", "disabled"),
    State("tijdslider", "value"),
)
def advance_slider(n, disabled, current):
    if disabled or current is None:
        raise PreventUpdate
    return (current + 1) % len(all_datetimes)


@app.callback(
    Output("marker-mpn", "hideout"),
    Input("pgb-dropdown", "value"),
)
def update_mpn_markers(selected_location_id):
    if not selected_location_id:
        return []

    if "peilgebied_combi_attr" not in df_locs_mpn.columns:
        return []

    mask = df_locs_mpn["peilgebied_combi_attr"].astype(str) == str(selected_location_id)
    points = df_locs_mpn[mask]

    if points.empty:
        return []

    return points["peilgebied_combi_attr"].astype(str).dropna().unique().tolist()


if __name__ == "__main__":
    app.run(debug=True)

# %%
