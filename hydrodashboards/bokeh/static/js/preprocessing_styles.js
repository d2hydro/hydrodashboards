
        // Function to traverse the DOM and collect specified elements with their parent hierarchy
        function traverseDOM(node, hierarchy, elementList, targetTags) {
            if (!node) return;

            // Clone the current hierarchy to avoid mutations in recursive calls
            let currentHierarchy = [...hierarchy];

            if (node.nodeType === Node.ELEMENT_NODE) {
                const element = node;
                let tagWithDescriptor = element.tagName.toLowerCase();

                // Include descriptor (tag with classes and ID)
                if (element.hasAttribute('data-root-id')) {
                    const dataRootId = element.getAttribute('data-root-id');
                    tagWithDescriptor += `[data-root-id='${dataRootId}']`;
                } else if (element.id) {
                    tagWithDescriptor += `#${element.id}`;
                }

                if (element.classList.length > 0) {
                    tagWithDescriptor += `.${[...element.classList].join('.')}`;
                }

                currentHierarchy.push(tagWithDescriptor);

                // If the current element is one of the target tags, record its hierarchy and attributes
                if (targetTags.has(element.tagName.toLowerCase())) {
                    elementList.push({
                        tag: tagWithDescriptor,
                        hierarchy: [...currentHierarchy],
                        style: [] // Empty style array as per your requirement
                    });
                }

                // If the element has a shadow root, indicate it in the hierarchy and traverse it
                if (element.shadowRoot) {
                    currentHierarchy.push('shadow-root');
                    traverseDOM(element.shadowRoot, currentHierarchy, elementList, targetTags);
                    currentHierarchy.pop(); // Remove 'shadow-root' after traversing shadow DOM
                }
            }

            // Traverse child nodes
            node.childNodes.forEach(child => traverseDOM(child, currentHierarchy, elementList, targetTags));
        }

        // Function to generate a JSON document from the collected element data and trigger download
        function exportElementHierarchy(elementList) {
            const jsonContent = JSON.stringify(elementList, null, 4); // Pretty-print with 4-space indentation
            const blob = new Blob([jsonContent], { type: 'application/json' });
            const url = URL.createObjectURL(blob);

            const a = document.createElement('a');
            a.href = url;
            a.download = 'data.json';
            document.body.appendChild(a);
            a.click();

            // Clean up
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }

        // Function to extract HTML content, including shadow DOM
        function extractHTMLWithShadow(node, indentLevel) {
            if (!node) return '';

            const indent = '    '.repeat(indentLevel);

            // Skip <style> elements
            if (node.nodeType === 1 && node.tagName.toLowerCase() === 'style') {
                return '';
            }

            // Handle text nodes
            if (node.nodeType === 3) {
                return node.textContent.trim() ? `${indent}${node.textContent.trim()}\n` : '';
            }

            // Handle element nodes
            if (node.nodeType === 1) {
                let tagName = node.tagName.toLowerCase();
                let outerHTML = `${indent}<${tagName}`;

                // Add attributes if any
                for (let attr of node.attributes) {
                    outerHTML += ` ${attr.name}="${attr.value}"`;
                }

                // If the node has a shadowRoot, extract its content
                if (node.shadowRoot) {
                    outerHTML += '>\n';
                    outerHTML += `${indent}<!-- #shadow-root (open) -->\n`;
                    node.shadowRoot.childNodes.forEach(child => {
                        outerHTML += extractHTMLWithShadow(child, indentLevel + 1);
                    });
                    outerHTML += `${indent}</${tagName}>\n`;
                    return outerHTML;
                }

                outerHTML += '>\n';

                // Recursively add child nodes (regular DOM nodes)
                node.childNodes.forEach(child => {
                    outerHTML += extractHTMLWithShadow(child, indentLevel + 1);
                });

                outerHTML += `${indent}</${tagName}>\n`;

                return outerHTML;
            }

            // Handle comment nodes
            if (node.nodeType === 8) {
                return `${indent}<!-- ${node.nodeValue} -->\n`;
            }

            return '';
        }

        // Function to create and download the HTML file
        function createAndDownloadFile(content, filename, type) {
            const blob = new Blob([content], { type });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(a.href);
        }

        // Main function to initiate traversal and export
        function collectAndExportElements() {
            const elementList = [];
            const targetTags = new Set(['div', 'button', 'input']); // Specify the tags to collect
            traverseDOM(document.body, [], elementList, targetTags); // Collect element data
            exportElementHierarchy(elementList); // Export as JSON

            const originalBodyHTML = extractHTMLWithShadow(document.body, 0); // Extract HTML
            createAndDownloadFile(originalBodyHTML, 'body-with-shadow-roots.html', 'text/html'); // Create and download HTML file
        }

        // Function to handle CSS file loading
        document.getElementById('loadButton').addEventListener('click', () => {
            const fileInput = document.getElementById('cssFileInput');
            fileInput.click(); // Trigger the hidden file input when the button is clicked

            fileInput.onchange = () => {
                const file = fileInput.files[0];
                if (!file) {
                    alert('Please select a CSS file.');
                    return;
                }

                const reader = new FileReader();
                reader.onload = function(event) {
                    const cssText = event.target.result; // Get the CSS text
                    const updatedCss = updateCssStyles(cssText); // Update CSS styles
                    displayLoadingOverlay(false); // Hide loading overlay
                    exportTXT(updatedCss); // Directly export the file after loading
                };

                displayLoadingOverlay(true); // Show loading overlay
                reader.readAsText(file); // Read the file as text
            };
        });

        // Function to update CSS styles in the desired format
        function updateCssStyles(cssText) {
            return cssText.replace(/(\{)([\s\S]*?)(\})/g, (match, p1, p2, p3) => {
                const stylesArray = p2.trim().split(';').map(style => style.trim()).filter(Boolean);
                const jsonStyles = stylesArray.map(style => `"${style}"`).join(',\n  '); // Format styles
                return `${p1} [\n  ${jsonStyles}\n] ${p3}`; // Return modified styles inside braces
            });
        }

        // Function to display the loading overlay
        function displayLoadingOverlay(show) {
            const overlay = document.getElementById('loadingOverlay');
            overlay.style.display = show ? 'flex' : 'none';
        }

        // Function to export updated CSS data as a file
        function exportTXT(updatedCss) {
            const blob = new Blob([updatedCss], { type: 'text/plain' }); // Create a blob
            const url = URL.createObjectURL(blob); // Create a URL for the blob

            // Create an anchor element for the download
            const a = document.createElement('a');
            a.href = url;
            a.download = 'styles.txt'; // Set the default filename
            document.body.appendChild(a);
            a.click(); // Simulate a click to download
            document.body.removeChild(a); // Remove the anchor element
            URL.revokeObjectURL(url); // Free up memory
        }

        // Initialize event listener for export button
        document.getElementById('exportButton').onclick = collectAndExportElements;

