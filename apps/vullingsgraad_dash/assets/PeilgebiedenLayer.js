window.PeilgebiedenLayer = Object.assign({}, window.PeilgebiedenLayer, {
    hoverStyle: function(feature, context) {
            return {
                weight: 2,
                color: 'rgba(50,50,50,0.8)',
                fillOpacity: 0.9
            };
        }

        ,
    clickHandler: function(e) {
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

});