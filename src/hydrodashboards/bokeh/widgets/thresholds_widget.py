from bokeh.models.widgets import Toggle


def make_button(thresholds_handler):
    thresholds_button = Toggle(label=" ",
                               active=False,
                               sizing_mode="stretch_both",
                               css_classes=['threshold'])

    thresholds_button.on_click(thresholds_handler)
    return thresholds_button
