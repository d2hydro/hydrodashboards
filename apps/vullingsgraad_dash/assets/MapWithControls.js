window.MapWithControls = Object.assign({}, window.MapWithControls, {
    styleHandle: function(feature, context) {
        const stylemap = context.hideout || {};
        const loc = feature.properties.location_id;
        const sel = context.selected;

        // basisstijl
        let base = stylemap[loc] || feature.properties.style || {};
        base = {
            ...base,
            color: "rgba(15,23,42,0.35)",
            weight: 1,
            fillOpacity: base.fillOpacity ?? 0.7
        };

        // bij selectie: dikke zwarte rand
        if (sel && loc === sel) {
            base = {
                ...base,
                color: "rgba(0,0,0,1.0)", // zwarte rand
                weight: 4, // dikker
                fillOpacity: 0.85 // iets meer vulling
            };
        }

        return base;
    }

});