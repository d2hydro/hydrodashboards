
# CSS as Python strings; written to /assets by generate_styles.py

RESET_MARGINS = """
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  overflow: hidden;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
  color: #1f2937;
  background-color: #ffffff;
}
.dash-loading .loading { font-size: 0 !important; }
"""

PAGE_LOADER = """
#page-loader{
  position: fixed; inset: 0; z-index: 2000;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.55);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}
#page-loader .loader-inner{
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  padding: 18px 20px;
  background: rgba(255,255,255,0.9);
  border: 1px solid rgba(0,0,0,0.05);
  border-radius: 14px;
  box-shadow: 0 6px 20px rgba(0,0,0,0.06);
}
.spinner-ring{
  width: 64px; height: 64px;
  border-radius: 50%;
  border: 6px solid #e5e7eb;
  border-top-color: #6b7280;
  animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loader-text{
  font: 600 14px/1.2 system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
  color: #1f2937; letter-spacing: .02em;
}
@media (prefers-reduced-motion: reduce){ .spinner-ring{ animation: none !important; } }
"""

SHARE_URL = """
.share-button {
  border: 1px solid #ccc;
  background-color: #fff;
  border-radius: 8px;
  padding: 0.4rem 0.6rem;
  font-size: 0.9rem;
  line-height: 1.2rem;
  cursor: pointer;
  transition: transform 0.08s ease, box-shadow 0.08s ease, background-color 0.12s ease;
  box-shadow: 0 2px 4px rgba(0,0,0,0.08);
}
.share-button:active {
  transform: scale(0.92);
  box-shadow: 0 1px 2px rgba(0,0,0,0.2) inset;
  background-color: #eef;
}
"""
