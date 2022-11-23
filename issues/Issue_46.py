from hydrodashboards.bokeh.main import (
    filters,
    parameters,
    locations,
    data,
    start_time_series_loader,
    update_time_series_view,
    time_figure_layout,
    search_time_figure_layout,
)

WARNING = "no time series for selected locations and parameters"

# choose theme oppervlaktewater
filters[0].active = [0]
# choose filter gemaal
filters[1].active = [4]

# choose location abelstok

id = locations.labels.index("Triplum (KGM071)")
locations.active = [id]

# choose debiet
parameters.active = [0]

start_time_series_loader()
update_time_series_view()

assert not data.time_series_sets.any_active
assert WARNING in search_time_figure_layout.children[0].text
assert WARNING in time_figure_layout.children[0].text
