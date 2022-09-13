from bokeh.models.widgets import Button
from bokeh.models import CustomJS


def make_update_graph(label):
    time_fig_button = Button(
        label=label,
        css_classes=["stoploading_time_fig"],
        sizing_mode="stretch_width",
        button_type="primary",
        disabled=True
    )

    time_fig_button.js_on_click(
        CustomJS(code="""$('#nav-tab button[data-target="#grafiek"]').tab('show')""")
                 )
    return time_fig_button
