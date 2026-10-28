# Recovering after an update or lost connection

Prepared 28 October 2026. Local compatibility safeguards and the 1.0.5 APK are saved; read [the current task checkpoint](../HANDOFF/tasks/firmware-resilience-2026-10-28.md) for final test status. The APK is not installed or physically accepted. This guide does not authorize handset changes and does not establish new firmware support.

## For the founder

An update can change the firmware number without breaking TCL's controls, or it can change something the guard actually needs. The app should explain the difference rather than require a new assistant to guess.

1. Do not uninstall the guard, clear its data, reset the phone, or accept another update as a repair step.
2. Keep the phone connected to a trusted PC if available. Unlock it and inspect any USB debugging authorization prompt.
3. Ask the next agent to read this project and run its read-only compatibility diagnosis. The PC command from the project folder is `python nxtpaper_diag.py compatibility --json`. With multiple connected ADB endpoints, put `--serial` and the intended handset identifier before `compatibility`.
4. Give the agent the diagnosis and latest handoff. Do not describe a matching firmware/profile result as proof of protection; running-controller status and handset behavior need their own evidence.
5. If the installed app reports an older live controller, leave it in place until its current session can be safely completed/stopped through a supported route. An idle reading does not guarantee it remains idle.

For manual native recovery, remove magnetic cases/holders, use the phone's physical NXTPAPER controls, and allow the native transition to finish. First establish whether a live guard is still enforcing; it may intentionally re-enter Ink if its commitment remains active. Its supported Stop may include the five-minute wait. Do not repeatedly fight that behavior or kill processes at random. If no working controller is available, the native physical controls are the manual recovery path. Normal mode must be visibly/technically confirmed; countdown zero is not confirmation.

## Read the diagnosis

| Result or observation | Meaning | Next step |
| --- | --- | --- |
| No authorized ADB phone | The PC cannot inspect this phone yet. | Check data cable, port, unlocked phone, USB debugging, and this PC's authorization. A File Explorer connection alone does not prove ADB. Never operate another connected phone by accident. |
| Shizuku unavailable/unauthorized | The on-phone app lacks the required shell bridge. | Inspect official Shizuku version, process, authorization, and startup state. Once separately approved, use the existing USB launcher or official startup flow. This is a phone change, not part of read-only diagnosis. |
| `UNVERIFIED_BUILD` | Identity differs from the reviewed profile; actual native controls might still work. | Compare identity and structural evidence, inspect relevant native code if needed, and propose a reviewed candidate profile. Do not just replace/remove the old fingerprint. |
| `CAPABILITY_MISSING` | Required native state, switch mapping, tool, or access failed/was unknown. | Repair the specific layer using evidence. Missing permission is different from renamed native state. Do not infer command numbers from similar model names. |
| `VERIFIED` | Observed checks match a historically qualified profile. | Independently inspect live process/controller identity and current state. This result is not a physical acceptance test or proof that enforcement is alive. |
| App/controller mismatch | Package/asset differs from the live script/process. | Treat as lifecycle/version reconciliation, separately from firmware. Preserve an unknown live controller; later use a controlled stop/completion and confirm stopped before deployment. |
| Android app fails to open | Application startup itself failed. | Collect bounded crash evidence, inspect installed version/SDK/signature and reproduce locally. Do not assume TCL native controls are broken. A previously running shell controller may still exist. |
| Native transition not confirmed | A command may have run without reaching settled Ink/Normal. | Preserve diagnostic evidence, disclose protection/restoration is unconfirmed, and follow native manual recovery. Never equate shell success with completed transition. |

If required controls/privileges have genuinely been removed and no supported stock route is established, say so. Do not replace the requested native experience with a screen filter or generic blocker and call it repaired.

## Agent procedure

### First, observe only

Read the root instructions, newest handoff, resilience task, and actual Git/source state. Preserve unrelated changes. Select exactly one authorized physical handset and use bounded read-only calls. The diagnostic path must not deploy a controller, write language/preference/status files, signal a process, inject keys, start Shizuku, disable a package, or reboot. Inspect helpers before running them.

Collect the following as separate facts:

- Model, region/device, Android/SDK, fingerprint, security patch, and relevant native package versions/hashes.
- Shell identity/available privileges, Shizuku process/version/authorization, and USB versus wireless debugging state.
- Native settings/configuration, switch capabilities and keylayout, and whether values are valid/unknown.
- Installed APK/version/signature, bundled asset/profile, deployed script, live process identity, boot identity, and fresh heartbeat.
- Current updater package/user state and active/staged OTA evidence without initiating a check/download/install.

Do not dump personal notifications, accounts, contacts, or network secrets into shareable reports. Keep raw private captures ignored. Default shareable diagnosis should omit the device serial.

### Then choose the affected layer

1. If connection/privilege is unavailable, propose its supported recovery before editing TCL mappings.
2. If only firmware identity differs, compare native structure and behavior evidence; a matching schema narrows the work but cannot qualify it alone.
3. If native capability changed, inspect the relevant new system implementation and propose a bounded adapter/profile change with a known restoration route. Do not install old system APKs over the new OS.
4. If the app and live controller differ, do not redeploy while a live controller might own a commitment. An `IDLE` observation can race with the physical switch. Later authorized reconciliation must use supported completion/stop and confirm actual stopped state.
5. If source/APK behavior is wrong, make the smallest local fix and run relevant tests before proposing phone work.

New builds remain unverified until separately approved handset qualification. No automatic profile promotion, remote executable repair, or blanket unsupported-firmware override is allowed. A cached report cannot authorize native commands. Restoration also needs the original reviewed profile/current valid state; it can involve both ON and OFF commands.

The current Android build and PC controller use the single reviewed AMD9 profile. The diagnostic registry can compare additional reviewed profiles, but adding a file alone does not change the Android build's selected asset or qualify a native adapter. Review the build selection and both consumers when adding support. Native package versions are reported for comparison; they are not a complete verified image of TCL's system components.

### Physical qualification, only when separately authorized

Start with all controllers stopped and native Normal confirmed. Establish a reviewed candidate mapping and predetermined restoration route. Run bounded native entry/restore trials, real physical switch detection and early-exit recovery, unchanged deadlines, ordinary expiry/extended reading, delayed Stop/Continue, app closure/sleep, and profile-10 behavior. Verify fresh native settled state after transitions. Test actual elapsed Stop timing rather than shortening the rule silently.

Keep outcomes separate: mocked tests, injected native events, genuine switch trials, installation, and long-duration use. A successful short trial does not establish 2/4/6/12-hour endurance. Record reboot/Shizuku recovery separately because reboot/controller loss still ends active enforcement.

## Update protection assessment

The observed phone already had `ota_disable_automatic_update=1`. That is a useful setting, not proof that pressing Update/Continue cannot install firmware. The exact observed TCL package was `com.tcl.fota.system`.

Before suggesting a restriction, establish its actual service owner/execution user, package/user enabled state, staged/active update status, expected impact, exact undo procedure, and what can be safely verified without installing an OTA. Do not disable every user copy merely because the package appears in users 0 and 10. Do not interfere with an applying update or guess when update state is unknown. A restriction can delay security fixes and may be reset/replaced by newer firmware. It is not currently applied or qualified by this guide.

Official Device Owner scheduling is a different deployment model; personal Island ownership is insufficient. It is outside this stock/no-reset project stage. A spare canary phone is optional. OEM integration availability remains a research question.

## Keep a kit for both PCs

| Commit-ready project material | Private material transferred separately |
| --- | --- |
| Source, wrapper files, strict profiles, regression tests, sanitized compatibility history, build/recovery instructions, newest handoff | Correct APK and hash, controller/profile asset copies, raw device captures/extracted native packages, private signing key, personal backup and PC-specific SDK paths |

Preserve the historical known APK rather than replacing it with an artifact that only has a similar filename. Verify internal version, signature, and bytes. Updating the same installed app from the other PC requires the same private signing key. Never commit that key. Source synchronization requires actual commit/push/pull authorization and execution; matching chat/project names do not transfer files. Ignored APKs and captures require a separate transfer.

An APK/settings/native-package archive helps diagnose and rebuild the application. It does not preserve a bootable Android firmware image. Android rollback protection may refuse older firmware. TCL's general PC upgrade tool installs latest software; no exact-model supported downgrade is established here. Do not switch A/B slots, flash partitions, or factory reset as an assumed recovery path.

Read [the full plan](../HANDOFF/tasks/firmware-resilience-plan-2026-10-28.md) for official sources and [the standalone Antigravity prompt](../HANDOFF/tasks/antigravity-firmware-resilience-prompt.md) to continue with another agent.
