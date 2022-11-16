from bokeh.models.widgets import DatePicker, Button
from bokeh.layouts import row


def make_search_period(data, on_change):
    start_date_picker = DatePicker(
        title=data.search_start_title,
        value=data.search_start.strftime("%Y-%m-%d"),
        min_date=data.history_start.strftime("%Y-%m-%d"),
        max_date=data.search_end.strftime("%Y-%m-%d"),
        sizing_mode="stretch_width",
        css_classes=["search_period"],
    )
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

    return row(start_date_picker, end_date_picker)


def make_button(disclaimer_file=None, graph_count=3):
    button = Button(label="", button_type="success", disabled=True)

    return button
