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
                                        update_time_series_view,
                                        update_time_series_search
                                        )

filters[0].active = [1]
locations.active = [0]
parameters.active = [0, 1]

start_time_series_loader()
update_time_series_view()
update_time_series_search()

search_period.children[0].value = "2017-01-01"



# for time_series in data.time_series_sets.time_series:
#     time_series.to_cache()
