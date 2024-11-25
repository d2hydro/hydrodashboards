from bokeh.layouts import column
from bokeh.models import TextInput, Div, Button, CustomJS
from bokeh.plotting import show
from bokeh.io import curdoc

# Create a TextInput widget
text_input = TextInput(value="Initial value", title="Text Input:")

# Create a Div to show the "input disabled" message, initially hidden
disabled_message = Div(text="Input disabled", visible=False, style={'color': 'red'})

# Create a button to toggle between enabled and disabled state
toggle_button = Button(label="Toggle Disabled")

# JavaScript callback to show message on hover if input is disabled
hover_callback = CustomJS(args=dict(text_input=text_input, disabled_message=disabled_message), code="""
    if (text_input.disabled) {
        disabled_message.visible = true;
    }
""")

# JavaScript callback to hide the message when the mouse leaves
leave_callback = CustomJS(args=dict(disabled_message=disabled_message), code="""
    disabled_message.visible = false;
""")

# Add hover and leave events
text_input.js_on_event('mouseenter', hover_callback)
text_input.js_on_event('mouseleave', leave_callback)

# Define a callback function to toggle input disabled state
def toggle_input():
    text_input.disabled = not text_input.disabled

toggle_button.on_click(toggle_input)

# Layout and show
layout = column(text_input, disabled_message, toggle_button)
curdoc().add_root(layout)
show(layout)