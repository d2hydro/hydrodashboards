import dash_leaflet as dl
from dash_extensions.javascript import Namespace
from pathlib import Path


class PeilgebiedenLayer:
    """Component die de GeoJSON-laag met peilgebieden bouwt."""

    def __init__(self, geojson_data, initial_stylemap, initial_options, assets_dir):
        self.geojson_data = geojson_data
        self.initial_stylemap = initial_stylemap
        self.initial_options = initial_options

        self.assets_dir = Path(assets_dir)
        self.assets_dir.mkdir(parents=True, exist_ok=True)

        # JavaScript namespace voor clientside functies
        self.ns = Namespace(self.__class__.__name__)
        self.ns.add(
            """
                function(feature, context){
                    return {weight: 2, color: 'rgba(50,50,50,0.8)', fillOpacity: 0.9};
                }
                """,
            name="hoverStyle",
        )
        self.ns.add(
            """
                    function(e){
                      // Robuuste klikfunctie met debug logging
                      const src = e && (e.sourceTarget || e.target);
                      const feat = src && src.feature ? src.feature : null;
                      const props = feat && feat.properties ? feat.properties : {};

                      // Debug naar console voor controle
                      console.log("[DEBUG] Click event:", {
                        feature: feat,
                        props: props,
                        layerId: src && src._leaflet_id
                      });

                      return props || {};
                    }
                    """,
            name="clickHandler",
        )

        self.ns.dump(assets_folder=self.assets_dir.as_posix())

    @property
    def layout(self):
        """Returnt de Leaflet GeoJSON-laag voor peilgebieden."""
        return dl.GeoJSON(
            id="geojson-pgb",
            data=self.geojson_data,
            hideout=self.initial_stylemap,
            options={**self.initial_options, "pane": "overlayPane"},
            zoomToBoundsOnClick=False,
            hoverStyle=self.ns("hoverStyle"),
            eventHandlers={"click": self.ns("clickHandler")},
        )

    def register_callbacks(self, app):
        """Callbacks specifiek voor de GeoJSON-laag (niet gebruikt, handled in map_base)."""
        pass
