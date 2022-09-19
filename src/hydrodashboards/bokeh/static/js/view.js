export function render(data) {
    const table = document.querySelector('table');

    const html = data
        .map(row => row.reduce((html, val) => html + `<td>${val}</td>`, ''))
        .map(row => `<tr>${row}</tr>`)
        .join('');

    table.innerHTML = html;
}