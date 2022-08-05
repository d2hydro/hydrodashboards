from bokeh.models.widgets import DateRangeSlider


def make_view_period(data, disabled=True, show_value=False):
    value = (data.view_start, data.view_end)
    start = data.search_start
    end = data.search_end

    period_slider = DateRangeSlider(value=value, start=start, end=end, bar_color="#e6e6e6", show_value=show_value)
    period_slider.format = "%d-%m-%Y"
    period_slider.disabled = disabled
    return period_slider
