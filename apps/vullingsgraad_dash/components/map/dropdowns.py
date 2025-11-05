from dash import html, dcc, Input, Output, State
from utils.style import controls_style


class DropdownControls:
    """Component met de variabele- en peilgebied-dropdowns."""

    def __init__(self, location_options, kaartvariabelen, default_pgb, initial_kaartvariabele, share_url,):
        self.location_options = location_options
        self.kaartvariabelen = kaartvariabelen
        self.default_pgb = default_pgb
        self.initial_kaartvariabele = initial_kaartvariabele
        self.share_url = share_url

    @property
    def layout(self):
        """Returnt de HTML layout van de dropdowncomponent."""
        return html.Div(
            style=controls_style,
            children=[
                html.Label(
                    [
                        "kaartvariabele: ",
                        html.Span("?", title="Variabele voor kaartkleuren", style={"cursor": "help"}),
                    ],
                    style={"fontSize": "13px"},
                ),
                dcc.Dropdown(
                    id="kaartvariabele-dropdown",
                    options=self.kaartvariabelen,
                    value=self.initial_kaartvariabele,
                    clearable=False,
                    style={"width": "240px", "marginBottom": "8px"},
                ),
                html.Label(
                    [
                        "peilgebied: ",
                        html.Span("?", title="Peilgebied voor grafieken", style={"cursor": "help"}),
                    ],
                    style={"fontSize": "13px"},
                ),
                dcc.Dropdown(
                    id="pgb-dropdown",
                    options=self.location_options,
                    value=self.default_pgb,
                    placeholder="Selecteer peilgebied",
                    clearable=True,
                    style={"width": "240px"},
                ),
                html.Div(
                    self.share_url.layout,
                    style={
                        "marginTop": "10px",
                        "background": "rgba(255,255,255,0.9)",
                        "borderRadius": "8px",
                        "padding": "6px 10px",
                        "boxShadow": "0 2px 8px rgba(0,0,0,0.15)",
                        "width": "fit-content",
                        "pointerEvents": "auto",
                    },
                ),
            ],
        )

    def register_callbacks(self, app):
        """Plaats hier eventuele dropdown callbacks (optioneel)."""
        pass
