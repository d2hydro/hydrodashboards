from hydrodashboards.bokeh.main import filters, locations_source, data, locations


# choose filter oppervlaktewater
filters[0].active = []
# choose filter gemaal
location_id = "NL34.HL.KGM007"


def test_sorting_at_select():
    filters[0].active = [0]
    filters[1].active = [0]
    # select = [i[0] for i in data.locations.options].index(location_id)
    select = 22
    locations.active = [select]

    assert data.locations.value == [location_id]
    assert data.locations.active == [0]
    assert locations.active == [0]
    locations.active = []


def test_sorting_at_map_select():
    # idx = [locations_source.data["id"].index(location_id)]
    locations_source.selected.indices = [3]
    assert data.locations.value == [location_id]
    assert data.locations.active == [0]
    assert locations.active == [0]
    locations.active = []


def test_in_locations():
    locations.active = [i for i in range(10)]
    assert data.locations.active == locations.active

    old = locations.active
    locations.active = old + [10]
    assert locations.active == old
    locations.active = []


def test_on_map():
    assert locations_source.selected.indices == []
    locations_source.selected.indices = [i for i in range(10)]
    old = locations_source.selected.indices
    locations_source.selected.indices = old + [10]
    assert len(locations_source.selected.indices) == 10
    locations_source.selected.indices = []
    assert locations.active == []
