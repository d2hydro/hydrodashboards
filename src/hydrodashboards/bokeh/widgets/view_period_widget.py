from bokeh.models.widgets import DateRangeSlider


def make_view_period(data):
    value = (data.view_start, data.view_end)
    start = data.search_start
    end = data.search_end

    period_slider = DateRangeSlider(value=value, start=start, end=end)
    period_slider.format = "%d-%m-%Y"
    return period_slider
