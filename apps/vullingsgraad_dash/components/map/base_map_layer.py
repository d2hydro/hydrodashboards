import dash_leaflet as dl

class BaseMapLayer:
    """Beheert de achtergrondkaart (OpenStreetMap, Topo, etc.)."""

    def __init__(self, basemap="osm", opacity=0.6):
        self.basemap = basemap
        self.opacity = opacity

    @property
    def layout(self):
        """Returnt de juiste TileLayer met instellingen."""
        if self.basemap == "osm":
            url = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution = '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
        elif self.basemap == "topo":
            url = "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
            attribution = '&copy; <a href="https://opentopomap.org">OpenTopoMap</a>'
        else:
            url = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution = ""

        return dl.TileLayer(url=url, opacity=self.opacity, attribution=attribution)

