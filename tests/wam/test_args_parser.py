from hydrodashboards.bokeh.main import (
    args_parser,
    filters,
    locations,
    parameters,
    search_period,
    view_period,
    convert_to_datetime,
)
from datetime import datetime


def test_faulty_datetime():
    result = convert_to_datetime("wrong_datetime")
    assert result is None


def test_selected_filters():
    args = {"filter_id": [b"WDB_OW_KGM"]}
    args_parser(args)
    assert filters[0].active == [0]
    assert filters[1].labels == [
        "Gemaal",
        "Stuw",
        "Inlaat",
        "Sluis",
        "Meetpunt (hydrologisch)",
    ]
    assert filters[1].active == [0]
    filters[0].active == []


def test_selected_locations():
    args = {"filter_id": [b"WDB_OW_KGM"], "location_id": [b"NL34.HL.KGM156"]}
    args_parser(args)
    assert filters[0].active == [0]
    assert filters[1].active == [0]
    assert locations.active == [0]
    filters[0].active = []
    assert locations.active == []


def test_selected_locations_no_filters():
    args = {"location_id": [b"NL34.HL.KGM156"]}
    args_parser(args)
    assert filters[0].active == [0]
    assert filters[1].active == [0]
    assert locations.active == [0]
    filters[0].active = []
    assert locations.active == []


def test_selected_parameters():
    args = {
        "filter_id": [b"WDB_OW_KGM"],
        "location_id": [b"NL34.HL.KGM156"],
        "parameter_id": [
            b"Q [m3/s] [NVT] [OW] * productie",
            b"WATHTE [m] [NAP] [OW] * productie",
        ],
    }
    args_parser(args)
    assert parameters.active == [0, 1]
    filters[0].active = []
    assert parameters.active == []


def test_updated_faulty_period():
    args = {"start_date": [b"faulty_start"], "end_date": [b"faulty_end"]}
    search_start = search_period.children[0].value
    search_end = search_period.children[1].value

    args_parser(args)

    search_period.children[0].value == search_start
    search_period.children[1].value == search_end


def test_updated_period():
    args = {
        "filter_id": [b"WDB_OW_KGM"],
        "location_id": [b"NL34.HL.KGM156"],
        "parameter_id": [
            b"Q [m3/s] [NVT] [OW] * productie",
            b"WATHTE [m] [NAP] [OW] * productie",
        ],
        "start_date": [b"2022-09-05"],
        "end_date": [b"2022-09-15"],
    }

    args_parser(args)
    assert search_period.children[0].value == "2022-09-04"
    assert search_period.children[1].value == "2022-09-16"
    assert view_period.value_as_datetime == (
        datetime(2022, 9, 5, 0, 0),
        datetime(2022, 9, 15, 0, 0),
    )
