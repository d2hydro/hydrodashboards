from fewspy import Api
from hydrodashboards.datamodel.filters import Filters

ROOT_FILTER = "WDB"
OPTIONS = [
    ("WDB_OW_KGM", "Gemaal"),
    ("WDB_OW_KST", "Stuw"),
    ("WDB_OW_INL", "Inlaat"),
    ("WDB_OW_KSL", "Sluis"),
    ("WDB_OW_MPN", "Meetpunt"),
]
TITLES = ["Oppervlaktewater", "Grondwater", "Fysisch/Chemisch", "Meteorologie"]

api = Api(
    url="https://www.hydrobase.nl/fews/nzv/FewsWebServices/rest/fewspiservice/v1/",
    ssl_verify=False,
)

fews_filters = api.get_filters(filter_id=ROOT_FILTER)

datamodel_filters = Filters.from_fews(fews_filters)
bokeh_filters = datamodel_filters.bokeh


def test_length():
    assert len(datamodel_filters.filters) == 4
    assert len(bokeh_filters.children) == 4


def test_titles():
    assert [i.title for i in datamodel_filters.filters] == TITLES
