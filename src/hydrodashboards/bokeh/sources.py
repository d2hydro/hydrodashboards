from bokeh.models import ColumnDataSource


def locations_source():
    return ColumnDataSource(
        "x",
        "y",
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
