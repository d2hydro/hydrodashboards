from hydrodashboards import bokeh

# %% here we overwrite the default (WAM) config with WIK
AAM_CONFIG_JSON = r"data\wik_config.json"
bokeh.set_config_json(AAM_CONFIG_JSON)
bokeh.delete_cache()

# %% now we import main (will be initialized for WIK)
from hydrodashboards.bokeh.main import (filters,
                                        data,
                                        locations,
                                        parameters,
                                        time_figure_layout,
                                        start_time_series_loader,
                                        update_time_series_view) # noqa 
def load_time_series():
    update_time_series_view()
    start_time_series_loader()

#def test_do_not_expand_parameter_labels():
filters[0].active = [0]  # select Keten.Neerslag
locations.active = [0]  # select 't Heufke
parameters_labels = parameters.labels
parameters.active = [0]  # select Neerslag (gecalibreerde radar)

load_time_series()

time_fig = time_figure_layout.children[0].children[0]
figure_id = time_fig.id
renderer_id = time_fig.renderers[0].id
line_color = time_fig.renderers[0].glyph.line_color

# %%
load_time_series()

time_fig = time_figure_layout.children[0].children[0]
assert time_fig.id == figure_id
assert time_fig.renderers[0].id == renderer_id
assert time_fig.renderers[0].glyph.line_color == line_color

locations.active = [0, 1]
load_time_series()

# %%
locations.active = [0]
load_time_series()