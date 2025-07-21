window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature) {
            return feature.properties.style;
        },
        function1: function(feature, context) {
                const stylemap = context.hideout || {};
                const loc = feature.properties.location_id;
                // gebruik uit stylemap, anders default uit feature.properties.style
                return stylemap[loc] || feature.properties.style;
            }

            ,
        function2: function(feature, context) {
                const stylemap = context.hideout || {};
                const loc = feature.properties.location_id;
                return stylemap[loc] || feature.properties.style;
            }

            ,
        function3: function(feature, context) {
                const colors = context.hideout.colors || {};
                const selected = context.hideout.selected;
                const loc = feature.properties.location_id;
                const base = colors[loc] || feature.properties.style;
                if (loc === selected) {
                    return {
                        ...base,
                        weight: 3,
                        color: 'blue'
                    };
                }
                return base;
            }

            ,
        function4: function(feature, context) {
                const colors = context.hideout.colors || {};
                const selected = context.hideout.selected;
                const loc = feature.properties.location_id;
                const base = feature.properties.style;
                const style = colors[loc] || base;
                if (selected && selected === loc) {
                    style.weight = 3;
                    style.color = 'blue';
                }
                return style;
            }

            ,
        function5: function(feature, context) {
            const cols = context.hideout.colors || {};
            const sel = context.hideout.selected;
            const loc = feature.properties.location_id;
            const base = feature.properties.style;
            const s = cols[loc] || base;
            if (sel && sel === loc) {
                s.weight = 3;
                s.color = 'blue';
            }
            return s;
        }

    }
});