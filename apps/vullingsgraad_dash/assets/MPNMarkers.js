window.MPNMarkers = Object.assign({}, window.MPNMarkers, {
    filterAllowed: function(feature, context) {
            const ho = context.hideout || {};
            const allowed = ho.allowed || [];
            const attr = String(feature.properties.peilgebied_combi_attr);
            return Array.isArray(allowed) && allowed.includes(attr);
        }

        ,
    styleSelected: function(feature, context) {
            const ho = context.hideout || {};
            const sel = ho.sel ?? null;
            const locId = feature.properties.location_id;
            let st = {
                radius: 5,
                fillColor: '#4cc9f0',
                color: '#1b4d5e',
                weight: 1.5,
                opacity: 1,
                fillOpacity: 0.9
            };
            if (sel && String(sel) === String(locId)) {
                st = {
                    ...st,
                    radius: 7,
                    fillColor: '#fde68a',
                    color: '#d97706',
                    weight: 2
                };
            }
            return st;
        }

        ,
    ptlSimple: function(feature, latlng) {
            const naam = feature.properties.naam || "meetpunt";
            const locId = feature.properties.location_id || "";
            const marker = L.circleMarker(latlng, {
                pane: 'veryTopPane'
            });
            marker.bindTooltip("<b>" + naam + "</b><br/>" + locId, {
                direction: 'top',
                opacity: 0.95
            });
            return marker;
        }

        ,
    onClickReturnProps: function(e) {
        const feat = e.layer.feature;
        const props = feat.properties;
        const ll = e.latlng;
        return {
            properties: props,
            lat: ll.lat,
            lng: ll.lng
        };
    }

});