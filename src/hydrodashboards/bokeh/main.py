"""Bokeh HydroDashboard"""
from bokeh.io import curdoc
from data import Data

from config import *

data = Data()



# add widgets to curdoc
## left column layout
curdoc().add_root(data.filters)
curdoc().add_root(data.locations)
curdoc().add_root(data.parameters)
curdoc().add_root(data.search_period)
curdoc().add_root(data.update_graph)

## map-figure layout
curdoc().add_root(data.map_figure)
curdoc().add_root(data.map_options)
curdoc().add_root(data.status)

## time-figure layout
curdoc().add_root(data.time_figure)
curdoc().add_root(data.select_search_time_series)
curdoc().add_root(data.download_search_time_series)
curdoc().add_root(data.view_period)
curdoc().add_root(data.search_time_figure)
"""

curdoc().title = TITLE
