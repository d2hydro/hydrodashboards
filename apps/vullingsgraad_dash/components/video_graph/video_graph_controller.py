from dash import html, dcc, Input, Output, State
from dash.exceptions import PreventUpdate
from .mini_graph import MiniGraph
from .time_slider import TimeSlider
from .play_pause import PlayPauseControls


class TimeControls:
    """Volledige tijdsbediening: play/pause, mini-grafiek, slider en datumlabel."""

    def __init__(self, all_datetimes, default_index, time_series_cache):
        self.all_datetimes = all_datetimes
        self.default_index = default_index
        self.time_series_cache = time_series_cache

        # Subcomponenten
        self.mini = MiniGraph("mini-tijdserie", all_datetimes, time_series_cache)
        self.slider = TimeSlider("tijdslider", all_datetimes, default_index)
        self.playpause = PlayPauseControls()

    # ========= Layout =========
    @property
    def layout(self):
        """Layout van de tijdsbediening, inclusief datumlabel."""
        return html.Div(
            style={
                "position": "absolute",
                "bottom": "14px",
                "left": "1%",
               # "transform": "translateX(-50%)",
                "background": "rgba(255,255,255,0.95)",
                "padding": "1px 1px",
                "borderRadius": "10px",
                "display": "flex",
                "flexDirection": "column",
                "alignItems": "center",
                "boxShadow": "0 2px 8px rgba(0,0,0,0.15)",
                "zIndex": 800,  # lager dan datumlabel elders
            },
            children=[
                # Datumlabel boven de slider
                html.Div(
                    id="datum-label",
                    children="2024-01-01 00:00",
                    style={
                        "marginBottom": "0px",
                        "fontWeight": "bold",
                        "background": "rgba(255,255,255,0.85)",
                        "padding": "3px 8px",
                        "borderRadius": "4px",
                        "zIndex": 850,
                    },
                ),

                # Rij met play/pause en sliderdeel
                html.Div(
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        #"gap": "14px",
                    },
                    children=[
                        # ▶️ Play/pauseknop
                        html.Div(
                            self.playpause.layout,
                            style={
                                "flex": "0 0 auto",
                                "display": "flex",
                                "alignItems": "center",
                                "justifyContent": "center",
                            },
                        ),

                        # 📈 Mini-grafiek + slider
                        html.Div(
                            [
                                html.Div(
                                    self.mini.layout,
                                    style={
                                        "height": "55px",
                                        "marginBottom": "0px",
                                        "overflow": "hidden",
                                    },
                                ),
                                html.Div(
                                    self.slider.layout,
                                    style={"height": "24px"},
                                ),
                            ],
                            style={
                                "display": "flex",
                                "flexDirection": "column",
                                "width": "400px",
                            },
                        ),
                    ],
                ),
            ],
        )

    # ========= Callbacks =========
    def register_callbacks(self, app):
        """Callbacks voor mini-grafiek, play/pause, slider-animatie en datumlabel."""

        # Mini-grafiek updaten
        @app.callback(
            Output(self.mini.id, "figure"),
            [
                Input("pgb-dropdown", "value"),
                Input("kaartvariabele-dropdown", "value"),
                Input(self.slider.id, "value"),
            ],
        )
        def _update_mini(sel, var, idx):
            if not sel or not var:
                raise PreventUpdate
            return self.mini.build(sel, var, idx)

        # 🔸 Datumlabel updaten
        @app.callback(
            Output("datum-label", "children"),
            Input(self.slider.id, "value"),
        )
        def _update_date_label(idx):
            """Zet juiste datum/tijd boven mini-grafiek."""
            if idx is None or idx >= len(self.all_datetimes):
                raise PreventUpdate
            dt = self.all_datetimes[int(idx)]
            return dt.strftime("%Y-%m-%d %H:%M")

        # Play/pause toggelen
        @app.callback(
            Output(self.playpause.store_id, "data"),
            Input(self.playpause.button_id, "n_clicks"),
            State(self.playpause.store_id, "data"),
            prevent_initial_call=True,
        )
        def toggle_play(n, is_playing):
            if not n:
                raise PreventUpdate
            return not is_playing

        # Interval aan/uit
        @app.callback(
            Output(self.playpause.interval_id, "disabled"),
            Input(self.playpause.store_id, "data"),
        )
        def start_stop_interval(is_playing):
            return not is_playing

        # Tijdslider vooruit laten lopen
        @app.callback(
            Output(self.slider.id, "value"),
            Input(self.playpause.interval_id, "n_intervals"),
            State(self.slider.id, "value"),
            prevent_initial_call=True,
        )
        def advance_time(n, current_idx):
            if current_idx is None:
                current_idx = 0
            new_idx = (current_idx + 1) % len(self.all_datetimes)
            return new_idx

        # Knop-icoon wisselen
        @app.callback(
            Output(self.playpause.button_id, "children"),
            Input(self.playpause.store_id, "data"),
        )
        def update_button_icon(is_playing):
            return "⏸️" if is_playing else "▶️"

