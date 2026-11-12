"""Capture README screenshots of the dashboard with the example config (sample family, no private data).

Needs: Chrome or Edge, and `pip install websocket-client`.
Usage: python tools/screenshots.py   ->  docs/screenshots/*.png
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websocket

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots"
PORT, CDP = 8799, 9333
W, H = 1280, 800

BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    shutil.which("google-chrome") or "", shutil.which("chromium") or "",
]


class Page:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=60, suppress_origin=True)
        self.n = 0

    def call(self, method, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == self.n:
                if "error" in m:
                    raise RuntimeError(m["error"])
                return m.get("result", {})

    def js(self, expr):
        r = self.call("Runtime.evaluate", expression=expr, awaitPromise=True, returnByValue=True)
        if r.get("exceptionDetails"):
            raise RuntimeError(r["exceptionDetails"])
        return r.get("result", {}).get("value")

    def shot(self, name):
        png = base64.b64decode(self.call("Page.captureScreenshot", format="png")["data"])
        (OUT / f"{name}.png").write_bytes(png)
        print(f"docs/screenshots/{name}.png  {len(png) // 1024} KB")


# Reset to a clean daytime view: no night mode, alerts, toasts or overlays.
CLEAN = """(() => { S.nightPeek = Date.now() + 36e5; renderNight(new Date());
  ['alertOv','toast','dayOv','briefOv','mantraOv'].forEach(id => document.getElementById(id).classList.remove('show'));
  clearInterval(slideTimer); try { speechSynthesis.cancel(); } catch (e) {} return 1; })()"""


def main():
    browser = next((b for b in BROWSERS if b and os.path.exists(b)), None)
    if not browser:
        sys.exit("Chrome or Edge not found")
    OUT.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, NEXUS_EXAMPLE="1")
    server = subprocess.Popen([sys.executable, "-I", str(ROOT / "tools" / "devserver.py"), str(PORT)], env=env)
    profile = tempfile.mkdtemp()
    chrome = subprocess.Popen([browser, "--headless=new", f"--remote-debugging-port={CDP}", f"--user-data-dir={profile}",
                               f"--window-size={W},{H}", "--hide-scrollbars", "--mute-audio", "--autoplay-policy=no-user-gesture-required",
                               "about:blank"])
    try:
        for _ in range(50):
            try:
                targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{CDP}/json"))
                ws_url = next(t["webSocketDebuggerUrl"] for t in targets if t["type"] == "page")
                break
            except Exception:
                time.sleep(0.3)
        p = Page(ws_url)
        p.call("Emulation.setDeviceMetricsOverride", width=W, height=H, deviceScaleFactor=1, mobile=False)
        p.call("Page.enable")
        p.call("Page.navigate", url=f"http://127.0.0.1:{PORT}/")
        time.sleep(9)  # boot animation, data and weather

        p.js(CLEAN); p.js("showSlide(0)"); time.sleep(1.5); p.shot("dashboard")
        p.js(CLEAN); p.js("(() => { const t = new Date(); t.setHours(7, 15, 0, 0); showBriefing(t); })()"); time.sleep(4); p.shot("briefing")
        p.js(CLEAN); p.js("(() => { playMantra(MANTRAS.morning[0], 'morning'); })()"); time.sleep(9); p.shot("mantra"); p.js("stopMantra()")
        p.js(CLEAN); p.js("(() => { S.events.filter(e => e.important).forEach(e => e); checkAlerts(new Date()); return document.getElementById('alertOv').classList.contains('show'); })()")
        time.sleep(1.5); p.shot("alert")
        p.js(CLEAN); p.js("(() => { openDay(startOfDay(addDaysD(new Date(), 1)).getTime()); })()"); time.sleep(1.5); p.shot("day-detail")
        p.js(CLEAN); p.js("(() => { CFG.nightMode = {start:'00:00', end:'23:59'}; S.nightPeek = 0; renderNight(new Date()); })()"); time.sleep(2.5); p.shot("night")
    finally:
        chrome.terminate(); server.terminate()
        time.sleep(1); shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
