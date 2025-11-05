import plotly.graph_objects as go
import pandas as pd


class VullingPlot:
    def __init__(self, kleurklassen):
        self.kleurklassen = kleurklassen

    def build(
        self,
        fig,
        df_vul,
        df_vg,
        pgb_props,
        row=2,
        x_min=None,
        x_max=None,
    ):
        """
        Subplot met vulling + drempels.
        - x-as begrensd op [x_min, x_max]
        - y-as loopt altijd tot max(ymax, 60)
        - kleurbanden doorlopend tot bovenste aswaarde
        """
        # --- Geen data ---
        if df_vul is None or df_vul.empty:
            if x_min is not None and x_max is not None:
                self._draw_bands(fig, x_min, x_max, 60, row)
                fig.update_yaxes(range=[0, 60], row=row, col=1)
            return fig

        # --- X-bereik bepalen ---
        x_min_data = df_vul.index.min()
        x_max_data = df_vul.index.max()
        x_min = x_min or x_min_data
        x_max = x_max or x_max_data

        # --- Y-bereik bepalen ---
        y_series = df_vul.iloc[:, 0].dropna()
        ymax = float(y_series.max()) if not y_series.empty else 0.0
        if pd.isna(ymax):
            ymax = 0.0

        axis_top = max(60.0, ymax)

        # --- Achtergrondbanden ---
        self._draw_bands(fig, x_min, x_max, axis_top, row)

        # --- Hoofdlijn ---
        fig.add_trace(
            go.Scatter(
                x=df_vul.index,
                y=df_vul.iloc[:, 0],
                mode="lines",
                line=dict(color="#1e40af", width=3),
                hovertemplate="tijd: %{x|%Y-%m-%d %H:%M}<br>vulling: %{y:.1f} mm<extra></extra>",
                showlegend=False,
            ),
            row=row,
            col=1,
        )

        # --- Drempel-lijnen ---
        self._add_thresholds(fig, df_vul, df_vg, pgb_props, row)

        # --- Asinstellingen ---
        fig.update_xaxes(
            range=[x_min, x_max],
            minallowed=x_min,
            maxallowed=x_max,
            autorange=False,
            automargin=False,
            showgrid=True,
            gridcolor="rgba(0,0,0,0.1)",
            row=row,
            col=1,
        )

        fig.update_yaxes(
            range=[0, axis_top],
            minallowed=0,
            maxallowed=axis_top,
            autorange=False,
            automargin=False,
            showgrid=True,
            gridcolor="rgba(0,0,0,0.1)",
            gridwidth=1,
            zeroline=False,
            row=row,
            col=1,
        )

        return fig

    # ============================================================
    # Hulpfuncties
    # ============================================================

    def _draw_bands(self, fig, x_min, x_max, axis_top, row):
        """Teken achtergrondkleurbanden tot aan axis_top."""
        for low, high, color in self.kleurklassen:
            upper = min(high, axis_top)
            if upper > low:
                fill_col = color.replace("1.0", "0.75") if "1.0" in color else color
                fig.add_trace(
                    go.Scatter(
                        x=[x_min, x_max, x_max, x_min],
                        y=[low, low, upper, upper],
                        mode="none",
                        fill="toself",
                        fillcolor=fill_col,
                        line=dict(width=0),
                        hoverinfo="skip",
                        showlegend=False,
                    ),
                    row=row,
                    col=1,
                )

        # Extra zone boven hoogste klasse
        if self.kleurklassen:
            highest_top = max(k[1] for k in self.kleurklassen)
            if axis_top > highest_top:
                last_color = self.kleurklassen[-1][2]
                fill_col = last_color.replace("1.0", "0.6") if "1.0" in last_color else last_color
                fig.add_trace(
                    go.Scatter(
                        x=[x_min, x_max, x_max, x_min],
                        y=[highest_top, highest_top, axis_top, axis_top],
                        mode="none",
                        fill="toself",
                        fillcolor=fill_col,
                        line=dict(width=0),
                        hoverinfo="skip",
                        showlegend=False,
                    ),
                    row=row,
                    col=1,
                )

    def _add_thresholds(self, fig, df_vul, df_vg, pgb_props, row):
        """Teken horizontale lijnen voor drempels."""
        def add_line(yval, kleur, tekst, x_vals):
            if yval is None or pd.isna(yval) or not x_vals:
                return
            fig.add_trace(
                go.Scatter(
                    x=[x_vals[0], x_vals[-1]],
                    y=[yval, yval],
                    mode="lines",
                    line=dict(color=kleur, width=2, dash="dot"),
                    hoverinfo="skip",
                    showlegend=False,
                ),
                row=row,
                col=1,
            )
            fig.add_annotation(
                x=x_vals[0],
                y=yval,
                xref=f"x{row}",
                yref=f"y{row}",
                text=tekst,
                font=dict(color=kleur, size=12),
                showarrow=False,
                bgcolor="rgba(255,255,255,0.7)",
                borderpad=2,
            )

        x_vals = df_vul.index.to_list()
        overlast = pgb_props.get("berging_bij_inundatiepeil")
        inundatiepeil = pgb_props.get("inundatiepeil")
        nulpeil = pgb_props.get("peil_bij_nul_berging")

        add_line(overlast, "red", "overlast", x_vals)
        if inundatiepeil:
            add_line(inundatiepeil * 10, "red", "inundatiepeil", x_vals)
        if nulpeil:
            add_line(nulpeil * 10, "green", "nulpeil", x_vals)
