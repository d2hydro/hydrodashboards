from bokeh.models.widgets import DatePicker, Div
from bokeh.layouts import row, column


def make_search_period(data, on_change):
    def _title_div(title):
        return Div(text=title, css_classes=["search_period_title"])

    start_date_title = _title_div(data.search_start_title)
    start_date_picker = DatePicker(
        value=data.search_start.strftime("%Y-%m-%d"),
        min_date=data.history_start.strftime("%Y-%m-%d"),
        max_date=data.search_end.strftime("%Y-%m-%d"),
        sizing_mode="stretch_width",
        css_classes=["search_period"],
    )
    end_date_title = _title_div(data.search_end_title)
    end_date_picker = DatePicker(
        title=data.search_end_title,
        value=data.search_end.strftime("%Y-%m-%d"),
        min_date=data.search_start.strftime("%Y-%m-%d"),
        max_date=data.search_end.strftime("%Y-%m-%d"),
        sizing_mode="stretch_width",
        css_classes=["search_period"],
    )
    start_date_picker.js_link("value", end_date_picker, "min_date")
    end_date_picker.js_link("value", start_date_picker, "max_date")
    for i in on_change:
        start_date_picker.on_change(*i)
        end_date_picker.on_change(*i)

    return row(
        column(start_date_title, start_date_picker),
        column(end_date_title, end_date_picker),
    )
