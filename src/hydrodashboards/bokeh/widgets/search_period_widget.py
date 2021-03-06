from bokeh.models.widgets import DatePicker
from bokeh.layouts import row


def make_search_period(data):
    start_date_picker = DatePicker(
        title=data.search_start_title,
        value=data.search_start.strftime("%Y-%m-%d"),
        min_date=data.history_start.strftime("%Y-%m-%d"),
        max_date=data.search_end.strftime("%Y-%m-%d"),
        sizing_mode="stretch_width",
    )
    end_date_picker = DatePicker(
        title=data.search_end_title,
        value=data.search_end.strftime("%Y-%m-%d"),
        min_date=data.search_start.strftime("%Y-%m-%d"),
        max_date=data.now.strftime("%Y-%m-%d"),
        sizing_mode="stretch_width",
    )
    start_date_picker.js_link("value", end_date_picker, "min_date")
    end_date_picker.js_link("value", start_date_picker, "max_date")

    return row(start_date_picker, end_date_picker)
