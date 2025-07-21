import numbers
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Union

from bokeh.models import BoxAnnotation, Range1d, RangeTool, Slider
from bokeh.plotting import figure

from bokeh_helpers.widgets.date_time_span import DateTimeSpan
from bokeh_helpers.widgets.shared_functions import get_formatter, round_seconds


@dataclass
class RangeToolTimePicker:
    y_range: Union[list[int]]
    xrange: Range1d
    span: DateTimeSpan
    name: str = "select_xrange"

    """
    span: DateTimeSpan
        span of selected timestep
    """

    def __post_init__(self):
        self.widget = figure(
            y_range=self.y_range,
            x_axis_type=None,
            y_axis_type=None,
            tools="",  # "reset,xwheel_zoom",
            # active_scroll="xwheel_zoom",
            toolbar_location=None,
            background_fill_color="#efefef",
            name=self.name,
            sizing_mode="stretch_both",
        )

        self.widget.toolbar.logo = None
        self.widget.ygrid.grid_line_color = None

        # Set initial xrange so we can still select timestamp when we dont have any location selected
        self.widget.x_range.start = self.xrange.start
        self.widget.x_range.end = self.xrange.end

        self.range_tool = RangeTool(x_range=self.xrange)
        self.range_tool.overlay.fill_color = "navy"
        self.range_tool.overlay.fill_alpha = 0.2

        self.widget.add_tools(self.range_tool)
        self.widget.add_layout(self.span.widget)

        # add a line in the main.py
        # self.widget.line(x="datetime", y="vullingsgraad", source=source_vullingsgraad, color="blue", line_width=1)
