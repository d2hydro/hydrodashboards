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



setTimeout(loading,1); 
console.log(button.css_classes); 

    
function loading() {
    button.css_classes = ["download_spinner"];    
}
function stoploading() {
    button.css_classes = ["stoploading_download_spinner"];    
}

// the functions we use to get things done
function getTimeZone() {
    setTimeout(loading,1); 
    const summer = new Date(1, 8, 2020).toString();
    const time_zone_summer = summer.replace(/.*[(](.*)[)].*/, '$1');
    const winter = new Date(1, 1, 2020).toString();
    const time_zone_winter = winter.replace(/.*[(](.*)[)].*/, '$1');
    if (time_zone_summer == time_zone_winter) {
        return String(time_zone_summer);
    } else {
        return String(([time_zone_summer, time_zone_winter])).replace(",", "/");
    }
        setTimeout(loading,100);
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

function write_excel(){
    XLSX.writeFile(wb, filename, {
    cellDates: true
    
})
setTimeout(stoploading,1000); 
}

// the constants we declare                                           
const time_zone = getTimeZone();
setTimeout(loading,1);
const event = new Date();
const options = {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric'
};

// new workbook
setTimeout(loading,1);
var filename = "TimeSeries_" + event.toLocaleDateString(options) + "T" + event.toLocaleTimeString() + ".xlsx";
setTimeout(loading,100);
var wb = XLSX.utils.book_new();
var col_num = 0

// add disclaimer
setTimeout(loading,1);
disclaimer = JSON.parse(disclaimer)
disclaimer.push(["* De datumtijd-stappen zijn weergegeven in tijdzone: " + time_zone])
var ws_disclaimer = XLSX.utils.aoa_to_sheet(disclaimer);

// add data
setTimeout(loading,1);
var ws_data = XLSX.utils.aoa_to_sheet([], {
    dateNF: 'yyyy-mm-dd hh:mm:ss'
});

// this we need to make an iter function
for (let i = 0; i < figure.children[0].children.length; i++) { //iterate figures
    setTimeout(loading,1); 
    var renderers = figure.children[0].children[i].renderers
    for (let j = 0; j < renderers.length; j++) { //iterate renderers
        var renderer = renderers[j]
        if (renderer.visible) {
            setTimeout(loading,1);
            var source = renderer.data_source
            var tags = source.tags
            var data = ['meetlocatie ident', 'meetlocatienaam', 'x,y', 'parameter', 'qualifiers', 'eenheid']

            // add header
            makeHeader(data, tags)
            {setTimeout(loading,1)}
            data.push(["datum-tijd", "waarde"])

            // add data
            addEvents(data, source)
            setTimeout(loading,1);
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
setTimeout(loading,10);
ws_data['!cols'] = Array(col_num).fill({
    width: 20
})
setTimeout(loading,1);
XLSX.utils.book_append_sheet(wb, ws_disclaimer, "disclaimer")
setTimeout(loading,1);
XLSX.utils.book_append_sheet(wb, ws_data, "gegevens")
setTimeout(loading,1);

// save workbook to file export.xlsx
write_excel()


"""


def make_button(time_figure_layout):
    button = Button(label="Download", button_type="success", disabled=True)
    
    button.js_event_callbacks['button_click'] = [
        CustomJS(args=dict(figure=time_figure_layout,
                           disclaimer=disclaimer_json,
                           button=button),
                           code=download_js)
                         
                         
        ]

    return button
