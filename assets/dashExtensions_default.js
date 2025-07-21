window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, context) {
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

    }
});