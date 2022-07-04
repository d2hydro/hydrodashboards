from fewspy import Api
from hydrodashboards.datamodel.parameters import Parameters
from datetime import datetime

ROOT_FILTER = "WDB"
EXCLUDE_PARS = "Dummy"
OPTIONS = [
    ("Q [m3/s] [NVT] [OW] * validatie", "Debiet [m3/s] [NVT] [OW] (validatie)"),
    ("WATHTE [m] [NAP] [OW] * validatie", "Waterhoogte [m] [NAP] [OW] (validatie)"),
]


api = Api(
    url="https://www.hydrobase.nl/fews/nzv/FewsWebServices/rest/fewspiservice/v1/",
    ssl_verify=False,
)


pi_headers = api.get_time_series(
    filter_id="WDB_OW_KGM",
    start_time=datetime(2022, 5, 5),
    end_time=datetime(2022, 5, 5),
    only_headers=True,
)

pi_qualifiers = api.get_qualifiers()
pi_parameters = api.get_parameters(filter_id=ROOT_FILTER)

parameters = Parameters.from_fews(
    pi_parameters=pi_parameters, pi_qualifiers=pi_qualifiers
)


def test_init():
    assert parameters._fews_parameters.equals(pi_parameters)


def test_update():
    parameters.update_from_pi_headers(pi_headers, exclude_pars=EXCLUDE_PARS)
    assert parameters.options == OPTIONS
