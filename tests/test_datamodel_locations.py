from fewspy import Api
from pathlib import Path
from hydrodashboards.datamodel.locations import Locations
from datetime import datetime

ROOT_FILTER = "WDB"
TEST_FILTER = "WDB_OW_KGM"
DATA_PATH = Path(__file__).parent / "data"
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

locations = Locations.from_fews(api.get_locations(filter_id=ROOT_FILTER))


def test_init():
    assert not locations.locations.empty
    assert len(locations.options) == 0


def test_update():
    locations.update_from_pi_headers(pi_headers)
    assert len(locations.options) == 139
