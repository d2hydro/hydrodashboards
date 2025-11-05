import plotly.graph_objs as go
from plotly.subplots import make_subplots

from .vullingsgraad_plot import VullingsgraadPlot
from .vulling_plot import VullingPlot
from .waterstand_plot import WaterstandPlot


class CombinedGraphFigure:
    """Bouwt de gecombineerde grafiek van vullingsgraad, vulling en waterstand."""

    def __init__(
        self,
        df_locs_mpn,
        geojson_data,
        cache,
        time_series_cache,
        vullingsgraad_classes,
        vulling_classes,
    ):
        self.df_locs_mpn = df_locs_mpn
        self.geojson_data = geojson_data
        self.cache = cache
        self.time_series_cache = time_series_cache

        self.vg_plot = VullingsgraadPlot(vullingsgraad_classes)
        self.vul_plot = VullingPlot(vulling_classes)
        self.ws_plot = WaterstandPlot(df_locs_mpn)

    def build(self, sel, kaartvariabele):
        """Genereer een gecombineerde grafiek met 3 subplots voor een selectie."""
        if not sel:
            return go.Figure()

        cache_key = f"combined_v5_{sel}"
        cached = self.cache.get(cache_key) if getattr(self.cache, "cache", None) else None
        if cached:
            return go.Figure(cached)

        # ------------------------------
        # Data ophalen
        # ------------------------------
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

        # ------------------------------
        # Figuur bouwen
        # ------------------------------
        fig = make_subplots(
            rows=3,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.06,
            subplot_titles=["Vullingsgraad [%]", "Vulling [mm]", "Waterstand [mNAP]"],
        )

        self.vg_plot.build(fig, df_vg, row=1)
        self.vul_plot.build(fig, df_vul, df_vg, pgb_props, row=2)
        self.ws_plot.build(fig, df_pgb, df_mpn, pgb_props, row=3)

        # ------------------------------
        # Layout instellingen
        # ------------------------------
        fig.update_xaxes(title_text="Tijd", row=3, col=1)
        fig.update_layout(
            uirevision=sel,
            margin=dict(l=40, r=10, t=60, b=40),
            plot_bgcolor="white",
            hovermode="closest",
            font=dict(size=13),
            showlegend=False,
        )

        # Opslaan in cache
        try:
            if getattr(self.cache, "cache", None) is not None:
                self.cache.set(cache_key, fig.to_dict())
        except Exception:
            pass

        return fig
