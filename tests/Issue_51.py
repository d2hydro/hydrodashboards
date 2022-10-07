from hydrodashboards.bokeh.main import (
    filters,
    parameters,
    locations,
    data,
    start_time_series_loader,
    update_time_series_view,
    update_time_series_search,
    time_figure_layout,
    get_visible_sources,
    toggle_download_button_on_sources,
    download_time_series,
    update_on_view_period_value_throttled,
    view_period,
    view_x_range,
    search_period,
    convert_to_datetime,
)
from bokeh.plotting import Figure

def load_data():
    start_time_series_loader()
    update_time_series_view()
    update_time_series_search()

# ValueError: ('NL34.FC.1102', 'Ca [mg/l] [nf] [OW] * CT_4*CF_2*MI_62*WW_5*WM_1000*WT_121*BM_369*BA_57') is not in list
# choose theme
filters[0].active = [2]
# choose filter
filters[1].active = [0]

# choose location
locations.active =  [3]

# choose debiet 
parameter = "Ca [mg/l] [nf] [OW] * CT_4*CF_2*MI_62*WW_5*WM_1000*WT_121*BM_369*BA_57"
values = [i[0] for i in data.parameters.options]
active = [values.index(parameter)]
parameters.active = active

load_data()