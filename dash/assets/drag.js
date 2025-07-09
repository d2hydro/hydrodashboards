console.log("drag.js loaded");

function setupDragbar() {
    const dragbar = document.getElementById("dragbar");
    const leftPanel = document.getElementById("left-panel");
    const container = document.getElementById("container");

    if (!dragbar || !leftPanel || !container) {
        console.log("Waiting for DOM...");
        setTimeout(setupDragbar, 100);
        return;
    }

    let dragging = false;

    dragbar.addEventListener("mousedown", function (e) {
        dragging = true;
        document.body.style.cursor = 'col-resize';
    });

    document.addEventListener("mouseup", function () {
        if (dragging) {
            dragging = false;
            document.body.style.cursor = 'default';
            console.log("resize")
            // ✅ Leaflet will react to window resize
            setTimeout(() => {
                window.dispatchEvent(new Event('resize'));
            }, 50);
        }
    });

    document.addEventListener("mousemove", function (e) {
        if (!dragging) return;

        const containerRect = container.getBoundingClientRect();
        let newWidth = e.clientX - containerRect.left;

        if (newWidth > 100 && newWidth < containerRect.width - 100) {
            leftPanel.style.width = newWidth + "px";
        }
    });
}

window.addEventListener("load", setupDragbar);
