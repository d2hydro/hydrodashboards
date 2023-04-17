from hydrodashboards import bokeh
from config import wik_config

# %% here we overwrite the default (WAM) config with WIK
wik_config()

# %% now we import main (will be initialized for WIK)
from hydrodashboards.bokeh.main import (
    filters,
    data,
    locations,
    parameters,
    time_figure_layout,
    start_time_series_loader,
    update_time_series_view,
)  # noqa


def load_time_series():
    update_time_series_view()
    start_time_series_loader()


# def test_retain_renderer_objects():
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
