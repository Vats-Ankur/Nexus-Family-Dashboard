# Setup guide

From a fresh clone to a dashboard running on the tablet: about 30 minutes.

**Contents**
1. [Configure and build](#1-configure-and-build)
2. [Google Apps Script](#2-google-apps-script)
3. [Calendars](#3-calendars)
4. [Mantra recordings](#4-mantra-recordings)
5. [The tablet](#5-the-tablet)
6. [Locking it down](#-locking-it-down)
7. [Changing settings later](#7-changing-settings-later)
8. [Troubleshooting](#8-troubleshooting)

**You need**
- A Google account for the dashboard. A dedicated one is tidiest.
- Python 3.10 or newer, on the PC.
- An Android tablet with [Fully Kiosk Browser](https://www.fully-kiosk.com). Any browser works for testing.

---

## 1. Configure and build

```bash
python tools/build.py
```

The first run creates two files, both git‑ignored:
- `src/config.local.json`, copied from the example;
- `access-key.txt`, a random family access key.

Edit `config.local.json`:

```jsonc
{
  "familyName": "Family",
  "city": { "name": "Boston", "lat": 42.3601, "lon": -71.0589 },
  "units": "F",
  "members": [
    { "name": "Alex", "color": "#3ee8ff", "match": ["alex"] },
    { "name": "Maya", "color": "#7dff8a", "match": ["maya", "mayu"] }
  ],
  "calendars": [
    { "id": "primary", "name": "Family" },
    { "id": "abc123…@group.calendar.google.com", "name": "Family" },
    { "id": "someone@gmail.com", "name": "Alex" }
  ],
  "nightMode": { "start": "22:30", "end": "05:30" }
}
```

Then build again. This writes `dist/Code.gs` (your settings and key built in) and `dist/Index.html`.

## 2. Google Apps Script

1. Open **https://script.google.com** as the dashboard account → **New project**. Name it `Nexus Family Deck`.
2. Replace the contents of `Code.gs` with `dist/Code.gs`.
3. Click **＋** next to *Files* → **HTML** → name it `Index` (without `.html`) → paste `dist/Index.html`.
4. ⚙ **Project Settings → Time zone**: set your local time zone. All‑day events use it.
5. Select **`testSetup`** → **▶ Run** and allow access. A healthy log looks like this:
   ```
   Family: 29 events
   Alex: 1 events
   Holidays: 7 from calendar
   Mantra recording "gayatri": 347 KB OK
   Weather in Boston: 40.5°F
   ```
6. **Deploy → New deployment → ⚙ Web app** → *Execute as:* **Me**, *Who has access:* **Anyone** → **Deploy**.
7. Your **tablet link** is the `/exec` URL followed by `?key=` and the contents of `access-key.txt`.

> **Two permissions are needed:** your calendars, and *Connect to an external service* (weather, holidays, audio).
> If Google shows "Sorry, unable to open the file at this time", you're signed in to several Google accounts.
> Authorise in a private window where only the dashboard account is signed in.

## 3. Calendars

The script reads the calendars listed in `calendars`. To show a calendar from **another Gmail account** (account A) on the dashboard account (B):

1. As **A**: calendar.google.com → ⚙ Settings → the calendar → **Share with specific people** → add B, with *See all event details*.
2. As **B**: open the invitation email → **Add this calendar**.
3. As **A**: same settings page → **Integrate calendar** → copy the **Calendar ID**. For a main calendar it's A's Gmail address.
4. Add the ID to `calendars`, then build and redeploy (see [section 7](#7-changing-settings-later)).

**Tip:** create one **"Family"** calendar in B and share it with everyone with *Make changes to events*. Anyone can then add events from their phone.

**Time zones:** events are sent as exact moments, so the dashboard always shows them in the tablet's local time.
- If a shared event looks shifted on calendar.google.com, set each account's **Settings → General → Time zone**, and each calendar's own time zone, to your local zone.
- Turn off *Ask to update my primary time zone*.

## 4. Mantra recordings

`audio/` already contains 8 recordings, and `audio/marks.json` holds their line timings.

1. Upload the MP3s to Google Drive. For each one: right‑click → **Share** → *General access: Anyone with the link* → **Copy link**.
2. Paste each link into `mantraAudio` in `config.local.json`, keyed by file name (`gayatri`, `karagre`, `ganesha`, `asato`, `shanti`, `deepa`, `mahamrityunjaya`, `sarve`).
3. Build, paste `Code.gs` and redeploy.

The script fetches the files from Drive for the tablet, because old Android web views can't play Drive links directly.
- **Your own recordings:** use `{ "url": "…", "rounds": 3 }` so the lines highlight roughly in sync.
- **A different voice:** `python tools/make_mantras.py --voice hi-IN-SwaraNeural`, then rebuild so the new timings are included.

## 5. The tablet

Tested on a Lenovo TAB3 8 (Android 6, WebView 95) with Fully Kiosk Browser 1.61.4, the last version for Android 6.

**Fully Kiosk settings**
- *Web Content → Start URL*: your tablet link.
- *Web Content → Autoplay Audio*: on. Needed for the scheduled mantras.
- *Advanced Web → Keep Screen On*: on.
- *Device Management → Launch on Boot*: on.
- *Web Auto Reload*: reload on network reconnect, and 60 s after a page error.
- Fullscreen; landscape orientation.
- *Unlock Screen*: **off**. When on, it disables the Android lock screen entirely.

**Entering the long link:** typing it on the tablet is painful. With USB debugging on, open the Start URL field and type it from the PC:

```bash
adb shell input text 'https://script.google.com/macros/s/…/exec?key'
adb shell input keyevent 70        # "=" (adb's text input drops it)
adb shell input text '<your key>'
```

**Behaviour**
- Scheduled mantras need one tap on the screen after each page load. That's a browser rule.
- The briefing card shows either way.
- Tap the **clock** for today's briefing.
- Tap the **NEXUS logo** to reload data.
- Tap **LIVE** for diagnostics.

## 🔒 Locking it down

| Layer | Protection |
|---|---|
| Dashboard settings | Live in the Apps Script project. Only its Google account can edit it, so turn on 2‑Step Verification. |
| Dashboard data | The `/exec` link only works with the access key. |
| Leaving the kiosk | Set an Android screen lock, then Settings → Security → **Screen pinning** → on, with *Ask for unlock pattern before unpinning*. Pin Fully from □ Overview → 📌. |
| After a power cut | Fully starts by itself. With a screen lock it waits behind the lock screen. Without one it comes straight back, but anyone can unpin it. |
| Fully's own settings | Free version: reachable by swiping in from the left edge. Locking them needs Fully PLUS (Kiosk Mode). |
| USB | Turn off USB debugging when you're done. |

## 7. Changing settings later

1. Edit `src/config.local.json`, or `src/dashboard.html` for design changes.
2. Run `python tools/build.py`.
3. Paste `dist/Code.gs` and/or `dist/Index.html` into the project.
4. **Deploy → Manage deployments → ✏ → Version: New version → Deploy.** The link and key stay the same.
5. Tap the NEXUS logo on the tablet, or wait about 10 minutes.

## 8. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Dark screen that never finishes booting | `Index` or `Code.gs` is out of date. Paste both from a fresh build. Apps Script strips comments and `//`, so never hand‑edit `"__RUNTIME_CONFIG__";` or the `https:\/\/` URLs. |
| `You do not have permission to call UrlFetchApp.fetch` | Run `testSetup` again and allow *Connect to an external service*. |
| Weather "Awaiting data" | Same permission as above. Tap **LIVE** to see the exact error. |
| No US holidays | The **LIVE** diagnostics show the holiday count. The calendar `en.usa#holiday@group.v.calendar.google.com` is added to the account (hidden) the first time. |
| Mantra lines move but no sound | The Drive link isn't shared as *Anyone with the link*: `testSetup` says so. Or the page hasn't been tapped since it loaded. |
| Events at the wrong time | The script time zone (Project Settings) or the tablet's time zone is wrong. |
| Tablet restarts overnight | Background app updates freeze old devices. Turn off Play Store auto‑updates, or remove the Google apps: see [tablet-notes.md](tablet-notes.md). |
