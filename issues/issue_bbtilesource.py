from bokeh.plotting import figure
import bokeh.models as bokeh_models
from bokeh.io import curdoc
from bokeh.models import Range1d

# define figure
bounds = [
    210000,
    544000,
    250000,
    625000
  ]
x_range = Range1d(start=bounds[0], end=bounds[2], min_interval=100)
y_range = Range1d(start=bounds[1], end=bounds[3], min_interval=100)
map_fig = figure(x_range=x_range,
        y_range=y_range,)

map_fig.xgrid.grid_line_color = None
map_fig.ygrid.grid_line_color = None

# add background
tile_source = bokeh_models.BBoxTileSource(
    url=(
            "https://service.pdok.nl/hwh/luchtfotorgb/wms/v1_0?"
            "service=WMS&version=1.3.0&request=GetMap&layers=Actueel_orthoHR"
            "&width=265&height=265&styles=&crs=EPSG:28992&format=image/jpeg"
            "&bbox={XMIN},{YMIN},{XMAX},{YMAX}"
        )
        )
map_fig.add_tile(tile_source, name="background")

# add second tile overlay
second_tile_source = bokeh_models.BBoxTileSource(
    url=("https://arcgis.noorderzijlvest.nl/server/rest/services/Watergangen/"
         "Watergangen/MapServer/export?dpi=96&bbox={XMIN},{YMIN},{XMAX},{YMAX}"
         "&bboxSR=28992&transparent=true&f=image&format=png8"
)
)

map_fig.add_tile(second_tile_source, name="water")


curdoc().add_root(map_fig)