from bokeh.io import curdoc


def animate_button(button, update_function):
    """Animate timeslider when clicking the play_button"""

    def stop_animation():
        global callback_id
        button.label = "► Play"
        curdoc().remove_periodic_callback(callback_id)

    def start_animation():
        global callback_id
        button.label = "❚❚ Pause"
        callback_id = curdoc().add_periodic_callback(update_function, 200)

    def animate():
        if button.label == "► Play":
            start_animation()
        else:
            stop_animation()

    return animate
