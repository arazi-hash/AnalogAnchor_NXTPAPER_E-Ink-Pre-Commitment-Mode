# E-Ink Pre-commitment Mode

## Standalone Android app (1.0.3 / code 4)

The Android app in `nxtpaper_guard/` uses Shizuku to run its bundled controller on the phone. Starting the guard deploys the controller and verifies its live process and input monitor. This is a personal test build for the TCL NXTPAPER 70 Pro firmware described in [FINDINGS.md](FINDINGS.md). Version **1.0.3 / code 4** builds with passing local checks. An earlier 1.0.3 build passed all four preset choices, the five-minute default, and bilingual UI checks on the handset; the Stop/reset correction was subsequently installed and its live controller verified. The latest boot-state correction awaits artifact and installation verification. No completed live commitment, recovery, or expiry trial is recorded yet.

1. Install the updated APK, start the official Shizuku app, and grant this app Shizuku permission when requested.
2. Start the guard. The default commitment is **five minutes**. Optional **2, 4, 6, or 12 hour** buttons select the next session only.
3. Move the physical switch to **Ink**. The first fresh physical Ink event starts entry; there is no three-move calibration. If the switch was already in Ink when the guard started, move it to Normal, let the native transition finish, then move it to Ink.
4. The selected duration is consumed when entry starts, and the next-session setting returns to five minutes. The active duration stays fixed. The countdown begins only after native Max Ink is fully confirmed.
5. During the commitment, an attempt to return to Normal triggers native Ink recovery without restarting the deadline. TCL's transition and recovery can take several seconds; the app does not promise an immediate screen change.
6. After the commitment ends, leaving the physical switch in Ink keeps reading open. Move it to Normal when finished. The controller's injected commands do not count as physical switch movements.
7. Use the emergency **Stop** override whenever needed. During an active controlled session it cancels the commitment and verifies normal restoration. Stopping idle monitoring leaves the phone's native mode unchanged. Stop, an error, or reboot clears the optional duration back to five minutes.

The compact Arabic and English screen keeps the app name **E-Ink Pre-commitment Mode** in both languages, with the language button at the bottom showing the other language. It shows the commitment, optional durations, and concise guard/Shizuku/switch status. Contextual help replaces repeated reassurance text; there are no marketing or support blocks. Android status-bar, navigation-bar, and cutout insets remain respected.

Physical switch position comes from raw input events. `TSWT_state` is a native software setting and is not proof of the physical position. TCL can report `TSWT_state=-1` at boot; the guard now treats that exact value as unknown and waits for a usable native snapshot without sending mode commands or guessing the switch position. The 1.0.2 first-Ink defect and this boot-state rejection were confirmed during investigation. The updated behavior still needs the repeated live trials listed in [FINDINGS.md](FINDINGS.md).

### Reboot, a different Wi-Fi network, or no Wi-Fi

The guard runs locally and needs no internet connection once running. Reboot ends the shell process. A saved enable preference is a request to resume protection; it is not evidence that protection survived a reboot. The app verifies live process identity and a fresh heartbeat before displaying the guard as running.

For easier startup, use [official Shizuku 13.6 or newer](https://github.com/RikkaApps/Shizuku/releases/tag/v13.6.0). On this Android 16 phone, its **Start on boot** setting can start Shizuku when connected to a trusted Wi-Fi network. In Android's per-network debugging dialog, choose **Always allow on this network** only for a network you trust. Moving to another network may require accepting its debugging dialog; that is separate from pairing Shizuku, which normally only needs to be done once. Automatic startup remains dependent on the phone's firmware and debugging service availability.

If Shizuku is unavailable, the app shows a recovery action. When previously enabled, the guard attempts to resume when an authorized Shizuku binder is delivered. Opening the app after starting Shizuku provides a recovery path. Optional notification permission allows a reminder after boot; declining it does not prevent the guard from running.

With **no Wi-Fi after a cold boot**, a stock unrooted phone cannot be promised automatic Shizuku startup. Use USB debugging and a trusted computer to start Shizuku, then return to the app. On either Windows PC, double-click `START_SHIZUKU_USB.cmd`; it resolves the installed official launcher and has a fallback for older Shizuku. Manual recovery uses the phone's native NXTPAPER controls. After a reboot with the guard disabled, a physical Ink movement produced native Max Ink, but a reported Normal movement still produced no OFF input; repeated physical switching remains under investigation. Losing shell privilege or an OEM killing the process means commitment enforcement is unavailable; this build does not claim immunity from Android process management.

### Build on either PC

Use JDK 17 and Android SDK platform 36 / build-tools 36.0.0. Keep each PC's SDK path in an ignored `nxtpaper_guard/local.properties`, for example `sdk.dir=C:/Users/YOUR_USER/AppData/Local/Android/Sdk`. Then run:

```powershell
cd nxtpaper_guard
.\gradlew.bat testDebugUnitTest lintDebug assembleDebug --max-workers=1 --no-parallel --console=plain
```

The Gradle output is `nxtpaper_guard/app/build/outputs/apk/debug/app-debug.apk`; the local distribution path is `dist/E-Ink-Precommitment-Mode-1.0.3.apk`. Verified artifact hashes and the pending boot-state correction are recorded in [FINDINGS.md](FINDINGS.md). `packageGuardController` copies the canonical root `nxtpaper_guard.sh` into the APK assets during the build. Generated outputs, SDK paths, device evidence, and signing keys are ignored by Git. Commit source, wrapper files, tests, and documentation to sync the two PCs. Debug signing keys are local to each PC; updating an already installed APK from the other PC requires the same private signing key. Never commit that key to GitHub.

`UPDATE_ON_PHONE.cmd` installs the built APK on exactly one connected, authorized phone and opens it. It does not launch a second external controller. Both USB helpers find ADB through `NXTPAPER_ADB`, `PATH`, or the default local Android SDK location.

Android build and controller regression results are recorded in `FINDINGS.md`. Physical-switch repetition, transition timing, Wi-Fi loss, reboot startup, and screen layout require a connected handset trial; automated tests do not establish those device outcomes.

Run `python -m unittest -q` from the repository root. The current Python suite has **147 passing tests**, with no skips: 73 PC/diagnostic tests and 74 shell-controller regressions, completed in 51.472 seconds. The shell regressions execute the shipped script with fake Android commands; they do not operate a phone. On Windows they require Git for Windows' `sh.exe` (or a POSIX shell on Linux). A missing shell skips those regressions and must be reported. Android verification also passed **seven unit tests**, with **zero lint errors and 14 warnings**; the combined Gradle test/lint/debug assembly passed in 15 seconds after the boot-state correction. Stop the PC demo before using the standalone guard so only one controller manages the phone.

## Original USB-connected PC demo

This PC program keeps your USB-connected TCL NXTPAPER 70 Pro in its **native Max Ink** experience for five minutes. Moving the physical slider to Ink starts a session after native Max Ink is confirmed. Early exits trigger native re-entry without restarting the timer. At expiry, the program restores normal mode even if the slider remains in the Ink position.

Native mode controls have been verified on this phone in both slider positions. A corrected **60-second live controller trial passed**, including recovery from an injected native exit and automatic restoration with the slider still ON. The full five-minute controller trial is **pending**. Standalone native transitions take roughly **5–7 seconds**; full early-exit recovery took about **13 seconds** in the controller trial. The original two-second recovery target was not met. See [FINDINGS.md](FINDINGS.md) for the evidence and limitations.

## Run one five-minute session

1. Connect the phone with a USB data cable, unlock it, and accept this PC's USB debugging authorization.
2. Start with the phone fully back in normal mode and the physical slider in its normal position. Wait for any NXTPAPER animation to finish.
3. Keep the PC awake and the USB cable connected. Stop other mode-enforcement programs; the Zenith monitor was stopped for this investigation.
4. Open `C:\AnalogAnchor_NXTPAPER_Demo` in **Windows File Explorer**, then double-click `START_DEMO.cmd`. A file link in the chat opens the source for reading; use File Explorer to run it.
5. Wait until the terminal says **Ready**. Then physically move the slider to normal/OFF, pause for two seconds, and move it to Ink/ON. The screen's colors do not tell you the physical slider position: normal mode can remain on screen with the slider still ON after a completed session.
6. The terminal shows the remaining time. At expiry, wait for **Normal mode fully restored**; the program then stops.

The launcher's **STARTING** message means it is opening the program; wait for **Ready** before moving the slider. **FINISHED** means the program ended, **STOPPED** means an operator interrupt was received, and **NOT RUNNING** means it stopped with an error. The window stays open so you can read the result.

To stop early as the operator, type `stop` and press Enter, or press Ctrl+C. Leave the terminal open while it restores normal. This operator override is intentional for the demonstration.

The phone's existing switch configuration must already select Max Ink with immediate switching. The controller verifies that configuration, refuses unsupported firmware, and stops if the configuration changes during a session. It does not change your selected apps or native defaults. The Analog Anchor app does not need to be among the apps selected for Max Ink because this controller runs on the PC.

Python 3.10+ and Android Platform Tools (ADB) are required. Both are already available on the original PC. No Python packages, Android Studio, phone app installation, or root access are required.

## Run from PowerShell

Open PowerShell in this project folder. The double-click launcher runs one 300-second session; these commands provide a short development trial or repeated sessions:

```powershell
# One 30-second development session
python nxtpaper_demo.py --duration 30 --once

# One five-minute session
python nxtpaper_demo.py --once

# Keep monitoring for additional five-minute sessions
python nxtpaper_demo.py
```

The supported duration is 5–300 seconds. The countdown uses a monotonic clock, and early exits do not extend it. In continuous mode, if the slider remains in Ink at expiry, you must move it back to normal before another Ink movement can start a session. `--once` stops only after the completed session has fully restored normal mode.

ADB is found in this order: `--adb`, the `NXTPAPER_ADB` environment variable, `PATH`, then `%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe`. Set a PC-specific path if needed:

```powershell
python nxtpaper_demo.py --adb "C:\path\to\platform-tools\adb.exe" --once
python nxtpaper_diag.py --adb "C:\path\to\platform-tools\adb.exe" doctor
```

Both programs accept `--serial SERIAL` to select a phone and `--output DIR` for local evidence. The default output is this project's ignored `logs` folder. For the diagnostic tool, put these global options **before** its subcommand.

## Recovery and connection troubleshooting

Automatic restoration depends on the connected PC. If USB disconnects, the PC sleeps, or the process is forcibly killed, restoration cannot be guaranteed. Unlock the phone, move the physical slider to **Ink**, then back to **normal**, and wait for the native transition to finish. Reconnect and restart the controller only after normal mode has settled.

Closing the terminal or killing Python is not the operator stop workflow. Use `stop` + Enter or Ctrl+C while connected so the program can attempt restoration. A second controller on the same PC is refused.

If the phone does not appear, run:

```powershell
python nxtpaper_diag.py doctor
```

- Enable Developer options by finding **Build number** in Settings → About phone or its version details and tapping it seven times. Turn on **USB debugging** in Developer options.
- Keep the phone unlocked, reconnect the data cable, and accept **Allow USB debugging?** for this PC. `unauthorized` means the phone still needs to accept the computer.
- An empty device list means ADB has not connected. Try a known data cable or another USB port.
- Seeing the TCL in File Explorer proves file transfer works; it does not prove ADB works or that a driver is missing. Investigate drivers only if Device Manager shows an unrecognized Android/ADB interface.

## Read-only investigation tools

`START_DIAGNOSTICS.cmd` opens help and checks the connection without changing phone mode. Snapshots read phone identity, settings, and relevant system state. Watches record finite input/Logcat streams without clearing logs.

For a normal → native Max Ink → normal investigation, use the slider yourself while coordinating the transitions with these captures:

```powershell
python nxtpaper_diag.py snapshot normal_before
python nxtpaper_diag.py watch --seconds 20 --kind both
python nxtpaper_diag.py snapshot max_ink
python nxtpaper_diag.py watch --seconds 20 --kind both
python nxtpaper_diag.py snapshot normal_after
```

Move the slider while each watch runs; take snapshots after the corresponding mode settles. Labels allow letters, numbers, underscores, and hyphens. Snapshots create timestamped folders with `metadata.json` and raw `.txt` results. Use `--kind input` or `--kind logcat` for one stream.

Compare the exact folder paths printed by the captures:

```powershell
python nxtpaper_diag.py compare "logs\TIMESTAMP-normal_before" "logs\TIMESTAMP-max_ink" --after "logs\TIMESTAMP-normal_after"
```

Replace the placeholders with actual folder names. Comparison reads saved PC files and writes a settings-difference JSON under the output directory; it does not contact or write to the phone. Record visible launcher behavior and physical slider position under ignored `observations`. Ink Paper display styling alone does not establish native Max Ink: its launcher and selected-app restrictions also matter.

## Validation and both-PC setup

Run the automated checks with:

```powershell
python -m unittest -v
```

The original PC/diagnostic suite has **73 tests**; the current total including standalone shell regressions is **147 passed**, plus **seven Android unit tests**. The 110-test pre-update baseline and current 1.0.3 verification are separated in [FINDINGS.md](FINDINGS.md). In the historical corrected 60-second PC trial, the original deadline stayed fixed through an injected native exit. Max Ink fully recovered in about 13 seconds, the expiry command was about 0.11 seconds after the deadline, and normal mode fully settled 5.68 seconds after that command with the physical slider still ON.

An idle monitor-failure trial on an earlier controller revision also detected a terminated input stream, attempted native normal restoration, confirmed normal mode, and exited with a failure status. It began in Ready/normal mode and did not start a commitment session.

Unit checks and those short trials do not replace the full five-minute handset trial, which remains **pending**. Screen-sleep behavior, USB disconnection, active-session process crashes, repeated physical slider moves during enforcement, and normal calling also need recorded live validation. The idle monitor-failure trial does not establish recovery from those failures during Max Ink.

This project is separate from the landing-page repository. Its local Git branch is `codex/nxtpaper-demo`; no GitHub remote or initial commit has been created yet. Commit reviewed source and documentation to its own GitHub repository, then clone it on the second PC:

```powershell
git clone YOUR_REPOSITORY_URL AnalogAnchor_NXTPAPER_Demo
cd AnalogAnchor_NXTPAPER_Demo
python nxtpaper_diag.py doctor
```

Replace `YOUR_REPOSITORY_URL` with the repository's clone URL. The original PC is ready; no downloads are needed there. On the second Windows PC:

1. Install 64-bit Python 3.10 or newer from [Python's official Windows downloads](https://www.python.org/downloads/windows/). Make Python available to terminal commands during installation, then open a new PowerShell window and confirm `python --version` reports 3.10 or newer.
2. Download the standalone Windows ZIP from [Android's official Platform Tools page](https://developer.android.com/tools/releases/platform-tools). Android Studio is unnecessary. Extract it on that PC, for example so ADB is at `C:\Tools\platform-tools\adb.exe`.
3. Connect the phone, enable USB debugging, and accept the authorization prompt for this PC. Its authorization is separate from the original PC's.
4. In the cloned project folder, check the connection and launch the demo using that PC's actual ADB path:

```powershell
python --version
python nxtpaper_diag.py --adb "C:\Tools\platform-tools\adb.exe" doctor
python nxtpaper_demo.py --adb "C:\Tools\platform-tools\adb.exe" --once
```

Alternatively, set the path for the current PowerShell session before running commands:

```powershell
$env:NXTPAPER_ADB = "C:\Tools\platform-tools\adb.exe"
python nxtpaper_diag.py doctor
python nxtpaper_demo.py --once
```

That temporary environment variable applies to this terminal and its child processes. Double-click launchers need ADB available through `PATH`, the default Android SDK location, or a Windows user environment variable named `NXTPAPER_ADB`. Keep the path local to each PC. Pull the latest committed changes before working.

Keep private captures, screenshots, extracted APKs, observations, virtual environments, and PC-specific configuration in ignored local folders. Handset QA screenshots belong under `captures/`; the existing `current_phone_screen*.png` files are also ignored. Keep the required launcher PNGs in `nxtpaper_guard/branding/` and the Android drawable assets with the source. Review `git status` and the staged diff before committing. This checkout has no initial commit or GitHub remote yet; Android source, scripts, and controller tests must be included in the reviewed source commit before the other PC can pull them.
