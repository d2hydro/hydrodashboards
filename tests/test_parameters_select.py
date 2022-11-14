from hydrodashboards.bokeh.main import filters, locations_source, data, locations, parameters


# choose filter oppervlaktewater
filters[0].active = [0]
# choose filter gemaal
filters[1].active = [0]


def test_parameter_sorting():
    # choose 1rd location
    locations.active = [0]
    # choose 2nd parameter
    parameters.active = [1, 3]
    assert parameters.active == [0, 1]
