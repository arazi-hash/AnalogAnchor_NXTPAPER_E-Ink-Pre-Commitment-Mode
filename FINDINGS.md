# Verified NXTPAPER controls

## Beta.2 handset checks — 8 November 2026

The 70 Pro T807D / Frida on Android 16 AMD9 completed a fresh guided test on a
private `1.0.6-beta.2` / code `8` acceptance copy. Android had rejected the
public-signed APK because the phone retained a package record for the earlier
private signer. The acceptance copy installed in the owner profile with the
historical signer and preserved the retained clone-profile data. The two public
beta builds use the same permanent certificate.

- The owner removed the magnetic holder and completed physical Normal → Max Ink
  → Normal. The owner confirmed the native reading screen and app restrictions.
- Software restored Normal with the switch still in Ink. After the owner moved
  the switch to Normal, software entry and restoration succeeded. The owner
  confirmed Normal was usable. Setup reached `QUALIFIED`, with the guard `STOPPED`.
- English and Arabic reports showed the qualified result. The Android share
  chooser and GitHub issue-template screen opened on request. Arabic report
  controls were visible at enlarged font size, then the original locale and font
  size were restored.
- Revoking only this app's Shizuku authorization left the basic report available
  with permission required and checks marked unperformed. Restoring permission
  returned the app to Ready.

These checks cover the tester experience and guided setup on the reference phone.
The controller, guided-test script and adapter bytes match beta.1. The full
commitment timing trials below were recorded on beta.1. Results from other phone
models and firmware are still unmeasured.

The final public APK with the display name `NXTPAPER_E-Ink-Pre-Commitment-Mode`
has SHA256 `a3c291cc62c7eabc9655b836d3150a0b8bb3659c695339d253a6d4fe4f465a81`.
Its matching private copy updated the owner profile in place. Qualification
remained Ready. The exact title and qualified report were confirmed in English
and Arabic, and the four store captures were reviewed and stripped of system
bars. Final Android verification passed 56 tests and release lint had zero
errors with 19 existing warnings.

## Public beta controller acceptance — 7 November 2026, 1.0.6-beta.1 / code 7

The TCL NXTPAPER 70 Pro **T807D / Frida, Android 16 AMD9** is now the physically
tested reference for the public beta controller and guided qualification flow.
Other phones/builds remain experimental candidates only when the reviewed
persistent ON/OFF slider protocol is recognized. A NXTPAPER button alone does not
establish support. See [the compatibility list](docs/COMPATIBILITY.md).

### Phone results actually recorded

| Check | Recorded result |
| --- | --- |
| Guided physical proof | Genuine Normal → native Max Ink → Normal movements were observed through raw switch events. The owner confirmed the full native reading environment and expected app restrictions. |
| Guided software trial | Software exit restored Normal with the physical switch still in Ink. With the switch subsequently in Normal, automatic Max Ink entry and Normal restoration passed. Final settled Normal and the owner's confirmation were required before qualification. |
| Activity closure/reopening | Native Max Ink hid the app. Reopening it after returning to Normal recovered the independent trial's progress. |
| Unsuccessful setup | A timed-out attempt remained incomplete and did not unlock commitments. A later complete trial qualified the exact phone/build. |
| Default commitment | The confirmed session ran for exactly 300 seconds between its original start and deadline. Genuine physical early exit triggered native Max Ink recovery in about 16 seconds without moving that deadline. |
| Ordinary expiry | With the physical switch in Ink, expiry entered extended reading. A later physical move to Normal restored Normal and it stayed there. |
| Optional duration | The two-hour preset was selected in the app and became a 7,200-second session. Consuming it reset the next-session choice to 300 seconds. The two-hour session was ended through the Stop test below; sustained two-hour use was not tested. |
| Stop and Continue | Repeated Stop requests retained the same exit deadline. Continue cancelled the exit request without extending the original commitment. These active-session transactions used the real controller protocol from the PC, rather than the on-screen buttons while native Max Ink restricted the app. |
| Full delayed Stop | A fresh Stop request on the two-hour session set a deadline exactly 300 seconds later. Restoration began on the next controller tick after that deadline; Normal settled about eight seconds after the native exit command, with the physical switch still in Ink. |
| Sleep/wake | A brief screen-off/wake trial during the pending Stop preserved both the commitment and exit deadlines; the remaining time decreased. This is not a sustained deep-sleep or long-duration battery test. |

The owner confirmed that Normal was usable and returned the physical switch to
Normal. The known test controller was stopped and the app's enable preference was
turned off. Stock firmware, personal app data and TCL's native selected-app
configuration were preserved. No OTA, root/reset/flashing or updater-package
restriction was performed.

### Signing and artifact evidence boundary

Phone trials used a **non-debuggable private release acceptance copy** signed with
the installation's historical certificate, preserving its data. For the tested
build, every APK ZIP entry except signature metadata was compared byte-for-byte
with the corresponding public release APK. The public release uses the new
permanent certificate
`434a6ec4f84e1720f8f05e826fe2ccc0d148c47df73e561eac02d1b6f0845202`.
That permanent signing identity was not installed on the founder's phone; its
migration remains separate. The private acceptance copy and recovery material
must never be public release assets. See [release/signing instructions](docs/RELEASE.md).

The exact reviewed AMD9 identity resolves TSWT keys to `343/344`, while its reverse
name table reports `KEYCODE_FP_LIFT_UP/KEYCODE_FP_LONGPRESS`. Only that precise
pair on the exact reviewed identity is accepted as a vendor alias. Unfamiliar
builds cannot inherit this exception or guessed numeric keys.

### Final beta verification

- Full Python discovery: **276 passed**, zero failures/skips, **321.433 seconds**.
- Android unit suite: **43 passed**. Release lint reported **zero errors and 19
  warnings**. Debug and release APK builds completed successfully.
- The public APK is **5,079,619 bytes**, SHA256
  `ab92945d1728891060d7a753f2d7ac448ca0ead5313cf3dd4540f2d5e792c4ac`.
  The APK is non-debuggable, reports version `1.0.6-beta.1` / code `7`, and
  bundles the verified controller and registry bytes. The phone UI acceptance
  copy is identical apart from signing metadata, SHA256
  `96db44920c2386930a990bc521a8e3011f2e356f25340e16292d044dd7c76dbb`.
- A read-only execution in the actual Android shell caught and corrected an awk
  parser difference; the schema2 preflight then returned
  `VERIFIED:t807d-eea-amd9` with empty stderr.
- Phone UI checks passed for the English and Arabic startup guide, next-visit
  reminder after Later, suppression after Got it, manual reopening, Show/Hide,
  configuration recreation, and disabled Start during incomplete setup. The
  owner's prior qualification and preferences were restored. Publication images
  are real phone captures with the notification bar cropped out.
- Setup now preserves Cancel requests made during startup and attempts bounded
  restoration after an uncertain command result. These failure paths have host
  regression coverage. The physical timing tests above used the same commitment
  controller before these setup-only recovery refinements.

Private evidence is under ignored `logs/public-beta-device-2026-11-07/`, including
the default-session and Stop watches, Stop/Continue transactions and sleep/wake
comparison. Raw captures and app selections are not public diagnostics. The
[active task](HANDOFF/tasks/public-beta-2026-11-05.md) and
[latest checkpoint](HANDOFF/LATEST.md) record publication status separately.

No other phone model, sustained 2/4/6/12-hour run, real OTA, reboot recovery,
USB-loss behavior or forced active-controller crash was physically accepted in
this beta trial. Missing privileges, stale qualification, ambiguous controls,
Cancel and unknown-controller preservation also have host regression coverage;
those mocked cases are not additional handset trials.

The dated sections below are preserved historical snapshots. Their old test
counts, artifact identities and statements about installation apply to those
specific updates, not to the beta evidence above.

## Firmware resilience — 28 October 2026, local 1.0.5 / code 6

The local successor adds one strict reviewed data-only AMD9 profile shared with PC tools and bundled in the Android APK. Unknown firmware remains unverified; changing/removing a fingerprint is not qualification. The diagnostic registry can compare additional profiles, but the current Android build and PC control adapter select the single AMD9 profile. A new native protocol requires reviewed adapter code/evidence.

`python nxtpaper_diag.py compatibility --json` prints identity, per-capability checks, recovery action, package versions, update-setting limits, and separate controller observations. It changes no phone state, saves no files, and omits serials/raw settings/PID/boot tokens/raw errors. The independent on-demand EN/AR app diagnosis streams source/profile in memory without deployment, preference/language writes or ordinary status reconciliation. Reports are observations, not command authorization or physical acceptance.

Fresh gates cover PC entry/restoration, shell entry/repair/restoration, and app mode tests. They require the original reviewed profile, privilege, input/keylayout, valid preset and fresh native state. A changing snapshot cannot authorize stale commands; restoration has no bypass. Tests refuse controller evidence and acknowledge dispatch only. Denied process inspection cannot authorize controller replacement; valid previous-boot tokens remain recognizable as stale. Current timers, delayed Stop/cancellation and ten-field status protocol are preserved.

### Verification actually completed

- Final Python discovery: **217 tests passed**, no failures/errors/skips, **168.543 seconds**: 99 PC/profile/diagnostic/demo, 110 controller/compatibility shell, 8 executing the Android runtime's embedded presence shell against fake `/proc`. Android commands are mocked in host regressions.
- **25 Android unit tests passed**, zero failures/errors/skips: 7 compatibility, 6 exit-policy, 12 status. **242 local tests total.**
- Integrated `testDebugUnitTest lintDebug assembleDebug --max-workers=1 --no-parallel --console=plain`: **BUILD SUCCESSFUL in 2m 47s**. Lint: **0 errors / 14 warnings**. Dependencies unchanged.
- Final APK controller/profile assets exactly match source. Shell syntax, new EN/AR keys/format arguments, layout XML, documentation links/UTF-8/LF and whitespace checks passed. Existing layout CRLF-normalization notice is informational.
- Earlier failing test setups (frozen clock, liveness-observation assertions and a short host timeout during overlapping Gradle work) were corrected before the final full pass. Read-only phone execution caught Android awk requiring parentheses around a printf ternary; corrected and rechecked before packaging.

### Artifact identity

- Deliverable: `dist/E-Ink-Precommitment-Mode-1.0.5-firmware-resilience.apk`, **6,067,137 bytes**, SHA256 `607414d93b14e5326a80c5d45cfd319bae9227c0b2c97a300648b049647cb25d`. Sidecar alongside; older APKs preserved.
- Manifest: `com.analoganchor.nxtpaperguard`, **1.0.5 / code 6**, min SDK 26 / target SDK 36. APKv2 verifies with historical debug certificate SHA256 `bb57ddf958f90324e214020a7f65e5aba9f4e3dd7ba1ebd6454868af8cb41d2e`.
- Controller: **57,753 bytes LF**, SHA256 `ce53dfb10c91beddabfbd8c4101db690ff9bfe8ab1ddb939b59378ca11721834`.
- Profile: **803 bytes LF**, SHA256 `c0fa4228ebb43f16e554b67e8b86188991754be2231e6d83363ea2cffa529688`.
- New bundle identity: SHA256(controller+NUL+profile), marker `1.0.5:dd8f0856c15a4b6c24d4213203b1b0c8c383d090077bcc52572bd5d6b2fd0833`. A marker alone still proves neither bytes nor live behavior.

### Read-only phone evidence and remaining acceptance

Final PC and source-via-stdin compatibility checks matched historical AMD9 structure; shell returned `VERIFIED:t807d-eea-amd9`, empty stderr. The Android embedded presence check separately identified the existing controller. The older live 1.0.3 controller still reported IDLE when sampled, hash `ef82dc007dda64392733d2cf28cd3bc9782065738ee554c08d4c20da0dad3553`. Earlier read-only inspection verified installed 1.0.4 / code 5 and its asset; this supersedes the preceding task's historical not-installed statement only for package presence, not behavioral acceptance.

**No new installation, controller stop/redeployment, native key injection, updater restriction, reboot, OTA, reset/root/flashing, commit or push occurred.** The 1.0.5 APK, diagnostic-dialog handset layout, real switch/recovery, delayed Stop, long commitments and future firmware still require separate acceptance. Native package versions are comparison evidence, not a complete pinned system image. Reboot/controller loss still ends enforcement.

The phone's automatic-update flag was 1 and exact updater `com.tcl.fota.system` enabled. No complete update block or exact-model downgrade is established. See [seven approaches](HANDOFF/tasks/firmware-resilience-plan-2026-10-28.md), [recovery guide](compatibility/RECOVERY.md), [Antigravity prompt](HANDOFF/tasks/antigravity-firmware-resilience-prompt.md), and [task/checkpoint](HANDOFF/tasks/firmware-resilience-2026-10-28.md). Private proof is under ignored `logs/firmware-*-2026-10-28.json`; binaries/signing material stay outside Git.

## Delayed Emergency Stop — 28 October 2026, 1.0.4 / code 5

This local update changes the standalone Shizuku app's normal Emergency Stop. During STARTING or COMMITTED, a request starts a 300-second uptime deadline, capped by the original commitment deadline once known. All five duration presets use this rule. The controller keeps enforcing Max Ink while waiting; a pending exit reaching either deadline restores Normal even with the physical switch still in Ink. Without an exit request, ordinary expiry continues to allow extended reading as before.

Repeated requests preserve the existing exit deadline. Continue commitment removes only the exit request; it never renews the commitment. Cancellation at or after the exit deadline cannot undo restoration. Idle monitoring stops without changing native mode; completed reading begins Normal restoration immediately. Countdown zero begins restoration, and only a settled native snapshot confirms Normal.

The controller exposes short `request-stop` / `cancel-stop` transactions bound to its PID/start-time/boot identity. Its status appends `exitDeadline:exitRemaining` after the existing eight fields. The Android parser accepts absent legacy fields as zero and rejects malformed present fields. The app durably disables future automatic restart before requesting exit; the existing daemon keeps enforcing. A narrowly scoped cancellation record recovers an interrupted preference update only for the same daemon and request. Command timeouts never delete live controller state. Updating a mismatched live controller no longer terminates it automatically.

The compact EN/AR UI shows the exit countdown, original commitment remaining, and Continue commitment. The early-exit rule is visible before entry and in contextual help. New Start, duration, and mode-test controls wait for an initial result; native mode tests additionally require actual STOPPED status.

### Local verification

- **168 unique Python tests passed**, no skips: 73 PC/control/diagnostic tests in 1.086 seconds; 93 shell tests in 312.721 seconds plus two later timing regressions in 13.596 seconds. The 95 shell tests execute canonical source with fake Android commands, without operating a phone.
- New controller cases cover all five presets, 299/300-second boundaries, earlier natural expiry, STARTING, repeated requests, cancellation/re-request, physical recovery preserving both deadlines, bilingual notifications, concurrent/stale/boot-bound mailboxes, short acknowledgements/timeouts, idle/completed stopping, fresh uptime after a slow native operation, and a sleep/missed-tick jump beyond the exit deadline. Existing bounded restoration tests remain included.
- EN/AR resource keys and format arguments match; layout XML parses. Independent source review found and resolved stale-clock cancellation and ambiguous restoration-acknowledgement edges.
- **18 Android unit tests passed**, no failures/errors/skips: 12 status and six cancellation-policy tests. Total: **186 local tests passed**.
- Final `testDebugUnitTest lintDebug assembleDebug --max-workers=1 --no-parallel --console=plain`: **BUILD SUCCESSFUL in 32 seconds**, **zero lint errors and 14 warnings**. An earlier integrated rebuild passed in 3 minutes 14 seconds before removing two unused labels and documenting checked synchronous preference writes. The initial overlapping-source attempt failed when a new helper/test was added after app compilation; both later integrated runs passed. Dependency/tooling, backup/icon, resource and Kotlin-style warnings remain; dependencies were not upgraded.
- Local deliverable: `dist/E-Ink-Precommitment-Mode-1.0.4-delayed-stop.apk`, **7,139,616 bytes**, SHA-256 `9b83a4a25b0a8bda89f5aecc434ce9ce90b858b2e7411da1536dfd929ea246d4`. Manifest verified: package `com.analoganchor.nxtpaperguard`, **1.0.4 / code 5**, min SDK 26, target SDK 36.
- The packaged controller exactly matches canonical source: **48,439 bytes, LF**, SHA-256 `7765bcab3e277a669752f538d0b9ae4d270e552a4c44223e4a743f3e65b023d3`. APKv2 signature verifies; certificate SHA-256 `bb57ddf958f90324e214020a7f65e5aba9f4e3dd7ba1ebd6454868af8cb41d2e`, matching the historical 1.0.3 record. This is artifact evidence, not a verified installed-phone update.
- Hash sidecar is beside the APK; ignored local proof is in `logs/delayed-exit-verification-2026-10-28.json`. Final source whitespace checks passed. No new handset screenshot, installation or acceptance is implied by local checks.

### Device acceptance boundary

No installation or handset operation was performed for this update. Five-minute real-time delayed exit, pending physical-switch recovery, cancellation, app closure/reopening, sleep/wake, profile-10 behavior, EN/AR layout and enlarged text remain unverified on the phone. Old 1.0.3 device evidence below does not verify the new behavior. Reboot or controller/Shizuku loss still ends enforcement; active sessions and pending exits are not restored across those losses. The original PC demonstration's operator override is unchanged.

The task started clean on `codex/nxtpaper-demo` at `553ec2a`. Changes remain local; no staging, commit, push, installation or publication was performed. The new deliverable uses `dist/E-Ink-Precommitment-Mode-1.0.4-delayed-stop.apk` to preserve an older local APK named 1.0.4 that internally reports 1.0.3 / code 4. See HANDOFF/LATEST.md for the latest saved checkpoint.

Investigation dates: 3–4 October 2026. These findings apply to the tested TCL NXTPAPER 70 Pro stock handset. Historical PC trials and older APKs are identified separately.

## Final standalone APK: 1.0.3 / code 4

The Arabic and English UI uses the exact name **E-Ink Pre-commitment Mode**. Five minutes is the default; 2, 4, 6, and 12 hours are one-session presets. Entry consumes the selection, freezes the active duration, and returns the next session to 300 seconds. Native Max Ink and settled theme/animation flags must be confirmed before the countdown begins. Early-exit repairs preserve the original deadline. At expiry, physical Ink continues reading until the user moves to Normal. Active-session Stop cancels and restores Normal; idle Stop only ends monitoring. Recovery takes native transition time, with measured physical recoveries of **15–19 seconds**.

### Verified fixes

- The first fresh physical ON is accepted without a preceding OFF or three-move calibration. The old 1.0.2 controller ignored sequence-1 ON events across five observed starts.
- Decompiled TCL `PhoneWindowManager` and SystemUI confirm `TSWT_state=-1` is a legitimate boot sentinel. It is now accepted as unknown rather than failing after three reads. Unknown native state causes no mode commands or physical-position inference; active entry/recovery/restoration retain 45-second bounds.
- Island profile 10's local resolver lacks native mode fields. UI snapshots now come from the same Shizuku context as the controller; failed reads display Unknown while retaining the controller phase.
- Duration locking now uses atomic per-caller PID/start-time/boot claim directories, with cleanup limited to owned claims. Orphan/empty locks cannot block duration requests indefinitely. Earlier setter processes were confirmed absent before deployment. Stop reloads the five-minute default when the daemon exits.

### Final build, tests, and artifact

- **153 Python tests passed**, no failures or skips: 80 shell-controller regressions plus 73 original PC/diagnostic tests, in **106.601 seconds**.
- **Eight Android unit tests passed**, no failures: **161 passing tests total**.
- Combined `testDebugUnitTest lintDebug assembleDebug --max-workers=1 --no-parallel`: **BUILD SUCCESSFUL** in **1 minute 31 seconds**. Lint: **zero errors, 14 warnings**. Unrelated lint warnings and the earlier SDK XML tooling warning remain recorded; dependencies were not upgraded.
- Installed deliverable: `dist/E-Ink-Precommitment-Mode-1.0.3.apk`, **7,118,216 bytes**, SHA-256 `6d39ea18a60a52db53f9ca26e0cc9056daf5ddccf2daadb98af2fa9d1ae8a4ec`.
- Canonical shell source, embedded APK asset, and installed live controller are byte-for-byte equal, SHA-256 `31168cd6877373bf44cf2deef2109767dea224cad0e6b5ed19429cd4813a89b1` (37,837 bytes, LF). Equality was verified directly rather than trusting a version marker.
- APK debug signature verified. Certificate SHA-256: `bb57ddf958f90324e214020a7f65e5aba9f4e3dd7ba1ebd6454868af8cb41d2e`.

### Final UI verification

On the final installed controller in Island profile 10, all duration selections were acknowledged: **7200, 14400, 21600, 43200, and 300 seconds**. Fresh UI selected highlights matched; the default was restored to 300 seconds. Evidence is in ignored `logs/final-timer-choices.json`.

Island now accurately shows physical Ink / Max Ink and physical Normal / Normal while its local secure resolver still lacks those fields. Arabic/English switching, the exact English brand in Arabic, compact timer controls, and the bottom language button were verified. Screenshots are retained under ignored `captures/final-active-en.png`, `captures/final-active-ar.png`, and `captures/final-ready-ar.png`. Earlier Arabic RTL checks at **200% font size** kept Stop, timers, and language reachable across two scroll positions; the original font scale **0.85** was restored.

An earlier fast tap occurred before the preceding selection acknowledgment. The static status-polling gate was corrected; QA waited for acknowledgment between taps. That observation does not establish status polling as its cause.

### Physical entry, expiry, and restoration on the final controller

The final controller accepted its **first-ever raw ON event, sequence 1**, at device uptime **15072**, with no earlier OFF. It confirmed `COMMITTED` at **15081**, establishing deadline **15381**: exactly **300 seconds**.

At **15381** it entered `EXTENDED` with zero observed delay, physical ON, and fully settled native Ink. Read-only assertions retained the original deadline and next duration 300 throughout. A physical OFF, sequence 2, at **15471** entered `RESTORING` at **15472**, reached fully Normal at **15477**, and acknowledged `IDLE` at **15479**. The user confirmed that Normal remained after 20 seconds. This completed the full default five-minute trial and post-expiry physical restoration. Evidence is in ignored `logs/default-five-minute-expiry.jsonl`.

The last verified handset state at uptime **16260** was **IDLE / physical OFF / next duration 300 / native Normal**. The guard remains enabled and ready for the next physical Ink event.

### Recovery and active Stop on the preceding controller

After removing the magnetic case and holder and using direct USB, the preceding boot-state-corrected controller (`d09b9110bd80c01081e2e8aa66c86605ebf0e402d2d619ed11c7052f49be2627`) accepted physical ON sequence 5 at **13864**, entered `STARTING` at **13865** with **7200 seconds**, observed settled Ink at **13871**, and confirmed `COMMITTED` at **13874**, deadline **21074**, next duration **300**. This verified two-hour selection consumption/reset; the full two-hour period was not observed.

**Five consecutive real physical early OFF recoveries passed**. OFF sequences 6, 8, 10, 12, and 14 recovered in **15, 17, 17, 19, and 18 seconds**. Every recovery preserved session start **13874** and deadline **21074**. Private summary: `logs/physical-recovery-summary.json`.

Separately, **three framework-injected native exits using key 344** fully recovered in **15.85, 14.77, and 15.85 seconds**, preserving deadline 21074. Raw physical OFF remained sequence 14. These are three native-exit trials, not additional physical-slider trials. Evidence: `logs/native-recovery-trials.jsonl`. No raw events were injected; a `sendevent` attempt was denied before changing device state and is not counted.

Active Stop through the profile-10 app also passed: STOP recorded at **14687**, key 344 at **14688**, fully Normal at **14695**, and acknowledgment at **14697**. The daemon stopped, session start/deadline became zero, next duration became 300, and native mode/transition flags were all zero. Those recovery and Stop trials used the preceding controller; the final controller changed duration locking and completed the separate five-minute trial above.

### Magnetic accessories and remaining acceptance

The user confirmed that both the case and holder were magnetic. Raw physical detection and controlled entry were observed after their removal. TCL explains that magnets near the NXTPAPER key can interfere with it and recommends removing magnetic cases. Remove magnetic cases and holders before switch testing or pairing troubleshooting. [TCL NXTPAPER key guidance](https://www.tcl.com/global/en/support-mobile/faq/q1770346246101540)

**Twenty consecutive physical recoveries are not yet validated**; only five consecutive physical recoveries were observed on the preceding controller. Full 2/4/6/12-hour operation, screen sleep/wake, active crashes, reboot/Shizuku recovery, calling, and USB-disconnection behavior still need recorded trials. Automated tests and injected native exits do not establish those outcomes. The final five-minute expiry/restoration and current UI results do not imply sustained reliability under all conditions.

### Baseline and Git readiness

Before this update, Python had **110 passing tests**, Android unit tests were `NO-SOURCE`, and lint failed with **5 errors and 21 warnings** from literal `100% Safe` formatting. The 1.0.2 APK assembled separately. The SDK tool also warned that it understood XML through version 3 while encountering version 4. These baseline facts are distinct from the final successful results above.

Current branch: `codex/nxtpaper-demo`. Existing HEAD: **`2eba81f`**, subject **`01`**. Existing `origin`: [AnalogAnchor_NXTPAPER_E-Ink-Pre-Commitment-Mode](https://github.com/anchorminimalism-del/AnalogAnchor_NXTPAPER_E-Ink-Pre-Commitment-Mode). The latest update consists of **ten tracked modified files**, uncommitted and ready for review. The agents did not stage, commit, or push.

Generated builds/APKs, SDK paths, signing keys, private logs, `captures/`, and `current_phone_screen*.png` are ignored. Required branding PNGs, wrapper, Android source, shell, scripts, and tests are tracked. Both PCs need JDK 17, SDK platform 36/build-tools 36.0.0, and their own ignored `local.properties`. Updating the same installed app from both PCs requires the same private signing key kept outside GitHub. Review and commit the source changes, then push them to the existing repository so the other PC can pull them.


## Supported handset

| Property | Verified value |
| --- | --- |
| Product/model | TCL NXTPAPER 70 Pro / `T807D` |
| Android / SDK | Android 16 / SDK 36 |
| Build fingerprint | `TCL/T807D_EEA/Frida:16/BP2A.250605.031.A3/AMD9:user/release-keys` |
| Existing switch preset | `tct_nxtpaper_mode_select=3` |
| Existing immediate-switch configuration | `tct_nxtpaper_switch_imm=1` |

The program reads the preset and immediate-switch configuration on every normal state read. It does not set them or alter the selected Max Ink apps. A configuration change causes enforcement to stop and normal restoration to be attempted.

## Native control and state proof

Ordinary ADB framework input injection reached the phone's existing native switch handler:

| Verified operation | Framework key | Observed result |
| --- | --- | --- |
| Enter native Max Ink | `343` (`TSWT_ON`) | Native Max Ink launcher, theme, and restrictions activated |
| Restore normal | `344` (`TSWT_OFF`) | Normal launcher and native state restored |
| Enter after the user physically moved the slider OFF | `343` | Full native Max Ink activated with the slider still OFF |
| Restore after the user physically moved the slider ON | `344` | Normal mode restored with the slider still ON |

These controls follow `PhoneWindowManager` → `TSWT_state` observer → TCL SystemUI, launcher, and Smart Manager handling. There were no direct settings writes, installed helper apps, rooting, flashing, or factory resets.

Native Max Ink is identified by `nxtpaper_ink_style_state=2` and `nxtpaper_book_style_state=1`. Normal mode has both values `0`. A transition is fully settled only when `nxtpaper_is_applying_theme=0` and `nxtpaper_animation_state=0`; a changed mode value by itself is not proof that the native transition finished.

Read-only inspection verified the physical-switch mapping:

- Linux `KEY_BRIGHTNESS_MIN` / `592` maps to framework `TSWT_ON` / `343`.
- Linux `KEY_BRIGHTNESS_MAX` / `593` maps to framework `TSWT_OFF` / `344`.
- The physical input device is named `tswt`. Its `/dev/input/eventN` number can change between boots, so the monitor discovers the node from its name and capabilities.

The controller listens to raw physical input separately from injected framework keys. Its own mode commands therefore do not count as another physical slider movement or renew the commitment timer.

## Historical USB-connected PC controller validation (3 October)

A corrected **60-second trial passed** on the connected handset. The physical slider stayed ON during an ADB-injected native exit (`344`), controller re-entry, and expiry restoration. Times below are seconds after native Max Ink was confirmed and the commitment began:

| Event | Elapsed time |
| --- | ---: |
| Native Max Ink confirmed; fixed deadline established | 0.00 s |
| Injected native exit while physical slider remained ON | 27.20 s |
| Controller requested native re-entry (`343`) | 27.42 s |
| Native Max Ink fully settled again | 40.02 s |
| Original commitment deadline | 60.00 s |
| Controller requested normal restoration (`344`) | 60.11 s |
| Normal mode fully settled with slider still ON | 65.79 s |

The original deadline remained unchanged throughout. Recovery took **12.60 seconds** from the controller's re-entry request, or about **13 seconds** from the injected exit. The expiry command was approximately **0.11 seconds** after the deadline; full normal restoration then took **5.68 seconds**. The controller reached its wait-for-physical-OFF state and exited successfully.

An initial 30-second trial exposed an OEM transition-state timing issue and failed. The corrected controller requires the same settled wrong-mode state to persist for two seconds before applying an OFF/ON repair, avoiding a transient intermediate state during a native transition. The corrected 60-second trial above passed after that fix. At that point the host suite had **73 passing tests**, including regression coverage for a stale normal-state snapshot combined with a fresh physical-ON event at expiry, and Ctrl+C during monitor cleanup.

An **idle input-monitor failure trial** on an earlier controller revision deliberately terminated only its exact child ADB `getevent` process while the controller was Ready and the phone was normal. The controller detected the ended input stream, attempted normal restoration with `344`, confirmed normal mode, recorded the failure, and exited with status `2`. No commitment session began. This is narrower than a controller crash or USB loss during active Max Ink.

A completed 300-second trial of the original PC controller is not recorded here. Its full five-minute result and physical early-exit checks remain **pending**. The final standalone APK's completed five-minute trial is recorded above.

Evidence is retained locally under the ignored `logs` directory. The injected-exit and idle-failure tests do not establish repeated physical-slider behavior, screen-sleep behavior, calling, active-session crashes, or USB-disconnection recovery.

## Historical PC demonstration status and limits

- All four native entry/restore experiments above succeeded on the tested handset.
- Standalone native transitions took roughly **5–7 seconds** to fully settle. Inspection found the native framework's first animation-completion check uses **4,000 ms**. Full early-exit recovery took about **13 seconds** in the controller trial; the proposed two-second recovery target is **not met**.
- Normal-mode visibility is possible during early-exit recovery; the trial measured full native state settling rather than promising an immediate screen change.
- The PC controller implements a default 300-second deadline, early-exit re-entry without renewing that deadline, expiry restoration, physical-OFF rearming, and an operator stop. Its full five-minute live trial is **pending**; this is separate from the verified final standalone APK trial.
- Screen sleep, repeated slider movements, normal calling, active-session process crashes, and USB-disconnection recovery still require recorded live validation. Automated tests cover software behavior and do not establish these handset outcomes.
- USB disconnection, PC sleep, or forced process termination can prevent automatic restoration. Manual recovery is to unlock the phone and move the slider to Ink, then back to normal.
- The Zenith monitor was stopped for testing. The Analog Anchor app need not be selected for Max Ink because enforcement runs on the PC.

The updated controller's typed `stop` command was also tested while Ready in normal mode: it confirmed normal restoration, closed its monitor, and exited successfully. Operator stop during active Max Ink still needs a live trial. The five-minute attempt received no fresh physical Ink entry; no 300-second commitment began, and the operator stopped it in normal mode.

Private serial numbers, selected-app lists, raw logs, screenshots, and extracted APKs are deliberately excluded from these findings and from source commits.

## Historical standalone APK correction (1.0.1)

The previous Android activity launched the on-device `nxtpaper_guard.sh`, not the unused `NxtpaperGuardService`. That script incorrectly treated secure `TSWT_state` as physical switch position, although injected framework mode keys also modify it. It also reacted to intermediate native states without checking theme/animation completion. These are code-level causes consistent with the reported intermittent exit; this investigation did not reproduce the user's exact sequence on a connected phone.

The correction separates raw physical input from native settings, retains a monotonic commitment deadline through recovery, and waits for settled native state before corrective commands. Extended reading follows actual physical switch events. The APK carries and deploys its own controller, verifies live process identity/heartbeat, remembers an explicit enable request, exposes Shizuku recovery, and applies Android system-bar/cutout insets. The obsolete exported Android service has been removed so there is one enforcement implementation.

Official Shizuku 13.6 adds non-root auto-start on Android 13+ connected to a trusted WLAN: https://github.com/RikkaApps/Shizuku/releases/tag/v13.6.0 . This can simplify restart recovery on the tested Android 16 model, but does not establish offline cold-boot startup. USB computer startup remains available without Wi-Fi. The app cannot silently create Shizuku privilege or accept Android's per-network debugging consent.

No Android phone or emulator was connected during this correction. Installation, repeated physical OFF/recovery/ON sequences, prolonged reading, expiry near a physical switch event, cold boot, network changes, and visual system-bar spacing remain unverified on-device. Do not describe this APK as a production-validated release.

### Local verification completed

- `python -m unittest -q`: **106 tests passed** (73 existing PC/diagnostic tests and 33 regressions executing the shipped shell controller).
- `assembleDebug lintDebug --max-workers=1 --no-parallel`: **BUILD SUCCESSFUL**. Lint reports **0 errors and 13 warnings** about dependency/tool versions, backup compatibility hints, resources/icon styling, and Kotlin style.
- Shell syntax validated with `sh` and `dash`; PowerShell USB helpers passed parser checks.
- APK package `com.analoganchor.nxtpaperguard`, version **1.0.1 / code 2**, signature verified. Its controller asset is byte-for-byte equal to the tested canonical script with LF line endings.
- Deliverable: ignored local `dist/AnalogAnchor-NXTPAPER-Guard-1.0.1.apk` (5,754,556 bytes); SHA-256 `653071d28f1c14989d23290986789f59c2a7d54263cacaabdf56a89e76ffc03c`.

Version 1.0.1 used the three-position startup instruction **Ink → Normal → Ink** to produce an OFF-to-ON event. That calibration is superseded by the 1.0.3 first-fresh-Ink behavior above. `INITIALIZING` is displayed before startup validation, so a cached state from a previous failed run cannot be mistaken for a newly started guard.
