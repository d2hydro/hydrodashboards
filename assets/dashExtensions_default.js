window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, ctx) {
                const precip = ctx.hideout.precip || {};
                const value = precip[feature.properties.node_id] || 0;
                let color = 'white';
                if (value > 10) color = '#08306b';
                else if (value > 5) color = '#2171b5';
                else if (value > 1) color = '#6baed6';
                else if (value > 0) color = '#c6dbef';
                return {
                    fillColor: color,
                    color: 'grey',
                    weight: 1,
                    fillOpacity: 0.8
                };
            }

            ,
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
            const weight = selected ? 5 : (cat.toLowerCase() === "hoofdwater" ? 4 : 4);
            return {
                color: color,
                weight: weight
            };
        },
        function4: function(feature, latlng) {
            return L.circleMarker(latlng, {
                fillOpacity: 0.8
            });
        }
    }
});