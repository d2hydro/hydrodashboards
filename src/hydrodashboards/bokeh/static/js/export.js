export function saveToXlsx(data) {
    import('./xlsxAdaptor.js')
        .then(({ default: XLSX }) => createXlsx(XLSX, data));
}

function createXlsx(XLSX, data) {
    // create new workbook 
    var wb = XLSX.utils.book_new();

    // converts an array of arrays into a worksheet.
    var ws = XLSX.utils.aoa_to_sheet(data);

    // add worksheet to workbook under name Sheet1
    XLSX.utils.book_append_sheet(wb, ws, "Sheet1");

    // save workbook to file export.xlsx
    XLSX.writeFile(wb, "export.xlsx");
}