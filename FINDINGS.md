# Verified NXTPAPER controls

Investigation dates: 3–4 October 2026. These findings apply to the tested personal stock handset; the controller refuses other firmware profiles. Historical PC trials and APK versions are identified below so they are not mistaken for validation of the current update.

## Current standalone update: 1.0.3 / code 4

The app name is **E-Ink Pre-commitment Mode** in the Arabic and English UI. The update retains Shizuku and the native TCL Max Ink controls, adds a compact bilingual screen and bottom language toggle, and exposes one-session commitments of **2, 4, 6, or 12 hours** alongside the default **five minutes**. A selected preset is consumed when the next session enters `STARTING`; the active duration is frozen and the next-session duration returns to 300 seconds. Stop, an error, and reboot also reset the optional selection.

The first fresh physical Ink event is intended to start the session without the old Ink → Normal → Ink calibration. Native Max Ink and cleared theme/animation flags must be confirmed before the countdown begins. Early exits are repaired without changing the original deadline. After expiry, a physical switch left in Ink keeps reading open until the user moves it to Normal. During an active controlled session, emergency Stop overrides the timer and verifies normal restoration. Stop while idle ends monitoring and leaves the native screen mode unchanged. Native transitions can take several seconds; immediate recovery is not guaranteed.

### Device-verified 1.0.2 startup defect

The installed 1.0.2 controller was verified to match the canonical script. Its local `guard.log` recorded five startup attempts where the first physical `ON` event was sequence 1 and the following `OFF` event was sequence 2, but no `STARTING` session was entered. Only a later `ON` at sequence 3 began entry: the log recorded `STARTING` at device uptime 4672 seconds and confirmed `COMMITTED` at 4678 seconds. The live guard was healthy in `IDLE`/physical `OFF`, with controller and monitor process identities matching.

This establishes an ignored-first-Ink startup defect rather than a pairing failure. The old arming logic required an earlier physical OFF event before accepting ON. A separate stalled-recovery path was reproduced statically; the user's full repeated physical-switch failure sequence still needs validation on the updated handset build.

### Confirmed OEM boot-state rejection and correction

Decompiled TCL `PhoneWindowManager` and SystemUI confirmed that **`TSWT_state=-1` is a legitimate OEM boot sentinel**. The previous strict native reader accepted only 0 or 1 and failed after three reads of this boot state. The corrected reader accepts exactly -1 as an unknown native snapshot; the input monitor can remain ready in `WAIT_SWITCH`. While the native state is unknown, it sends no mode commands and does not infer a physical switch position. Active entry, recovery, and restoration retain their **45-second bounds** rather than waiting indefinitely.

The corrected canonical controller SHA-256 is `d09b9110bd80c01081e2e8aa66c86605ebf0e402d2d619ed11c7052f49be2627`. Its final APK hash, installation, and live asset confirmation are pending.

### Completed baseline before this update

- `python -m unittest -v`: **110 passed**, no failures or skips, in 39.176 seconds. This includes 73 PC/diagnostic tests and 37 regressions executing the shipped shell with fake Android commands.
- `testDebugUnitTest`: **NO-SOURCE**. There were no Android unit-test sources before this update.
- `lintDebug`: **failed with 5 errors and 21 warnings**. The five errors were `StringFormatInvalid` records caused by literal `100% Safe` copy in the English/Arabic safety guide and English Shizuku-help title. The refreshed concise help removes that absolutist wording; current lint results are recorded below.
- Separate `assembleDebug --max-workers=1 --no-parallel --console=plain`: **BUILD SUCCESSFUL**. Its APK is version **1.0.2 / code 3**, 7,102,188 bytes, and the bundled controller is byte-for-byte equal to the canonical script. SHA-256: `38bfdaa2c9dd040dd407e963f47ba4014d90e3866d82791aad554defa41d5f7f`.
- The build emitted an SDK-tooling metadata warning: the installed tool understood SDK XML through version 3 while encountering version 4. This did not prevent APK assembly.

### Completed 1.0.3 local verification

- Root Python suite: **147 passed**, no failures or skips, comprising 73 PC/diagnostic tests and **74 shell-controller regressions**, in **51.472 seconds**. Coverage includes the OEM boot sentinel and the Stop/reset check that five minutes is authoritative when the daemon exits.
- Android `testDebugUnitTest`: **seven tests passed**.
- Android `lintDebug`: **zero errors and 14 warnings**. The existing SDK-tooling metadata warning and unrelated lint warnings remain documented; dependencies were not upgraded as part of this update.
- Combined `testDebugUnitTest lintDebug assembleDebug --max-workers=1 --no-parallel`: **BUILD SUCCESSFUL** in **15 seconds** after the boot-state correction. The APK remains version **1.0.3 / code 4**.
- The preceding Stop/reset correction was installed and its live controller SHA-256 verified as `c563ffdbe75269478d216c175eb5bf5825de20da0a62472e190d860b665c7f8c`.
- That preceding artifact was `dist/E-Ink-Precommitment-Mode-1.0.3.apk`, **7,118,004 bytes**, SHA-256 `77856dabb06c6c1097363fb61f386de019c26069e9dc1d87b64e83e9d97f5f10`, with a byte-exact controller asset. It precedes the boot-state correction and is not its final artifact record.
- The preceding APK debug signature was verified; certificate SHA-256: `bb57ddf958f90324e214020a7f65e5aba9f4e3dd7ba1ebd6454868af8cb41d2e`. The new artifact/signature/live hash checks are pending.
- An earlier 1.0.3 build was installed with live controller SHA-256 `11006cbda58fe697c15e3114daf09e853d9355a14528115724745b059391dc3f` for the UI checks below.

### Completed UI verification on the earlier 1.0.3 build

Fresh handset UI hierarchies and acknowledged backend status confirmed every preset: **7200, 14400, 21600, and 43200 seconds**, with **300 seconds** as the default. The selected highlight matched the acknowledged choice. An earlier fast tap was not accepted while the previous selection was awaiting acknowledgment; the static status-polling gate was corrected, and final QA waited for each selection acknowledgment before the next tap. The earlier observation does not establish status polling as its cause.

The dynamic Arabic/English language button was tested, and the exact English app name was retained in the Arabic UI. At **200% font size**, Arabic RTL layout kept emergency Stop, timer choices, and the bottom language button reachable across two scroll positions. The handset's original font scale of **0.85** was restored after inspection.

### Remaining 1.0.3 handset verification

An initial attempted physical-slider trial produced no raw input event or native mode change, and the user confirmed that the phone remained on its regular app screen. The live controller stayed in `WAIT_SWITCH` with physical position `UNKNOWN`; it was stopped through the app to isolate native switch behavior.

After a reboot with the guard disabled, one physical Ink movement produced `KEY_BRIGHTNESS_MIN` at device uptime **136.86 seconds**, incremented the ON interrupt counter (IRQ 57) to 1, and fully entered native Max Ink. A later ON incremented that counter to 2, but the OFF interrupt counter (IRQ 60) remained 0 despite a reported Normal movement. Native framework key **343** also fully entered Max Ink in an isolated test. These establish individual native entry paths, not a controlled commitment. The subsequent guard remained in `WAIT_SWITCH`/`UNKNOWN`; no session began. Idle app Stop intentionally ended monitoring while leaving native Ink unchanged.

**No live commitment, recovery, expiry, or active-session emergency Stop trial has passed on the updated app.** The missing physical OFF input and repeated switching remain under investigation. Planned simulated raw events will be labeled as pipeline QA and will not count as physical-slider validation.

Artifact/install/live confirmation of the boot-state correction and physical-switch acceptance remain pending. Required live scenarios are first fresh Ink entry into a controlled session; **20 consecutive physical-switch early exits and recoveries** with an unchanged deadline; a native exit while the physical switch stays in Ink; expiry in both switch positions; rapid reversals; screen sleep/wake; active-session emergency Stop; Shizuku loss/recovery; and restart behavior. Preset selection is verified above; active duration consumption/reset still needs the corresponding live session checks. An actual long-duration screen-off trial remains necessary before claiming sustained enforcement.

Arabic/English UI and enlarged-font reachability are verified above. Automated tests and short simulated timers do not establish hours of real device reliability. `scripts/device_qa.py` can capture bounded native-state snapshots and framework-key exit/recovery trials under ignored `logs/`; those injected exits do not satisfy the 20 physical-switch trial requirement.

### Git and two-PC readiness

The source has portable build configuration and passing local checks, with remaining handset acceptance recorded above. The repository has no initial commit or GitHub remote. Existing root files are intent-to-add entries; the Android project, canonical shell, USB helpers, and shell-controller tests are untracked. No staging, committing, or pushing was performed during this update. Generated builds, SDK paths, signing keys, `captures/`, and `current_phone_screen*.png` are ignored. The required branding source and runtime launcher PNGs remain eligible for source commits.

Both PCs need JDK 17, SDK platform 36/build-tools 36.0.0, and their own ignored `nxtpaper_guard/local.properties`. Commit the Gradle wrapper and reviewed source together. Updating the same installed app from both PCs requires the same private signing key; that key must remain outside GitHub. Final source and staged-diff review remains required before creating the first source commit.

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

## Live controller validation

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

A completed 300-second PC trial is not recorded here. The full five-minute result and physical early-exit checks remain **pending**; starting or confirming entry is not a completed pass.

Evidence is retained locally under the ignored `logs` directory. The injected-exit and idle-failure tests do not establish repeated physical-slider behavior, screen-sleep behavior, calling, active-session crashes, or USB-disconnection recovery.

## Demonstration status and limits

- All four native entry/restore experiments above succeeded on the tested handset.
- Standalone native transitions took roughly **5–7 seconds** to fully settle. Inspection found the native framework's first animation-completion check uses **4,000 ms**. Full early-exit recovery took about **13 seconds** in the controller trial; the proposed two-second recovery target is **not met**.
- Normal-mode visibility is possible during early-exit recovery; the trial measured full native state settling rather than promising an immediate screen change.
- The PC controller implements a default 300-second deadline, early-exit re-entry without renewing that deadline, expiry restoration, physical-OFF rearming, and an operator stop. The full five-minute live trial is **pending**.
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
