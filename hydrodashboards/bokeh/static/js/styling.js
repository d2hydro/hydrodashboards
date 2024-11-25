function loadJsonData() {
    const jsonFilePath = 'wam/static/css/data.json'; // Specify the correct path to your JSON file

    // Show the loading spinner
    const spinner = document.getElementById('loading-spinner');
    if (spinner) spinner.style.display = 'flex';

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
        })
        .finally(() => {
            // Hide and remove the spinner
            if (spinner) {
                spinner.style.display = 'none'; // Hide the spinner
                spinner.remove(); // Optionally remove it from the DOM
            }
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
            // Check if the element is .noUi-target
            if (currentElement.classList.contains('noUi-target')) {
                console.log('noUi-target element found:', currentElement);

                // Get the .noUi-connect element within this target
                const connectElement = currentElement.querySelector('.noUi-connect');
                if (!connectElement) {
                    console.warn('No .noUi-connect element found inside the .noUi-target');
                    return;
                }

                // Extract the colors from the JSON "style" property
                let disabledColor = 'lightgrey'; // Default colors if not in JSON
                let enabledColor = 'green';

                style.forEach(styleRule => {
                    const [property, value] = styleRule.split(':').map(s => s.trim());
                    if (property === 'background-disabled') {
                        disabledColor = value; // Set disabled color from JSON
                    } else if (property === 'background-enabled') {
                        enabledColor = value; // Set enabled color from JSON
                    }
                });

                // Setup MutationObserver to detect changes to the 'disabled' attribute
                const observer = new MutationObserver((mutationsList) => {
                    mutationsList.forEach(mutation => {
                        if (mutation.type === 'attributes' && mutation.attributeName === 'disabled') {
                            console.log('Mutation detected for disabled attribute:', mutation.target);

                            if (mutation.target.hasAttribute('disabled')) {
                                // Disabled state
                                console.log(`Element is disabled. Changing background to ${disabledColor}.`);
                                connectElement.style.setProperty('background', disabledColor, 'important');
                            } else {
                                // Enabled state (disabled attribute is removed)
                                console.log(`Element is enabled. Changing background to ${enabledColor}.`);
                                connectElement.style.setProperty('background', enabledColor, 'important');
                            }
                        } else {
                            console.log(`Attribute changed: ${mutation.attributeName}, but it's not 'disabled'.`);
                        }
                    });
                });

                // Observe changes to the 'disabled' attribute on the .noUi-target element
                observer.observe(currentElement, {
                    attributes: true, // Observe attribute changes
                    attributeFilter: ['disabled'] // Only observe changes to the 'disabled' attribute
                });

                // Log if the observer is attached
                console.log('MutationObserver attached to .noUi-target element:', currentElement);
            } else {
                console.log('Current element is not a .noUi-target:', currentElement);
            }

            // Apply any other styles in the JSON (for buttons, etc.)
            if (style.length > 0) {
                style.forEach(styleRule => {
                    const [property, value] = styleRule.split(':').map(s => s.trim());
                    if (property && value) {
                        currentElement.style.setProperty(property, value, 'important'); // Apply each style property
                        console.log(`Style applied: ${property}: ${value}`);
                    }
                });
            }

            // Set up a separate MutationObserver for button elements
            if (currentElement.tagName.toLowerCase() === 'button') {
                console.log('Button detected:', currentElement);

                // Set up MutationObserver for button
                const buttonObserver = new MutationObserver((mutationsList) => {
                    for (let mutation of mutationsList) {
                        if (mutation.type === 'attributes' && mutation.attributeName === 'disabled') {
                            console.log('Button disabled attribute changed:', mutation.target);
                            // Reapply styles for the button
                            applyDynamicStyle([data], mapping); // Reapply the styles for the button
                        }
                    }
                });

                buttonObserver.observe(currentElement, {
                    attributes: true // Observe attribute changes
                });

                console.log('MutationObserver attached to button:', currentElement);
            }
        });
    });
}


// Call the loadJsonData function after a delay of 2 seconds after the window is fully loaded
window.addEventListener('load', function() {
    setTimeout(loadJsonData, 2000); // Delay for 2 seconds (2000 milliseconds)
});
