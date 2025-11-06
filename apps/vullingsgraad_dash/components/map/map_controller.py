import dash_leaflet as dl
from dash import html, dcc, Input, Output, State
from dash.exceptions import PreventUpdate
import pandas as pd
import logging

from .peilgebieden_layers import PeilgebiedenLayer
from .mpn_markers import MPNMarkers
from .base_map_layer import BaseMapLayer
from utils.map_utils import get_kaartdata_for_datetime
from utils.style import map_style


class MapWithControls:
    """Bouwt en beheert de kaart met peilgebieden, meetpunten en interacties."""

    def __init__(
        self,
        geojson_data,
        df_locs_mpn,
        dd_locs_mpn_default,
        map_center,
        map_bounds,
        style_handle,
        initial_stylemap,
        initial_options,
        all_datetimes,
        time_series_cache,
    ):
        self.geojson_data = geojson_data
        self.df_locs_mpn = df_locs_mpn
        self.dd_locs_mpn_default = dd_locs_mpn_default
        self.map_center = map_center
        self.map_bounds = map_bounds
        self.style_handle = style_handle
        self.initial_stylemap = initial_stylemap
        self.initial_options = initial_options
        self.all_datetimes = all_datetimes
        self.time_series_cache = time_series_cache

        # Subcomponenten
        self.base_layer = BaseMapLayer(basemap="osm", opacity=0.5)
        self.peil_layer = PeilgebiedenLayer(
            geojson_data, style_handle, initial_stylemap, initial_options
        )
        self.mpn_layer = MPNMarkers(df_locs_mpn)

    # ------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------
    @property
    def layout(self):
        """Bouwt de Leaflet-kaart met lagen en opslagcomponenten."""
        return html.Div(
            style={"position": "relative", "height": "100%", "width": "100%"},
            children=[
                dl.Map(
                    id="main-map",
                    center=self.map_center,
                    zoom=10,
                    bounds=self.map_bounds,
                    style=map_style,
                    preferCanvas=False,
                    children=[
                        dl.Pane(id="pane-top", name="veryTopPane", style={"zIndex": 650}),
                        self.base_layer.layout,  # Achtergrondkaart
                        self.peil_layer.layout,  # Peilgebieden
                        self.mpn_layer.layout,   # Meetpunten
                        dl.LayerGroup(id="mpn-click-layer", pane="veryTopPane"),
                    ],
                ),
                # Opslag voor interacties
                dcc.Store(id="clicked-mpn-store", data=None),
                dcc.Store(id="clicked-trace-store", data=None),
            ],
        )

    # ------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------
    def register_callbacks(self, app):
        """Registreert alle kaartgerelateerde callbacks."""

        # ========================================================
        # 1️⃣  Update GeoJSON-stijl en opties bij tijd / variabele / selectie
        # ========================================================
        @app.callback(
            Output("geojson-pgb", "hideout"),
            Output("geojson-pgb", "options"),
            [
                Input("tijdslider", "value"),
                Input("pgb-dropdown", "value"),
                Input("kaartvariabele-dropdown", "value"),
            ],
            prevent_initial_call=True,
        )
        def update_geojson_map(idx, selected_pgb, kaartvariabele):
            """Werk kaartkleuren bij bij wijziging tijd, peilgebied of variabele."""
            if idx is None or not selected_pgb or not kaartvariabele:
                raise PreventUpdate

            dt = self.all_datetimes[int(idx)]
            stylemap = get_kaartdata_for_datetime(
                self.time_series_cache, dt, kaartvariabele
            )
            stylemap["selected"] = selected_pgb

            options = {
                "style": self.style_handle,
                "selected": selected_pgb,
                "interactive": True,
                "bubblingMouseEvents": True,
            }

            logging.debug(
                f"🗺️ Kaart bijgewerkt: variabele={kaartvariabele}, tijd={dt}, selectie={selected_pgb}"
            )
            return stylemap, options

        # ========================================================
        # 2️⃣  Klik op peilgebied of URL-herstel -> update controls
        # ========================================================
        @app.callback(
            [
                Output("pgb-dropdown", "value", allow_duplicate=True),
                Output("tijdslider", "value", allow_duplicate=True),
                Output("kaartvariabele-dropdown", "value", allow_duplicate=True),
            ],
            [Input("geojson-pgb", "clickData"), Input("url-state", "data")],
            [
                State("pgb-dropdown", "value"),
                State("tijdslider", "value"),
                State("kaartvariabele-dropdown", "value"),
            ],
            prevent_initial_call="initial_duplicate",
        )
        def select_controls(click_data, url_state, current_pgb, current_idx, current_var):
            """Synchroniseer UI-controls vanuit kaartklik of URL."""
            from dash import callback_context as ctx
            trigger = ctx.triggered_id if ctx.triggered_id else None

            # URL herstel bij opstart
            if trigger == "url-state" and url_state:
                new_pgb = url_state.get("peilgebied", current_pgb)
                new_idx = url_state.get("tijdindex", current_idx)
                new_var = url_state.get("kaartvariabele", current_var)
                try:
                    new_idx = int(new_idx) if new_idx is not None else current_idx
                except (ValueError, TypeError):
                    new_idx = current_idx
                return new_pgb, new_idx, new_var

            # Klik op peilgebied
            if trigger == "geojson-pgb" and click_data:
                props = click_data.get("properties", {}) or {}
                location_id = props.get("location_id") or props.get("CODE")
                if not location_id or location_id == current_pgb:
                    raise PreventUpdate
                return location_id, current_idx, current_var

            raise PreventUpdate

        # ========================================================
        # 3️⃣  Onthoud laatst aangeklikt meetpunt
        # ========================================================
        @app.callback(
            Output("clicked-mpn-store", "data"),
            Input("marker-mpn", "clickData"),
            prevent_initial_call=True,
        )
        def store_clicked_mpn(cd):
            """Sla klikdata van meetpunt op."""
            return cd

        # ========================================================
        # 4️⃣  Update zichtbare meetpunten en selectie
        # ========================================================
        @app.callback(
            Output("marker-mpn", "hideout"),
            [
                Input("pgb-dropdown", "value"),
                Input("tijdslider", "value"),
                Input("clicked-mpn-store", "data"),
                Input("clicked-trace-store", "data"),
            ],
        )
        def update_mpn_markers(selected_location_id, idx, mpn_clickdata, clicked_trace_id):
            """Bepaalt welke meetpunten zichtbaar zijn en markeert selectie."""
            df = self.df_locs_mpn

            if not selected_location_id or "peilgebied_combi_attr" not in df.columns:
                return {"allowed": [], "sel": None, "tick": int(idx) if idx is not None else 0}

            mask = df["peilgebied_combi_attr"].astype(str) == str(selected_location_id)
            points = df[mask]
            allowed = (
                points["peilgebied_combi_attr"].astype(str).dropna().unique().tolist()
                if not points.empty
                else []
            )

            sel_id = None
            if mpn_clickdata and mpn_clickdata.get("properties"):
                sel_id = (
                    mpn_clickdata["properties"].get("location_id")
                    or mpn_clickdata["properties"].get("id")
                )
            elif clicked_trace_id:
                sel_id = (
                    clicked_trace_id.get("id")
                    if isinstance(clicked_trace_id, dict)
                    else clicked_trace_id
                )

            return {
                "allowed": allowed,
                "sel": sel_id,
                "tick": int(idx) if idx is not None else 0,
            }
