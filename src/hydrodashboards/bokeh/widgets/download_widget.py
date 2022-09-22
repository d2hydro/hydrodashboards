from bokeh.models.widgets import Button
from bokeh.models import CustomJS


donwload_search_js = """
function table_to_csv(source) {

    const columns = Object.keys(source.data)
    const nrows = source.get_length()
    const lines = [columns.join(',')]

    for (let i = 0; i < nrows; i++) {
        let row = [];
        for (let j = 0; j < columns.length; j++) {
            const column = columns[j]

            if (column == 'datetime') {
                var dtobj = new Date(source.data[column][i])
                row.push(dtobj.toLocaleString('nl-NL'))
            } else if (column == 'index') {
                row.push(source.data[column][i].toString())
            } else if (column == 'value') {
                row.push(source.data[column][i].toString())
            }
        }
        lines.push(row.join(','))

    }
    return lines.join('\\n').concat('\\n')
}

function csv_name(source) {
    const file_name = source.name.concat(".csv").replace(/ /g, "_")
    console.log(file_name)
    return file_name
}

const filename = csv_name(source)
const filetext = table_to_csv(source)
const blob = new Blob([filetext], {
    type: 'text/csv;charset=utf-8;'
})

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

download_js = """

var data = [
    ["MPN_IDENT", "","MPN_IDENT", ""],
    ["OBJ_LONGNAME","","OBJ_LONGNAME",""],
    ["X_COORD, Y_COORD","","X_COORD, Y_COORD",""], 
    ["WAM_ParameterID","","WAM_ParameterID",""],
    ["WAM_EenheidCode","","WAM_EenheidCode",""],
    ["Qualifier","","Qualifier",""],
    ["datum-tijd", "waarde","datum-tijd", "waarde"],
    
   
  
    [new Date(Date.UTC(2021, 8, 1, 1, 0, 0)), 0.15,new Date(Date.UTC(2021, 8, 1, 1, 0, 0)), 0.30],
    [new Date(Date.UTC(2021, 8, 1, 1, 15, 0)), 0.20,new Date(Date.UTC(2021, 8, 1, 1, 0, 0)), 0.35],
    [new Date(Date.UTC(2021, 8, 1, 1, 30, 0)), 0.18,new Date(Date.UTC(2021, 8, 1, 1, 0, 0)), 0.40],
    [new Date(Date.UTC(2021, 8, 1, 1, 45, 0)), 0.25,new Date(Date.UTC(2022, 9, 21, 11, 17, 0)), 0.45],
    [new Date(Date.UTC(2021, 8, 1, 2, 0, 0)), 0.3],
    [new Date(Date.UTC(2021, 8, 1, 2, 15, 0)), 0.2],
    [new Date(Date.UTC(2021, 8, 1, 2, 30, 0)), 0.15]
    
  
];



var filename ="test.xlsx";
    var wb = XLSX.utils.book_new();

    // converts an array of arrays into a worksheet.
    var ws = XLSX.utils.aoa_to_sheet(data,{ dateNF: 'yyyy-mm-dd hh:mm:ss'});

    // add worksheet to workbook under name Sheet1
    XLSX.utils.book_append_sheet(wb, ws, "Sheet1");
    
    // save workbook to file export.xlsx
     XLSX.writeFile(wb, filename,{cellDates: true});

 function getTimeZone(){
    const zomer = new Date(1,8,2020).toString();
    const timeZone_zomer = zomer.replace(/.*[(](.*)[)].*/,'$1');//extracts the content between parenthesis
    const winter = new Date(1,1,2020).toString();
    const timeZone_winter = winter.replace(/.*[(](.*)[)].*/,'$1');//extracts the content between parenthesis
    return [timeZone_zomer,timeZone_winter];
}
console.log(getTimeZone());

"""


def make_button(source, search_series=True):
    button = Button(label="Download", button_type="success", disabled=True)
    if search_series:
        callback = donwload_search_js
    else:
        callback = download_js
    button.js_event_callbacks['button_click'] = [
        CustomJS(args=dict(source=source), code=callback)
        ]
        
      
    print(button)
    return button
