from bokeh.models.widgets import Button
from bokeh.models import CustomJS
import json

disclaimer_json = json.dumps(
    [
        ["* Aan de gegevens in dit Excelbestand mogen geen rechten worden ontleend"],
        [
            "* Met debietformules worden berekeningen uitgevoerd die de werkelijkheid versimpelen; dit gebeurt nooit helemaal correct; er is dus altijd een zekere foutmarge en onzekerheid die in acht moet worden genomen bij het gebruik van deze data"
        ],
        [
            "* De data is tot stand gekomen uit bewerkingen met grotendeels handmatig gevalideerde data; gaten in de tijdreeksen die hierdoor zijn ontstaan zijn niet opgevuld en beschikbaar"
        ],
        ["* De x,y coordinaten zijn geprojecterd in: Amersfoort / RD New (epsg:28992)"],
    ]
)

download_js = """
function resolveAfter1Seconds() {
  console.log("starting fast promise");
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve("fast");
      console.log("fast promise is done");
      button.css_classes = ["download_spinner"];    
    }, 50);
  });
}  

async function sequentialStart() {
console.log("==SEQUENTIAL START==");

// 1. Execution gets here almost instantly
const fast = await resolveAfter1Seconds();
console.log(fast); // 1. this runs  seconds
  
const slow = await resolveAfter2Seconds();
console.log(slow); // 2. this runs 2 seconds after 1.
}
 
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

function write_excel(wb,filename){
    XLSX.writeFile(wb, filename, {
    cellDates: true,
    compression: true
    
})
setTimeout(stoploading,50); 
}

function resolveAfter2Seconds(){ 
  console.log("starting slow promise");
  return new Promise((resolve) => {
   setTimeout(() => {
   resolve("slow");
   console.log("slow promise is done");
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
ws_data['!cols'] = Array(col_num).fill({
    width: 20
})

XLSX.utils.book_append_sheet(wb, ws_disclaimer, "disclaimer")
XLSX.utils.book_append_sheet(wb, ws_data, "gegevens")

// save workbook to file export.xlsx
write_excel(wb,filename)
  }, 500);
  });
}

sequentialStart(); //
"""

scale_figs_js = """
console.log(button.disabled)
if (!button.disabled) {
    var fig_len = figure.children[0].children.length
    var h = document.getElementById("grafiek_upper")
    var vh = Math.round(window.innerHeight * 0.6)
    console.log(vh)
    console.log(h)
    if (fig_len == 1) {
            figure.children[0].height = vh;
            figure.children[0].children[0].height = vh;
            }
    else if (fig_len > 1) {
        figure.children[0].height = Math.round(fig_len * vh / 2);
        for (let i = 0; i < figure.children[0].children.length; i++) {
               figure.children[0].children[i].height = Math.round(vh / 2); 
               }
               }
        }
"""


def make_button(time_figure_layout):
    button = Button(label="", button_type="success", disabled=True)

    button.js_on_click(CustomJS(
        args=dict(
            figure=time_figure_layout, disclaimer=disclaimer_json, button=button
        ),
        code=download_js,
    ))

    button.js_on_change("disabled", CustomJS(args=dict(
        button=button,
        figure=time_figure_layout),
        code=scale_figs_js))

    return button
