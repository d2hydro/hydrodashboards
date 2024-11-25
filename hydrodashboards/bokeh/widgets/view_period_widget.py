from bokeh.models.widgets import DateRangeSlider
from bokeh.models import CustomJS


update_source_js = """
var start = period_slider.value[0]
var end = period_slider.value[1]
source.data = {
    "x": [start, start, end, end],
    "y": [-(10 ** 9), 10 ** 9, 10 ** 9, -(10 ** 9)],
}
"""


def make_view_period(data, patch_source, disabled=True, show_value=False):
    value = (data.view_start, data.view_end)
    start = data.search_start
    end = data.search_end

    period_slider = DateRangeSlider(
        value=value, start=start, end=end, bar_color="#e6e6e6", show_value=show_value
    )
    period_slider.js_on_change(
        "value",
        CustomJS(
            args=dict(period_slider=period_slider, source=patch_source),
            code=update_source_js,
        ),
    )
    period_slider.format = "%d-%m-%Y"
    period_slider.disabled = disabled
    return period_slider


def update_view_period(view_period, data):
    view_period.value = (data.view_start, data.view_end)
    view_period.start = data.search_start
    view_period.end = data.search_end
