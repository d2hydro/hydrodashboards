from bokeh.models import MultiSelect

select_locations = MultiSelect(
    title="Locaties:", value=[], options=data.locations.options
)