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

bk_checkbox = """
.bk.filter_checkboxgroup_{ident}
{{
  color: white; overflow-y: auto;background:#495568;
  padding: 6px;min-height:{height}px;max-height:{height}px;
}}"""


def checkbox_filters(filter_heights):
    return "".join(
        [
            bk_checkbox.format(ident=idx + 1, height=i)
            for idx, i in enumerate(filter_heights)
        ]
    )
