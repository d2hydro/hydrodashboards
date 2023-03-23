from hydrodashboards import bokeh
from datetime import datetime
from bokeh.plotting import figure
from bokeh.io import show
from bokeh.models import ColumnDataSource,FuncTickFormatter

from hydrodashboards.bokeh.widgets.time_figure_widget import DT_JS_FORMAT


# %% here we overwrite the default (WAM) config with WIK
AAM_CONFIG_JSON = r"data\wik_config.json"
bokeh.set_config_json(AAM_CONFIG_JSON)
#bokeh.delete_cache()

# %% now we import main (will be initialized for WIK)
from hydrodashboards.bokeh.main import (data,
                                        filters,
                                        locations,
                                        parameters,
                                        search_period,
                                        start_time_series_loader,
                                        update_time_series_view
                                        )

filters[0].active = [0]
locations.active = [0]
parameters.active = [0,1,2]
search_period.children[0].value = "2017-01-01"

# %%
start_time_series_loader()
update_time_series_view()

# %% some code snippets
# self = data
# import itertools
# for location, parameter in itertools.product(
#         data.locations.value,
#         data.parameters.value
#         ):
#     self.time_series_sets.append_from_cache(location, parameter)
#self = data.time_series_sets
#time_series = self.time_series[0]
#time_series.to_cache()

# %%
# from hydrodashboards.datamodel.cache import Cache
# from hydrodashboards.datamodel import TimeSeriesSets
# df = ts.time_series[0].events

# def plot_fig(df):
#     fig = figure(sizing_mode="stretch_width", width=1200)
#     source = ColumnDataSource(data=df)
#     fig.line(x="datetime", y="value", source=source)
#     fig.xaxis.formatter = FuncTickFormatter(code=DT_JS_FORMAT.format("tick"))

#     show(fig)

# #%% example plot

# plot_fig(df.sample(min(len(df), 10000)).sort_index())

