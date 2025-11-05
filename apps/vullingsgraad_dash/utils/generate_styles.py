
from pathlib import Path
from utils.style_definitions import RESET_MARGINS, PAGE_LOADER, SHARE_URL

def ensure_assets_css(assets_dir: Path):
    assets_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "reset_margins.css": RESET_MARGINS,
        "page_loader.css": PAGE_LOADER,
        "share_url.css": SHARE_URL,
    }
    for name, content in files.items():
        (assets_dir / name).write_text(content.strip() + "\n", encoding="utf-8")
