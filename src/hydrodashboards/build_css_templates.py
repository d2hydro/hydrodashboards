map_opt = """
.map_opt
{{
  display:block;
  position: fixed;
  background: white;
  width: {map_options_width}px;
  top: calc(100% - {map_options_height}px);
  left: calc(100% - {map_options_left}px);
  background-color: white;
  padding: 2px;
  border: 1px solid #F1F2F3;
  border-radius:4px;
}}
"""

filter_bar = """
#sidebar .sidebar-bokeh1 {{
    width: 100%;
    padding-right: 14px;
    padding-left:14px;
    height: {filter_height}px;
    padding-top:0px;
    margin-top:5px;
}}
"""
