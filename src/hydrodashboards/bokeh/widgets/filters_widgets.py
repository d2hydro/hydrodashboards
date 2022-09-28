from bokeh.models.widgets import MultiSelect, CheckboxGroup, Div
from bokeh.layouts import column
from bokeh.models import CustomJS
from typing import List, Union

SIZING_MODE = "stretch_width"


def clear_control_js(filter, filters_layout):
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
        i.js_on_change("value", clear_control_js(i, filters_layout))


def make_filter(data, on_change=[], filter_type="MultiSelect", filter_length=5) -> Union[MultiSelect, CheckboxGroup]:
    """Return a Bokeh MultiSelect filter from data filter."""
    
    if filter_type == "MultiSelect":
        bokeh_filter = MultiSelect(title=data.title, value=data.value, options=data.options)
        bokeh_filter.size = min(len(bokeh_filter.options), filter_length)
        selector = "value"
    elif filter_type == "CheckBoxGroup":
        bokeh_filter = CheckboxGroup(active=data.active, labels=data.labels, name=data.title)
        selector = "active"

    if type(on_change) == list:
        for i in on_change:
            bokeh_filter.on_change(selector, i)
    elif type(on_change) == dict:
        for i in on_change[data.id]:
            bokeh_filter.on_change(selector, i)

    bokeh_filter.sizing_mode = SIZING_MODE

    return bokeh_filter


def make_filters(data, on_change=[], filter_type="MultiSelect", filter_length=5, thematic_view=False) -> list:
    """Return list of Bokeh MultiSelect filters from data filters."""
    if thematic_view:
        filters = [make_filter(data=i, on_change=on_change, filter_type=filter_type, filter_length=filter_length) for i in data.thematic_filters]
    else:
        filters = [make_filter(data=i, on_change=on_change, filter_type=filter_type, filter_length=filter_length) for i in data.filters]
    return filters


def get_filters_values(filters, thematic_view=False) -> List[MultiSelect]:
    """Return all values from a list of Bokeh MultiSelect filters."""
    if thematic_view:
        values = filters[1].value
    else:
        values = [i.value for i in filters]
        values = [i for j in values for i in j]
    return values


def get_filters_actives(filters, thematic_view=False) -> List[MultiSelect]:
    """Return a all active in a list of lists of Bokeh CheckBoxGroup filters"""
    if thematic_view:
        active = filters[1].active
    else:
        active = [i.active for i in filters]
    return active


def set_filter_values(filters, filter_ids):
    """Set filter values on a selected set of filter_ids."""
    for i in filters:
        value = [j[0] for j in i.options if j[0] in filter_ids]
        if value:
            i.value = value


def finish_filter(filter, filter_type="MultiSelect", css_class_num=1):
    if filter_type == "CheckBoxGroup":
        div = Div(text=filter.name, sizing_mode="stretch_width", css_classes = ["filter_title"])
        filter = [div, filter]
    return filter


def finish_filters(filters, filter_type="MultiSelect", thematic_view=False):
    if (filter_type == "MultiSelect"):
        filters_layout = column(filters, name="filters", sizing_mode="stretch_width")
        if not thematic_view:
            clear_control(filters_layout)
    elif filter_type == "CheckBoxGroup":
        filters = [finish_filter(i, filter_type=filter_type) for i in filters]
        filters = [i for j in filters for i in j]
        filters_layout = column(filters, name="filters", sizing_mode="stretch_width")

    return filters_layout


def add_css_classes(filters, locations, parameters):
    class_num = 1
    for i in filters + [locations] + [parameters]:
        if type(i) == MultiSelect:
            i.css_classes = [f"filter_multiselect_{class_num}"]
        elif type(i) == CheckboxGroup:
            i.css_classes = [f"filter_checkboxgroup_{class_num}"]
        class_num += 1
