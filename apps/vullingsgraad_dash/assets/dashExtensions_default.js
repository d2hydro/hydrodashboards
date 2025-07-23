window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, context) {
                const stylemap = context.hideout || {};
                const loc = feature.properties.location_id;
                const sel = context.selected;
                let base = stylemap[loc] || feature.properties.style;
                if (sel && loc === sel) {
                    base = {
                        ...base,
                        weight: 3,
                        color: 'yellow'
                    };
                }
                return base;
            }

            ,
        function1: function(e) {
            return e?.target?.feature?.properties || {};
        }
    }
});