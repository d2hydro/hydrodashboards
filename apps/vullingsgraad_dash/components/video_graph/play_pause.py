from dash import html, dcc


class PlayPauseControls:
    def __init__(
        self,
        button_id="playpause-button",
        store_id="is-playing",
        interval_id="interval",
        button_style=None,
    ):
        self.button_id = button_id
        self.store_id = store_id
        self.interval_id = interval_id
        self.button_style = button_style or {
            "width": "72px",
            "height": "32px",
            "borderRadius": "6px",
            "margin-left": "5px",
            "backgroundColor": "#f0f0f0",     
            "color": "white",
            "fontWeight": "bold",
            "fontSize": "14px",
            "border": "none",
            "cursor": "pointer",
            "boxShadow": "0 2px 4px rgba(0,0,0,0.2)",
        }

    @property
    def layout(self):
        """
        Layout met:
        - Play/pause-knop
        - Store voor afspeelstatus
        - Interval voor autoplay
        """
        return html.Div(
            [
                # De knop zelf
                html.Button(
                    id=self.button_id,
                    n_clicks=0,
                    children="▶️",  # start-icoon (kan via callback veranderen)
                    style=self.button_style,
                ),
                # Afspeelstatus (True = playing, False = paused)
                dcc.Store(id=self.store_id, data=False),

                # Interval voor automatisch doorschuiven (1 seconde)
                dcc.Interval(id=self.interval_id, interval=1000, disabled=True),
            ],
            style={
                "display": "flex",
                "gap": "4px",
                "alignItems": "center",
            },
        )
