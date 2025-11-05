from dash import dcc

class TimeSlider:
    def __init__(self, id, all_datetimes, default_index):
        self.id = id
        self.all_datetimes = all_datetimes
        self.default_index = default_index

    @property
    def layout(self):
        return dcc.Slider(
            id=self.id,
            min=0,
            max=len(self.all_datetimes) - 1,
            value=self.default_index,
            updatemode="mouseup",
            marks=None,
        )
