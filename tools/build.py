"""Build the two files you paste into Google Apps Script: dist/Code.gs and dist/Index.html.

Settings come from src/config.local.json (private, git-ignored). If it doesn't exist yet,
it's created from src/config.example.json for you to edit.
"""
import json
import secrets
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
DIST = ROOT / "dist"


def load_config():
    local = SRC / "config.local.json"
    if not local.exists():
        shutil.copy(SRC / "config.example.json", local)
        print("Created src/config.local.json from the example. Edit it with your family's details, then build again.")
    return json.loads(local.read_text(encoding="utf-8"))


def main():
    config = load_config()
    calendars = config.pop("calendars", [{"id": "primary", "name": "Family"}])
    key_file = ROOT / "access-key.txt"  # generated once; the tablet link must use the same key
    if not key_file.exists():
        key_file.write_text(secrets.token_urlsafe(18), encoding="utf-8")
    key = key_file.read_text(encoding="utf-8").strip()
    marks = ROOT / "audio" / "marks.json"  # line timings of the generated mantra recordings
    if marks.exists():
        config["mantraMarks"] = json.loads(marks.read_text(encoding="utf-8"))
    code = (SRC / "Code.template.gs").read_text(encoding="utf-8")
    code = code.replace("/*__CONFIG__*/", json.dumps(config, indent=2, ensure_ascii=False))
    code = code.replace("/*__CALENDARS__*/", json.dumps(calendars, indent=2, ensure_ascii=False))
    code = code.replace("/*__ACCESS_KEY__*/", key)
    DIST.mkdir(exist_ok=True)
    (DIST / "Code.gs").write_text(code, encoding="utf-8")
    html = (SRC / "dashboard.html").read_text(encoding="utf-8")
    (DIST / "Index.html").write_text(html, encoding="utf-8")
    for f in ("Code.gs", "Index.html"):
        print(f"dist/{f}  {(DIST / f).stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    sys.exit(main())
