from hydrodashboards import bokeh
from datetime import datetime
from bokeh.plotting import figure
from bokeh.io import show
from bokeh.models import ColumnDataSource,FuncTickFormatter

from hydrodashboards.bokeh.widgets.time_figure_widget import DT_JS_FORMAT


# %% here we overwrite the default (WAM) config with WIK
AAM_CONFIG_JSON = r"data\wik_config.json"
bokeh.set_config_json(AAM_CONFIG_JSON)
bokeh.delete_cache()

# %% now we import main (will be initialized for WIK)
from hydrodashboards.bokeh.main import data

# ts = data._fews_api.get_time_series(
#     filter_id=data.config.root_filter,
#     location_ids=["4120"],
#     parameter_ids=["Q.meting.m3uur"],
#     start_time=datetime(2017,6,29),
#     end_time=datetime(2020,6,13),
#     omit_missing=True,
#     )

# df = ts.time_series[0].events

# def plot_fig(df):
#     fig = figure(sizing_mode="stretch_width", width=1200)
#     source = ColumnDataSource(data=df)
#     fig.line(x="datetime", y="value", source=source)
#     fig.xaxis.formatter = FuncTickFormatter(code=DT_JS_FORMAT.format("tick"))

#     show(fig)

# #%% example plot

# plot_fig(df.sample(min(len(df), 10000)).sort_index())

