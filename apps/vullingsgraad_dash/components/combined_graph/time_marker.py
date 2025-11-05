import plotly.graph_objs as go
import pandas as pd


class TimeMarker:
    """Voegt een verticale tijdlijn toe en controleert of deze binnen de zichtbare x-range valt."""

    def __init__(self, all_datetimes):
        self.all_datetimes = all_datetimes

    def apply(self, fig: go.Figure, idx: int, rows: int = 3) -> go.Figure:
        print(f"[DEBUG] TimeMarker.apply() called with idx={idx}")
        if idx is None or not self.all_datetimes:
            print("[DEBUG] -> No all_datetimes or idx=None, skipping")
            return fig

        try:
            idx = max(0, min(int(idx), len(self.all_datetimes) - 1))
            dt = pd.to_datetime(self.all_datetimes[idx])
        except Exception as e:
            print(f"[DEBUG] -> Index error: {e}")
            return fig

        print(f"[DEBUG] -> Candidate line time: {dt}")

        # -------------------------------------------------
        # 1️⃣ Controleer of de tijd binnen huidige x-range ligt
        # -------------------------------------------------
        for ax_name in fig.layout:
            if ax_name.startswith("xaxis"):
                xaxis = getattr(fig.layout, ax_name)
                if hasattr(xaxis, "range") and xaxis.range and len(xaxis.range) == 2:
                    try:
                        x0, x1 = pd.to_datetime(xaxis.range[0]), pd.to_datetime(xaxis.range[1])
                        if x0 <= dt <= x1:
                            print(f"[DEBUG] {ax_name}: dt binnen zichtbare range ({x0} - {x1})")
                            # niets doen, de lijn blijft gewoon staan
                        else:
                            # tijdlijn valt buiten zichtbare range → lichte buffer aanbrengen
                            buffer = (x1 - x0) * 0.03
                            if dt > x1:
                                xaxis.range = [x0, dt + buffer]
                                print(f"[DEBUG] {ax_name}: range uitgebreid naar rechts tot {dt + buffer}")
                            elif dt < x0:
                                xaxis.range = [dt - buffer, x1]
                                print(f"[DEBUG] {ax_name}: range uitgebreid naar links tot {dt - buffer}")
                    except Exception as e:
                        print(f"[DEBUG] Error parsing {ax_name} range: {e}")

        # -------------------------------------------------
        # 2️⃣ Oude shapes opruimen behalve andere objecten
        # -------------------------------------------------
        existing = []
        if fig.layout.shapes:
            for s in fig.layout.shapes:
                name = getattr(s, "name", None)
                if isinstance(s, dict):
                    name = s.get("name")
                if name != "time_marker":
                    existing.append(s)

        # -------------------------------------------------
        # 3️⃣ Nieuwe verticale lijn tekenen
        # -------------------------------------------------
        new_shapes = []
        for i in range(1, rows + 1):
            xref = "x" if i == 1 else f"x{i}"
            new_shapes.append(
                dict(
                    type="line",
                    name="time_marker",
                    x0=dt,
                    x1=dt,
                    y0=0,
                    y1=1,
                    xref=xref,
                    yref="paper",
                    layer="above",
                    line=dict(color="lightblue", width=3, dash="dot"),
                )
            )

        fig.layout.shapes = tuple(existing + new_shapes)
        print(f"[DEBUG] -> Added {len(new_shapes)} time_marker shapes")
        return fig
