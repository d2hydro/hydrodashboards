from bokeh.models.widgets import CheckboxGroup, Div, TextInput, Button
from bokeh.models import CustomJS
from bokeh.layouts import column, row
from typing import List

SIZING_MODE = "stretch_width"


thematic_filters_js = """
if (window.MenuEvents && typeof window.MenuEvents.onFiltersChanged === 'function') {
    window.MenuEvents.onFiltersChanged();
}
"""

reset_filter_active = "filter.active = []"


def make_filter(data, on_change=[], filter_length=5) -> CheckboxGroup:
    """Return a Bokeh CheckboxGroup filter from data filter."""

    bokeh_filter = CheckboxGroup(
        active=data.active, labels=data.labels, name=data.title
    )
    selector = "active"

    if type(on_change) == list:
        for i in on_change:
            bokeh_filter.on_change(selector, i)
    elif type(on_change) == dict:
        for i in on_change[data.id]:
            bokeh_filter.on_change(selector, i)

    bokeh_filter.sizing_mode = SIZING_MODE

    return bokeh_filter


def make_filters(data, on_change=[], filter_length=5, thematic_view=False) -> list:
    """Return list of Bokeh CheckboxGroup filters from data filters."""
    if thematic_view:
        filters = [
            make_filter(
                data=i,
                on_change=on_change,
                filter_length=filter_length,
            )
            for i in data.thematic_filters
        ]
        filters[1].js_on_change("active", CustomJS(code=thematic_filters_js))
    else:
        filters = [
            make_filter(
                data=i,
                on_change=on_change,
                filter_length=filter_length,
            )
            for i in data.filters
        ]
    return filters


def get_filters_values(filters, thematic_view=False) -> List[CheckboxGroup]:
    """Return all values from a list of app filters."""
    if thematic_view:
        values = filters[1].value
    else:
        values = [i.value for i in filters]
        values = [i for j in values for i in j]
    return values


def get_filters_actives(filters, thematic_view=False) -> List[CheckboxGroup]:
    """Return a all active in a list of lists of Bokeh CheckBoxGroup filters"""
    if thematic_view:
        active = filters[1].active
    else:
        active = [i.active for i in filters]
    return active


def set_filter_values(filters, filter_ids, thematic_view, data_filters):
    """Set filter values on a selected set of filter_ids."""
    if thematic_view:
        theme_active = []
        for i in range(len(filters[0].labels)):
            _, values, _ = data_filters.get_filter_options(active=[i])
            if any((i in values for i in filter_ids)):
                theme_active += [i]
        filters[0].active = theme_active
        filters_active = [
            idx
            for idx, i in enumerate(data_filters.thematic_filters[1].options)
            if i[0] in filter_ids
        ]
        filters[1].active = filters_active
    else:
        for i in filters:
            i.active = [idx for idx, j in enumerate(i.options) if j[0] in filter_ids]


def finish_filter(filter, reset_button=False, search_input=None):
    header = [Div(
        text=filter.name, sizing_mode="stretch_width"
    )]
    if reset_button:
        button = Button(label="", sizing_mode="stretch_width", css_classes=["filter_reset_button"])
        button.js_on_click(CustomJS(code=reset_filter_active, args={"filter": filter}))
        header = [button] + header
    if search_input is not None:
        text_input = TextInput(sizing_mode="stretch_width", css_classes=["filter_search"])
        text_input.on_change(*search_input)
        header += [text_input]
    filter = [row(header, css_classes=["filter_title"]), filter]
    return filter


def finish_filters(filters, thematic_view=False, reset_button=False, search_input=None):
    filters = [finish_filter(i, reset_button, search_input) for i in filters]
    filters = [i for j in filters for i in j]
    filters_layout = column(filters, name="filters", sizing_mode="stretch_width")

    return filters_layout


def add_css_classes(filters, locations, parameters):
    class_num = 1
    for i in filters + [locations, parameters]:
        i.css_classes = [f"filter_checkboxgroup_{class_num}"]
        class_num += 1