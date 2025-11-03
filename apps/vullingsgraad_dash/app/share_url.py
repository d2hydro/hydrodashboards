from dash import Dash, dcc, html, Input, Output, State, exceptions
import urllib.parse
from pathlib import Path


def _parse_querystring(search: str, mapping) -> dict:
    """By exammple url?location=my_selected_location&date=2025-10-01"""
    if not search:
        return {}
    # strip de leading "?"
    query = urllib.parse.parse_qs(search.lstrip("?"))
    # strip first value from list
    state = {key: vals[0] for key, vals in query.items() if key in mapping.keys()}
    return state


def _write_css(assets_folder: Path):
    """Write button styling to css-file"""
    assets_folder.mkdir(exist_ok=True, parents=True)
    css_file = assets_folder.joinpath("share_url.css")
    css_file.write_text(""".share-button {
    border: 1px solid #ccc;
    background-color: #fff;
    border-radius: 8px;
    padding: 0.4rem 0.6rem;
    font-size: 0.9rem;
    line-height: 1.2rem;
    cursor: pointer;
    transition: transform 0.08s ease, box-shadow 0.08s ease, background-color 0.12s ease;
    box-shadow: 0 2px 4px rgba(0,0,0,0.08);
}

.share-button:active {
    transform: scale(0.92);
    box-shadow: 0 1px 2px rgba(0,0,0,0.2) inset;
    background-color: #eef;
}""")


class ShareURL:
    def __init__(
        self,
        mapping: dict,
        assets_folder: Path = Path(__file__).parent.joinpath("assets"),
        block_control_update: list[str] = [],
    ):
        """Class to init the app from url parameters and share the current app state als url

        Args:
            mapping (dict): dict with url_key -> app_component_id, component_prop
            example:
            {
                "gebied": ("gebied-dropdown", "value"),
                "date": ("datum-picker", "date"),
            }
        """
        self.mapping = mapping
        self.block_control_update = block_control_update
        _write_css(assets_folder)

    @property
    def layout(self):
        """Components to include in app HTML"""
        return html.Div(
            [
                # app url to strip search parameters from
                dcc.Location(id="url", refresh=False),
                # url-state to parse url search to and strip later
                dcc.Store(id="url-state"),
                # track initialization state so we'll trigger a cleanup after parsing url-state
                dcc.Store(id="app-initialized"),
                # track ui-state for our client-side URL-copy
                dcc.Store(id="ui-state"),
                # share-dummy is to let clientside_callback return something (=compulsory)
                dcc.Store(id="share-dummy"),
                # our button
                html.Button(
                    id="share-button",
                    title="Copy url",
                    children="🔗",
                    className="share-button",
                ),
            ]
        )

    def register_callbacks(self, app: Dash):
        mapping = self.mapping
        """All callbacks to register"""
        ## INIT APP FROM URL CALLBACKS

        # -------- 1. url -> url-state + initialized
        @app.callback(
            Output("url-state", "data"),
            Output("app-initialized", "data"),
            Input("url", "search"),
            prevent_initial_call=False,
        )
        def sync_url_to_urlstate(search):
            # parse query
            parsed = _parse_querystring(search=search or "", mapping=mapping)

            # set inizialized so we'll trigger a search cleanup
            did_init = bool(search and search != "")

            return parsed, {"initialized": did_init}

        # -------- 2. cleanup URL after init
        @app.callback(
            Output("url", "search", allow_duplicate=True),
            Input("app-initialized", "data"),
            prevent_initial_call=True,
        )
        def cleanup_url_search(app_init):
            # clean search url {"initialized": True}
            if not app_init or not app_init.get("initialized"):
                raise exceptions.PreventUpdate

            # Return empty search
            return ""

        # -------- 3. apply url-state -> controls
        keys = [k for k in mapping.keys() if k not in self.block_control_update]

        urlstate_to_control_outputs = []
        urlstate_to_control_states = []

        for k in keys:
            comp_id, comp_prop = mapping[k]
            urlstate_to_control_outputs.append(Output(comp_id, comp_prop))
            urlstate_to_control_states.append(State(comp_id, comp_prop))

        if urlstate_to_control_outputs:

            @app.callback(
                urlstate_to_control_outputs,
                Input("url-state", "data"),
                urlstate_to_control_states,
                prevent_initial_call=False,
            )
            def apply_urlstate_to_controls(url_state, *current_values):
                if url_state is None:
                    url_state = {}

                results = []
                # Voor elke key in dezelfde volgorde
                for i, k in enumerate(mapping.keys()):
                    current_val = current_values[i]
                    val_from_url = url_state.get(k)
                    # keep control value if any, else take from url
                    new_val = current_val if current_val is not None else val_from_url
                    results.append(new_val)

                return results

        # -------- 4. controls -> ui-state

        controls_to_uistate_inputs = [Input(*v) for v in mapping.values()]

        @app.callback(
            Output("ui-state", "data"),
            controls_to_uistate_inputs,
            prevent_initial_call=False,
        )
        def controls_to_ui_state(*values):
            return {k: values[i] for i, k in enumerate(list(mapping.keys()))}

        # -------- 5. share button -> clipboard
        app.clientside_callback(
            """
        function(n_clicks, ui_state) {
            if (!n_clicks) {
                return window.dash_shared_dummy || null;
            }

            var params = new URLSearchParams();
            if (ui_state && typeof ui_state === "object") {
                Object.keys(ui_state).forEach(function(key) {
                    if (ui_state[key] !== undefined && ui_state[key] !== null) {
                        params.set(key, ui_state[key]);
                    }
                });
            }

            var shareUrl = window.location.origin + window.location.pathname;
            var qs = params.toString();
            if (qs.length > 0) {
                shareUrl += "?" + qs;
            }

            if (navigator && navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(shareUrl);
            } else {
                var tmp = document.createElement("textarea");
                tmp.value = shareUrl;
                document.body.appendChild(tmp);
                tmp.select();
                try { document.execCommand("copy"); } catch(e) {}
                document.body.removeChild(tmp);
            }

            window.dash_shared_dummy = shareUrl;
            return shareUrl;
        }
        """,
            Output("share-dummy", "data"),
            Input("share-button", "n_clicks"),
            State("ui-state", "data"),
        )
