import plotly.graph_objs as go
import pandas as pd


class WaterstandPlot:
    def __init__(self, df_locs_mpn):
        self.df_locs_mpn = df_locs_mpn

    def build(self, fig, df_pgb, df_mpn, pgb_props, row=3):
        """Subplot met peilgebied- en meetpuntwaterstanden."""
        if (df_pgb is None or df_pgb.empty) and (df_mpn is None or df_mpn.empty):
            return fig

        # ====== Bereik bepalen ======
        # Combineer alle tijdassen
        x_all = []
        if df_pgb is not None and not df_pgb.empty:
            x_all.append(df_pgb.index)
        if df_mpn is not None and not df_mpn.empty:
            x_all.append(df_mpn.index)

        x_min = min([x.min() for x in x_all]) if x_all else None
        x_max = max([x.max() for x in x_all]) if x_all else None

        # Combineer alle y-waarden voor bereik
        y_all = []
        if df_pgb is not None and not df_pgb.empty:
            y_all.extend(df_pgb.values.flatten())
        if df_mpn is not None and not df_mpn.empty:
            y_all.extend(df_mpn.values.flatten())

        y_min = float(pd.Series(y_all).min()) if y_all else None
        y_max = float(pd.Series(y_all).max()) if y_all else None

        # ====== Meetpunt-traces ======
        if df_mpn is not None and not df_mpn.empty:
            for location_id in df_mpn.columns.get_level_values("location_id"):
                naam = self.df_locs_mpn.loc[
                    self.df_locs_mpn.location_id == location_id, "naam"
                ].iat[0]
                fig.add_trace(
                    go.Scatter(
                        x=df_mpn.index,
                        y=df_mpn[location_id].iloc[:, 0],
                        mode="lines",
                        line=dict(color="rgba(100,116,139,0.4)", width=2),
                        meta=location_id,
                        hovertemplate=(
                            "tijd: %{x|%Y-%m-%d %H:%M}<br>"
                            "waterstand: %{y:.3f} mNAP<br>"
                            f"naam: {naam}<br>"
                            "location_id: %{meta}<extra></extra>"
                        ),
                        showlegend=False,
                    ),
                    row=row,
                    col=1,
                )

        # ====== Peilgebiedlijn ======
        if df_pgb is not None and not df_pgb.empty:
            fig.add_trace(
                go.Scatter(
                    x=df_pgb.index,
                    y=df_pgb.iloc[:, 0],
                    mode="lines",
                    line=dict(color="#1e40af", width=3),
                    hovertemplate="tijd: %{x|%Y-%m-%d %H:%M}<br>peilgebied: %{y:.3f} mNAP<extra></extra>",
                    showlegend=False,
                ),
                row=row,
                col=1,
            )

        # ====== Streefpeil ======
        streefpeil = pgb_props.get("streefpeil")
        if streefpeil is not None and pd.notnull(streefpeil):
            x_vals = (
                list(df_pgb.index)
                if df_pgb is not None and not df_pgb.empty
                else sorted(list(df_mpn.index.unique()))
            )
            if x_vals:
                y_val = streefpeil
                fig.add_trace(
                    go.Scatter(
                        x=x_vals,
                        y=[y_val] * len(x_vals),
                        mode="lines",
                        line=dict(dash="dash", color="#facc15", width=2),
                        hoverinfo="text",
                        hovertext=[f"Streefpeil: {y_val:.2f} mNAP"] * len(x_vals),
                        showlegend=False,
                    ),
                    row=row,
                    col=1,
                )
                fig.add_annotation(
                    x=x_vals[0],
                    y=y_val,
                    xref=f"x{row}",
                    yref=f"y{row}",
                    text="streefpeil",
                    font=dict(color="#facc15", size=13),
                    showarrow=False,
                    bgcolor="rgba(255,255,255,0.7)",
                    borderpad=2,
                )

        # ====== As-instellingen ======
        if x_min is not None and x_max is not None:
            fig.update_xaxes(
                range=[x_min, x_max],
                minallowed=x_min,
                maxallowed=x_max,
                showgrid=True,
                gridcolor="rgba(0,0,0,0.1)",
                autorange=False,
                automargin=False,
                row=row,
                col=1,
            )

        if y_min is not None and y_max is not None:
            # Kleine marge toevoegen voor betere leesbaarheid
            margin = (y_max - y_min) * 0.05 if y_max > y_min else 0.1
            fig.update_yaxes(
                range=[y_min - margin, y_max + margin],
                minallowed=y_min - margin,
                maxallowed=y_max + margin,
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
