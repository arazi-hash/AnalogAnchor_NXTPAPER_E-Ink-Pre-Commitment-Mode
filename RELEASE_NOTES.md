# E-Ink Pre-commitment Mode 1.0.6-beta.1

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
