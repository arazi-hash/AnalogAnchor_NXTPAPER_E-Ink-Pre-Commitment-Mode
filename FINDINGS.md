# Verified NXTPAPER controls

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
