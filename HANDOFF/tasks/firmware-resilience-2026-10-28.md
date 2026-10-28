# Firmware resilience — 28 October 2026

Status: LOCAL IMPLEMENTATION/BUILD/VERIFICATION COMPLETE; no handset installation or physical acceptance. No operations running.

## Final delivery — authoritative over progress notes below

- Full Python discovery passed: **217 tests**, no failures/errors/skips, **168.543 seconds**. This includes 99 PC/profile/diagnostic/demo, 110 controller/compatibility shell, and eight Android embedded-presence shell tests. Android unit tests: **25 passed**, no failures/errors/skips. Total: **242 local tests**.
- Integrated Gradle testDebugUnitTest/lintDebug/assembleDebug succeeded in **2m 47s**, one worker/no parallel. Lint: **0 errors, 14 warnings**. XML/new EN/AR formats, source/package equality, shell syntax, documentation links/encoding and whitespace checks passed. All earlier progress-run failures below were resolved before this final pass.
- Deliverable: `dist/E-Ink-Precommitment-Mode-1.0.5-firmware-resilience.apk`, **6,067,137 bytes**, SHA256 `607414d93b14e5326a80c5d45cfd319bae9227c0b2c97a300648b049647cb25d`. Version 1.0.5/code 6, min SDK 26, target SDK 36. APKv2 signature verifies with historical debug certificate SHA256 `bb57ddf958f90324e214020a7f65e5aba9f4e3dd7ba1ebd6454868af8cb41d2e`.
- Canonical/embedded controller: 57,753 bytes LF, SHA256 `ce53dfb10c91beddabfbd8c4101db690ff9bfe8ab1ddb939b59378ca11721834`. Profile:803 bytes LF, SHA256 `c0fa4228ebb43f16e554b67e8b86188991754be2231e6d83363ea2cffa529688`. Combined identity is script+NUL+profile: `1.0.5:dd8f0856c15a4b6c24d4213203b1b0c8c383d090077bcc52572bd5d6b2fd0833`.
- Portable recovery archive: `dist/NXTPAPER-Recovery-Kit-2026-10-28.zip`, **15,135,470 bytes**, SHA256 `a08f728c26b9bf3762bbf19248eca73c473c79c0760e57b9da91457cf18d3cf1`. ZIP integrity and every manifested payload hash verified. Contains three historical/local APKs, current controller/profile, read-only captured live1.0.3 script, plan/prompt/recovery/build findings and manifest. No signing keys, serials, raw process tokens or personal data. This is neither firmware nor a full repository backup; transfer Git source and the private signing key separately through their appropriate routes.
- Final read-only PC and source-via-stdin phone checks matched the historical AMD9 profile. Final Android embedded presence check reported present/identified. Existing older live1.0.3 controller still reported IDLE when sampled; script hash unchanged. Its exact bytes were read to the private kit, not executed or replaced. No new APK was installed. Current installed1.0.4/package presence is separate from live-controller/physical acceptance.
- Independent diagnostic paths perform no deployment/preferences/language/status publication or native commands. Command gates require fresh identity, native configuration/state, input/keylayout; restoration has no unsupported-firmware bypass. Profile is frozen per process. Unknown/malformed/denied process identity blocks replacement. Schema1 deliberately retains current native semantics. Android and PC control select AMD9; additional diagnostic registry profiles do not automatically enable either consumer. Native package versions are comparison evidence, not a fully pinned system image.
- Durable user/agent deliverables: [seven-approach plan](firmware-resilience-plan-2026-10-28.md), [standalone Gemini prompt](antigravity-firmware-resilience-prompt.md), [recovery guide](../../compatibility/RECOVERY.md). README/FINDINGS updated. Private proof: logs/firmware-resilience-verification-2026-10-28.json plus firmware-compatibility, firmware-shell-readonly and firmware-android-presence-readonly JSON files.

### Remaining work and boundaries

This local task is complete. No installation, controller stop/redeploy, native key injection, updater restriction, reboot, OTA, root/reset/flashing, outreach, staging/commit/push was performed. The full native experience on future firmware is not guaranteed. Updater restriction remains unqualified optional research; no safe exact-model downgrade is established. A spare device is optional; OEM access availability is unknown.

Handset acceptance remains separate: diagnostic-dialog layout/EN/AR/large text, real switch/recovery, fixed deadlines, actual five-minute delayed Stop/Continue, app closure/sleep, profile10, reboot/Shizuku recovery, and long commitments. Existing reboot/controller-loss limits remain. Never treat a report, APK asset, successful command, or idle snapshot as proof of live protection or Normal restoration.

The user can copy the saved Gemini prompt. The next agent starts read-only, rechecks actual Git/device state, then proposes the next concrete work package. Do not rerun passed local tests without a new change/failure/concern. Any later authorized deployment must safely finish/stop the matching old controller and confirm actual stopped state; never replace it based on a stale IDLE observation. Source changes remain uncommitted on codex/nxtpaper-demo at HEAD553ec2a, alongside preserved delayed-stop changes. Artifacts are ignored and need separate transfer between PCs.

## Historical implementation progress follows

## Authorization and scope

The founder requested a comprehensive update-resilience plan and copyable Antigravity/Gemini prompt, then said "proceed". Implement local safeguards and durable documentation while preserving the full native Max Ink experience, stock phone, personal data, and existing delayed-stop work. Current and newer NXTPAPER 70 Pro builds are in scope; spare phone optional. Updater controls may be investigated, but not applied in this stage. Phone changes, installation, controller replacement, reboots, OTA, reset/root/flashing, outreach, commits and pushes remain outside this stage.

## Starting truth

- Repository C:\AnalogAnchor_NXTPAPER_Demo, branch codex/nxtpaper-demo, HEAD 553ec2a. Existing uncommitted delayed-stop source/tests/docs must remain.
- Prior read-only phone observation: T807D/Frida, Android16 SDK36, fingerprint TCL/T807D_EEA/Frida:16/BP2A.250605.031.A3/AMD9:user/release-keys; security patch 2026-07-05. ota_disable_automatic_update=1; com.tcl.fota.system enabled; Shizuku13.6 running; personal Island profile10, no Device Owner.
- Installed APK1.0.4/code5 SHA256 9b83a4a25b0a8bda89f5aecc434ce9ce90b858b2e7411da1536dfd929ea246d4; embedded/source controller SHA256 7765bcab3e277a669752f538d0b9ae4d270e552a4c44223e4a743f3e65b023d3. Live controller separately identified1.0.3, SHA256 ef82dc007dda64392733d2cf28cd3bc9782065738ee554c08d4c20da0dad3553, idle when sampled. Do not confuse package installation with running-controller acceptance.
- Historical documented local baseline:168 Python +18 Android tests passed. Not rerun for the new task yet.

## Intended delivery

1. Shared reviewed firmware profile, preserving exact AMD9 qualification; no arbitrary shell execution or automatic promotion.
2. Independent read-only compatibility report/CLI and app diagnosis; no controller deployment or native commands from diagnosis.
3. Fresh command validation across shell/PC/app mode tests, immutable per-controller profile, no unsafe restoration bypass.
4. Portable founder/agent recovery guide, seven-layer strategy, exact baseline, and standalone Antigravity prompt. Explain updater restrictions as unverified optional research, not executed or guaranteed.
5. Meaningful local regression tests/build/artifact verification; handset acceptance remains separate.

## Work ownership and next step

Root: shell controller, shell tests, integration/build, task checkpoint and LATEST.
Agents will own non-overlapping PC/profile, Android, and documentation files. Coordinate profile contract before integration. No active builds started. Save milestones and final actual test results here.

## Milestone checkpoint

- PC/profile implementation saved: canonical restricted properties; nxtpaper_compatibility.py and tests; independent CLI; fresh PC command gates. Root reran 99 focused PC/diagnostic tests successfully in 1.309s after the agent's initial 97-test pass.
- Android saved: new GuardCompatibility/parser/tests, on-demand EN/AR diagnostics, bundled profile, combined controller/profile identity, gated native tests and Start, intended1.0.5/code6. No Gradle build yet. Root is hardening conservative process-presence handling; unverified.
- Shell saved: strict frozen profile parser, independent check-compatibility action, native test actions, fresh identity/layout/native command gates. New shell compatibility regression module saved.
- First full shell run:107 tests in121.709s, one failure caused by the new frozen-clock test harness overriding the direct clock unit test. Its test setup has now been corrected, but rerun is pending. This is NOT a passing integrated result.
- Three durable documents saved: firmware-resilience-plan-2026-10-28.md, antigravity-firmware-resilience-prompt.md, and compatibility/RECOVERY.md. Their implementation/test status still delegates to this checkpoint.
- Two implementation subagents hit account usage limits after saving their changes. Root continues integration; do not assume their last reported self-review finished. No phone operations or Git mutations performed.

Next: finish conservative absence/command safety review; rerun shell checks after final source changes; run integrated Gradle test/lint/assemble; verify packaged assets/signature; run only independently reviewed read-only phone diagnosis; update README/FINDINGS and final handoff with actual evidence. No test/build operation is currently running at this checkpoint.

### Integration update — operations running

Root hardened Android and shell to preserve possible controllers when process identity cannot be inspected, while allowing valid previous-boot tokens to be recognized as stale. Added shell cases for this. Second shell suite is running (exec session25512); do not count it passed yet. Gradle testDebugUnitTest/lintDebug/assembleDebug has started (exec session52714), one worker/no parallel; outcome pending.

Read-only phone diagnosis: the PC report matched the historical AMD9 profile and observed the older live1.0.3 controller separately. Initial source-via-stdin shell probe exposed Android awk requiring parentheses around printf ternary arguments. Corrected; repeated READ-ONLY check-compatibility now returns VERIFIED:t807d-eea-amd9 with empty stderr. This executed no phone writes or native commands and did not deploy or replace the live script. Ignored proof: logs/firmware-compatibility-2026-10-28.json and logs/firmware-shell-readonly-2026-10-28.json. Multiple ADB endpoints were present, so explicit previously verified USB handset selection was used; no other endpoint was operated.

### Before final integrated Python verification

Gradle session52714 completed successfully in2m47s: testDebugUnitTest/lintDebug/assembleDebug,25 Android tests (7 compatibility+6 exit policy+12 status),0 failures/errors. Artifact packaging/signature and lint counts still need explicit inspection.

Second shell suite completed110 tests in168.232s with3 failures: one new test expected the unnormalized duration field; two existing safety tests treated even kill -0 observation as a destructive signal. Root corrected the new test protocol setting and reordered the absence check to avoid unnecessary kill -0 when /proc already proves the record stale. A separate Android embedded-shell presence run had one10-second host process timeout during overlapping Gradle work; timeout was raised to the existing shell-suite45-second standard. These runs are not passing integrated proof. Final full Python discovery is starting now with stable source and no concurrent build. Do not count it passed until completion is recorded.
