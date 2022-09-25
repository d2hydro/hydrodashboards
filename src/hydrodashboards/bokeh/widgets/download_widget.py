from bokeh.models.widgets import Button
from bokeh.models import CustomJS
import json

disclaimer_json = json.dumps([
    ["* Aan de gegevens in dit Excelbestand mogen geen rechten worden ontleend"],
    ["* Met debietformules worden berekeningen uitgevoerd die de werkelijkheid versimpelen; dit gebeurt nooit helemaal correct; er is dus altijd een zekere foutmarge en onzekerheid die in acht moet worden genomen bij het gebruik van deze data"],
    ["* De data is tot stand gekomen uit bewerkingen met grotendeels handmatig gevalideerde data; gaten in de tijdreeksen die hierdoor zijn ontstaan zijn niet opgevuld en beschikbaar"],  
    ["* De x,y coordinaten zijn geprojecterd in: Amersfoort / RD New (epsg:28992)"]
    ])

download_js = """
// the functions we use to get things done
function getTimeZone() {
    const summer = new Date(1, 8, 2020).toString();
    const time_zone_summer = summer.replace(/.*[(](.*)[)].*/, '$1');
    const winter = new Date(1, 1, 2020).toString();
    const time_zone_winter = winter.replace(/.*[(](.*)[)].*/, '$1');
    if (time_zone_summer == time_zone_winter) {
        return String(time_zone_summer);
    } else {
        return String(([time_zone_summer, time_zone_winter])).replace(",", "/");
    }
}

function makeHeader(data, tags) {
    data.forEach((item, index) => {
        data[index] = [item, tags[index]]
    })
}

function addEvents(data, source) {
    source.data["datetime"].forEach((item, index) => {
        data.push([new Date(item), source.data["value"][index]])
    })
}

// the constants we declare                                           
const time_zone = getTimeZone();
const event = new Date();
const options = {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric'
};

// new workbook
var filename = "TimeSeries_" + event.toLocaleDateString(options) + "T" + event.toLocaleTimeString() + ".xlsx";
var wb = XLSX.utils.book_new();
var col_num = 0

// add disclaimer
disclaimer = JSON.parse(disclaimer)
disclaimer.push(["* De datumtijd-stappen zijn weergegeven in tijdzone: " + time_zone])
var ws_disclaimer = XLSX.utils.aoa_to_sheet(disclaimer);

// add data
var ws_data = XLSX.utils.aoa_to_sheet([], {
    dateNF: 'yyyy-mm-dd hh:mm:ss'
});

// this we need to make an iter function
for (let i = 0; i < figure.children[0].children.length; i++) { //iterate figures
    var renderers = figure.children[0].children[i].renderers
    for (let j = 0; j < renderers.length; j++) { //iterate renderers
        var renderer = renderers[j]
        if (renderer.visible) {
            var source = renderer.data_source
            var tags = source.tags
            var data = ['meetlocatie ident', 'meetlocatienaam', 'x,y', 'parameter', 'qualifiers', 'eenheid']

            // add header
            makeHeader(data, tags)
            data.push(["datum-tijd", "waarde"])

            // add data
            addEvents(data, source)
            XLSX.utils.sheet_add_json(ws_data, data, {
                skipHeader: true,
                origin: {
                    r: 0,
                    c: col_num
                },
                dateNF: 'yyyy-mm-dd hh:mm:ss'
            })
            col_num = col_num + 2
        }
    }
}


//append worksheeds to workbook
ws_data['!cols'] = Array(col_num).fill({
    width: 20
})
XLSX.utils.book_append_sheet(wb, ws_disclaimer, "disclaimer")
XLSX.utils.book_append_sheet(wb, ws_data, "gegevens")

// save workbook to file export.xlsx
XLSX.writeFile(wb, filename, {
    cellDates: true
});
"""


def make_button(time_figure_layout):
    button = Button(label="Download", button_type="success", disabled=True)
    button.js_event_callbacks['button_click'] = [
        CustomJS(args=dict(figure=time_figure_layout,
                           disclaimer=disclaimer_json),
                 code=download_js)
        ]

    return button
