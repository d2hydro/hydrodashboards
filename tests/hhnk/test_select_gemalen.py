#%%
from hydrodashboards import bokeh
from pathlib import Path

CONFIG_JSON = Path(__file__).parent.joinpath("app", "config.json")
bokeh.set_config_json(CONFIG_JSON)
bokeh.delete_cache()



from app.main import filters, parameters, locations, data, filters_widgets, config, start_time_series_loader, update_time_series_view

# for HHNK we ignore qualifiers
assert data.parameters.ignore_qualifiers

# select theme Kunstwerken and check labels of filters
FILTERS = ['Gemalen', 'Stuwen', 'Inlaten', 'Sluizen']
filters[0].active = [0]
assert filters[1].labels == FILTERS

# select first filter & check parameters
filters[1].active = [0]
assert "Bias" in parameters.labels
assert "'t Hoekje" in locations.labels

# select first location and parameter
parameters.active = [0]
locations.active = [0]

# %%
