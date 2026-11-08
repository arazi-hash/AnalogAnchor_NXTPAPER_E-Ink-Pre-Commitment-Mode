# NXTPAPER compatibility

NXTPAPER_E-Ink-Pre-Commitment-Mode is designed for TCL NXTPAPER phones with
native Max Ink and requires compatibility testing. Confirm support with the
guided test, including the native Max Ink launcher and selected-app restrictions.

| Device/build | Evidence | Public-beta status |
| --- | --- | --- |
| TCL NXTPAPER 70 Pro T807D/Frida, Android 16 AMD9 | Beta.1 guided trial, switch recovery, fixed timers, expiry, full delayed Stop, sleep/wake, and English/Arabic startup guide on 7 November. See [version-specific evidence](../FINDINGS.md). | Maintainer-tested reference build. Local setup is required on each installation. |
| Other phones/builds with the recognized TCL slider protocol | Read-only eligibility plus owner-completed setup | Experimental on that exact phone/build only |
| Push/cycle keys, display-only devices or missing/ambiguous native controls | No reviewed interaction adapter | Unsupported/report only |

Support assessment has three outcomes: **maintainer tested**, **eligible for
experimental setup**, and **unsupported**. Shizuku availability, successful local
setup and a live controller are separate facts. An unfamiliar eligible phone can
run the guided test; passing it records local evidence for that exact phone/build
without promoting the whole model to this tested-device list.

Recorded acceptance covers one reference phone/build. The success rate across
other NXTPAPER models is unknown. A physical slider and native Max Ink make a
phone a candidate for a guided test. Passing depends on its exact firmware.

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

The 7 November beta.1 phone acceptance used a non-debuggable private release copy
whose APK entries matched the public build except for signing metadata. This
preserved the existing installation's data and signing identity. The public
beta.1 and beta.2 APKs share their permanent certificate for in-place updates.
Development and private acceptance copies require a separate migration. See
[the evidence and its limits](../FINDINGS.md) and
[the separate migration procedure](RELEASE.md).

Setup results are local and bound to the build, adapter/controller revision,
layout/mapping and relevant native versions. They do not automatically qualify
every phone of a marketing model. An event-node number changing after reboot is
not a different physical mapping. Firmware/control changes require reassessment;
lost privileges block operation until restored. Reboot does not recover an old
commitment.

## Tester experience in 1.0.6-beta.2

The release target is `1.0.6-beta.2` / code `8`. Consult [FINDINGS.md](../FINDINGS.md)
for the recorded handset checks for each version.

Setup messages explain the next action for missing Shizuku access, unrecognized
controls, incomplete tests and restoration problems. A basic compatibility
report is available even before Shizuku connects. It identifies checks that
could not run and labels cached observations so they can be interpreted correctly.
Only a completed guided test qualifies the exact phone/build for commitments.

### Send a successful or unsuccessful result

1. Open **Phone setup → Show → Preview compatibility report**.
2. Read the report and choose **Copy report**.
3. Choose **Open GitHub report form**, sign in if needed, and paste the report
   into the form. Review the completed form before submitting it.
4. Choose the result that matches your experience, including a successful test.
   You may add your market/carrier and whether the physical control is a slider,
   a push button or something else. Leave uncertain details as unknown.

The same form is available directly through [GitHub compatibility reports](https://github.com/arazi-hash/AnalogAnchor_NXTPAPER_E-Ink-Pre-Commitment-Mode/issues/new?template=compatibility.yml).
**Share** opens Android's share menu if you prefer to use another app. Opening
the GitHub form does not submit it or place your report in the browser URL.

Reports include the app version, model, Android version, firmware build, security
patch date, Shizuku access status and available compatibility/test observations.
Review them before sharing. Keep serials, account details, selected app lists,
private keys and raw device dumps out of public reports. See [privacy and permissions](../PRIVACY.md).

### Ask an AI assistant for help

Copy this prompt with your reviewed report into your assistant.

> Interpret this NXTPAPER compatibility report using the project's compatibility
> guide at https://github.com/arazi-hash/AnalogAnchor_NXTPAPER_E-Ink-Pre-Commitment-Mode/blob/codex/nxtpaper-demo/docs/COMPATIBILITY.md.
> Explain what was checked, what remains unknown and the next safe step. Separate
> Shizuku access problems from unrecognized phone controls and incomplete guided
> tests. Keep the guided qualification requirement and use read-only investigation
> for missing evidence. Ask me before any phone changes. Treat reports from other
> models or firmware builds as separate evidence.

Published specifications can identify phones worth investigating. New firmware
identifiers, event mappings and native controls require evidence from that exact
build. The tested AMD9 Linux switch codes are `592/593`, mapped to Android
commands `343/344`. Its current controller uses a direct Shizuku shell connection.
General reports about failures in other apps' Shizuku user services do not establish
this controller's result. See [recorded controls and phone trials](../FINDINGS.md).
