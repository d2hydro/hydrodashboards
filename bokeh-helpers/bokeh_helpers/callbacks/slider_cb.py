def set_slider_on_change(slider, target_fun, throttle=False):
    # TODO not used anymore?
    """Switch between throttled and non throttled on_change callback.
    Throttled doesnt work with a play button, but it still is superior
    for normal user interaction. Therefore we remove the on_change
    callback and replace it by its throttled or non throttled version
    """
    for key in ["value", "value_throttled"]:
        cbs = slider._callbacks
        if key in cbs:
            if target_fun in cbs[key]:
                print(f"Removing callback; {key}:{target_fun}")
                slider.remove_on_change(key, target_fun)
            else:
                print(f"callback is: {cbs[key]}")

    if throttle:
        key = "value_throttled"
    else:
        key = "value"
    slider.on_change(key, target_fun)
    print(f"Adding callback; {key}:{target_fun}")
