import dash_leaflet as dl
from dash_extensions.javascript import assign


class PeilgebiedenLayer:
    """Component die de GeoJSON-laag met peilgebieden bouwt."""

    def __init__(self, geojson_data, style_handle, initial_stylemap, initial_options):
        self.geojson_data = geojson_data
        self.style_handle = style_handle
        self.initial_stylemap = initial_stylemap
        self.initial_options = initial_options

    @property
    def layout(self):
        """Returnt de Leaflet GeoJSON-laag voor peilgebieden."""
        return dl.GeoJSON(
            id="geojson-pgb",
            data=self.geojson_data,
            hideout=self.initial_stylemap,
            options={**self.initial_options, "pane": "overlayPane"},
            zoomToBoundsOnClick=False,
            hoverStyle=assign(
                """
                function(feature, context){
                    return {weight: 2, color: 'rgba(50,50,50,0.8)', fillOpacity: 0.9};
                }
                """
            ),
            eventHandlers={
                "click": assign(
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
                    """
                )
            },
        )

    def register_callbacks(self, app):
        """Callbacks specifiek voor de GeoJSON-laag (niet gebruikt, handled in map_base)."""
        pass
