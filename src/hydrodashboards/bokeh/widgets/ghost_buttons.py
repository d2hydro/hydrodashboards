from bokeh.models.widgets import Button
from bokeh.models import CustomJS

scale_figs_js = """
console.log(graph_count)
console.log(button.disabled)
if (button.disabled) {
    var fig_len = figure.children[0].children.length;
    console.log(fig_len)
    const vh = Math.round(parent.innerHeight * 0.6);

    if (fig_len < graph_count){
            console.log("fig_len<");
            figure.children[0].height = Math.round(fig_len * vh / fig_len);
            for (let i = 0; i < figure.children[0].children.length; i++) {
                   figure.children[0].children[i].height = Math.round(vh / fig_len); 
                   }
                   }
    else  {
            console.log("fig_len>");
            figure.children[0].height = Math.round(fig_len * vh / graph_count); 
            for (let i = 0; i < figure.children[0].children.length; i++) {
                   figure.children[0].children[i].height = Math.round(vh / graph_count); 
                   }
                   }
    }

   
"""


def make_button(time_figure_layout, js_callback=scale_figs_js, graph_count=3):
    button = Button(label="", button_type="success", disabled=True)
    button.js_on_change(
        "disabled",
        CustomJS(
            args=dict(
                button=button, figure=time_figure_layout, graph_count=graph_count
            ),
            code=scale_figs_js,
        ),
    )
    return button
