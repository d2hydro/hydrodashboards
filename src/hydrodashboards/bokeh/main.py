"""Bokeh HydroDashboard"""

from bokeh.io import curdoc
from data import Data
from config import TITLE

data = Data()

# add widgets to curdoc
#  left column layout
curdoc().add_root(data.filters.bokeh)
curdoc().add_root(data.locations.bokeh)
curdoc().add_root(data.parameters.bokeh)
curdoc().add_root(data.search_period.bokeh)
curdoc().add_root(data.update_graph.bokeh)

#  map-figure layout
curdoc().add_root(data.map_figure.bokeh)
curdoc().add_root(data.map_options.bokeh)
curdoc().add_root(data.status.bokeh)

#  time-figure layout
curdoc().add_root(data.time_figure.bokeh)
curdoc().add_root(data.select_search_time_series.bokeh)
curdoc().add_root(data.download_search_time_series.bokeh)
curdoc().add_root(data.view_period.bokeh)
curdoc().add_root(data.search_time_figure.bokeh)

curdoc().title = TITLE
