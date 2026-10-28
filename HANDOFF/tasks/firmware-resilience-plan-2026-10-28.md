# NXTPAPER firmware resilience plan

Prepared 28 October 2026, Asia/Bahrain. The founder approved proceeding with local safeguards and durable documentation. Local implementation/build and 242 local tests are complete; the 1.0.5 APK is not installed or physically accepted. Use [the task checkpoint](firmware-resilience-2026-10-28.md) and [LATEST](../LATEST.md) for current evidence before acting. This plan does not record handset acceptance.

## Goal and boundaries

Reduce the chance that an accidental TCL/Android update strands the founder, and give another agent enough evidence to diagnose and repair a newer build without starting from zero. Preserve the full native Max Ink experience, physical-switch handling, and commitment enforcement on the current phone and newer NXTPAPER 70 Pro units.

Keep the phone stock and preserve personal data. A spare phone is optional. Generic kiosk, accessibility, launcher, or screen-filter behavior does not satisfy the native Max Ink requirement. Root, bootloader unlocking, flashing, factory reset, and speculative downgrade are outside this plan. No phone installation, controller replacement, updater restriction, reboot, OTA, outreach, commit, or push is authorized by this local implementation stage.

There are two distinct update outcomes: the guard can refuse an unfamiliar firmware even when TCL's controls still work, or the update can genuinely change the native interfaces/permissions. The first often permits a small reviewed compatibility change; the second needs new evidence and may not be repairable on a stock phone. The Android app opening is separate from enforcement working.

## Observed baseline

The preceding read-only investigation on 28 October 2026 observed the following. Recheck before handset work; these are not current live-state guarantees.

| Item | Observed value |
| --- | --- |
| Model/device | TCL NXTPAPER 70 Pro, `T807D` / `Frida`, European build |
| Android/SDK | Android 16 / SDK 36 |
| Firmware | `TCL/T807D_EEA/Frida:16/BP2A.250605.031.A3/AMD9:user/release-keys` |
| Security patch | `2026-07-05` |
| Boot state | Verified Boot green; bootloader reported locked |
| Update setting | `ota_disable_automatic_update=1` |
| TCL updater | `com.tcl.fota.system`, enabled in users 0 and 10 |
| Shizuku/debugging | Shizuku 13.6 running; USB debugging enabled; wireless debugging disabled |
| Management | Personal Island profile 10; organization-owned false; no Device Owner |
| Installed APK | 1.0.4 / code 5, matching the PC delayed-stop deliverable |
| Live controller | Separately identified as 1.0.3; idle when sampled; not equal to the APK asset |
| Native state | Settled Normal; Max Ink preset 3; immediate switching 1 |
| Physical input | `tswt`; Linux 592/593 mapped to `TSWT_ON`/`TSWT_OFF` |
| Git starting point | `codex/nxtpaper-demo`, HEAD `553ec2a`, existing uncommitted delayed-stop work |

Historical SHA-256 values, not hashes of future builds:

- Installed 1.0.4 APK: `9b83a4a25b0a8bda89f5aecc434ce9ce90b858b2e7411da1536dfd929ea246d4`.
- Its bundled controller and then-current PC source: `7765bcab3e277a669752f538d0b9ae4d270e552a4c44223e4a743f3e65b023d3`.
- Separately running 1.0.3 script: `ef82dc007dda64392733d2cf28cd3bc9782065738ee554c08d4c20da0dad3553`.

The old handoff's statement that 1.0.4 had not been installed was superseded by this package inspection. Installation and matching asset bytes still do not establish that the new controller ran or passed physical acceptance. Do not stop the older live process merely because a newer APK exists.

## Seven approaches, in practical order

| Approach | Concrete work | Limit and priority |
| --- | --- | --- |
| 1. Native update precautions | Preserve Android's existing setting; inspect TCL's auto-download, scheduling, and installation choices; document exact behavior. | First layer. The Android flag is already set; this does not prove manual or every OEM update path is blocked. |
| 2. Reversible exact-updater restriction | Research `com.tcl.fota.system`, its actual execution user/services, active/staged OTA state, side effects, and exact undo procedure. | Optional future approved handset step. Never blanket-disable package copies or claim it cancels an already staged update. |
| 3. Reviewed firmware profiles | Share fixed, restricted profile data across Android, shell, and PC code. Preserve AMD9 qualification; classify other builds as unverified. | Main software investment. A newer fingerprint needs qualification, not automatic acceptance or wholesale removal of the guard. |
| 4. Independent diagnosis and guided qualification | Report which layer failed; keep diagnostics available when enforcement is unavailable; validate a reviewed candidate with bounded handset trials. | Matching fields alone cannot prove command semantics. No automatic promotion or downloaded executable repair. |
| 5. Portable recovery kit | Preserve reproducible source, correct APK/controller identity, native-interface evidence, USB Shizuku instructions, both-PC setup, and an agent/founder decision tree. | USB may recover privilege startup. It cannot recreate access the OS denies. Copies of APKs/settings are not a firmware image. |
| 6. Optional canary phone | Qualify candidate updates on a spare 70 Pro and maintain results by model, region, build, and tested behavior. | Prefer before an intentional primary-phone update; no purchase or spare is required for the initial work. |
| 7. Official TCL integration | Research whether a supported native interface or OEM partnership route exists; document required capabilities. | Long-term research; availability unknown. No contact is authorized in this stage. |

Use approaches 1, 3, 4, and 5 as the initial local foundation. Research approach 2 without applying it. Keep 6 optional and 7 exploratory. No collection of these measures guarantees an unknown future TCL release retains undocumented native access.

## Implementation packages and interfaces

**Baseline and continuity.** Preserve the exact prior evidence and unrelated changes. Record installed APK, bundled asset, deployed script, and live process separately. Commit-ready source, profiles, tests, sanitized instructions, and compatibility history belong in Git; raw identifiers/captures, binaries, signing keys, and personal data remain private and ignored. Transfer the private kit and signing key securely to the other PC separately. Never embed secrets in handoff files.

**Shared profile.** Use one strict declarative format under `compatibility/profiles/`, with identity, switch mapping, fixed native commands, state/configuration keys, and qualification provenance. Reject duplicate/unknown keys and malformed values. Profile data must not be evaluated as shell code. Schema 1 represents the reviewed current semantics; a genuinely new native protocol requires a reviewed adapter change and evidence, not guessed data values.

**Read-only report.** Add `python nxtpaper_diag.py compatibility --json` and an independent app diagnosis path. A `CompatibilityReport` distinguishes `VERIFIED`, `UNVERIFIED_BUILD`, `CAPABILITY_MISSING`, and `PRIVILEGE_UNAVAILABLE`, with individual checks and a recovery action. Controller mismatch is a separate issue. A verified result means the observed structure matches a historically qualified profile; it is not proof that this live controller or handset behavior has passed acceptance. Keep compatibility reporting separate from the existing controller status/timer protocol.

**Command authorization.** All native mode commands, including app test buttons and restoration, use fresh checks against the selected reviewed profile. A cached report cannot authorize a command. Freeze profile selection for the controller lifetime. Do not redeploy/replace profiles or controllers while a live process could own a session. A qualifying trial is a separately approved operation on a reviewed candidate, with all controllers stopped, Normal confirmed, a predetermined restoration path, and bounded operations.

**Failure behavior.** Preserve raw physical events versus native desired state, the exact boot sentinel, settled-theme/animation checks, bounded retries, fixed monotonic commitment/Stop deadlines, cancellation rules, profile-10 reads through shell context, and existing live-controller preservation. Restoration sometimes uses both native commands; it must not bypass compatibility. If required identity or state becomes invalid, withhold guessed commands and report: "Protection unavailable; Normal mode has not been confirmed." Reboot/controller loss still ends enforcement; this work does not add session recovery across those losses.

**Updater assessment.** Record initial package/user states, actual primary-user execution path, staged/active OTA evidence, expected effects, and exact undo steps before any approval request. Do not alter updater state while an OTA is applying or if state cannot be established. A restriction delays firmware security fixes and needs review before deliberate updating. Profile-10 presence alone is not evidence that its copy controls primary-user updates.

## Verification and acceptance

- Preserve the documented starting baseline of 168 Python and 18 Android tests, then run relevant new regressions and the integrated build. These are historical counts until the current task records fresh results.
- Cover changed fingerprint/model/SDK, denied privilege/input, missing/duplicate/malformed state, changed input mapping/node, stale diagnostic results, native commands from all entry points, unknown live-controller preservation, and existing delayed-stop behavior.
- Verify diagnostics make no phone writes, deployments, preference updates, or mode commands. Do not classify a file-writing status action as read-only.
- Inspect the delivered APK's version, signature, controller/profile assets, and byte equality separately from any phone result. Intended local successor is 1.0.5/code 6; verify actual artifact identity before use.
- Future approved phone work begins with a fresh identity/firmware/live-controller inspection. Resolve the old-controller mismatch using a controlled supported stop/completion route and confirmed stopped state; an idle snapshot can race with a physical Ink event.
- Physically qualify native entry/Normal restoration, real switch events, early exit with unchanged deadline, ordinary expiry/extended reading, real elapsed delayed Stop, Continue, app closure, sleep/wake, EN/AR layout, and profile-10 behavior. Record Shizuku/reboot recovery separately. Short trials do not prove 2/4/6/12-hour endurance.
- If updater restriction is later approved, verify relevant entry points, collateral behavior, exact restoration, and persistence after an authorized reboot. Never install an OTA merely to prove blocking.

## Official references and limits

- Android's developer flag maps value 1 to disabled automatic updates in [AOSP's controller](https://android.googlesource.com/platform/packages/apps/Settings/+/903d2610dd6479445633db86336bde3208e5b4da/src/com/android/settings/development/DisableAutomaticUpdatesPreferenceController.java). This does not establish every TCL updater route honors it.
- [Shizuku 13.6](https://github.com/RikkaApps/Shizuku/releases/tag/v13.6.0) adds Android 16 QPR1 support and trusted-WLAN automatic startup on Android 13+. Availability depends on the phone's debugging service/firmware; the observed phone had wireless debugging disabled.
- [Current DevicePolicyManager requirements](https://developer.android.com/reference/android/app/admin/DevicePolicyManager#setSystemUpdatePolicy(android.content.ComponentName,%20android.app.admin.SystemUpdatePolicy)) permit policy control for Device Owner or an organization-owned managed profile. Ordinary personal Island does not qualify. [Android policies](https://developer.android.com/work/dpc/system-updates) have temporary postponement/freeze limits; managed deployment is a separate project outside the selected no-reset scope.
- [Verified Boot rollback protection](https://source.android.com/docs/security/features/verifiedboot/verified-boot) can reject older firmware. [TCL's general Mobile Upgrade guidance](https://support.tcl.com/how-can-i-upgrade-my-device?kb_language=en_US) describes installing latest software, not a supported downgrade for this exact model/region.

Continue using [the founder/agent recovery guide](../../compatibility/RECOVERY.md) and [the standalone Antigravity prompt](antigravity-firmware-resilience-prompt.md). Read the newest task checkpoint before acting.
