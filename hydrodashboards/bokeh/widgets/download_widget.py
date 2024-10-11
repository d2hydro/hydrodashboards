from bokeh.models.widgets import Button
from bokeh.models import CustomJS
import json


def read_disclaimer(disclaimer_file, encoding="utf-8"):
    if disclaimer_file is not None:
        disclaimer_json = json.dumps(
            [[i] for i in disclaimer_file.read_text(encoding=encoding).split("\n")]
        )
    else:
        disclaimer_json = json.dumps(
            [
                ["* This is an hydrodashboards export"],
                ["* Data comes as is without warranty of any kind"],
            ]
        )
    return disclaimer_json


download_xls = """
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
        const date = new Date(item);
        const options = { 
            timeZone: 'Europe/Amsterdam', 
            year: 'numeric', 
            month: '2-digit', 
            day: '2-digit', 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit',
            hour12: false // Use 24-hour format
        };
        const formattedDate = date.toLocaleString('nl-NL', options).replace(',', ''); // Format for Excel
        data.push([formattedDate, source.data["value"][index]]);
    });
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

download_csv = """
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

    const fast = await resolveAfter1Seconds();
    console.log(fast); // Fast promise resolved
    
    const slow = await resolveAfter2Seconds();
    console.log(slow); // Slow promise resolved
}

function loading() {
    button.css_classes = ["download_spinner"];    
}

function stoploading() {
    button.css_classes = ["stoploading_download_spinner"];    
}

function getTimeZone() {
    setTimeout(loading, 1); 
    const summer = new Date(1, 8, 2020).toString();
    const time_zone_summer = summer.replace(/.*[(](.*)[)].*/, '$1');
    const winter = new Date(1, 1, 2020).toString();
    const time_zone_winter = winter.replace(/.*[(](.*)[)].*/, '$1');
    if (time_zone_summer === time_zone_winter) {
        return String(time_zone_summer);
    } else {
        return String(([time_zone_summer, time_zone_winter])).replace(",", "/");
    }
}

function makeHeader(tags) {
    const header = [];
    header.push(["meetlocatie ident", tags[0]]);
    header.push(["meetlocatienaam", tags[1]]);
    header.push(["x", tags[2].split(",")[0]]); // x value
    header.push(["y", tags[2].split(",")[1]]); // y value
    header.push(["parameter", tags[3]]);
    header.push(["qualifiers", tags[4]]);
    header.push(["eenheid", tags[5]]);
    header.push(["datum-tijd", "waarde"]); // Header for date-time and value
    return header;
}

function addEvents(data, source) {
    source.data["datetime"].forEach((item, index) => {
        const date = new Date(item);
        const options = { 
            timeZone: 'Europe/Amsterdam', 
            year: 'numeric', 
            month: '2-digit', 
            day: '2-digit', 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit',
            hour12: false // Use 24-hour format
        };
        const formattedDate = date.toLocaleString('nl-NL', options).replace(',', ''); // Format for CSV
        data.push([formattedDate, source.data["value"][index]]);
    });
}

function newFile(data, fileName) {
    const blob = new Blob([data], { type: 'text/csv;charset=utf-8;' });
    return { blob, fileName }; // Return blob and fileName
}

async function zipFiles(files) {
    const zip = new JSZip(); // Assuming JSZip is available in your environment
    files.forEach(file => {
        zip.file(file.fileName, file.blob);
    });
    const content = await zip.generateAsync({ type: 'blob' });
    return content;
}

function resolveAfter2Seconds() {
    console.log("starting slow promise");
    return new Promise(async (resolve) => {
        setTimeout(async () => {
            resolve("slow");
            console.log("slow promise is done");

            const time_zone = getTimeZone();
            setTimeout(loading, 1);
            
            let disclaimerContent = "";
            let disclaimerArray = JSON.parse(disclaimer);
            disclaimerArray.forEach((line) => {
                disclaimerContent += line[0] + "\\n";
            });
            disclaimerContent += "\\n";
            disclaimerContent += "* De datumtijd-stappen zijn weergegeven in tijdzone: " + time_zone + "\\n\\n";

            const disclaimerFile = newFile(disclaimerContent, "disclaimer.txt"); // Create disclaimer file

            let meetlocatieData = {};
            let nonUniqueData = {};

            for (let i = 0; i < figure.children[0].children.length; i++) {
                var renderers = figure.children[0].children[i].renderers;
                for (let j = 0; j < renderers.length; j++) {
                    var renderer = renderers[j];
                    if (renderer.visible) {
                        var source = renderer.data_source;
                        var tags = source.tags;
                        var meetlocatieIdent = tags[0]; // Group by meetlocatie_ident
                        var meetlocatieNaam = tags[1];  // Keep meetlocatienaam unchanged
                        var parameter = tags[3].replace(/\//g, "_"); // Replace slashes in parameter
                        let csvData = [];

                        // Add header and data for this specific meetlocatie and parameter
                        const header = makeHeader(tags);
                        csvData = csvData.concat(header);

                        // Add events (data rows)
                        addEvents(csvData, source);
                        
                        // Convert array to CSV string
                        let csvContent = "";
                        csvData.forEach(row => {
                            csvContent += row.join(",") + "\\n";
                        });

                        // Initialize meetlocatie_ident if not exist
                        if (!meetlocatieData[meetlocatieIdent]) {
                            meetlocatieData[meetlocatieIdent] = {};
                        }

                        // Check for uniqueness of parameter
                        if (!meetlocatieData[meetlocatieIdent][parameter]) {
                            meetlocatieData[meetlocatieIdent][parameter] = { content: csvContent, meetlocatieNaam: meetlocatieNaam };
                        } else {
                            // If duplicate parameter, add to non-unique data
                            if (!nonUniqueData[meetlocatieIdent]) {
                                nonUniqueData[meetlocatieIdent] = {};
                            }
                            nonUniqueData[meetlocatieIdent][parameter] = { content: csvContent, meetlocatieNaam: meetlocatieNaam };
                        }
                    }
                }
            }

            const zipFilesList = [];
            
            // Create files for unique meetlocatie_ident and parameter
            for (const meetlocatieIdent in meetlocatieData) {
                for (const parameter in meetlocatieData[meetlocatieIdent]) {
                    const meetlocatieNaam = meetlocatieData[meetlocatieIdent][parameter].meetlocatieNaam;
                    const fileName = `${meetlocatieNaam}_${meetlocatieIdent}_${parameter}.csv`; // Include meetlocatienaam in filename
                    const file = newFile(meetlocatieData[meetlocatieIdent][parameter].content, fileName);
                    zipFilesList.push(file);
                }
            }

            // Create separate files for non-unique meetlocatie_ident/parameter
            for (const meetlocatieIdent in nonUniqueData) {
                for (const parameter in nonUniqueData[meetlocatieIdent]) {
                    const meetlocatieNaam = nonUniqueData[meetlocatieIdent][parameter].meetlocatieNaam;
                    const fileName = `${meetlocatieNaam}_${meetlocatieIdent}_${parameter}_nonunique.csv`; // Include meetlocatienaam in filename for non-unique files
                    const file = newFile(nonUniqueData[meetlocatieIdent][parameter].content, fileName);
                    zipFilesList.push(file);
                }
            }

            // Include the disclaimer file in the zip
            zipFilesList.push(disclaimerFile);

            // Zip all collected files
            const zipContent = await zipFiles(zipFilesList);
            const zipUrl = URL.createObjectURL(zipContent);
            const downloadLink = document.createElement('a');
            downloadLink.href = zipUrl;
            downloadLink.download = 'Timeseries_csv.zip';
            document.body.appendChild(downloadLink);
            downloadLink.click();
            document.body.removeChild(downloadLink);

            setTimeout(stoploading, 50);

        }, 500);
    });
}

sequentialStart();



"""

def make_ghost_button_xls(time_figure_layout, disclaimer_file=None, graph_count=3):
    button = Button(
        label="", button_type="success", disabled=True, visible=False, width=1, height=1
    )

    disclaimer_json = read_disclaimer(disclaimer_file)

    button.js_on_change(
        "disabled",
        CustomJS(
            args=dict(
                figure=time_figure_layout, disclaimer=disclaimer_json, button=button
            ),
            code=download_xls,
        ),
    )
    return button

def make_ghost_button_csv(time_figure_layout, disclaimer_file=None, graph_count=3):
    button = Button(
        label="", button_type="success", disabled=True, visible=False, width=1, height=1
    )

    disclaimer_json = read_disclaimer(disclaimer_file)

    button.js_on_change(
        "disabled",
        CustomJS(
            args=dict(
                figure=time_figure_layout, disclaimer=disclaimer_json, button=button
            ),
            code=download_csv,
        ),
    )
    return button


def make_button(on_click):
    button = Button(label="", button_type="success", disabled=True)
    button.on_click(on_click)
    return button
