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

    // 1. Execution gets here almost instantly
    const fast = await resolveAfter1Seconds();
    console.log(fast); // 1. this runs almost immediately
    
    const slow = await resolveAfter2Seconds();
    console.log(slow); // 2. this runs after slow promise
}

function loading() {
    button.css_classes = ["download_spinner"];    
}

function stoploading() {
    button.css_classes = ["stoploading_download_spinner"];    
}

// Function to determine time zone
function getTimeZone() {
    setTimeout(loading, 1); 
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

// Function to format the CSV header rows with labels
function makeHeader(data, tags, isFirstOccurrence) {
    // Always add meetlocatie ident
    data.push(["meetlocatie ident", tags[0]]);

    if (isFirstOccurrence) {
        // Add full header for the first occurrence
        data.push(["meetlocatienaam", tags[1]]);
        data.push(["x", tags[2].split(",")[0]]); // Add x value
        data.push(["y", tags[2].split(",")[1]]); // Add y value
    }

    // Add common header data for both first and subsequent occurrences
    data.push(["parameter", tags[3]]);
    data.push(["qualifiers", tags[4]]);
    data.push(["eenheid", tags[5]]);
    data.push(["datum-tijd", "waarde"]); // Add the header for date-time and value
}

// Function to add events and data rows to CSV with formatted date-time
function addEvents(data, source) {
    source.data["datetime"].forEach((item, index) => {
        // Format the date-time in YYYY-MM-DD HH:MM:SS format, recognized by Excel
        const formattedDate = new Date(item).toISOString().replace("T", " ").slice(0, 19); // Format for Excel
        data.push([formattedDate, source.data["value"][index]]);
    });
}

// New function to create and download CSV files
function newFile(data, fileName) {
    // Create a Blob for the CSV content
    const blob = new Blob([data], { type: 'text/csv;charset=utf-8;' });

    // Create a Blob URL
    const exportUrl = URL.createObjectURL(blob);
    
    // Trigger download
    const link = document.createElement('a');
    link.href = exportUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    
    // Cleanup
    document.body.removeChild(link);
    URL.revokeObjectURL(exportUrl);
}

function resolveAfter2Seconds() {
    console.log("starting slow promise");
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve("slow");
            console.log("slow promise is done");

            const time_zone = getTimeZone();
            setTimeout(loading, 1);
            const event = new Date();
            const options = { year: 'numeric', month: 'numeric', day: 'numeric' };

            // Initialize disclaimer file content
            let disclaimerContent = "";
            let disclaimerArray = JSON.parse(disclaimer);
            disclaimerArray.forEach((line) => {
                disclaimerContent += line[0] + "\\n"; // Add each line to disclaimer
            });
            disclaimerContent += "\\n"; // Add an extra line break after the disclaimer
            disclaimerContent += "* De datumtijd-stappen zijn weergegeven in tijdzone: " + time_zone + "\\n\\n";

            // Save disclaimer.txt separately
            const disclaimerBlob = new Blob([disclaimerContent], { type: 'text/plain;charset=utf-8;' });
            const disclaimerLink = document.createElement("a");
            const disclaimerUrl = URL.createObjectURL(disclaimerBlob);
            disclaimerLink.setAttribute("href", disclaimerUrl);
            disclaimerLink.setAttribute("download", "disclaimer.txt");
            document.body.appendChild(disclaimerLink);
            disclaimerLink.click();
            document.body.removeChild(disclaimerLink);

            // Add headers and data from each visible renderer
            let meetlocatieData = {};
            let processedMeetlocaties = {}; // Track processed meetlocatie identifiers

            for (let i = 0; i < figure.children[0].children.length; i++) {
                var renderers = figure.children[0].children[i].renderers;
                for (let j = 0; j < renderers.length; j++) {
                    var renderer = renderers[j];
                    if (renderer.visible) {
                        var source = renderer.data_source;
                        var tags = source.tags;
                        var meetlocatieIdent = tags[1]; // Extract meetlocatie ident value
                        var data = [];

                        // Check if this meetlocatieIdent has already been processed
                        const isFirstOccurrence = !processedMeetlocaties[meetlocatieIdent];

                        // Add header with the specified labels, adjusted based on first occurrence
                        makeHeader(data, tags, isFirstOccurrence);

                        // Add data rows
                        addEvents(data, source);

                        // Mark this meetlocatieIdent as processed
                        processedMeetlocaties[meetlocatieIdent] = true;

                        // Store the data for this meetlocatie ident
                        if (!meetlocatieData[meetlocatieIdent]) {
                            meetlocatieData[meetlocatieIdent] = [];
                        }
                        meetlocatieData[meetlocatieIdent].push(data);
                    }
                }
            }

            // Create CSV files for each meetlocatie ident using newFile function
            for (const meetlocatieIdent in meetlocatieData) {
                let csvContent = "";

                // Add rows to the CSV content
                meetlocatieData[meetlocatieIdent].forEach((dataRows) => {
                    dataRows.forEach((row) => {
                        csvContent += row.join(",") + "\\n"; // Join each row with commas and newlines
                    });
                });

                // Debugging the csvContent creation
                console.log("CSV Content for meetlocatie ident: " + meetlocatieIdent, csvContent);

                // Use newFile to trigger the download
                newFile(csvContent, `${meetlocatieIdent}.csv`);
            }

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
