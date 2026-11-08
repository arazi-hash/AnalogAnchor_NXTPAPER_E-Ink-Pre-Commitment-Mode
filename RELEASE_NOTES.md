# NXTPAPER_E-Ink-Pre-Commitment-Mode 1.0.6-beta.3

Version code `9`. Git tag `v1.0.6-beta.3`.

The website button now opens the landing page in the language selected in the
app, even when the browser remembers another language.

Public beta.1 and beta.2 installations can update in place using the same
permanent certificate. [Release and migration instructions](docs/RELEASE.md)

## Published 1.0.6-beta.2

Version code `8`. Git tag `v1.0.6-beta.2`.

- Clearer English and Arabic setup explanations with a next action for access,
  phone-control and incomplete-test problems.
- A basic compatibility report even when Shizuku cannot connect. Reports include
  firmware build and security patch date, label cached observations and identify
  checks that could not run.
- **Copy report**, **Share** and **Open GitHub report form** actions in the report
  preview. Opening the form lets you paste, review and submit the report yourself.
- The Android app uses the display name `NXTPAPER_E-Ink-Pre-Commitment-Mode`.

To report a successful test or a problem, open **Phone setup → Show → Preview
compatibility report**, review the text, choose **Copy report**, then **Open GitHub
report form**. Add your result and optional market/carrier or physical-control
details. Keep uncertain details as unknown. [Open the compatibility form](https://github.com/arazi-hash/AnalogAnchor_NXTPAPER_E-Ink-Pre-Commitment-Mode/issues/new?template=compatibility.yml)

The reference phone remains **TCL NXTPAPER 70 Pro T807D/Frida, Android 16 AMD9**.
Successful guided setup on the exact phone/build remains required before
commitments. [Compatibility and troubleshooting](docs/COMPATIBILITY.md) · [Recorded handset checks](FINDINGS.md)

The public beta.1 APK can update to beta.2 in place using the same permanent
certificate. Older development and private test copies use a different certificate.
If Android shows **Update incompatible**, check which copy is installed and follow
the coordinated migration procedure to protect app data. [Release and migration instructions](docs/RELEASE.md)

## Published 1.0.6-beta.1

Just like people hunt for old Pixels for unlimited storage, NXTPAPER phones hide the ultimate digital minimalism secret. This app unlocks the hardware switch for enforced Max Ink pre-commitment and eye-strain-free focus.

Experimental beta for compatible TCL NXTPAPER phones with native Max Ink.
Shizuku and successful on-device setup are required before commitments.

- A startup guide and compact, expandable Phone setup row. **Later** reminds
  you on the next visit, while **Got it** remembers your acknowledgement for
  the current setup.
- Guided compatibility testing with physical switch proof, owner confirmation,
  and supervised native entry, exit and restoration.
- Eligible unfamiliar phones/builds can attempt experimental setup when the
  recognized native slider protocol is present. Push/cycle buttons require a
  separate reviewed adapter.
- Local qualification bound to the tested phone/build and native controls;
  reassessment after relevant updates.
- Previewable reports shared only when the owner chooses.
- Existing commitment durations, fixed timers, delayed Stop/Continue and extended
  reading behavior retained.
- Apache-2.0 source and a permanent public release signing identity.

Native controls and commitment behavior were tested on **TCL NXTPAPER 70 Pro
T807D/Frida, Android 16 AMD9**. Other eligible models/builds remain experimental;
a NXTPAPER button or successful installation does not guarantee support.
Display-only modes are unsupported.

Reboot, lost privileges or controller loss ends enforcement; old commitments are
not recovered. Native transitions take time, so wait for confirmed Normal after
the Stop countdown ends.

This public release uses a new permanent signing identity. Existing development
installations need a separately planned migration rather than an automatic
uninstall or data clear. See [release and migration instructions](docs/RELEASE.md).
