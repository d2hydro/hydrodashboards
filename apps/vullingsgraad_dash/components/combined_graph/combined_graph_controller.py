import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from dash import dcc, html, Input, Output, State, callback_context, no_update
from dash.exceptions import PreventUpdate
from datetime import datetime

from .vullingsgraad_plot import VullingsgraadPlot
from .vulling_plot import VullingPlot
from .waterstand_plot import WaterstandPlot
from .time_marker import TimeMarker
from utils.style import combined_graph_style


# ============================================================
# 📊 FIGURE BUILDER — data ophalen + subplots bouwen
# ============================================================

class CombinedGraphFigure:
    """Bouwt de gecombineerde grafiek met drie subplots."""

    def __init__(self, df_locs_mpn, geojson_data, cache, time_series_cache,
                 vullingsgraad_classes, vulling_classes):
        self.df_locs_mpn = df_locs_mpn
        self.geojson_data = geojson_data
        self.cache = cache
        self.time_series_cache = time_series_cache
        self.vg_plot = VullingsgraadPlot(vullingsgraad_classes)
        self.vul_plot = VullingPlot(vulling_classes)
        self.ws_plot = WaterstandPlot(df_locs_mpn)

    def build(self, sel, kaartvariabele):
        """Genereer de gecombineerde grafiek."""
        if not sel:
            return go.Figure()

        cache_key = f"combined_v5_{sel}"
        cached = self.cache.get(cache_key) if getattr(self.cache, "cache", None) else None
        if cached:
            return go.Figure(cached)

        ts = self.time_series_cache

        df_vg = ts.get_time_series("VullingsgraadOutput", "vullingsgraad", location_ids=[sel])
        df_vul = ts.get_time_series("VullingsgraadOutput", "vulling_mm", location_ids=[sel])
        df_pgb = ts.get_time_series("PeilgebiedWaterstandOutput", "H.meting", location_ids=[sel])

        mpn_ids = self.df_locs_mpn.loc[
            self.df_locs_mpn["peilgebied_combi_attr"] == sel, "location_id"
        ].tolist()
        df_mpn = ts.get_time_series(
            "PeilgebiedWaterstandMeetpunt", "H.meting", location_ids=mpn_ids
        )

        pgb_props = next(
            (f["properties"] for f in self.geojson_data["features"]
             if f["properties"].get("location_id") == sel),
            {},
        )

        # Subplots
        fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=["Vullingsgraad [%]", "Vulling [mm]", "Waterstand [mNAP]"],
        )

        self.vg_plot.build(fig, df_vg, row=1)
        self.vul_plot.build(fig, df_vul, df_vg, pgb_props, row=2)
        self.ws_plot.build(fig, df_pgb, df_mpn, pgb_props, row=3)

        # Layout
        fig.update_xaxes(title_text="Tijd", row=3, col=1)
        fig.update_layout(
            uirevision=sel,
            margin=dict(l=40, r=10, t=60, b=40),
            plot_bgcolor="white",
            hovermode="closest",
            font=dict(size=13),
            showlegend=False,
        )

        # Cache
        try:
            if getattr(self.cache, "cache", None) is not None:
                self.cache.set(cache_key, fig.to_dict())
        except Exception:
            pass

        return fig


# ============================================================
# ⚙️ COMBINED GRAPH — Dash layout + callbacks
# ============================================================

class CombinedGraph:
    """Dash-component die de gecombineerde grafiek aanstuurt."""

    def __init__(self, df_locs_mpn, geojson_data, cache, time_series_cache,
                 all_datetimes, vullingsgraad_classes, vulling_classes):
        self.all_datetimes = all_datetimes
        self.figure_builder = CombinedGraphFigure(
            df_locs_mpn, geojson_data, cache, time_series_cache,
            vullingsgraad_classes, vulling_classes,
        )
        self.time_marker = TimeMarker(all_datetimes)

    # ------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------
    @property
    def layout(self):
        """UI-component met lege initiële grafiek."""
        empty_fig = go.Figure()
        empty_fig.update_xaxes(visible=False)
        empty_fig.update_yaxes(visible=False)
        empty_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False,
        )

        graph_config = {
            "displayModeBar": True,
            "scrollZoom": True,
            "displaylogo": False,
            "modeBarButtonsToRemove": ["toImage"],
            "edits": {"shapePosition": True},
            "responsive": True,
        }

        return html.Div(
            [
                dcc.Store(id="combined-fig-store"),
                dcc.Graph(
                    id="combined-graph",
                    figure=empty_fig,
                    config=graph_config,
                    style=combined_graph_style,
                ),
            ]
        )

    # ------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------
    def register_callbacks(self, app):
        """Registreert alle callbacks voor de gecombineerde grafiek."""

        # --- Callback: figuur opbouwen bij start en wijziging ---
        @app.callback(
            Output("combined-fig-store", "data"),
            [Input("pgb-dropdown", "value"), Input("kaartvariabele-dropdown", "value")],
            prevent_initial_call=False,
        )
        def update_combined_figure(sel, var):
            if not sel:
                from app import default_pgb as sel
            if not var:
                from app import initial_kaartvariabele as var

            if not sel or not var:
                raise PreventUpdate

            fig = self.figure_builder.build(sel, var)
            fig = self.time_marker.apply(fig, 0)
            return fig.to_dict()

        # --- Callback: update + highlight + tijdlijn ---
        @app.callback(
            Output("combined-graph", "figure"),
            Output("clicked-mpn-store", "data", allow_duplicate=True),
            [
                Input("combined-fig-store", "data"),
                Input("marker-mpn", "clickData"),
                Input("clicked-mpn-store", "data"),
                Input("clicked-trace-store", "data"),
                Input("tijdslider", "value"),
                Input("combined-graph", "relayoutData"),
            ],
            State("combined-graph", "figure"),
            prevent_initial_call=True,
        )
        def update_and_highlight(fig_dict, marker_click, clicked_mpn,
                                 clicked_trace, idx, relayout, current_fig):
            ctx = callback_context
            trigger = ctx.triggered_id

            # Figuurselectie met fallback
            if trigger == "combined-graph" and relayout:
                fig = go.Figure(current_fig)
                if (not fig.data or len(fig.data) == 0) and fig_dict:
                    fig = go.Figure(fig_dict)
            else:
                fig = go.Figure(fig_dict or current_fig)

            if not fig.data:
                fig = go.Figure(fig_dict or {})

            # Selectie bepalen
            sel_id = None
            if trigger == "clicked-trace-store" and clicked_trace:
                sel_id = clicked_trace.get("id")
            elif trigger in ["marker-mpn", "clicked-mpn-store"]:
                props = (marker_click or clicked_mpn or {}).get("properties", {})
                sel_id = props.get("location_id")

            # Highlight toepassen
            if sel_id:
                for tr in fig.data:
                    meta_val = getattr(tr, "meta", None)
                    if meta_val:
                        if meta_val == sel_id:
                            tr.line.color = "rgba(251,191,36,1)"
                            tr.line.width = 3.4
                        else:
                            tr.line.color = "rgba(100,116,139,0.25)"
                            tr.line.width = 2

            # Tijdlijn tekenen
            if idx is not None:
                fig = self.time_marker.apply(fig, idx)
            elif relayout and isinstance(relayout, dict) and len(relayout) > 0:
                fig = self.time_marker.apply(fig, idx)

            if trigger == "clicked-trace-store":
                return fig, None

            return fig, no_update

        # --- Callback: sync tijdslider bij vline-slepen ---
        @app.callback(
            Output("tijdslider", "value", allow_duplicate=True),
            Input("combined-graph", "relayoutData"),
            prevent_initial_call=True,
        )
        def sync_slider_from_vline(relayout):
            if not relayout:
                raise PreventUpdate
            x_vals = [
                pd.to_datetime(v)
                for k, v in relayout.items()
                if k.endswith(".x0") or k.endswith(".x1")
            ]
            if not x_vals:
                raise PreventUpdate

            dt = x_vals[0]
            idx = min(
                range(len(self.all_datetimes)),
                key=lambda i: abs(self.all_datetimes[i] - dt),
            )
            return idx

        # --- Callback: klik op grafiek onthoud geselecteerde trace ---
        @app.callback(
            Output("clicked-trace-store", "data"),
            Input("combined-graph", "clickData"),
            State("combined-graph", "figure"),
            prevent_initial_call=True,
        )
        def remember_clicked_trace(graph_click, current_fig_dict):
            if not graph_click or not current_fig_dict or "points" not in graph_click:
                raise PreventUpdate
            fig = go.Figure(current_fig_dict)
            point = graph_click["points"][0]
            trace = fig.data[point["curveNumber"]]
            sel_id = getattr(trace, "meta", None)
            if sel_id is None:
                raise PreventUpdate
            return {"id": sel_id, "ts": datetime.utcnow().isoformat()}
