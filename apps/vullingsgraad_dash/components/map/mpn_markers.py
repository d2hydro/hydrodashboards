import dash_leaflet as dl
from dash_extensions.javascript import Namespace
import json
from pathlib import Path


class MPNMarkers:
    """GeoJSON-laag met dynamische meetpunt-markers."""

    def __init__(self, df_locs_mpn, assets_dir):
        self.df_locs_mpn = df_locs_mpn
        self.assets_dir = Path(assets_dir)
        self.assets_dir.mkdir(parents=True, exist_ok=True)

        # JavaScript namespace voor clientside functies
        self.ns = Namespace(self.__class__.__name__)
        self.ns.add(
            """
            function(feature, context){
              const ho = context.hideout || {};
              const allowed = ho.allowed || [];
              const attr = String(feature.properties.peilgebied_combi_attr);
              return Array.isArray(allowed) && allowed.includes(attr);
            }
            """,
            name="filterAllowed",
        )
        self.ns.add(
            """
            function(feature, context){
              const ho = context.hideout || {};
              const sel = ho.sel ?? null;
              const locId = feature.properties.location_id;
              let st = { radius: 5, fillColor: '#4cc9f0', color: '#1b4d5e',
                         weight: 1.5, opacity: 1, fillOpacity: 0.9 };
              if (sel && String(sel) === String(locId)) {
                st = {...st, radius: 7, fillColor: '#fde68a',
                      color: '#d97706', weight: 2};
              }
              return st;
            }
            """,
            name="styleSelected",
        )
        self.ns.add(
            """
            function(feature, latlng){
              const naam = feature.properties.naam || "meetpunt";
              const locId = feature.properties.location_id || "";
              const marker = L.circleMarker(latlng, { pane: 'veryTopPane' });
              marker.bindTooltip("<b>"+naam+"</b><br/>"+locId,
                                 {direction:'top', opacity:0.95});
              return marker;
            }
            """,
            name="ptlSimple",
        )
        self.ns.add(
            """
            function(e){
              const feat = e.layer.feature;
              const props = feat.properties;
              const ll = e.latlng;
              return {properties: props, lat: ll.lat, lng: ll.lng};
            }
            """,
            name="onClickReturnProps",
        )

        self.ns.dump(assets_folder=self.assets_dir.as_posix())

    @property
    def layout(self):
        """Bouwt GeoJSON met clientside style en filtering."""
        layout = dl.GeoJSON(
            id="marker-mpn",
            data=json.loads(self.df_locs_mpn.to_json()),
            filter=self.ns("filterAllowed"),
            hideout={"allowed": [], "sel": None, "tick": 0},
            options={
                "pane": "veryTopPane",
                "style": self.ns("styleSelected"),
                "pointToLayer": self.ns("ptlSimple"),
                "bubblingMouseEvents": True,
            },
            eventHandlers={"click": self.ns("onClickReturnProps")},
        )
        return layout
