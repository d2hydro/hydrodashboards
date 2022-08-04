from bokeh.models.widgets import Button


def make_update_graph(label):
    time_fig_button = Button(
        label=label,
        css_classes=["stoploading_time_fig"],
        sizing_mode="stretch_width",
        button_type="primary",
        disabled=True
    )
    return time_fig_button
