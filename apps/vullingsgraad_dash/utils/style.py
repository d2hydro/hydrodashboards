from dash_extensions.javascript import assign
# Centralized style definitions for the Vullingsgraad dashboard

page_wrapper_style = {
    "display": "flex",
    "flexDirection": "row",
    "height": "100vh",
    "width": "100vw",
    "overflow": "hidden",
}

left_col_style = {
    "position": "relative",
    "flex": "1 1 50%",
    "minWidth": 0,
    "minHeight": 0,
    "overflow": "hidden",
    "height": "100vh",
}

right_col_style = {
    "display": "flex",
    "flexDirection": "column",
    "flex": "1 1 50%",
    "height": "100vh",
    "minWidth": 0,
    "minHeight": 0,
    "padding": "0px",
    "boxShadow": "0 2px 8px rgba(0,0,0,0.05)",
    "borderRadius": "5px",
    "backgroundColor": "rgba(255,255,255,0.0)",
    "overflow": "hidden",
}

controls_style = {
    "position": "absolute",
    "top": "10px",
    "left": "10px",
    "zIndex": 1002,
    "background": "rgba(220,240,255,1)",
    "borderRadius": "8px",
    "padding": "10px",
    "boxShadow": "0 2px 8px rgba(0,0,0,0.15)",
}

slider_container_style = {
    "position": "absolute",
    "bottom": "10px",
    "left": "10px",
    "background": "rgba(255,255,255,0.9)",
    "padding": "8px",
    "borderRadius": "6px",
    "zIndex": 1000,
    "display": "flex",
    "gap": "10px",
    "alignItems": "center",
    "boxShadow": "0 2px 8px rgba(0,0,0,0.15)",
}

slider_inner_box_style = {
    "position": "relative",
    "width": "400px",
    "height": "50px",
    "display": "inline-block",
}

mini_graph_style = {
    "height": "50px",
    "width": "350px",
    "position": "absolute",
    "top": 0,
    "left": "25px",
    "pointerEvents": "none",
}

playpause_button_style = {
    "width": "72px"
}

loader_style = {
    "position": "absolute",
    "top": 0,
    "left": 0,
    "right": 0,
    "bottom": 0,
    "backgroundColor": "rgba(255,255,255,0.6)",
    "backdropFilter": "blur(2px)",
    "zIndex": 2000,
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "center",
    "flexDirection": "column",
    "fontSize": "14px",
    "fontWeight": "500",
    "color": "#0f172a",
}

combined_graph_style = {
    "flex": "1 1 auto",
    "minHeight": 0,
    "minWidth": 0,
    "margin": "10px",
    "height": "96vh",
    "width": "48vw",
    "overflow": "hidden",
}

map_style = {
    "height": "100%",
    "width": "100%",
}

# Centralized STYLES dict for all inline Dash styles.

STYLES = {
    "page_wrapper": {
    "display": "flex",
    "flexDirection": "row",
    "height": "100vh",
    "width": "100vw",
    "overflow": "hidden",
},
    "left_col": {
    "position": "relative",
    "flex": "1 1 50%",
    "minWidth": 0,
    "minHeight": 0,
    "overflow": "hidden",
    "height": "100vh",
},
    "right_col": {
    "display": "flex",
    "flexDirection": "column",
    "flex": "1 1 50%",
    "height": "100vh",
    "minWidth": 0,
    "minHeight": 0,
    "padding": "0px",
    "boxShadow": "0 2px 8px rgba(0,0,0,0.05)",
    "borderRadius": "5px",
    "backgroundColor": "rgba(255,255,255,0.0)",
    "overflow": "hidden",
},
    "controls": {
    "position": "absolute",
    "top": "10px",
    "left": "10px",
    "zIndex": 1002,
    "background": "rgba(220,240,255,1)",
    "borderRadius": "8px",
    "padding": "10px",
    "boxShadow": "0 2px 8px rgba(0,0,0,0.15)",
},
    "slider_container": {
    "position": "absolute",
    "bottom": "10px",
    "left": "10px",
    "background": "rgba(255,255,255,0.9)",
    "padding": "8px",
    "borderRadius": "6px",
    "zIndex": 1000,
    "display": "flex",
    "gap": "10px",
    "alignItems": "center",
    "boxShadow": "0 2px 8px rgba(0,0,0,0.15)",
},
    "slider_inner_box": {
    "position": "relative",
    "width": "400px",
    "height": "50px",
    "display": "inline-block",
},
    "mini_graph": {
    "height": "50px",
    "width": "350px",
    "position": "absolute",
    "top": 0,
    "left": "25px",
    "pointerEvents": "none",
},
    "playpause_button": {
    "width": "72px"
},
    "loader": {
    "position": "absolute",
    "top": 0,
    "left": 0,
    "right": 0,
    "bottom": 0,
    "backgroundColor": "rgba(255,255,255,0.6)",
    "backdropFilter": "blur(2px)",
    "zIndex": 2000,
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "center",
    "flexDirection": "column",
    "fontSize": "14px",
    "fontWeight": "500",
    "color": "#0f172a",
},
    "combined_graph": {
    "flex": "1 1 auto",
    "minHeight": 0,
    "minWidth": 0,
    "margin": "10px",
    "height": "96vh",
    "width": "48vw",
    "overflow": "hidden",
},
    "map": {
    "height": "100%",
    "width": "100%",
},
}
# ========= Kaartvariabelen =========
kaartvariabelen = [
    {"label": "vullingsgraad [%]", "value": "vullingsgraad"},
    {"label": "vulling [mm]", "value": "vulling"},
]

vullingsgraad_classes = [
    (0, 25, "rgba(120,200,120,1.0)"),
    (25, 50, "rgba(255,255,100,1.0)"),
    (50, 75, "rgba(255,200,100,1.0)"),
    (75, 100, "rgba(255,100,100,1.0)"),
]

vulling_mm_classes = [
    (0, 10, "rgba(255,255,255,1.0)"),
    (10, 20, "rgba(180,211,231,1.0)"),
    (20, 30, "rgba(114,178,215,1.0)"),
    (30, 40, "rgba(62,145,196,1.0)"),
    (40, 60, "rgba(28,95,165,1.0)"),
]


# ========= Leaflet StyleHandle =========
style_handle = assign("""
function(feature, context){
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
      color: "rgba(0,0,0,1.0)",       // zwarte rand
      weight: 4,                      // dikker
      fillOpacity: 0.85               // iets meer vulling
    };
  }

  return base;
}
""")



