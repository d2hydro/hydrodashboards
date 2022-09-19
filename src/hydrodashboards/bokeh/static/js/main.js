// main.js
import { loadData } from './data.js';
import { saveToXlsx } from './export.js'

loadData().then(data => {
    document.querySelector('button').onclick = () => saveToXlsx(data);
});