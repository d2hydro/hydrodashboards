from config import wik_config
wik_config()

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
    filters[0].active = []

# %% select filter keten.rioolgemalen, location 't Broek and all params
filters[0].active = [1]
locations.active = [0]
parameters.active = [0, 1]

# %% add keten.neerslag to selection and add location 't Heufke
filters[0].active = [0, 1]
locations.active = [0, 1]  # here is our bug

# # fix section
# data.locations.set_active([0, 1])
#         # data.locations.set_active(locations.active)
# values = data.locations.value
# self = data
# self.locations.set_value(values)
#data.update_on_locations_select(data.locations.value)
# parameters.labels should be extended with Neerslag... (3x)