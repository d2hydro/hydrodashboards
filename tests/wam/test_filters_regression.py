from config import wam_config

wam_config()

from hydrodashboards.bokeh.main import (
    filters,
    parameters,
    locations,
    data,
    sync_locations_active_with_data,
)  # noqa

theme_ids = [i[0] for i in data.filters.thematic_filters[0].options]
filter_ids_gen = ([j[0] for j in i.options] for i in data.filters.filters)
filter_ids = [j for i in filter_ids_gen for j in i]

FIRST_LOCATION = ["NL34.HL.KGM156"]
THIRD_LOCATION = ["NL34.HL.KGM056"]
SECOND_FILTER_LOCATION = ["NL34.HL.KST0472"]


def _get_theme_values(idx):
    return [theme_ids[i] for i in idx]


def _get_filter_values(idx):
    return [filter_ids[i] for i in idx]


def _reset_app():
    filters[0].active = []
    assert filters[1].active == []
    assert locations.active == []
    assert parameters.active == []


def test_first_location():
    # select themes
    theme_active = [0]
    filter_active = [0]
    location_active = [0]
    location_value = FIRST_LOCATION

    filters[0].active = theme_active

    filters[1].active = theme_active

    locations.active = theme_active

    # check if correct filter and location
    assert data.filters.thematic_filters[1].value == _get_filter_values(filter_active)
    assert locations.active == location_active
    assert data.locations.value == location_value

    _reset_app()


def test_ordering_location():
    theme_active = [0]
    filter_active = [0]
    location_active = [2]

    filters[0].active = theme_active
    filters[1].active = filter_active
    locations.active = location_active

    # location should be reordered to first index
    assert locations.active == [0]
    # but value should be correct
    assert data.locations.value == THIRD_LOCATION
    _reset_app()


def test_add_other_filter():
    theme_active = [0]
    filter_active = [0]
    location_active = [2]

    filters[0].active = theme_active
    filters[1].active = filter_active
    locations.active = location_active

    filter_active = [0, 1]
    filters[1].active = filter_active

    # location should be reordered to first index
    assert locations.active == [0]
    # but value should be correct
    assert data.locations.value == THIRD_LOCATION
    _reset_app()


def test_unselecting_second_filter():
    theme_active = [0]
    filter_active = [1]
    location_active = [0]

    filters[0].active = theme_active
    filters[1].active = filter_active
    locations.active = location_active

    # location should be reordered to first index
    assert locations.active == [0]
    # but value should be correct
    assert data.locations.value == SECOND_FILTER_LOCATION

    filter_active = [0, 1]
    location_active = [0, 3]

    filters[1].active = filter_active
    locations.active = location_active

    # location should be reordered to first index
    assert locations.active == [0, 1]

    # but value should be correct
    assert data.locations.value == THIRD_LOCATION + SECOND_FILTER_LOCATION

    filter_active = [1]
    filters[1].active = filter_active
    sync_locations_active_with_data()

    # location should be reordered to first index
    assert locations.active == [0]
    # but value should be correct
    assert data.locations.value == SECOND_FILTER_LOCATION
    _reset_app()


def test_add_second_filter():
    theme_active = [0]
    filter_active = [0]
    location_active = [2]

    filters[0].active = theme_active
    filters[1].active = filter_active
    locations.active = location_active

    filters[1].active = [0, 1]

    # location should be reordered to first index
    assert locations.active == [0]
    # but value should be correct
    assert data.locations.value == THIRD_LOCATION
    _reset_app()
