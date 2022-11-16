map_opt = """
.map_opt
{{
  display:block!important;
  position: fixed!important;
  background: white!important;
  width: {map_options_width}px!important;
  top: calc(100% - {map_options_height}px)!important;
  left: calc(100% - {map_options_left}px)!important;
  background-color: white!important;
  padding: 2px!important;
  border: 1px solid #F1F2F3!important;
  border-radius:4px!important;
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
