from hydrodashboards.bokeh.main import filters, locations_source, data, locations


# choose filter oppervlaktewater
filters[0].active = [0]
# choose filter gemaal
filters[1].active = [0]

# choose 3rd location
#locations.active = [3]

# deselect location
#locations.active = []

# select on map
locations_source.selected.indices = [43]


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
