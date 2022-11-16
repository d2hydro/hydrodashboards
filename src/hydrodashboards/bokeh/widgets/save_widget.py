from bokeh.models.widgets import Button
from bokeh.models import CustomJS


save_js = """console.log("save"")"""


def make_button(disclaimer_file=None, graph_count=3):
    button = Button(label="", button_type="success", disabled=True)

    button.js_on_click(
        CustomJS(
            code=save_js,
        )
    )

    return button
