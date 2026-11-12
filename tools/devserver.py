"""Local preview server: serves the dashboard with sample calendar events.

Usage:  python tools/devserver.py [port]
Then open http://localhost:8787  (or on the tablet via `adb reverse tcp:8787 tcp:8787`).
Sample events are generated relative to today; real Indian holidays are fetched from Google.
"""
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
HOLIDAYS = [
    "https://calendar.google.com/calendar/ical/en.usa%23holiday%40group.v.calendar.google.com/public/basic.ics",
]
_holiday_cache = {"t": None, "ics": []}


def ics_dt(d: datetime) -> str:
    return d.strftime("%Y%m%dT%H%M%S")


def load_config() -> dict:
    """Private settings if present (and NEXUS_EXAMPLE isn't set), else the committed example."""
    local = SRC / "config.local.json"
    use = local if local.exists() and not os.environ.get("NEXUS_EXAMPLE") else SRC / "config.example.json"
    cfg = json.loads(use.read_text(encoding="utf-8"))
    cfg.pop("calendars", None)
    return cfg


def sample_ics(names) -> str:
    a, b, c, d = (list(names) + ["A", "B", "C", "D"])[:4]
    today = date.today()
    D = lambda n: today + timedelta(days=n)
    at = lambda n, h, m=0: datetime(D(n).year, D(n).month, D(n).day, h, m)
    now = datetime.now()
    soon = now + timedelta(minutes=12)
    wd = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
    ev = []

    # Floating (local) times so the preview looks right in any browser timezone;
    # the PTM event below still exercises the UTC path, and TZID handling was verified separately.
    def add(uid, summary, start, end=None, extra="", allday=False, tz=False):
        if allday:
            s = f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}\nDTEND;VALUE=DATE:{(end or start + timedelta(days=1)).strftime('%Y%m%d')}"
        else:
            p = ";TZID=Asia/Kolkata" if tz else ""
            s = f"DTSTART{p}:{ics_dt(start)}\nDTEND{p}:{ics_dt(end or start + timedelta(hours=1))}"
        ev.append(f"BEGIN:VEVENT\nUID:{uid}@demo\nSUMMARY:{summary}\n{s}\n{extra}END:VEVENT")

    add("piano", f"[{c}] Piano lesson", at(-21, 16, 30), at(-21, 17, 30),
        f"RRULE:FREQ=WEEKLY;BYDAY={wd[today.weekday()]},{wd[(today.weekday() + 3) % 7]}\n")
    add("yoga", "Morning yoga", at(-5, 6, 30), at(-5, 7, 15),
        f"RRULE:FREQ=DAILY;COUNT=30\nEXDATE:{ics_dt(at(2, 6, 30))}\n")
    add("yoga", "Morning yoga (late start)", at(1, 7, 30), at(1, 8, 15),
        f"RECURRENCE-ID:{ics_dt(at(1, 6, 30))}\n")
    add("dentist", f"[{c}] Dentist – Dr. Patel", at(1, 10, 30), at(1, 11, 15),
        "LOCATION:Family Dental\\, Main St\nDESCRIPTION:Six-month cleaning.\\nBring insurance card.\n")
    add("cardio", f"{d}: annual physical with Dr. Lee", at(3, 9, 0), at(3, 10, 0), "LOCATION:City Medical Center\n")
    add("bday", f"{b}'s Birthday", D(2), allday=True, extra="RRULE:FREQ=YEARLY\n")
    add("dinner", "Family dinner out", at(4, 19, 30), at(4, 21, 30))
    add("flight", f"[{a}] Flight to Chicago UA 1123", at(5, 8, 10), at(5, 10, 0), "LOCATION:Logan Airport Terminal B\n")
    add("bill", "!Pay electricity bill", at(6, 11, 0), at(6, 11, 30))
    utc = at(1, 19, 0).astimezone(timezone.utc).replace(tzinfo=None)
    ev.append(f"BEGIN:VEVENT\nUID:ptm@demo\nSUMMARY:School parent-teacher conference\nDTSTART:{ics_dt(utc)}Z\nDTEND:{ics_dt(utc + timedelta(hours=1))}Z\nEND:VEVENT")
    add("cancel", "Cancelled meeting", at(2, 15, 0), extra="STATUS:CANCELLED\n")
    add("swim", f"[{c}] Swim practice", at(0, 7, 0), at(0, 8, 0))
    add("call", "Video call with grandparents", soon, soon + timedelta(minutes=30))
    add("vacc", f"[{b}] Flu shot at CVS", at(0, now.hour + 2 if now.hour < 21 else 23, 0), None)
    add("monthly", "HOA dues", at(-40, 10, 0), extra="RRULE:FREQ=MONTHLY;BYMONTHDAY=15\n")
    add("trip", "Weekend trip – Cape Cod", D(5), D(7), allday=True)
    return "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//demo//EN\n" + "\n".join(ev) + "\nEND:VCALENDAR\n"


def holidays() -> list:
    t = _holiday_cache["t"]
    if t and (datetime.now() - t).total_seconds() < 3600:
        return _holiday_cache["ics"]
    out = []
    for url in HOLIDAYS:
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                out.append(r.read().decode("utf-8", "replace"))
        except Exception as e:  # offline: keep going without holidays
            print("holiday fetch failed:", e)
    _holiday_cache.update(t=datetime.now(), ics=out)
    return out


class H(BaseHTTPRequestHandler):
    def send(self, body, ctype, code=200):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.send_header("cache-control", "no-store")
        self.send_header("content-length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"):
            cfg = load_config()
            # Preview: use the generated recordings in audio/ for any mantra without a link.
            marks = ROOT / "audio" / "marks.json"
            if marks.exists():
                cfg["mantraMarks"] = json.loads(marks.read_text(encoding="utf-8"))
                for mid in cfg.get("mantraAudio", {}):
                    if not cfg["mantraAudio"][mid] and (ROOT / "audio" / f"{mid}.mp3").exists():
                        cfg["mantraAudio"][mid] = f"/audio/{mid}.mp3"
            html = (SRC / "dashboard.html").read_text(encoding="utf-8")
            html = html.replace('"__RUNTIME_CONFIG__";',"window.FD_CONFIG=" + json.dumps(cfg, ensure_ascii=False) + ";")
            return self.send(html, "text/html; charset=utf-8")
        if p == "/api/data":
            # Second calendar in the same shape Apps Script's getData() returns.
            t = date.today()
            k = datetime(t.year, t.month, t.day, 17, 0) + timedelta(days=2)
            gas_events = [
                {"uid": "karate@gas", "title": "Karate belt test", "desc": "", "loc": "Community Rec Center", "allDay": False,
                 "start": int(k.timestamp() * 1000), "end": int((k + timedelta(hours=1)).timestamp() * 1000)},
                {"uid": "trip@gas", "title": "School science trip", "desc": "", "loc": "", "allDay": True,
                 "startDate": (t + timedelta(days=3)).isoformat(), "endDate": (t + timedelta(days=4)).isoformat()},
            ]
            names = [m["name"] for m in load_config().get("members", [])]
            body = {"calendars": [{"name": "Family", "ok": True, "ics": sample_ics(names)},
                                  {"name": names[2] if len(names) > 2 else "Family", "ok": True, "events": gas_events}],
                    "holidays": holidays(), "fetchedAt": datetime.now(timezone.utc).isoformat(), "configured": True}
            return self.send(json.dumps(body), "application/json")
        if p.startswith("/audio/") and p.endswith(".mp3"):
            f = ROOT / "audio" / Path(p).name
            if f.is_file():
                return self.send(f.read_bytes(), "audio/mpeg")
        if p == "/audio/test.wav":  # 8 s test tone standing in for a mantra recording
            import io, math, struct, wave
            buf = io.BytesIO()
            with wave.open(buf, "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
                frames = b"".join(struct.pack("<h", int(6000 * math.sin(2 * math.pi * (220 + 20 * (i // 16000)) * i / 16000)
                                                   * (0.5 + 0.5 * math.sin(math.pi * (i % 16000) / 16000)))) for i in range(16000 * 8))
                w.writeframes(frames)
            return self.send(buf.getvalue(), "audio/wav")
        if p == "/api/weather":
            q = dict(kv.split("=", 1) for kv in self.path.split("?", 1)[1].split("&")) if "?" in self.path else {}
            lat, lon = float(q.get("lat", 28.61)), float(q.get("lon", 77.21))
            url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                   "&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,is_day,wind_speed_10m"
                   "&daily=weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_probability_max,uv_index_max"
                   "&timezone=auto&forecast_days=8")
            if q.get("unit", "C").upper() == "F":
                url += "&temperature_unit=fahrenheit&wind_speed_unit=mph"
            try:
                with urllib.request.urlopen(url, timeout=15) as r:
                    return self.send(r.read(), "application/json")
            except Exception as e:
                return self.send(json.dumps({"error": str(e)}), "application/json", 502)
        self.send("not found", "text/plain", 404)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    print(f"Nexus preview on http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
