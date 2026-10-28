# Latest checkpoint — AnalogAnchor_NXTPAPER_Demo

Updated: 2026-10-28 (Asia/Bahrain)
Task owner: Codex — delayed Emergency Stop
Status: implemented; 186 local tests passed; final packaging after lint cleanup in progress
Project root: C:\AnalogAnchor_NXTPAPER_Demo

## Objective and latest user steering

The founder approved the plan and said "proceed". Every 5-minute / 2 / 4 / 6 / 12-hour commitment now uses a five-minute Emergency Stop wait, including entry. Protection continues. The original commitment ending sooner triggers the requested exit then. Repeated taps preserve the exit deadline. Continue commitment cancels the exit request without changing the original timer. At zero, restoration must finish before claiming Normal. Idle/completed stopping remains immediate.

Local implementation, testing and APK preparation are authorized. No handset operation/installation, commit or push is authorized. Existing reboot/controller-loss limits remain. Preserve the compact EN/AR UI, native selected apps, original no-request expiry/extended reading, and unrelated work.

## Completed and saved

- Canonical nxtpaper_guard.sh: uptime-based delayed exit; request-stop/cancel-stop mailbox bound to daemon PID/start/boot; exact 10-field status with exitDeadline:exitRemaining suffix; due-before-cancel ordering; fresh-clock and missed-tick protection. Existing internal stop remains recovery-only.
- Android runtime/status/application and new GuardExitPolicy: durable future-restart intent; daemon-specific cancellation journal; reconnect recovery; no live-state cleanup on pending/timeouts; preserve unknown live controllers on updates; direct versus fallback restoration acknowledgement distinction.
- MainActivity/layout/EN+AR resources: exit timer, original remaining timer, Continue commitment, visible exit policy and updated help; initial-result gates for Start/duration/native tests. Version now1.0.4/code5.
- README and FINDINGS distinguish new local behavior from historical1.0.3 phone evidence. Two unused old-stop labels removed and narrow lint annotations explain why checked synchronous preference writes are required.

## Verification actually run

- 73 PC/control/diagnostic tests passed in1.086s.
- 95 unique shell tests passed, no skips: full93 in312.721s plus2 later clock/sleep timing regressions in13.596s.
- 18 Android tests passed:12 status +6 cancellation-policy, no failures/errors/skips. Total186 local tests.
- Integrated Gradle test/lint/debug assembly passed in3m14s (zero lint errors,20 warnings before targeted unused-label/checked-commit cleanup). First overlapping-source build failed on a helper/test snapshot mismatch; frozen-source rebuild succeeded.
- Final Gradle test/lint/assembly after cleanup is now running (session9197); result unknown. Canonical shell unchanged since its95 passing tests. Verify APK asset equality/signature/manifest after success.
- EN/AR exit-resource keys and format arguments match; layout XML parses. Independent source review completed; timing and false-ack findings fixed. git diff --check passed, layout CRLF-normalization notice only.

## Pending and boundaries

No installation or phone action performed. Actual five-minute exit, physical-switch recovery during pending exit, cancellation, sleep/wake/app close/reopen, Island profile10, RTL/enlarged text layout remain phone acceptance work. Active commitments/pending exits do not survive controller loss/reboot.

Final APK not yet copied/verified. Use dist/E-Ink-Precommitment-Mode-1.0.4-delayed-stop.apk; preserve existing dist/E-Ink-Precommitment-Mode-1.0.4.apk (internally1.0.3/code4). dist/logs/build outputs are ignored, so transfer APK separately if using another PC. Current source changes uncommitted from clean base553ec2a on codex/nxtpaper-demo.

## Exact next action

Poll current Gradle operation only if still valid. On success copy the unique APK, check aapt manifest, apksigner, exact embedded/source controller equality and hashes. Update FINDINGS and this checkpoint with final proof and remove in-progress claims. Review Git diff/status. Do not install/commit/push. If interrupted, recheck saved source and operation status before acting.

## Resume prompt

Read AGENTS.md, HANDOFF/START_HERE.md, this checkpoint, README.md and FINDINGS.md. Inspect current source/Git and continue the delayed Emergency Stop task from verified evidence. Preserve unrelated work, avoid phone/release actions, and save updated checkpoints.
