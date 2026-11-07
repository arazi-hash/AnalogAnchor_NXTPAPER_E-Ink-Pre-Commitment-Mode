# NXTPAPER compatibility

Designed for compatible TCL NXTPAPER phones with native Max Ink; compatibility
testing is required. Installing the APK or having a NXTPAPER key alone does not
establish support. A display filter or Ink Paper theme is not the native Max Ink
launcher and selected-app restrictions.

| Device/build | Evidence | Public-beta status |
| --- | --- | --- |
| TCL NXTPAPER 70 Pro T807D/Frida, Android 16 AMD9 | Recorded 7 November guided trial, switch recovery, fixed timers, expiry, full delayed Stop, sleep/wake, and English/Arabic startup guide. See FINDINGS.md. | Maintainer-tested reference build. Local setup is required on each installation. |
| Other phones/builds with the recognized TCL slider protocol | Read-only eligibility plus owner-completed setup | Experimental on that exact phone/build only |
| Push/cycle keys, display-only devices or missing/ambiguous native controls | No reviewed interaction adapter | Unsupported/report only |

Support assessment has three outcomes: **maintainer tested**, **eligible for
experimental setup**, and **unsupported**. Shizuku availability, successful local
setup and a live controller are separate facts. An unfamiliar eligible phone can
run the guided test; passing it records local evidence for that exact phone/build
without promoting the whole model to this tested-device list.

The experimental path requires the TCL slider feature, native state and preset
semantics, readable raw events, the actual active layout and distinct runtime
TSWT symbolic key mappings. Unknown builds do not inherit numeric `343/344` guesses.
The owner first demonstrates physical Normal → Ink → Normal; only then can the
supervised software trial begin. Commitments require final settled Normal and
owner confirmation of the native experience.

On the exact reviewed AMD9 build, TCL resolves TSWT_ON/OFF to `343/344` while its
reverse-name table reports `KEYCODE_FP_LIFT_UP/KEYCODE_FP_LONGPRESS`. This precise
alias pair is treated as part of the reviewed AMD9 mapping only when model
`T807D`, device `Frida`, Android `16`, SDK `36` and the exact fingerprint all match:

```text
TCL/T807D_EEA/Frida:16/BP2A.250605.031.A3/AMD9:user/release-keys
```

Unfamiliar builds with these aliases remain unsupported until separately reviewed; there is no
general numeric fallback for them.

The founder's phone acceptance used a non-debuggable private release copy whose
APK entries matched the public build except for signing metadata. This preserved
the existing installation's data and signing identity; it does not claim the new
permanent public signer was installed on that phone. See
[the evidence and its limits](../FINDINGS.md) and
[the separate migration procedure](RELEASE.md).

Setup results are local and bound to the build, adapter/controller revision,
layout/mapping and relevant native versions. They do not automatically qualify
every phone of a marketing model. An event-node number changing after reboot is
not a different physical mapping. Firmware/control changes require reassessment;
lost privileges block operation until restored. Reboot does not recover an old
commitment.

Use the app's visible setup and report controls. Preview reports before sharing
them through the GitHub compatibility template. Do not post serials, account
information, selected app lists, private keys or full raw dumps. No automatic
upload or executable profile download is part of compatibility setup.
