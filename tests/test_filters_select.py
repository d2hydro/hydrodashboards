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
    # choose filter oppervlaktewater
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


def test_fysisch_chemisch():
    # choose filter fysisch/chemisch
    filters[0].active = [2]
    # choose meetlocaties
    filters[1].active = [0]
    assert not data.locations.sets.data[data.filters.thematic_filters[1].value[0]].empty
    filters[0].active = []


def test_meteo_empty_set():
    filters[0].active = [3]
    filters[1].active = [0]
    filter_value = data.filters.thematic_filters[1].value[0]
    assert data.locations.sets.data[filter_value].empty
    filters[0].active = []
