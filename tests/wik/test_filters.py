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


def test_add_new_filter_and_location():
    # %% select filter keten.rioolgemalen, location 't Broek and all params
    filters[0].active = [1]
    locations.active = [0]
    parameters.active = [0, 1]
    assert parameters.labels == [
        "Gemeten debiet [m3/uur]",
        "Gemeten waterstand (m NAP)",
    ]

    # %% add keten.neerslag to selection and add location 't Heufke
    filters[0].active = [0, 1]
    locations.active = [0, 1]  # here is our bug
    assert parameters.labels == [
        "Gemeten debiet [m3/uur]",
        "Gemeten waterstand (m NAP)",
        "Neerslag (gecalibreerde radar)",
        "Neerslag (gecalibreerde radar) early reanalysis",
        "Neerslag (gecalibreerde radar) realtime",
    ]
    filters[0].active = []
