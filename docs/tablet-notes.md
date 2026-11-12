# Tablet notes: Lenovo TAB3 8 (TB3-850F)

- **Device:** MT6735m, Android 6.0, Chrome 106 / WebView 95, 2 GB RAM.
  - No official updates past 6.0.
  - Rooting wasn't possible with the tools available: the TWRP and stock-firmware downloads are gone, mtkclient couldn't connect, and Lenovo's tool had no firmware.
- **Certificates:** Android 6's certificate store rejects Let's Encrypt and Cloudflare certificates but trusts Google's. That's why everything is served through Apps Script.
- **Overnight restarts:** in testing, a Google Play services auto-update at 04:21 blocked the package manager. Android's watchdog then restarted its system services, which unpinned Fully. Removing or stopping the Google apps avoids this.

## Apps removed to free memory

Each was removed with `adb shell pm uninstall -k --user 0 <package>` (Android 6 doesn't allow `disable-user` over USB on this ROM).
The apps stay on the system partition, and a factory reset restores them all.
Google Play services is registered as a device administrator: deactivate it in Settings → Security → Device administrators before removing it.

```
com.android.chrome
com.google.android.apps.docs
com.google.android.apps.maps
com.google.android.apps.messaging
com.google.android.apps.photos
com.google.android.apps.cloudprint
com.google.android.calendar
com.google.android.gm
com.google.android.gm.exchange
com.google.android.googlequicksearchbox
com.google.android.apps.inputmethod.hindi
com.google.android.music
com.google.android.videos
com.google.android.youtube
com.google.android.feedback
com.google.android.marvin.talkback
com.lenovo.anyshare.gps
com.sinoangel.kids.mode.Lenovo
com.wsandroid.suite
com.wantjoin.childmodel.launcher3
com.wantjoin.childmodel.settings
com.lenovo.ota
com.mediatek.mtklogger
com.android.galaxy4
com.android.noisefield
com.android.phasebeam
com.android.wallpaper.holospiral
com.android.dreams.phototable
com.android.fmradio
com.android.soundrecorder
com.android.gallery3d
com.mediatek.camera
com.android.calculator2
com.android.deskclock
com.android.facelock
com.android.contacts
com.android.calllogbackup
com.android.printspooler
com.android.bookmarkprovider
com.android.providers.partnerbookmarks
com.android.partnerbrowsercustomizations.example
com.mediatek.calendarimporter
com.android.vending
com.google.android.gsf.login
com.google.android.gsf
com.google.android.backuptransport
com.google.android.syncadapters.contacts
com.google.android.partnersetup
com.google.android.configupdater
```
