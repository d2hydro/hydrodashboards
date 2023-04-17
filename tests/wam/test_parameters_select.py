from config import wam_config

wam_config()

from hydrodashboards.bokeh.main import (
    filters,
    data,
    locations,
    parameters,
)  # noqa


# choose filter oppervlaktewater
filters[0].active = [0]
# choose filter gemaal
filters[1].active = [0]
location_id = "NL34.HL.KGM156"
idx = [i[0] for i in data.locations.options].index(location_id)
expected = data.locations.app_df.at["NL34.HL.KGM156", "parameter_ids"]
locations.active = [idx]


def test_parameter_sorting():
    # choose 1rd location
    locations.active = [0]
    # choose 2nd parameter
    parameters.active = [1, 3]
    assert parameters.active == [0, 1]
