from hydrodashboards import bokeh
from config import wik_config

# %% here we overwrite the default (WAM) config with WIK
wik_config()

# %% now we import main (will be initialized for WIK)
from hydrodashboards.bokeh.main import filters, data, locations, parameters  # noqa


def test_do_not_expand_parameter_labels():
    filters[0].active = [0]  # select Keten.Neerslag
    locations.active = [0]  # select 't Heufke
    parameters_labels = parameters.labels
    assert len(data.parameters._options) == 3  # 3 select-able parameters
    parameters.active = [0]  # select Neerslag (gecalibreerde radar)
    filters[1].active = [0]  # select Oppervlaktewater.Oppervlaktewater...
    assert parameters.labels == parameters_labels
    assert len(data.parameters._options) == 19  # 19 select-able parameters