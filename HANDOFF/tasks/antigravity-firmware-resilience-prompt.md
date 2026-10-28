# Antigravity / Gemini continuation prompt

Prepared 28 October 2026. Copy the text below into Antigravity. Codex completed the local safeguards, 1.0.5 APK and 242 passing local tests; the APK is not installed or physically accepted. The newest on-disk checkpoint owns later status. This prompt deliberately starts the next agent with read-only inspection.

---

You are continuing Analog Anchor's NXTPAPER project. Begin with **READ-ONLY INSPECTION, THEN A CONCRETE PLAN**. Do not implement anything in this first assignment. The founder is nontechnical; explain plainly and investigate discoverable facts yourself. Ask questions only for unresolved decisions that materially affect the work.

Project root: `C:\AnalogAnchor_NXTPAPER_Demo`.

First read the following files and their relevant linked evidence:

- `C:\AnalogAnchor_NXTPAPER_Demo\AGENTS.md`
- `C:\AnalogAnchor_NXTPAPER_Demo\README.md`
- `C:\AnalogAnchor_NXTPAPER_Demo\HANDOFF\START_HERE.md`
- `C:\AnalogAnchor_NXTPAPER_Demo\HANDOFF\LATEST.md`
- `C:\AnalogAnchor_NXTPAPER_Demo\HANDOFF\tasks\firmware-resilience-2026-10-28.md`
- `C:\AnalogAnchor_NXTPAPER_Demo\HANDOFF\tasks\firmware-resilience-plan-2026-10-28.md`
- `C:\AnalogAnchor_NXTPAPER_Demo\compatibility\RECOVERY.md`
- `C:\AnalogAnchor_NXTPAPER_Demo\FINDINGS.md`

Inspect actual Git state and source. The task started on `codex/nxtpaper-demo`, HEAD `553ec2a`, with existing uncommitted delayed-Emergency-Stop work. Codex subsequently began local compatibility safeguards, diagnostics, and documentation. Do not assume those edits/builds are finished: read the newest checkpoint and inspect files. Preserve all unrelated work; do not reset, clean, stash, overwrite, stage, commit, or push.

## Objective and constraints

Prepare this application for an accidental Android/TCL system update and for another NXTPAPER 70 Pro supplied with newer firmware. Preserve the **full native Max Ink experience and commitment enforcement**. A new firmware number should trigger informed diagnosis and qualification rather than blind failure or a speculative bypass.

Keep phones stock and preserve personal data. No root, unlocking, flashing, factory reset, speculative downgrade, or substitution with a generic launcher/kiosk/screen-filter blocker. A spare test phone is optional. The immediate scope is local software and recovery readiness; handset changes, installations, controller replacement, reboots, OTA, updater restriction, outreach, commits, and pushes require separate later authorization.

## Historical observed baseline — recheck it

Read-only inspection on 28 October 2026 observed:

- TCL NXTPAPER 70 Pro, `T807D` / `Frida`, European firmware.
- Android 16, SDK 36, security patch `2026-07-05`.
- Fingerprint: `TCL/T807D_EEA/Frida:16/BP2A.250605.031.A3/AMD9:user/release-keys`.
- Verified Boot green and bootloader reported locked.
- `ota_disable_automatic_update=1`; exact updater `com.tcl.fota.system` enabled in users 0 and 10.
- Shizuku 13.6 running; USB debugging enabled, wireless debugging disabled.
- Personal Island profile 10; organization-owned false; no Device Owner.
- Installed guard app 1.0.4/code 5. Its APK and embedded controller matched the PC delayed-stop deliverable.
- Separately running controller identified as 1.0.3 and differed from that asset. It reported IDLE when sampled; this does not authorize replacing it or prove it remains idle.
- Native state was settled Normal, preset 3, immediate switching 1.
- Raw input device named `tswt`; Linux keys 592/593 mapped to `TSWT_ON`/`TSWT_OFF`. Native commands on this qualified firmware were framework keys 343/344.

Historical SHA-256 values, not values for any newly built successor:

- Installed 1.0.4 APK: `9b83a4a25b0a8bda89f5aecc434ce9ce90b858b2e7411da1536dfd929ea246d4`.
- Its embedded controller and then-current PC source: `7765bcab3e277a669752f538d0b9ae4d270e552a4c44223e4a743f3e65b023d3`.
- Separately live 1.0.3 script: `ef82dc007dda64392733d2cf28cd3bc9782065738ee554c08d4c20da0dad3553`.

The preceding plan investigation made no phone/file changes. The later local implementation stage is recorded separately on disk. The intended local successor was 1.0.5/code 6; verify actual source/artifact version. No statement here establishes installation or handset acceptance of that successor. A historical handoff saying 1.0.4 had not been installed is superseded only for package presence, not live-controller/physical acceptance.

## Findings and architecture to preserve

Originally both shell and PC implementations pinned the exact firmware fingerprint. A changed fingerprint alone could stop enforcement even if TCL's controls still worked. Do not solve this by deleting the check or blindly substituting another fingerprint.

Other real dependencies include shell privilege, Shizuku bridge, raw input access, `tswt` mapping/keylayout, framework keys, seven native settings and their meanings, settled theme/animation state, process identity/storage, and OEM process management. The Android app opening is separate from native enforcement functioning.

The local design introduces a strict declarative reviewed profile shared across Android/shell/Python, an independent read-only compatibility report, and fresh command checks. Inspect what actually exists. Profile data must not execute shell text. Schema 1 only represents reviewed current semantics; a new native protocol needs reviewed code and evidence, not guessed data.

Expected PC interface: `python nxtpaper_diag.py compatibility --json`, from the project root. Confirm implementation before using it. It should print a shareable report without phone writes or serial disclosure. Android should have a separate compact EN/AR diagnosis path rather than reuse normal status operations that write files/preferences. Verify this independence.

Report `VERIFIED`, `UNVERIFIED_BUILD`, `CAPABILITY_MISSING`, and `PRIVILEGE_UNAVAILABLE`, plus per-check results and a next action. `VERIFIED` means structure matches a historically qualified profile; it does not prove live enforcement or physical acceptance. Report controller-version mismatch separately.

Every mode-changing path needs fresh validation: entry, recovery, restoration, and mode-test buttons. A cached report cannot authorize a command. Freeze profile selection for the controller lifetime. Do not replace a profile/controller while a live process might own a commitment. No automatic profile promotion or remote executable repair.

Unknown firmware permits observation/manual guidance, not automatic native commands. Controlled qualification requires a reviewed candidate mapping, separate authorization, all controllers stopped, Normal confirmed, bounded operations, and a predetermined restoration procedure. Restoration sometimes uses both ON and OFF; do not give it an unconditional unsupported-firmware bypass. If required identity/state becomes invalid, withhold guessed commands and say: "Protection unavailable; Normal mode has not been confirmed."

Preserve raw physical events versus native desired state, the exact `TSWT_state=-1` boot sentinel, settled transition checks, fixed monotonic deadlines, all five duration choices, delayed Stop/Continue rules, shell-context reads for profile 10, and unknown live-controller preservation. Reboot or controller loss still ends active enforcement and pending exits; this project does not recover those sessions across loss.

Installed APK, embedded asset, deployed script, and live process are distinct facts. The observed mismatch is not proof of firmware failure. An IDLE snapshot can race with a new physical Ink event. A future separately approved reconciliation must use a supported controlled stop/completion route and confirm actual stopped state before deployment; do not kill the live controller merely because a newer APK exists.

## Assess all seven approaches

1. **Native update precautions:** preserve Android's existing flag; inspect exact TCL auto-download/scheduling/install options without changing them. The observed flag does not establish that pressing Update/Continue is blocked.
2. **Reversible exact-updater restriction:** investigate `com.tcl.fota.system`, actual execution user/services, staged/active OTA status, side effects, scope, and exact undo. Do not blanket-disable profile copies or promise to cancel an already staged update. Do not interfere with an applying/unknown-state OTA. Delaying firmware updates also delays security fixes.
3. **Qualified firmware profiles:** preserve current AMD9 support and make newer builds unverified until qualified. Matching marketing name/model/settings alone is insufficient.
4. **Independent diagnosis and guided repair:** distinguish connection/privilege loss, unfamiliar identity, changed native capability, app startup failure, and app/controller mismatch; repair only the affected layer using evidence.
5. **Portable baseline/recovery kit:** preserve correct APK/controller/profile identity, relevant native investigation evidence, USB startup instructions, both-PC build requirements, and founder/agent recovery steps. The PC demo shares TCL dependencies. USB startup can recover some Shizuku failures, not permissions removed by the OS.
6. **Optional canary phone:** track model/region/build and tested results on a spare before deliberately updating the primary phone. Do not assume a purchase or another device exists.
7. **Official TCL integration:** research whether supported native integration exists; record required capabilities and unanswered questions. Do not contact anyone.

## Evidence, testing, and portability

Preserve the historical documented baseline of 168 Python and 18 Android tests, but use the current task for actual fresh counts/results. Mocked tests, APK packaging/signature checks, injected native events, real switch trials, long-duration use, and publication are separate evidence categories.

Local checks should cover changed identity, missing/duplicate/malformed settings, denied shell/input access, changed switch mapping/node, unavailable Shizuku, stale report authorization, every native command path, unknown live-controller preservation, and current delayed-stop behavior. Do not run handset-affecting tests in this first assignment.

Future physical qualification must establish native entry/restoration, real physical-switch events, early-exit recovery preserving deadline, ordinary expiry/extended reading, actual elapsed delayed Stop and Continue, app closure/sleep, EN/AR and profile-10 behavior. Short tests do not prove full 2/4/6/12-hour operation. Normal is confirmed from settled native evidence, not countdown zero or shell success.

Commit-ready source/profiles/tests/sanitized history/instructions belong in Git after authorization. Keep serials, raw captures, APK/system binaries, personal data, PC-specific SDK paths, and signing keys private and ignored. Securely transfer the signing key separately when needed for app updates from both PCs. Matching chat/project names do not synchronize files. Never describe APK/settings archives as a restorable OS firmware image.

Verify official references before relying on them:

- Android policies: https://developer.android.com/work/dpc/system-updates
- Current ownership requirements: https://developer.android.com/reference/android/app/admin/DevicePolicyManager
- Automatic-update flag: https://android.googlesource.com/platform/packages/apps/Settings/+/903d2610dd6479445633db86336bde3208e5b4da/src/com/android/settings/development/DisableAutomaticUpdatesPreferenceController.java
- Shizuku 13.6: https://github.com/RikkaApps/Shizuku/releases/tag/v13.6.0
- Rollback protection: https://source.android.com/docs/security/features/verifiedboot/verified-boot
- TCL upgrade guidance: https://support.tcl.com/how-can-i-upgrade-my-device?kb_language=en_US

Ordinary personal Island ownership does not grant official system-update policy control. Managed-device provisioning is a separate project outside current no-reset scope, and Android's supported scheduling has time limits. Shizuku 13.6 trusted-WLAN startup is version/firmware dependent. TCL's general upgrade tool installs latest software; no supported exact-model downgrade is established.

## Your first response

After bounded read-only inspection, deliver:

1. Current state and differences from this historical baseline, with unknowns labeled.
2. What local compatibility safeguards/documents are actually implemented and what verification really passed.
3. A ranked assessment of all seven approaches: useful now, investigational, or unavailable under these constraints.
4. One concrete next work package with affected components/interfaces, tests, recovery/undo steps, and remaining uncertainty.
5. A staged plan separating local software work from future approved handset operations and physical acceptance.
6. Questions only for unresolved material choices.

For this first assignment, do not edit files, install apps, stop/redeploy controllers, inject keys, change settings, start Shizuku, disable packages, reboot, update firmware, clear data, reset, commit, or push. Inspect helper side effects before invoking them. Do not assume legacy status actions are read-only. Do not declare new firmware supported from names/structure/mock tests alone, and do not guarantee future TCL releases preserve undocumented access.
