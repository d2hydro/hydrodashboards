from datetime import datetime, timedelta
from bokeh.models import BBoxTileSource
from pathlib import Path
import os

# system_settings
LOG_DIR = Path(os.getcwd()).joinpath("logs")

# Layout settings
TITLE = "test dashboard"
LANGUAGE = "dutch"
BOUNDS = [210000, 544000, 250000, 625000]
FILTER_COLORS = {
    "WDB_OW_KGM": {"fill": "cyan", "line": "blue"},
    "WDB_OW_KST": {"fill": "lightgreen", "line": "green"},
    "WDB_OW_INL": {"fill": "orange", "line": "red"},
    "WDB_OW_KSL": {"fill": "grey", "line": "black"},
    "WDB_OW_MPN": {"fill": "yellow", "line": "orange"},
    "WDB_GW_GMW": {"fill": "greenyellow", "line": "green"},
    "WDB_FC_MPN": {"fill": "darkorange", "line": "red"},
    "WDB_EL_MPN": {"fill": "fuchsia", "line": "purple"},
    "WDB_ML_KNMI": {"fill": "lightblue", "line": "blue"},
}
MAP_OVERLAYS = {
    "watergangen": {
        "url": (
            "https://arcgis.noorderzijlvest.nl/server/rest/services/Watergangen/Watergangen/MapServer/export?dpi=96"
            "&bbox={XMIN},{YMIN},{XMAX},{YMAX}&bboxSR=28992&transparent=true&f=image&format=png8"
        ),
        "class": BBoxTileSource,
        "visible": True,
    },
    "grens NZV": {
        "url": (
            "https://arcgis.noorderzijlvest.nl/server/rest/services/Referentie/BegrenzingNoorderzijlvest/MapServer/export?"
            "&width=1280&height=709&bbox={XMIN},{YMIN},{XMAX},{YMAX}&bboxSR=28992&transparent=true&f=image&format=png8"
        ),
        "class": BBoxTileSource,
        "visible": True,
    },
}

# FEWS Settings
EXCLUDE_PARS = ["Dummy"]
FEWS_URL = r"https://www.hydrobase.nl/fews/nzv/FewsWebServices/rest/fewspiservice/v1"
HEADERS_FULL_HISTORY = ["WDB_FC_MPN", "WDB_ML_KNMI", "WDB_GW_GMW"]
ROOT_FILTER = "WDB"
SSL_VERIFY = False

# Search Settings
HISTORY_PERIOD = timedelta(days=3650)
#MAX_VIEW_PERIOD = timedelta(days=180)
MAX_VIEW_PERIOD = None
