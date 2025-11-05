import plotly.graph_objs as go
from dash import dcc


class MiniGraph:
    def __init__(self, id, all_datetimes, time_series_cache):
        self.id = id
        self.all_datetimes = all_datetimes
        self.time_series_cache = time_series_cache

    @property
    def layout(self):
        """Kleine inactieve grafiek voor tijdsoverzicht"""
        return dcc.Graph(
            id=self.id,
            config={"displayModeBar": False},
            style={
                "height": "50px",
                "width": "350px",
                "left": "25px",
                "position": "relative",  
                "pointerEvents": "none", 
                "zIndex": 1,
            },
        )

    def build(self, sel, var, idx):
        import pandas as pd
        if not sel or not var:
            return go.Figure()

        parameter_id = "vullingsgraad" if var == "vullingsgraad" else "vulling_mm"
        try:
            df = self.time_series_cache.get_time_series(
                "VullingsgraadOutput", parameter_id, location_ids=[sel]
            )
        except Exception:
            df = None

        if df is not None and not df.empty:
            series = df.iloc[:, 0]
            vals = [series.get(ts, None) for ts in self.all_datetimes]
        else:
            vals = [None] * len(self.all_datetimes)

        idx0 = int(idx) if idx is not None else 0
        mini = go.Figure(
            go.Scatter(
                x=list(range(len(self.all_datetimes))),
                y=vals,
                mode="lines",
                line=dict(width=2, color="#2563eb"),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        mini.add_vline(x=idx0, line_width=2, line_dash="dash", line_color="#bbbbbb")
        mini.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            height=50,
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(visible=False, range=[0, len(self.all_datetimes)-1], fixedrange=True),
            yaxis=dict(visible=False, fixedrange=True),
        )
        return mini
