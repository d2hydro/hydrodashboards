from bokeh.models.widgets import Button
from bokeh.models import CustomJS


save_js = """
html2canvas(document.getElementById("grafiek_upper")).then(canvas => {
    canvas.toBlob(function(blob) {
        window.saveAs(blob, 'grafiek.jpg');
    });
});
"""


def make_button():
    button = Button(label="", button_type="success", disabled=True)

    button.js_on_click(
        CustomJS(
            code=save_js,
        )
    )

    return button
