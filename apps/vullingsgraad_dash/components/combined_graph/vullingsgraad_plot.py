import plotly.graph_objs as go

class VullingsgraadPlot:
    def __init__(self, kleurklassen):
        self.kleurklassen = kleurklassen

    def build(self, fig, df_vg, row=1):
        """Bouw subplot voor vullingsgraad [%]."""
        if df_vg is None or df_vg.empty:
            return fig

        # Bereik van de x-as bepalen
        x_min, x_max = df_vg.index.min(), df_vg.index.max()

        # Achtergrondbanden
        for low, high, color in self.kleurklassen:
            fig.add_trace(
                go.Scatter(
                    x=[x_min, x_max, x_max, x_min],
                    y=[low, low, high, high],
                    mode="none",
                    fill="toself",
                    fillcolor=color.replace("1.0", "0.75"),
                    line=dict(width=0),
                    hoverinfo="skip",
                    showlegend=False,
                ),
                row=row,
                col=1,
            )

        # Hoofdlijn
        fig.add_trace(
            go.Scatter(
                x=df_vg.index,
                y=df_vg.iloc[:, 0],
                mode="lines",
                line=dict(color="#1e40af", width=3),
                hovertemplate="tijd: %{x|%Y-%m-%d %H:%M}<br>vullingsgraad: %{y:.1f}%<extra></extra>",
                showlegend=False,
            ),
            row=row,
            col=1,
        )

        # X-as instellingen
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

        # Y-as instellingen
        fig.update_yaxes(
            range=[0, 100],
            minallowed=0,
            maxallowed=100,
            autorange=True, 
            fixedrange=False,
            automargin=False,
            tickformat=".0f",
          #  tickvals=[25, 50, 75, 100],
            showgrid=True,
            gridcolor="rgba(0,0,0,0.1)",
            gridwidth=1,
            zeroline=False,
            row=row,
            col=1,
        )

        return fig
