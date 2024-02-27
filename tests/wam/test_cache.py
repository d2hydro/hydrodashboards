# %%
from hydrodashboards.bokeh.main import filters, data

# prepare test
data.delete_cache()
filters[0].active = [0]
filters[1].active = [0]

filter_id = "WDB_OW_KGM"


def test_filters_exist_in_memory():
    assert data.filters.filters[0].cache.exists(filter_id)
    assert data.locations.sets.exists(filter_id)


# FIXME: use fixtures to make this test working (function runs 'local')
# def test_filters_exist_as_file():
#     data.filters.filters[0].cache.data = {}
#     data.locations.sets.data = {}
#     print(data.filters.filters[0].cache)
#     assert data.filters.filters[0].cache.exists(filter_id)
#     assert data.locations.sets.exists(filter_id)


def test_filters_deleted():
    data.delete_cache()
    assert not data.filters.filters[0].cache.exists(filter_id)
    assert not data.locations.sets.exists(filter_id)


# %%
