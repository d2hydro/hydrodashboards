from dash import Dash, dcc, html, Input, Output, State, exceptions
import urllib.parse


def _parse_querystring(search: str) -> dict:
    # search is bv "?gebied=hhnk&date=2025-10-01&autoplay=true"
    if not search:
        return {}
    # strip de leading "?"
    query = urllib.parse.parse_qs(search.lstrip("?"))
    # parse_qs geeft lists terug: {'gebied': ['hhnk'], 'date': ['2025-10-01']}
    # wij willen scalars
    flat = {key: vals[0] for key, vals in query.items()}

    # type casting & defaults
    state = {
        "gebied": flat.get("gebied", "hhnk"),
        "date": flat.get("date", "2025-10-01"),
        "autoplay": flat.get("autoplay", "false").lower() == "true",
    }
    print(state)
    return state


class ShareButton:
    @property
    def layout(self):
        return layout()


def layout():
    return html.Div(
        [
            dcc.Location(id="url", refresh=False),
            dcc.Store(id="url-state"),
            dcc.Store(id="ui-state"),
            dcc.Store(id="app-initialized"),
            html.Button(
                id="share-button",
                title="Kopieer link",
                children="🔗",
                className="share-button",
            ),
        ]
    )


def register_callbacks(app: Dash):
    # check url and set initialized
    @app.callback(
        Output("url-state", "data"),
        Output("app-initialized", "data"),
        Input("url", "search"),
        prevent_initial_call=False,
    )
    def sync_url_to_urlstate(search):
        # Stap 1: lees URL -> state
        print(search)
        parsed = _parse_querystring(search or "")

        # Stap 2: zet initialized True ALS er iets in de query zat
        # (als iemand gewoon / opent zonder ?params, willen we niet 'forceren'
        # en ook niet de URL herschrijven)
        did_init = bool(search and search != "")

        print(parsed)

        return parsed, {"initialized": did_init}

    # clean na app-initialized
    @app.callback(
        Output("url", "search", allow_duplicate=True),
        Input("app-initialized", "data"),
        prevent_initial_call=True,
    )
    def cleanup_url_search(app_init):
        # app_init is bijvoorbeeld {"initialized": True}
        if not app_init or not app_init.get("initialized"):
            raise exceptions.PreventUpdate

        # We zetten de querystring leeg
        return ""

    # update app from url-state
    @app.callback(
        Output("gebied-dropdown", "value"),
        Output("datum-picker", "date"),
        Input("url-state", "data"),
        State("gebied-dropdown", "value"),
        State("datum-picker", "date"),
        prevent_initial_call=False,
    )
    def apply_urlstate_to_controls(url_state, current_gebied, current_date):
        if url_state is None:
            url_state = {}

        gebied_from_url = url_state.get("gebied")
        date_from_url = url_state.get("date")

        new_gebied = current_gebied if current_gebied is not None else gebied_from_url
        new_date = current_date if current_date is not None else date_from_url

        return new_gebied, new_date

    @app.callback(
        Output("ui-state", "data"),
        Input("gebied-dropdown", "value"),
        Input("datum-picker", "date"),
        prevent_initial_call=False,
    )
    def controls_to_ui_state(gebied, date):
        return {
            "gebied": gebied,
            "date": date,
        }

    app.clientside_callback(
        """
        function(n_clicks, ui_state, current_style) {
            // n_clicks is how we know user actually clicked
            if (!n_clicks) {
                // nothing clicked yet -> don't change visibility of the feedback bubble
                return current_style || {};
            }

            // 1. Build querystring from ui_state
            // ui_state is e.g. {gebied: "hhnk", date: "2025-10-01"}
            var params = new URLSearchParams();

            if (ui_state && typeof ui_state === "object") {
                Object.keys(ui_state).forEach(function(key) {
                    if (ui_state[key] !== undefined && ui_state[key] !== null) {
                        params.set(key, ui_state[key]);
                    }
                });
            }

            // 2. Compose full share URL
            // window.location.origin = "http://localhost:8050"
            // window.location.pathname = "/"
            var shareUrl = window.location.origin + window.location.pathname;
            var qs = params.toString();
            if (qs.length > 0) {
                shareUrl += "?" + qs;
            }

            // 3. Copy to clipboard
            if (navigator && navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(shareUrl);
            } else {
                // fallback voor oudere browsers: maak tijdelijk een textarea
                var tmp = document.createElement("textarea");
                tmp.value = shareUrl;
                document.body.appendChild(tmp);
                tmp.select();
                try {
                    document.execCommand("copy");
                } catch(e) {}
                document.body.removeChild(tmp);
            }
        }
        """,
        Input("share-button", "n_clicks"),
        State("ui-state", "data"),
    )
