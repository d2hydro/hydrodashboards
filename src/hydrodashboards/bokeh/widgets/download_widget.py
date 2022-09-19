from bokeh.models.widgets import Button
from bokeh.models import CustomJS


donwload_js = """
function table_to_csv(source) {

    const columns = Object.keys(source.data)
    const nrows = source.get_length()
    const lines = [columns.join(',')]

    for (let i = 0; i < nrows; i++) {
        let row = [];
        for (let j = 0; j < columns.length; j++) {
            const column = columns[j]

            if (column=='datetime'){
            var dtobj = new Date(source.data[column][i])
            row.push(dtobj.toLocaleString('nl-NL'))
            }
            else if (column=='index'){
            row.push(source.data[column][i].toString())
            }

            else if (column=='value'){
            row.push(source.data[column][i].toString())
            }
        }
        lines.push(row.join(','))

    }
    return lines.join('\\n').concat('\\n')
}

function csv_name(source) {
    const file_name = source.name.concat(".csv").replace(/ /g,"_")
    console.log(file_name)
    return file_name
}

const filename = csv_name(source)
const filetext = table_to_csv(source)
const blob = new Blob([filetext], { type: 'text/csv;charset=utf-8;' })

//addresses IE
if (navigator.msSaveBlob) {
    navigator.msSaveBlob(blob, filename)
} else {
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    link.target = '_blank'
    link.style.visibility = 'hidden'
    link.dispatchEvent(new MouseEvent('click'))
}

"""


def make_button(source, search_series=True):
    button = Button(label="Download", button_type="success", disabled=True)
    if search_series:
        button.js_event_callbacks['button_click'] = [
            CustomJS(args=dict(source=source), code=donwload_js)
            ]
    return button
