from bokeh.models.widgets import Button
from bokeh.models import CustomJS

# Hard-coded text to be added to the canvas
constant_text = "Aan deze figuur kunnen geen rechten worden ontleend"  # Update this text as needed

save_js = f"""
var grafiekElement = document.getElementById("grafiek_upper");

// Find all toolbars within the element
var toolbars = grafiekElement.querySelectorAll(".bk-toolbar");

// Check if there are any toolbars and target the one you want (e.g., the first one)
if (toolbars.length > 0) {{
    var toolbarToHide = toolbars[0]; // Change the index as needed

    // Hide all toolbars
    toolbars.forEach(function(toolbar) {{
        toolbar.style.display = "none";
    }});

    // Capture and save the plot after a short delay
    setTimeout(function() {{
        var scaleFactor = 5; // Higher values for higher resolution

        // Use html2canvas to capture the element and draw onto a new canvas
        html2canvas(grafiekElement, {{ scale: scaleFactor }}).then(canvas => {{
            // Create a new canvas for final scaling and text addition
            var finalCanvas = document.createElement('canvas');
            var context = finalCanvas.getContext('2d');

            // Set canvas size
            finalCanvas.width = grafiekElement.clientWidth * scaleFactor;
            finalCanvas.height = grafiekElement.clientHeight * scaleFactor;

            // Draw the captured image onto the final canvas
            context.drawImage(canvas, 0, 0, finalCanvas.width, finalCanvas.height);

            // Now add text to the canvas (in the top-right corner)
            var text = "{constant_text}";  // Use the hard-coded constant text here
            var fontSize = 10 * scaleFactor; // Set font size to 10px, adjusted by scale factor
            context.font = "italic " + fontSize + "px 'Helvetica', 'Arial', sans-serif";  // Set font style and size
            context.fillStyle = "grey";  // Set text color

            // Align the text to the right
            context.textAlign = "right";  // Right alignment for the text
            context.textBaseline = "top"; // Align to the top

            // Position the text (top-right corner)
            var padding = 10 * scaleFactor;  // Padding from the right and top edges
            context.fillText(text, finalCanvas.width - padding, padding);

            // Export the canvas to a Blob
            finalCanvas.toBlob(function(blob) {{
                window.saveAs(blob, 'grafiek_with_text.png');
            }});

            // Show all toolbars again after saving
            toolbars.forEach(function(toolbar) {{
                toolbar.style.display = ""; // Restore the toolbar visibility
            }});
        }});
    }}, 100); // Adjust the delay as needed
}}
"""

def make_button():
    button = Button(label="", button_type="success", disabled=True)  

    button.js_on_click(
        CustomJS(
            code=save_js,
        )
    )

    return button