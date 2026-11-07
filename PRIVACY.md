# Privacy and permissions

E-Ink Pre-commitment Mode runs its commitment controller locally. The app does
not request Android's INTERNET permission and does not upload diagnostics,
selected app lists, contacts, or account information. No analytics or ad SDK is
included. Opening the website or a GitHub page uses the browser you choose.

Shizuku access lets the app read the hardware-switch events and relevant native
Max Ink state, run its bundled local controller, and request native transitions.
This is powerful Android shell access; enable it only if you trust the app. The
app does not request root, change firmware, or disable the system updater.

Notification permission is optional for status/restart reminders. Boot events
allow the app to check startup conditions. Reboot or controller loss ends current
enforcement; a saved enable preference does not prove a session survived.

Compatibility records stay on the phone and are bound to the build and native
controls tested. A firmware or relevant component change requires reassessment.
Diagnostics are shared only when you choose Preview/Share. The report omits the
device serial, raw process/boot tokens, unrelated settings and selected app names.
It may include the model, firmware fingerprint, native component versions and
test results. Review it before posting it publicly on GitHub.

Removing app data removes local app preferences and qualification records. Do not
uninstall an existing development build or replace a live controller as a routine
troubleshooting step. See docs/RELEASE.md for the separate signing migration.
