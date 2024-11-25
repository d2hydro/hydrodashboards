// Wait for the document to be fully loaded
$(document).ready(function () {
    // Add click event listener to the sidebar collapse button
    $('#sidebarCollapse').on('click', function () {
        // Toggle the 'active' class on the sidebar and the button itself
        $('#sidebar').toggleClass('active');
        $(this).toggleClass('active');

        // Call functions from AnimationUtils to manage elements and page resizing
        AnimationUtils.tagElements();
        AnimationUtils.onResizePage();
    });
});

// Function to scale the graph display
function scale_graph() {
    // Get the graph and button elements by their IDs
    var zoekgraf = document.getElementById("zoekgrafiek-en-slider");
    var but = document.getElementById("button_lower");
    var h = document.getElementById("grafiek_upper");

    // Toggle icon classes for the button to indicate state
    but.classList.toggle("fa-angle-double-up");
    but.classList.toggle("fa-angle-double-down");

    // Check the current display state of the graph
    if (zoekgraf.style.display === "none") {
        // If hidden, show the graph and adjust height
        zoekgraf.style.display = "block";
        h.style.height = "62.5vh";	
    } else {
        // If visible, hide the graph and reset height
        zoekgraf.style.display = "none";
        h.style.height = "78vh";
        zoekgraf.style.opacity = "1"; // Ensure opacity is reset
    }

    // Dispatch a resize event to inform other components of the change
    AnimationUtils.dispatchResizeEvent();
}

// Function to toggle the visibility of the map legend
function popMapLegend() {
    // Get the map options and the map itself
    var map_opt = document.getElementById("map_opt");
    var kaart = document.getElementById("kaart");

    // Check if the map options are less than a certain opacity
    if (map_opt.style.opacity < "0.1") {
        // Set opacity to visible
        map_opt.style.opacity = "1";
    } else if (map_opt.style.display == "none") {
        // If hidden, set position and display to show it
        map_opt.style.position = "fixed";
        map_opt.style.display = "block";		
    } else {
        // Otherwise, hide the map options
        map_opt.style.display = "none";
    }
}

// Variable to track the Control key state
let ctrlKey = false;

// Function to handle keydown events
const keyDown = () => {
    document.addEventListener('keydown', function (e) {
        if (e.key == "Control") {
            ctrlKey = true; // Set ctrlKey to true if Control is pressed
        }
    });
};

// Function to handle keyup events
const keyUp = () => {
    document.addEventListener('keyup', function (e) {
        if (e.key == "Control") {
            ctrlKey = false; // Reset ctrlKey to false if Control is released
        }
    });
};

// Initialize the keydown and keyup event listeners
keyDown();
keyUp();

// Function to refresh the application
function refresh_app() {
    window.location.reload(); // Reload the current page
}
