from bokeh.models import (
    HoverTool,
    Range1d,
    ColumnDataSource,
    BBoxTileSource,
    TapTool,
)
from bokeh.plotting import figure
from bokeh.layouts import row, column
import bokeh.models as bokeh_models
from bokeh.models.widgets import Div, RadioGroup, CheckboxGroup


BOKEH_BACKGROUNDS = {
    "luchtfoto": {
        "url": (
            "https://service.pdok.nl/hwh/luchtfotorgb/wms/v1_0?"
            "service=WMS&version=1.3.0&request=GetMap&layers=Actueel_orthoHR"
            "&width=265&height=265&styles=&crs=EPSG:28992&format=image/jpeg"
            "&bbox={XMIN},{YMIN},{XMAX},{YMAX}"
        ),
        "class": "BBoxTileSource",
    },
    "topografie": {
        "url": (
            "https://services.arcgisonline.nl/arcgis/rest/services/Basiskaarten/Topo/"
            "MapServer/export?"
            "bbox={XMIN},{YMIN},{XMAX},{YMAX}"
            "&layers=show"
            "&size=385,385"
            "&bboxSR=28892"
            "&dpi=2500"
            "&transparent=true"
            "&format=png"
            "&f=image"
        ),
        "class": "BBoxTileSource",
    },
}

BOKEH_LOCATIONS_SETTINGS = {
    "size": 10,
    "line_color": "line_color",
    "fill_color": "fill_color",
    "selection_color": "red",
    "selection_fill_alpha": 1,
    "nonselection_fill_alpha": 0.6,
    "nonselection_line_alpha": 0.5,
    "hover_color": "red",
    "hover_alpha": 0.6,
    "line_width": 1,
    "legend_field": "label",
}

BOKEH_SETTINGS = {
    "background": "topografie",
    "save_tool": "save",
    "active_scroll": "wheel_zoom",
    "toolbar_location": "above",
}


def get_tilesource(layer, map_configs=BOKEH_BACKGROUNDS):
    url = map_configs[layer]["url"]
    if "args" in map_configs[layer]:
        args = map_configs[layer]["args"]
    else:
        args = {}
    return getattr(bokeh_models, map_configs[layer]["class"])(url=url, **args)


def make_map(
    bounds: list,
    locations_source: ColumnDataSource,
    map_overlays: dict = {},
    settings=BOKEH_SETTINGS,
) -> row:
    # figure ranges
    x_range = Range1d(start=bounds[0], end=bounds[2], min_interval=100)
    y_range = Range1d(start=bounds[1], end=bounds[3], min_interval=100)

    # set tools
    map_hover = HoverTool(tooltips=[("Locatie", "@name"), ("ID", "@id")])

    map_hover.toggleable = False

    tools = [
        "tap",
        "wheel_zoom",
        "pan",
        "reset",
        "box_select",
        map_hover,
        "save",
    ]

    # initialize figure
    map_fig = figure(
        tools=tools,
        active_scroll=settings["active_scroll"],
        x_range=x_range,
        y_range=y_range,
        toolbar_location=settings["toolbar_location"],
    )

    # misc settings
    map_fig.axis.visible = False
    map_fig.toolbar.logo = None
    map_fig.toolbar.autohide = True
    map_fig.xgrid.grid_line_color = None
    map_fig.ygrid.grid_line_color = None
    map_fig.select(type=TapTool)

    # add background
    tile_source = get_tilesource(settings["background"])
    map_fig.add_tile(tile_source, name="background")

    # add custom map-layers (if any)
    if map_overlays:
        layer_names = list(map_overlays.keys())
        layer_names.reverse()
        for layer_name in layer_names:
            tile_source = get_tilesource(layer_name, map_configs=map_overlays)
            if "alpha" in map_overlays[layer_name].keys():
                alpha = map_overlays[layer_name]["alpha"]
            else:
                alpha = 1
            map_fig.add_tile(
                tile_source,
                name=layer_name,
                visible=map_overlays[layer_name]["visible"],
                alpha=alpha,
            )

    # add locations glyph
    map_fig.circle(x="x", y="y", source=locations_source, **BOKEH_LOCATIONS_SETTINGS)

    return map_fig


def make_options(
    map_overlays: dict,
    overlays_change,
    background_title: str,
    background_change,
):
    # set overlay and handlers
    overlay_options = list(map_overlays.keys())
    active_overlays = [
        idx for idx, (_, v) in enumerate(map_overlays.items()) if v["visible"]
    ]
    overlay_control = CheckboxGroup(labels=overlay_options, active=active_overlays)
    overlay_control.on_change("active", overlays_change)

    # set background and handlers
    background_options = list(BOKEH_BACKGROUNDS.keys())
    background_active = list(BOKEH_BACKGROUNDS.keys()).index(
        BOKEH_SETTINGS["background"]
    )
    background_control = RadioGroup(labels=background_options, active=background_active)
    background_control.on_change("active", background_change)
    map_controls = column(
        overlay_control,
        Div(text=f"<h6>{background_title}</h6>"),
        background_control,
    )
    return map_controls
