# %%
from dash import Dash, html, dcc
import plotly.express as px
import dash_leaflet as dl
import pandas as pd

app = Dash(__name__)

df = pd.date_range("2023-01-01", periods=100, freq="D").to_frame(
    index=False, name="date"
)
df["value"] = (df.index**1.5) % 50
fig = px.line(df, x="date", y="value", title="Dummy Time Series")


app.layout = html.Div(
    [
        html.Div(
            [
                html.Div(
                    [
                        dl.Map(
                            id="leaflet-map",
                            center=[52.1, 5.1],
                            zoom=13,
                            style={"width": "100%", "height": "100%"},
                            children=[dl.TileLayer()],
                        )
                    ],
                    id="left-panel",
                    style={
                        "width": "50%",
                        "height": "100%",
                        "overflow": "auto",
                    },
                ),
                html.Div(
                    id="dragbar",
                    style={
                        "width": "10px",
                        "cursor": "col-resize",
                        "backgroundColor": "gray",
                        "height": "100%",
                        "zIndex": "10",
                    },
                ),
                html.Div(
                    [dcc.Graph(figure=fig, style={"width": "100%", "height": "100%"})],
                    id="right-panel",
                    style={
                        "flex": "1",
                        "height": "100%",
                        "minWidth": "200px",
                    },
                ),
            ],
            id="container",
            style={"display": "flex", "flexDirection": "row", "height": "100vh"},
        )
    ]
)

if __name__ == "__main__":
    app.run(debug=False)
