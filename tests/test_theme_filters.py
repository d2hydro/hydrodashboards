from hydrodashboards.bokeh.main import filters, parameters, locations, data


def test_keep_filter_peilbuis_selected():
    select_label = "Peilbuis"
    # choose theme grondwater
    filters[0].active = [1]
    assert filters[1].labels == ["Peilbuis"]
    # choose filter peilbuis
    filters[1].active = [filters[1].labels.index(select_label)]
    # choose themes grondwater and oppervlaktewater
    filters[0].active = [0, 1]
    # index of peilbuis now changed to 5
    labels = [
        "Gemaal",
        "Stuw",
        "Inlaat",
        "Sluis",
        "Meetpunt (hydrologisch)",
        "Peilbuis",
    ]
    assert filters[1].labels == labels
    assert filters[1].active == [filters[1].labels.index(select_label)]

    # clear app
    filters[0].active = []
    assert filters[1].active == []
    assert filters[1].labels == []


def test_switch_theme():
    # chosse filter oppervlaktewater
    filters[0].active = [0]
    labels = ["Gemaal", "Stuw", "Inlaat", "Sluis", "Meetpunt (hydrologisch)"]
    assert filters[1].labels == labels
    # choose filter gemaal
    filters[1].active = [0]
    assert parameters.labels == data.parameters.labels
    assert locations.labels == locations.labels
    # choose Abelstok
    locations.active = [0]
    assert data.locations.value == ["NL34.HL.KGM156"]
    # choose parameter
    parameters.active = [0]
    assert data.parameters.value == ["STSTP [n] [NVT] [NT] * productie"]
    # choose Grondwater
    filters[0].active = [0, 1]
    filters[0].active = [1]
    assert filters[1].labels == ["Peilbuis"]
    assert locations.labels == []
    assert parameters.labels == []
    filters[0].active = []
