from hydrodashboards.bokeh.main import args_parser, filters, locations


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

#def test_selected_locations():
# args = {"filter_id": [b"WDB_OW_KGM"],"location_id": [b"NL34.HL.KGM156"]}
# args_parser(args)
