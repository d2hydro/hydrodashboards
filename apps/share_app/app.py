# %%
from dash import Dash, dcc, html
from share_url import ShareURL
from pathlib import Path

assets_folder = Path(__file__).parent.joinpath("assets")
assets_folder.mkdir(exist_ok=True, parents=True)
app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    assets_folder=assets_folder.as_posix(),
    assets_url_path="/assets",
)

# layout components
share_button = ShareURL(
    mapping={
        "locatie": ("location-dropdown", "value"),
    },
    assets_folder=assets_folder,
)

app.layout = html.Div(
    [
        html.Div(
            [
                html.H3(
                    "Mijn Dashboard",
                    style={"display": "inline-block", "marginRight": "0.5rem"},
                ),
                share_button.layout,
            ],
            style={"display": "flex", "alignItems": "center", "gap": "0.25rem"},
        ),
        dcc.Dropdown(
            id="location-dropdown",
            options=[
                {"label": "HHNK", "value": "hhnk"},
                {"label": "Delfland", "value": "delfland"},
            ],
            clearable=False,
        ),
        dcc.DatePickerSingle(
            id="datum-picker",
        ),
        html.Div(id="content"),
    ]
)

# CALLBACKS

# callbacks for share button and parsing url
share_button.register_callbacks(app=app)

# %%
if __name__ == "__main__":
    app.run(debug=True)
