# %%
import math
import time
from datetime import timedelta
from pathlib import Path

import bokeh.models.widgets as bwidgets
import bokeh_helpers as bh
import numpy as np
import pandas as pd
from bokeh.io import curdoc
from bokeh.models import (
    BoxSelectTool,
    ColumnDataSource,
    CustomJS,
    CustomJSHover,
    CustomJSTickFormatter,
    DatetimePicker,
    HoverTool,
    Label,
    LinearColorMapper,
    PanTool,
    Range1d,
    RangeTool,
    ResetTool,
    Select,
    Span,
    TapTool,
    WheelZoomTool,
)
from bokeh.palettes import Blues5
from bokeh.plotting import figure
from bokeh_helpers.bokeh_logger import get_bokeh_logger
from bokeh_helpers.callbacks import animate_button

# import local modules
from bokeh_helpers.fews_api.api_config import ApiConfig
from bokeh_helpers.widgets import DateTimeSpan, map_figure_widget
from read import read_mpn_locs, read_peilgebieden

# globals
CONFIG_JSON = Path(__file__).parent.joinpath("config.json")
STEP = timedelta(minutes=15)
DATA_DIR = Path(__file__).parent / "data"

config = ApiConfig.from_json(CONFIG_JSON)
t0 = time.time()

# %% init logger
app_file = Path(__file__)
logger = get_bokeh_logger(app_file)
logger.info("start loading document")

peilgebieden_gpkg = DATA_DIR / "peilgebieden_cso_combi.shp"


def get_pivot(feather_timeseries: bh.FeatherTimeseries, df_locs: pd.DataFrame, location_ids: list = []):
    # TODO staat ook in EGV
    if "value" in df_locs.columns:
        _df_locs = df_locs.drop(columns="value")
    else:
        _df_locs = df_locs

    df_vals_pivot = feather_timeseries.as_pivot(
        location_ids,
    )

    df_vals_pivot = df_vals_pivot.merge(_df_locs, left_index=True, right_on="location_id", how="left")
    df_vals_pivot["line_color"] = None
    df_vals_pivot["line_color_legend"] = "."

    if "x" in df_vals_pivot:
        xcol = "x"
    elif "xs" in df_vals_pivot:
        xcol = "xs"
    missing_locs = df_vals_pivot[df_vals_pivot[xcol].isna()]

    if not missing_locs.empty:
        logger.warning(f"miss locations. Fix please:{missing_locs}")

    return df_vals_pivot


def get_bound_value(values, increment=1, offset=1, function=max, method="ceil"):
    # Return zero when values are empty. Otherwise the function will raise.
    if len(values) == 0:
        return 0

    values = np.concatenate(values).ravel()
    if method in ["floor", "ceil"]:
        rounder = getattr(math, method)
    else:
        rounder = round

    value = function(values) + offset
    return rounder(value / increment) * increment


def get_bounds(values, min_range):
    increment = min_range / 2
    min_value = get_bound_value(values, increment=increment, offset=-increment, function=min, method="floor")
    max_value = get_bound_value(values, increment=increment, offset=increment, function=max, method="ceil")
    return min_value, max_value


def update_overlay_source(attrname, old, new):
    date_time_picker.value = span_selected_time.snapped_location

    date_time = span_selected_time.snapped_location_as_datetime

    source_pgb.data["vullingsgraad"], _ = feather_vullingsgraad.at_timestep(
        date_time, df_locs=df_locs_pgb, loc_id_col="location_id"
    )
    source_pgb.data["vulling_mm"], _ = feather_berging.at_timestep(
        date_time, df_locs=df_locs_pgb, loc_id_col="location_id"
    )


def update_locations_select(attr, old, new):
    if new is not None:
        indices = [list(source_pgb.data["naam"]).index(new)]
        # make sure we only set source_pgb when it's not allready set in callback_select_location
        if not all(i in source_pgb.selected.indices for i in indices):
            source_pgb.selected.indices = [list(source_pgb.data["naam"]).index(new)]


def callback_select_location(attr, old, new):
    """Callback when selecting pbg on map."""
    logger.debug(f"select location(s): {new}")
    if new == []:  # If deselected, clear graph source
        source_vullingsgraad.data = {"datetime": [], "value": [], "location_id": [], "naam": []}
        source_berging.data = {"datetime": [], "value": [], "location_id": [], "naam": []}
        source_wlvl.data = {"location_id": [], "datetime": [], "value": [], "color": [], "x": [], "y": []}
        select_peilgebied.value = None
        fig_berging.y_range.end = 60
        fig_wlvl.y_range.end = 0.1
        fig_wlvl.y_range.start = -0.1

        fig_berging.y_range.reset_end = 60
        fig_wlvl.y_range.reset_end = 0.1
        fig_wlvl.y_range.reset_start = -0.1

    else:
        t0 = time.time()
        source_wlvl.selected.indices = []

        # Get peilgebied_id
        pgb_id = source_pgb.data["location_id"][new][-1]
        pgb_naam = df_locs_pgb[df_locs_pgb["location_id"] == pgb_id]["naam"].iloc[0]

        # Update vullingsgraad [%] grafiek (source_vullingsgraad)
        df = get_pivot(feather_timeseries=feather_vullingsgraad, df_locs=df_locs_pgb, location_ids=[pgb_id])
        df["naam"] = pgb_naam
        source_vullingsgraad.data = ColumnDataSource.from_df(df)

        # Update vulling [mm] grafiek (source_berging)
        df = get_pivot(feather_timeseries=feather_berging, df_locs=df_locs_pgb, location_ids=[pgb_id])
        df["naam"] = pgb_naam
        source_berging.data = ColumnDataSource.from_df(df)

        # Select wlvl meetlocaties
        mpn_locations = df_locs_mpn[df_locs_mpn["peilgebied_combi_attr"] == pgb_id]
        mpn_location_ids = mpn_locations["location_id"].to_list()
        mpn_wlvl = get_pivot(feather_wlvl_mpn, df_locs_mpn, location_ids=mpn_location_ids)
        mpn_wlvl["color"] = "grey"

        # Wlvl peilgebied
        pgb_wlvl = get_pivot(feather_wlvl_pgb, df_locs_pgb, location_ids=[pgb_id])
        pgb_wlvl["color"] = "blue"

        # Samenvoegen indiv ws mpn en pgb gemiddelde.
        source_wlvl_df = pd.concat([mpn_wlvl, pgb_wlvl]).reset_index()
        source_wlvl.data = ColumnDataSource.from_df(source_wlvl_df)

        # Update spans
        pgb_row = df.iloc[0]
        span_overlast_berging.location = pgb_row["berging_bij_inundatiepeil"]
        span_inundatiepeil.location = pgb_row["inundatiepeil"] * 10  # FIXME eenheden gelijk zetten in CSO
        span_streefpeil.location = pgb_row["streefpeil"] * 1000  # FIXME eenheden gelijk zetten in CSO
        span_nulpeil.location = pgb_row["peil_bij_nul_berging"] * 10  # FIXME eenheden gelijk zetten in CSO

        label_overlast_berging.y = pgb_row["berging_bij_inundatiepeil"]
        label_inundatiepeil.y = pgb_row["inundatiepeil"] * 10
        label_streefpeil.y = pgb_row["streefpeil"] * 1000
        label_nulpeil.y = pgb_row["peil_bij_nul_berging"] * 10

        # Update ranges
        fig_berging.y_range.end = max(get_bound_value(source_berging.data["value"], increment=5), 60)

        fig_wlvl.y_range.start, fig_wlvl.y_range.end = get_bounds(source_wlvl.data["value"], min_range=0.2)

        if len(source_vullingsgraad.data["datetime"]) > 0:
            start_datetime = min(np.concatenate(source_vullingsgraad.data["datetime"]).ravel())
            end_datetime = max(np.concatenate(source_vullingsgraad.data["datetime"]).ravel())
            select_xrange.x_range.start, select_xrange.x_range.end = start_datetime, end_datetime
            date_time_picker.min_date, date_time_picker.max_date = start_datetime, end_datetime

        fig_berging.y_range.reset_end = fig_berging.y_range.end
        fig_wlvl.y_range.reset_start = fig_wlvl.y_range.start
        fig_wlvl.y_range.reset_end = fig_wlvl.y_range.end

        select_peilgebied.value = pgb_naam

        logger.info(f"selected peilgebied {pgb_naam} ({pgb_id}) in {(time.time() - t0):.3f}")


def change_overlay(attr, old, new):
    variable_id = map_variable_options.loc[new]
    polygons_pgb.glyph.fill_color.field = variable_id
    if variable_id == "vulling_mm":
        polygons_pgb.glyph.fill_color.transform.palette = pallete_berging
        polygons_pgb.glyph.fill_color.transform.high = 60
    elif variable_id == "vullingsgraad":
        polygons_pgb.glyph.fill_color.transform.palette = palette_vullingsgraad
        polygons_pgb.glyph.fill_color.transform.high = 100


def update_map_figure_background_control(attrname, old, new):
    """Update map_figure when background is selected"""
    tile_source = map_figure_widget.get_tilesource(map_options.children[-1].labels[new])
    idx = next(idx for idx, i in enumerate(map_figure.renderers) if i.name == "background")
    map_figure.renderers[idx].tile_source = tile_source


def update_map_figure_overlay_control(attrname, old, new):
    """Update visible map-overlays on change"""
    map_overlays = map_options.children[0]
    map_fig_idx = {i.name: idx for idx, i in enumerate(map_figure.renderers) if i.name in map_overlays.labels}
    for idx, i in enumerate(map_overlays.labels):
        if idx in new:
            map_figure.renderers[map_fig_idx[i]].visible = True
        else:
            map_figure.renderers[map_fig_idx[i]].visible = False


### Play button
def animate_update():
    """Add 1 timestep during animation."""
    # stop if we reach the end
    next_step = span_selected_time.widget.location + span_selected_time.step
    if (next_step > bh.to_miliseconds(xrange.end)) or (next_step < bh.to_miliseconds(xrange.start)):
        span_selected_time.widget.location = xrange.start
    else:
        span_selected_time.set_location(next_step)
    update_overlay_source(None, None, None)


def update_on_time_picker_location(attrname, old, new):
    span_selected_time.set_location(date_time_picker.value)


# %% VULLINGSGRAAD uit fews
feather_vullingsgraad = bh.FeatherTimeseries(
    name="vullingsgraad",
    file_path=DATA_DIR / "vullingsgraad.arrow",
    value_col="value",
    int_factor=1,
)

feather_berging = bh.FeatherTimeseries(
    name="berging",
    file_path=DATA_DIR / "vulling.arrow",
    value_col="value",
    int_factor=10,
)

logger.debug(f"init feather time series: {(time.time() - t0):.3f} seconds")


# Inlezen location dfs
df_locs_mpn = read_mpn_locs(file_path=DATA_DIR / "mpn_locations.arrow")


df_locs_pgb = read_peilgebieden(
    file_path=peilgebieden_gpkg,
    code_col="CODE",
    columns=["naam", "streefpeil", "inundatiepeil", "berging_bij_inundatiepeil", "peil_bij_nul_berging"],
)
logger.debug(f"read location-files: {time.time() - t0}")

# Vul peilgebieden met laatste beschikbare waarde
df_locs_pgb.loc[:, ["vullingsgraad"]], _ = feather_vullingsgraad.at_timestep(
    feather_vullingsgraad.df.datetime.max(), df_locs=df_locs_pgb, loc_id_col="location_id"
)
logger.debug(f"pivot vullingsgraad: {(time.time() - t0):.3f}")

df_locs_pgb.loc[:, ["vulling_mm"]], _ = feather_berging.at_timestep(
    feather_vullingsgraad.df.datetime.max(), df_locs=df_locs_pgb, loc_id_col="location_id"
)
logger.debug(f"pivot vullingsgraad_mm: {(time.time() - t0):.3f}")


feather_wlvl_mpn = bh.FeatherTimeseries(
    name="wlvl_mpn",
    file_path=DATA_DIR / "waterstand_meetpunt.arrow",
    value_col="value",
    int_factor=1000,
)
feather_wlvl_pgb = bh.FeatherTimeseries(
    name="wlvl_pgb",
    file_path=DATA_DIR / "waterstand_pgb.arrow",
    value_col="value",
    int_factor=1000,
)

logger.debug(f"init time-series: {(time.time() - t0):.3f}")

# kaart
df_locs_pgb["naam"] = df_locs_pgb["naam"] + " (" + df_locs_pgb["location_id"] + ")"
source_pgb = ColumnDataSource(df_locs_pgb)
palette_vullingsgraad = ["green", "yellow", "orange", "red"]
pallete_berging = list(Blues5)[::-1]
cm_percentage = LinearColorMapper(palette=palette_vullingsgraad, low=0, high=100, nan_color="rgba(112, 112, 112, 0.5)")

map_figure = map_figure_widget.make_map(
    bounds=config.bounds,
    locations_source=None,
    map_overlays=config.map_overlays,
)


polygons_pgb = map_figure.multi_polygons(
    xs="xs",
    ys="ys",
    source=source_pgb,
    line_color=None,
    fill_color={"field": "vullingsgraad", "transform": cm_percentage},
    selection_fill_alpha=1,
    selection_line_color="yellow",
    selection_line_width=2,
    nonselection_fill_alpha=0.9,
)

hover_polygons_pgb = HoverTool(
    tooltips=[
        ("naam", "@naam"),
        ("code", "@location_id"),
        ("vullingsgraad", "@vullingsgraad [%]"),
        ("vulling", "@vulling_mm [mm]"),
    ],
    renderers=[polygons_pgb],
)
hover_polygons_pgb.visible = False

map_tap = TapTool(mode="replace", renderers=[polygons_pgb])
map_select = BoxSelectTool(renderers=[polygons_pgb])

map_wheelzoom = WheelZoomTool()
map_figure.tools = [
    map_wheelzoom,
    PanTool(),
    ResetTool(),
    map_select,
    map_tap,
    hover_polygons_pgb,
]
map_figure.toolbar.active_drag = map_select
map_figure.toolbar.active_scroll = map_wheelzoom

source_vullingsgraad = ColumnDataSource({"datetime": [], "value": [], "location_id": [], "naam": []})
source_berging = ColumnDataSource({"datetime": [], "value": [], "location_id": [], "naam": []})
source_wlvl = ColumnDataSource(
    {"naam": [], "location_id": [], "datetime": [], "value": [], "color": [], "x": [], "y": []}
)

source_pgb.selected.on_change("indices", callback_select_location)


scatter_mpns = map_figure.scatter(
    x="x",
    y="y",
    source=source_wlvl,
    size=10,
    fill_color="#2171b5",
    line_color="black",
    selection_color="yellow",
    selection_line_color="red",
    selection_fill_alpha=1,
    hover_color="red",
    hover_line_color="yellow",
    hover_fill_alpha=1,
    nonselection_fill_alpha=0.6,
    nonselection_line_alpha=0.5,
    hit_dilation=2,
)

hover_scatter_mpns = HoverTool(
    tooltips=[
        ("naam", "@naam"),
        ("code", "@location_id"),
    ],
    renderers=[scatter_mpns],
)
hover_scatter_mpns.visible = False
map_figure.tools += [hover_scatter_mpns]

logger.debug(f"create map figure: {(time.time() - t0):.3f}")


# Vertical line in timeseries figure
start_dt = feather_vullingsgraad.df.datetime.min()
end_dt = feather_vullingsgraad.df.datetime.max()
span_selected_time = DateTimeSpan(
    start=start_dt,
    end=end_dt,
    location=end_dt,
    step=STEP,
    kwargs=dict(dimension="height", line_color="grey", line_dash="dotted"),
)

span_selected_time.widget.on_change("location", update_overlay_source)

date_time_picker = DatetimePicker(
    second_increment=int(STEP.total_seconds()),
    minute_increment=int(STEP.total_seconds() / 60),
    value=end_dt,
    position="above",
    sizing_mode="stretch_both",
    name="date_time_picker",
)


date_time_picker.on_change("value", update_on_time_picker_location)


span_hover = Span(dimension="height", line_width=0.5, line_color="grey", line_dash="dotted")

# Selecteer kaart variabele (vullingsgraad of vulling)
map_variable_options = pd.Series(index=["vullingsgraad [%]", "vulling [mm]"], data=["vullingsgraad", "vulling_mm"])
select_map_variable = Select(
    title="kaartvariabele:",
    description="Kies de variabele voor op de kaart",
    value=map_variable_options.index[0],
    options=map_variable_options.index.to_list(),
    name="select_kaartvariabele",
    width=175,
)
select_map_variable.on_change("value", change_overlay)


# Selecteer peilgebied dropdown
peilgebieden_options = df_locs_pgb.set_index("naam")["location_id"]
peilgebieden_options = peilgebieden_options[peilgebieden_options.index.notna()]
peilgebieden_options.sort_index(inplace=True)
select_peilgebied = Select(
    title="peilgebied:",
    description="Selecteer een peilgebied (op de kaart)",
    options=list(peilgebieden_options.index.unique()),
    name="select_peilgebied",
    width=175,
)
select_peilgebied.on_change("value", update_locations_select)


def callback_tap_figure(event):
    """On clicking the figure, find the closest time in the available data
    and draw a vertical line. Update the map as well.
    """
    span_selected_time.set_location(event.x)


mm_to_m = CustomJSHover(
    code="""
    return (special_vars.y / 1000).toFixed(3)
"""
)

hover_fig_wlvl = HoverTool(
    line_policy="nearest",
    formatters={"$snap_x": "datetime", "@y": mm_to_m},
    tooltips=[
        ("datum", "$snap_x{%Y-%m-%d %H:%M}"),
        ("waarde", "@y{custom}"),
        ("naam", "@naam"),
    ],
)

hover_fig = HoverTool(
    line_policy="nearest",
    formatters={"$snap_x": "datetime"},
    tooltips=[
        ("datum", "$snap_x{%Y-%m-%d %H:%M}"),
        ("waarde", "$snap_y"),
        ("naam", "@naam"),
    ],
)

# Create three scatter plots
xrange = Range1d(
    start=start_dt,
    end=end_dt,
    min_interval=STEP,
)


fig_vullingsgraad = figure(
    background_fill_color="#fafafa",
    x_axis_type="datetime",
    name="fig_vullingsgraad",
    sizing_mode="stretch_both",
    active_scroll="xwheel_zoom",
    active_drag="xbox_zoom",
    title="vullingsgraad [%]",
    tools=[hover_fig, "tap,pan,wheel_zoom,xwheel_zoom,ywheel_zoom,box_zoom,xbox_zoom,save,reset,help"],
    x_range=xrange,
    y_range=(-5, 105),
    min_border_left=45,
)

fig_vullingsgraad.xaxis.formatter = bh.xaxis_date_formatter()
# Let span follow mouse
callback = CustomJS(args=dict(span=span_hover), code="span.location = cb_obj.x;")

# Add a mouseleave callback to reset the Span position
mouseleave_callback = CustomJS(args=dict(span=span_hover), code="span.location = 0")

fig_vullingsgraad.js_on_event("mousemove", callback)
fig_vullingsgraad.js_on_event("mouseleave", mouseleave_callback)  # Add the mouseleave event

bh.add_box_annotations(
    fig_vullingsgraad,
    [
        {"top": 25},
        {"bottom": 25, "top": 50},
        {"bottom": 50, "top": 75},
        {"bottom": 75},
    ],
    palette=palette_vullingsgraad,
)

fig_vullingsgraad.multi_line(xs="datetime", ys="value", source=source_vullingsgraad, color="blue", line_width=2)
bh.apply_default_toolbar(fig_vullingsgraad)
fig_vullingsgraad.on_event("tap", callback_tap_figure)
fig_vullingsgraad.add_layout(span_selected_time.widget)
fig_vullingsgraad.add_layout(span_hover)

fig_berging = figure(
    background_fill_color="#fafafa",
    name="fig_berging",
    sizing_mode="stretch_both",
    title="vulling [mm]",
    active_scroll="xwheel_zoom",
    tools=[hover_fig, "tap,pan,wheel_zoom,xwheel_zoom,ywheel_zoom,box_zoom,xbox_zoom,save,reset,help"],
    x_range=xrange,
    y_range=(0, 60),
    min_border_left=45,
)

fig_berging.xaxis.formatter = bh.xaxis_date_formatter()

fig_berging.js_on_event("mousemove", callback)
fig_berging.js_on_event("mouseleave", mouseleave_callback)
# Horizontal spans
span_overlast_berging = Span(dimension="width", line_color="red", line_width=2, line_dash="dotted", location=45)
label_overlast_berging = Label(
    x=span_selected_time.start, y=45, text="overlast", text_color="red", text_font_size="12px"
)
span_inundatiepeil = Span(dimension="width", line_color="red", line_width=2, line_dash="dotted", location=0.5)
label_inundatiepeil = Label(
    x=span_selected_time.start, y=0.5, text="inundatiepeil", text_color="red", text_font_size="12px"
)
span_streefpeil = Span(dimension="width", line_color="orange", line_width=2, line_dash="dotted", location=0.25)
label_streefpeil = Label(
    x=span_selected_time.start, y=0.25, text="streefpeil", text_color="orange", text_font_size="12px"
)
span_nulpeil = Span(dimension="width", line_color="green", line_width=2, line_dash="dotted", location=0)
label_nulpeil = Label(x=span_selected_time.start, y=0, text="nulpeil", text_color="green", text_font_size="12px")


bh.add_box_annotations(
    fig_berging,
    [
        {"top": 10},
        {"bottom": 10, "top": 20},
        {"bottom": 20, "top": 30},
        {"bottom": 30, "top": 40},
        {
            "bottom": 40,
        },
    ],
    palette=pallete_berging,
)

fig_berging.multi_line(xs="datetime", ys="value", source=source_berging, color="blue", line_width=2)
fig_berging.add_layout(span_overlast_berging)
bh.apply_default_toolbar(fig_berging)
fig_berging.on_event("tap", callback_tap_figure)
fig_berging.add_layout(span_selected_time.widget)
fig_berging.add_layout(label_overlast_berging)
fig_berging.add_layout(span_hover)

logger.debug(f"berging figure: {time.time() - t0:.3f}")


fig_wlvl = figure(
    background_fill_color="#fafafa",
    name="fig_wlvl",
    sizing_mode="stretch_both",
    title="waterstand [mNAP]",
    active_scroll="xwheel_zoom",
    tools=[hover_fig_wlvl, "tap,pan,wheel_zoom,xwheel_zoom,ywheel_zoom,box_zoom,xbox_zoom,save,reset,help"],
    x_range=xrange,
    y_range=(-1000, 1000),
    lod_factor=1000,
    lod_threshold=20,
    lod_interval=2000,
    min_border_left=45,
)
fig_wlvl.js_on_event("mousemove", callback)
fig_wlvl.js_on_event("mouseleave", mouseleave_callback)
y_axis_format = """
    return (tick / 1000).toFixed(3)
"""

fig_wlvl.yaxis.formatter = CustomJSTickFormatter(code=y_axis_format)
fig_wlvl.xaxis.formatter = bh.xaxis_date_formatter()


fig_wlvl.multi_line(
    xs="datetime",
    ys="value",
    source=source_wlvl,
    line_color="color",
    hover_line_width=2,
    hover_line_color="blue",
    selection_width=2,
    selection_line_color="blue",
    nonselection_alpha=0.6,
)
fig_wlvl.on_event("tap", callback_tap_figure)
fig_wlvl.add_layout(span_selected_time.widget)
fig_wlvl.add_layout(span_inundatiepeil)
fig_wlvl.add_layout(label_inundatiepeil)
fig_wlvl.add_layout(span_streefpeil)
fig_wlvl.add_layout(label_streefpeil)
fig_wlvl.add_layout(span_nulpeil)
fig_wlvl.add_layout(label_nulpeil)
fig_wlvl.add_layout(span_hover)


logger.debug(f"wlvl figure: {time.time() - t0:.3f}")

# Move labels when xrange changes so its always visible at same position
xrange.js_on_change(
    "start",
    CustomJS(
        args={
            "overlast_berging_label": label_overlast_berging,
            "inundatiepeil_label": label_inundatiepeil,
            "streefpeil_label": label_streefpeil,
            "nulpeil_label": label_nulpeil,
        },
        code="""
overlast_berging_label.x = this.start
inundatiepeil_label.x = this.start
streefpeil_label.x = this.start
nulpeil_label.x = this.start
""",
    ),
)

bh.apply_default_toolbar(fig_wlvl)


#
select_xrange = figure(
    y_range=fig_vullingsgraad.y_range,
    x_axis_type=None,
    y_axis_type=None,
    tools="",  # "reset,xwheel_zoom",
    # active_scroll="xwheel_zoom",
    toolbar_location=None,
    background_fill_color="#efefef",
    name="select_xrange",
    sizing_mode="stretch_both",
)

# Set initial xrange so we can still select timestamp when we dont have any location selected
select_xrange.x_range.start = xrange.start
select_xrange.x_range.end = xrange.end
select_xrange.add_layout(span_selected_time.widget)
select_xrange.toolbar.logo = None
range_tool = RangeTool(x_range=xrange)
range_tool.overlay.fill_color = "navy"
range_tool.overlay.fill_alpha = 0.2


select_xrange.multi_line(xs="datetime", ys="value", source=source_vullingsgraad, color="blue", line_width=1)
select_xrange.ygrid.grid_line_color = None
select_xrange.add_tools(range_tool)

select_xrange.on_event("tap", callback_tap_figure)


button_play = bwidgets.Button(label="► Play", width=60, name="play_button", sizing_mode="stretch_both")
button_play.on_click(animate_button(button=button_play, update_function=animate_update))
###

# Map options widget
map_options = map_figure_widget.make_options(
    map_overlays=config.map_overlays,
    overlays_change=update_map_figure_overlay_control,
    background_title="Achtergrond",
    background_change=update_map_figure_background_control,
)
map_options.name = "map_options"

# toevoegen aan app
map_figure.sizing_mode = "stretch_both"
map_figure.name = "map_figure"

map_figure.match_aspect = True

curdoc().add_root(map_figure)
curdoc().add_root(select_xrange)
curdoc().add_root(fig_vullingsgraad)
curdoc().add_root(fig_berging)
curdoc().add_root(fig_wlvl)
curdoc().add_root(button_play)
curdoc().add_root(map_options)
curdoc().add_root(select_peilgebied)
curdoc().add_root(select_map_variable)
curdoc().add_root(date_time_picker)
curdoc().title = "Vullingsgraad"

logger.info(f"app loaded in: {(time.time() - t0):.3f} seconds")
