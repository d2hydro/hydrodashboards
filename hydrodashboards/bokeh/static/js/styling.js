function loadJsonData() {
    const jsonFilePath = 'wam/static/css/data.json'; // Specify the correct path to your JSON file

    fetch(jsonFilePath)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text(); // Read as text to allow comment removal
        })
        .then(text => {
            const jsonString = removeComments(text); // Remove comments from the JSON string
            const data = JSON.parse(jsonString); // Parse the cleaned JSON
            const mapping = mapBokehDataRoots(); // Get the Bokeh data root mapping
            applyDynamicStyle(data, mapping); // Call your function to apply styles
        })
        .catch(error => {
            console.error('Error loading JSON:', error);
        });
}

/**
 * Function to remove comments from JSON-like text.
 * @param {string} text - The input text potentially containing comments.
 * @returns {string} - The cleaned text without comments.
 */
function removeComments(text) {
    text = text.replace(/\/\/.*$/gm, ''); // Remove single-line comments (// comment)
    text = text.replace(/\/\*[\s\S]*?\*\//g, ''); // Remove multi-line comments (/* comment */)
    return text;
}

/**
 * Function to collect all Bokeh data-root-id elements, sort them, and assign custom names
 */
function mapBokehDataRoots() {
    const dataRootElements = document.querySelectorAll('[data-root-id]');
    const dataRootArray = Array.from(dataRootElements);

    dataRootArray.sort((a, b) => {
        const idA = a.getAttribute('data-root-id');
        const idB = b.getAttribute('data-root-id');
        return idA.localeCompare(idB);
    });

    const rootMapping = {};
    dataRootArray.forEach((element, index) => {
        const customName = `dataroot${index + 1}`;
        rootMapping[customName] = element.getAttribute('data-root-id');
    });

    console.log('Data Root Mapping:', rootMapping);

    return rootMapping;
}

/**
 * Function to directly apply styles to elements identified by the given hierarchy.
 * @param {Array} dataArray - The parsed JSON data containing hierarchy and styles.
 * @param {Object} mapping - The mapping of data-root identifiers to their actual values.
 */
function applyDynamicStyle(dataArray, mapping) {
    dataArray.forEach(data => {
        let { tag, hierarchy, style } = data;

        // Update tag if it includes dataroot
        if (tag.includes('dataroot')) {
            const match = tag.match(/dataroot(\d+)/);
            if (match) {
                const rootKey = `dataroot${match[1]}`;
                tag = tag.replace(`dataroot${match[1]}`, mapping[rootKey]);
            }
        }

        // Update hierarchy steps for dataroot mapping
        hierarchy = hierarchy.map(step => {
            if (step.includes('dataroot')) {
                const match = step.match(/dataroot(\d+)/);
                if (match) {
                    const rootKey = `dataroot${match[1]}`;
                    return step.replace(`dataroot${match[1]}`, mapping[rootKey]);
                }
            }
            return step; // If not a dataroot placeholder, return the step unchanged
        });

        let currentElements = [document.querySelector(hierarchy[0])]; // Start with the root element, usually "body"

        if (!currentElements[0]) {
            console.error('Starting element not found:', hierarchy[0]);
            return;
        }

        // Traverse the hierarchy to find the target elements
        for (let i = 1; i < hierarchy.length; i++) {
            const currentStep = hierarchy[i];
            let nextElements = [];

            if (currentStep === 'shadow-root') {
                currentElements.forEach(currentElement => {
                    if (currentElement.shadowRoot) {
                        nextElements.push(currentElement.shadowRoot);
                    } else {
                        console.error('Shadow root not found at:', currentElement);
                    }
                });
            } else {
                currentElements.forEach(currentElement => {
                    const foundElements = Array.from(currentElement.querySelectorAll(currentStep));
                    nextElements = nextElements.concat(foundElements);
                });

                if (nextElements.length === 0) {
                    console.error(`No elements found for step: ${currentStep}`);
                    return;
                }
            }

            currentElements = nextElements;
        }

        // Apply styles to found elements
        currentElements.forEach(currentElement => {
            // Check if the element is .noUi-connect
            if (currentElement.classList.contains('noUi-connect')) {
                console.log('noUi-connect element found:', currentElement);

                // Apply initial style immediately
                currentElement.style.setProperty('background', 'purple');
                console.log('Initial background style set.');

                // Setup MutationObserver to detect future changes
                const observer = new MutationObserver(() => {
                    if (currentElement.classList.contains('disabled')) {
                        currentElement.style.setProperty('background', 'grey', 'important'); // Active state
                    } else {
                        currentElement.style.setProperty('background', 'green', 'important'); // Disabled state
                    }
                });

                observer.observe(currentElement, {
                    attributes: true, // Observe attribute changes
                    attributeFilter: ['class'] // Only observe changes to the class attribute
                });
            }

            // Apply any other styles in the JSON (for buttons, etc.)
            if (style.length > 0) {
                style.forEach(styleRule => {
                    const [property, value] = styleRule.split(':').map(s => s.trim());
                    if (property && value) {
                        currentElement.style.setProperty(property, value, 'important'); // Apply each style property
                    }
                });
            }

            // Set up a MutationObserver for any button detected
            if (currentElement.tagName.toLowerCase() === 'button') {
                console.log('Button detected:', currentElement);

                // Set up MutationObserver for style reapplication
                const observer = new MutationObserver((mutationsList) => {
                    for (let mutation of mutationsList) {
                        if (mutation.type === 'attributes' && mutation.attributeName === 'disabled') {
                            console.log('Button disabled attribute changed:', mutation.target);
                            // Reapply styles for the button
                            applyDynamicStyle([data], mapping); // Reapply the styles for the button
                        }
                    }
                });

                observer.observe(currentElement, {
                    attributes: true // Observe attribute changes
                });

                console.log('MutationObserver attached to element:', currentElement);
            }
        });
    });
}

// Call the loadJsonData function after a delay of 2 seconds after the window is fully loaded
window.addEventListener('load', function() {
    setTimeout(loadJsonData, 2000); // Delay for 2 seconds (2000 milliseconds)
});
