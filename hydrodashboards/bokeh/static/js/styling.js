// Function to load JSON data from a specified path
function loadJsonData() {
    const jsonFilePath = 'wam/static/css/data.json'; // Specify the correct path to your JSON file

    console.log('Starting JSON data load from:', jsonFilePath);

    fetch(jsonFilePath)
        .then(response => {
            console.log('Fetch response received:', response);
            if (!response.ok) {
                console.error('Network response was not ok:', response.status, response.statusText);
                throw new Error('Network response was not ok');
            }
            return response.text(); // Read as text to allow comment removal
        })
        .then(text => {
            console.log('Raw JSON text received:', text);
            const jsonString = removeComments(text); // Remove comments from the JSON string
            console.log('Cleaned JSON string (comments removed):', jsonString);

            const data = JSON.parse(jsonString); // Parse the cleaned JSON
            console.log('Parsed JSON data:', data);

            const mapping = mapBokehDataRoots(); // Get the Bokeh data root mapping
            console.log('Bokeh Data Root Mapping:', mapping);

            applyDynamicStyle(data, mapping); // Call your function to apply styles
        })
        .catch(error => {
            console.error('Error loading JSON:', error);
        });
}

/**
 * Function to remove comments from JSON-like text.
 */
function removeComments(text) {
    console.log('Removing comments from text...');
    text = text.replace(/\/\/.*$/gm, ''); // Remove single-line comments (// comment)
    text = text.replace(/\/\*[\s\S]*?\*\//g, ''); // Remove multi-line comments (/* comment */)
    return text;
}

/**
 * Function to collect all Bokeh data-root-id elements, sort them, and assign custom names
 */
function mapBokehDataRoots() {
    console.log('Collecting Bokeh data-root-id elements...');
    const dataRootElements = document.querySelectorAll('[data-root-id]');
    const dataRootArray = Array.from(dataRootElements);

    console.log('Data-root elements found:', dataRootArray);

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

    console.log('Final Data Root Mapping:', rootMapping);
    return rootMapping;
}

/**
 * Function to apply styles dynamically based on hierarchy.
 */
function applyDynamicStyle(dataArray, mapping) {
    console.log('Applying dynamic styles...');
    console.log('Data Array:', dataArray);
    console.log('Mapping:', mapping);

    dataArray.forEach(data => {
        console.log('Processing data item:', data);

        let { tag, hierarchy, style } = data;

        // Update tag if it includes dataroot
        if (tag.includes('dataroot')) {
            const match = tag.match(/dataroot(\d+)/);
            if (match) {
                const rootKey = `dataroot${match[1]}`;
                console.log('Replacing tag dataroot placeholder with mapping:', rootKey);
                tag = tag.replace(`dataroot${match[1]}`, mapping[rootKey]);
            }
        }

        // Debug hierarchy processing
        console.log('Hierarchy before mapping:', hierarchy);
        hierarchy = hierarchy.map(step => {
            if (step.includes('dataroot')) {
                const match = step.match(/dataroot(\d+)/);
                if (match) {
                    const rootKey = `dataroot${match[1]}`;
                    console.log('Replacing hierarchy dataroot placeholder with mapping:', rootKey);
                    return step.replace(`dataroot${match[1]}`, mapping[rootKey]);
                }
            }
            return step; // If not a dataroot placeholder, return the step unchanged
        });
        console.log('Hierarchy after mapping:', hierarchy);

        let currentElements = [document.querySelector(hierarchy[0])]; // Start with the root element, usually "body"

        if (!currentElements[0]) {
            console.error('Starting element not found:', hierarchy[0]);
            return;
        }

        console.log('Starting elements found:', currentElements);

        // Traverse the hierarchy to find the target elements
        for (let i = 1; i < hierarchy.length; i++) {
            const currentStep = hierarchy[i];
            console.log(`Traversing hierarchy step: ${currentStep}`);
            let nextElements = [];

            if (currentStep === 'shadow-root') {
                currentElements.forEach(currentElement => {
                    if (currentElement.shadowRoot) {
                        console.log('Shadow root found:', currentElement.shadowRoot);
                        nextElements.push(currentElement.shadowRoot);
                    } else {
                        console.error('Shadow root not found at:', currentElement);
                    }
                });
            } else {
                currentElements.forEach(currentElement => {
                    const foundElements = Array.from(currentElement.querySelectorAll(currentStep));
                    console.log(`Elements found for step ${currentStep}:`, foundElements);
                    nextElements = nextElements.concat(foundElements);
                });

                if (nextElements.length === 0) {
                    console.error(`No elements found for step: ${currentStep}`);
                    return;
                }
            }

            currentElements = nextElements;
        }

        console.log('Final elements to apply styles to:', currentElements);

        // Apply styles to found elements
        currentElements.forEach(currentElement => {
            console.log('Applying styles to element:', currentElement);

            if (style.length > 0) {
                style.forEach(styleRule => {
                    const [property, value] = styleRule.split(':').map(s => s.trim());
                    if (property && value) {
                        console.log(`Applying style: ${property}: ${value}`);
                        currentElement.style.setProperty(property, value, 'important');
                    }
                });
            }
        });
    });
}

// Call the loadJsonData function after the window is loaded
window.addEventListener('load', function () {
    console.log('Window loaded. Starting delayed execution...');
    setTimeout(loadJsonData, 2000);
});


// Call the loadJsonData function after a delay of 2 seconds after the window is fully loaded
window.addEventListener('load', function() {
    const loadingOverlay = document.getElementById('loading-overlay');

    // Display the spinner during loading
    loadingOverlay.style.display = 'flex';

    // Simulate a delay to showcase the spinner (or load your data)
    setTimeout(() => {
        loadJsonData(); // Your function to load JSON data

        // Hide the spinner after loading is complete
        loadingOverlay.style.display = 'none';
    }, 2000); // Adjust the delay as necessary
});

