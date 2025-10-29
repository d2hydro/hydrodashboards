# %%
from dash import Dash, dcc, html
import share_button


app = Dash(__name__, suppress_callback_exceptions=True)

app.layout = html.Div(
    [
        html.Div(
            [
                html.H3(
                    "Mijn Dashboard",
                    style={"display": "inline-block", "marginRight": "0.5rem"},
                ),
                share_button.layout(),
            ],
            style={"display": "flex", "alignItems": "center", "gap": "0.25rem"},
        ),
        dcc.Dropdown(
            id="gebied-dropdown",
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
share_button.register_callbacks(app)

# %%
if __name__ == "__main__":
    app.run(debug=True)
