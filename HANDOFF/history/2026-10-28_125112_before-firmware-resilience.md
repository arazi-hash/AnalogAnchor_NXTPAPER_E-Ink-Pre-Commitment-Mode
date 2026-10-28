# Latest checkpoint — AnalogAnchor_NXTPAPER_Demo

Updated: 2026-10-28 (Asia/Bahrain)
Task owner: Codex — delayed Emergency Stop
Status: local implementation and APK complete; phone acceptance pending
Project root: C:\AnalogAnchor_NXTPAPER_Demo

## Objective and latest user steering

The founder approved the plan and said "proceed". Emergency Stop now waits five minutes during every five-minute, 2-hour, 4-hour, 6-hour and 12-hour commitment, including entry. Protection continues. Earlier original commitment expiry triggers the requested exit sooner. Repeated requests preserve the deadline. Continue commitment cancels the exit without changing the original timer. At zero, Normal restoration must finish before claiming completion. Idle/completed stopping remains immediate.

Local implementation, tests and APK preparation were authorized. Installation, handset operations, commits and pushes were not performed and still require authorization. Existing reboot/controller-loss limits remain. Preserve compact EN/AR UI, native app selections and ordinary expiry/extended reading when no exit is requested.

## Completed and saved

- nxtpaper_guard.sh + test_nxtpaper_guard.py: controller-owned uptime deadline, daemon/boot-bound request-stop and cancel-stop mailboxes, due-before-cancel ordering, fresh-clock and missed-tick handling; 10-field status appends exitDeadline:exitRemaining. Existing internal stop is recovery-only.
- Android GuardRuntime/GuardStatus/GuardApplication + new GuardExitPolicy and tests: durable future-restart preference, daemon-specific cancellation recovery, no live-file deletion on pending/timeouts, preserved unknown live controllers on updates, accurate fallback acknowledgement handling.
- MainActivity/layout/EN+AR resources: exit countdown, original remaining time, Continue commitment, visible rule/help, initial-result gates and actual STOPPED requirement for native tests. Version 1.0.4 / code 5.
- README/FINDINGS record behavior and local evidence separately from historical 1.0.3 device evidence.
- Deliverable: [E-Ink-Precommitment-Mode-1.0.4-delayed-stop.apk](../dist/E-Ink-Precommitment-Mode-1.0.4-delayed-stop.apk), 7,139,616 bytes. SHA-256: 9b83a4a25b0a8bda89f5aecc434ce9ce90b858b2e7411da1536dfd929ea246d4. Hash sidecar alongside it. Preserve older 1.0.4-named APK (internally 1.0.3 / code 4).

## Verification actually run

- 168 unique Python tests passed, no skips: 73 PC/control/diagnostic in 1.086s; full 93 shell tests in 312.721s plus 2 later timing regressions in 13.596s = 95 shell tests. Mocked Android commands; no phone.
- 18 Android unit tests passed, no failures/errors/skips: 12 status + 6 policy. Total 186 local tests.
- Final Gradle testDebugUnitTest/lintDebug/assembleDebug with one worker/no parallel passed in 32s; lint 0 errors / 14 warnings. Earlier integrated rebuild passed in 3m 14s; first overlapping-source attempt failed on a new helper/test snapshot mismatch and was corrected by the integrated rebuilds.
- Manifest verified: com.analoganchor.nxtpaperguard, 1.0.4 / code 5, min SDK 26, target SDK 36. APKv2 signature verifies with historical 1.0.3 debug certificate SHA256 bb57ddf958f90324e214020a7f65e5aba9f4e3dd7ba1ebd6454868af8cb41d2e.
- Packaged/source controller byte-for-byte equal, 48,439 bytes LF; SHA-256 7765bcab3e277a669752f538d0b9ae4d270e552a4c44223e4a743f3e65b023d3.
- Final EN/AR resource/placeholder and XML parsing checks passed. Independent source review completed; deadline timing and ambiguous acknowledgement findings fixed. Whitespace checks passed; layout CRLF-normalization notice only.
- Detailed ignored local proof: logs/delayed-exit-verification-2026-10-28.json. No operations still running.

## Working tree and boundaries

Started clean on codex/nxtpaper-demo at 553ec2a. This task's controller/Android/tests/docs/handoff changes remain uncommitted; new helper/tests and checkpoint histories are intended source additions. No unrelated work overwritten. APK/build/logs are ignored; transfer the APK separately between PCs.

No handset installation or operation was performed. Actual real-time exit, pending physical-switch recovery, cancellation, app closure/reopening, sleep/wake, Island profile 10, EN/AR and enlarged-text layout still need phone acceptance. Old device results do not prove new behavior. Active commitments and pending exits are not recovered across controller loss/reboot. An unknown live old controller is preserved; stop/finish it using the old version before updating rather than replacing an active commitment.

## Exact next action

For source work, review Git status/diff and the evidence in FINDINGS. Do not repeat passed tests unless source changes or a new concern justifies it. If the founder authorizes phone installation/testing, first inspect the currently installed version, firmware and live guard state read-only, verify signer/version compatibility, coordinate safe old-controller completion, then install without clearing data and perform the manual acceptance cases. Commit/push only when authorized. Local implementation/APK task is complete.

## Resume prompt

Read AGENTS.md, HANDOFF/START_HERE.md, this checkpoint, README.md and FINDINGS.md. Check current files and Git state. The delayed Emergency Stop APK is prepared and locally verified; phone acceptance and GitHub sync remain separate authorized steps. Preserve data, unrelated work and continuity checkpoints.
