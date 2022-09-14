from bokeh.models.widgets import MultiSelect
from bokeh.models import CustomJS
from typing import List

MAX_FILTER_LEN = 5
SIZING_MODE = "stretch_width"


def custom_js(filter, filters_layout):
    return CustomJS(args={"filter": filter,
                          "filters_layout": filters_layout},
                    code="""
function clearFilter(item) {
    if (item.title != filter.title) {
        item.value = []
    }
}

function clearFilterValues() {
    if ((ctrlKey == false) && (filter.value.length > 0)) {
        filters_layout.children.forEach(item => clearFilter(item))
    }
}
clearFilterValues();
""")


def clear_control(filters_layout):
    for i in filters_layout.children:
        i.js_on_change("value", custom_js(i, filters_layout))


def make_filter(data, on_change=[]) -> MultiSelect:
    """Return a Bokeh MultiSelect filter from data filter."""
    bokeh_filter = MultiSelect(title=data.title, value=data.value, options=data.options)
    bokeh_filter.size = min(len(bokeh_filter.options), MAX_FILTER_LEN)
    bokeh_filter.sizing_mode = SIZING_MODE

    for i in on_change:
        bokeh_filter.on_change(*i)

    return bokeh_filter


def make_filters(data, on_change=[]) -> list:
    """Return list of Bokeh MultiSelect filters from data filters."""
    return [make_filter(data=i, on_change=on_change) for i in data.filters]


def get_filters_values(filters) -> List[MultiSelect]:
    """Return all values from a list of Bokeh MultiSelect filters."""
    values = [i.value for i in filters]
    return [i for j in values for i in j]


def set_filter_values(filters, filter_ids):
    """Set filter values on a selected set of filter_ids."""
    for i in filters:
        value = [j[0] for j in i.options if j[0] in filter_ids]
        if value:
            i.value = value
