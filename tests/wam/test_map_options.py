from hydrodashboards.bokeh.main import map_options, map_figure


def test_update_map_figure_background():
    background_url = map_figure.renderers[0].tile_source.url
    map_options.children[-1].active = 0
    assert map_figure.renderers[0].tile_source.url != background_url


def test_update_map_figure_overlay():
    visible_overlays = map_options.children[0].active
    set_invisible = map_options.children[0].labels[visible_overlays[0]]
    visible_overlays.pop(0)
    map_options.children[0].active = visible_overlays
    renderer = next(i for i in map_figure.renderers if i.name == set_invisible)
    assert not renderer.visible
