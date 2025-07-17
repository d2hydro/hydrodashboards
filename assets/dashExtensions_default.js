window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, ctx) {
            return {
                color: 'steelblue',
                weight: 1,
                fillOpacity: 0.1
            };
        },
        function1: function(feature, ctx) {
            const sel = ctx.hideout.pumps || [];
            const z = ctx.hideout.zoom || 10;
            const scale = z < 9 ? 0.4 : z < 11 ? 0.7 : 1.0;
            const selected = sel.includes(feature.properties.node_id);
            const radius = selected ? 6 * scale : 4 * scale;
            const color = selected ? 'red' : 'green';
            return {
                color: color,
                fillColor: color,
                radius: radius
            };
        },
        function2: function(feature, ctx) {
                const sel = ctx.hideout.basin_nodes || [];
                const z = ctx.hideout.zoom || 10;
                const scale = z < 9 ? 0.6 : z < 11 ? 0.9 : 1.2;
                const selected = sel.includes(feature.properties.node_id);
                const radius = selected ? 8 * scale : 6 * scale;
                const color = selected ? 'yellow' : 'blue';
                return {
                    color: color,
                    fillColor: color,
                    radius: radius
                };
            }

            ,
        function3: function(feature, ctx) {
            const selected = ctx.hideout.selected_link === feature.properties.link_id;
            const cat = feature.properties.meta_categorie || "";
            const color = selected ? "yellow" : (cat.toLowerCase() === "hoofdwater" ? "#003366" : "#66ccff");
            const weight = selected ? 5 : (cat.toLowerCase() === "hoofdwater" ? 4 : 2.5);
            return {
                color: color,
                weight: weight
            };
        },
        function4: function(feature, ctx) {
            return {
                color: 'transparent',
                weight: 10,
                opacity: 0,
                fillOpacity: 0
            };
        },
        function5: function(feature, latlng) {
            return L.circleMarker(latlng, {
                fillOpacity: 0.8
            });
        }
    }
});