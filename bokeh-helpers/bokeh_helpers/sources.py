from bokeh.models import ColumnDataSource, CustomJS

locations_source_js = """
if (window.MenuEvents && typeof window.MenuEvents.onLocationsDataChanged === 'function') {
    window.MenuEvents.onLocationsDataChanged();
}
"""


def locations_source():
    source = ColumnDataSource(
        data={
            i: []
            for i in [
                "x",
                "y",
                "id",
                "name",
                "line_color",
                "fill_color",
                "label",
            ]
        },
    )

    source.js_on_change("data", CustomJS(args=dict(), code=locations_source_js))

    return source
