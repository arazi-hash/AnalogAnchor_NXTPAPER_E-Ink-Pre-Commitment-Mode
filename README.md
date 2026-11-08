# NXTPAPER_E-Ink-Pre-Commitment-Mode

**Designed for compatible TCL NXTPAPER phones with native Max Ink; compatibility testing is required.**

Release target `1.0.6-beta.3` / code `9` opens the website in the language selected
in the app. It includes the clearer setup explanations and compatibility
reporting introduced in beta.2. The tested reference is the TCL NXTPAPER 70 Pro
T807D/Frida on Android 16 AMD9. Other eligible phones and system builds must pass
setup on the exact handset. Push/cycle buttons need a separate reviewed adapter.
See [compatibility](docs/COMPATIBILITY.md) and [handset evidence](FINDINGS.md).

## App setup

1. Install the [GitHub beta](https://github.com/arazi-hash/AnalogAnchor_NXTPAPER_E-Ink-Pre-Commitment-Mode/releases/tag/v1.0.6-beta.3), start official Shizuku, and grant access to this app.
2. Open the **Phone setup** controls. Read the experimental status and native recovery instructions. Checks inspect the phone before sending any mode commands. An existing live or uncertain controller must be resolved safely before setup can run.
3. Follow the genuine physical Normal → Max Ink → Normal test. Confirm that TCL's full native reading environment and selected-app restrictions appeared.
4. Follow the bounded software entry, re-entry and restoration test. It runs independently of the activity, so the native launcher hiding the app does not erase progress. **Cancel test** immediately attempts restoration; it never starts a commitment or a five-minute Stop wait.
5. Enable commitments only after all required checks pass and Normal restoration is confirmed.

Five minutes remains the default commitment; optional durations are 2, 4, 6 or 12 hours. Physical early exit during a commitment triggers native Max Ink recovery without renewing the deadline. Emergency Stop waits five minutes or the earlier commitment deadline; **Continue commitment** cancels the exit request without extending the session. Ordinary expiry permits extended reading until you move the switch to Normal.

On 7 November 2026, the founder's AMD9 phone running `1.0.6-beta.1` passed the guided native trial,
physical early-exit recovery, ordinary five-minute expiry, actual delayed Stop /
Continue controller transactions and brief sleep/wake checks. Those trials used
a non-debuggable release acceptance copy signed for the existing installation;
its contents matched the corresponding public APK except for signing metadata.
The startup guide explains setup when it is required. **Later** brings the guide
back on the next visit. **Got it** remembers the acknowledgement for the current
setup. Use **Phone setup → Show** to reopen the guide or run the test.
See [the recorded results and limits](FINDINGS.md).

If Max Ink closes the app screen, reopen it to inspect progress. Screen color alone is not proof of the physical switch position. Native transitions can take several seconds. Remove magnetic cases/holders when investigating missing switch events; [TCL's guidance](https://www.tcl.com/global/en/support-mobile/faq/q1770346246101540) describes magnetic interference near the NXTPAPER key.

## System updates and recovery

Setup is local and bound to the tested build, adapter revision, runtime key mapping, active layout and relevant native component versions. Relevant changes invalidate that result and require fresh checks/setup. A cached success never overrides missing Shizuku access or changed controls. No executable profiles are downloaded, and no updater packages are automatically disabled.

Reboot, lost privileges or controller loss ends enforcement. An old commitment is not recovered by restarting the app. After reboot, restart Shizuku and verify the live controller before relying on protection. With no Wi-Fi, use the trusted USB helper `START_SHIZUKU_USB.cmd`; stock unrooted phones cannot be promised automatic Shizuku startup offline.

For manual recovery, use TCL's physical switch: move to Ink, then back to Normal and let the native transition finish. Never flash/reset or uninstall as routine troubleshooting. Read [recovery precautions](compatibility/RECOVERY.md) and [the original seven approaches](HANDOFF/tasks/firmware-resilience-plan-2026-10-28.md).

Preview a compatibility report before choosing to share it. Reports omit serials, selected app names, unrelated settings and process tokens. The app does not request INTERNET permission or upload reports in the background. See [privacy and permissions](PRIVACY.md).

## Report a setup result

In beta.2 or later, open **Phone setup → Show → Preview compatibility
report**. A basic report is available even when Shizuku cannot connect. Review it,
choose **Copy report**, then **Open GitHub report form**. Paste the report, select
your result and submit the form yourself. Successful tests are useful too. **Share**
opens Android's share menu for another destination.

Owners using beta.1 can use its **Share this report** action and open
the [GitHub compatibility form](https://github.com/arazi-hash/AnalogAnchor_NXTPAPER_E-Ink-Pre-Commitment-Mode/issues/new?template=compatibility.yml)
directly. Include the exact phone/build and leave uncertain details as unknown.
The [compatibility guide](docs/COMPATIBILITY.md) includes troubleshooting guidance
and a short prompt for asking an AI assistant to interpret your reviewed report.

## Build and release

Use JDK 17, Android SDK platform36/build-tools36.0.0 and each PC's ignored `nxtpaper_guard/local.properties`. From `nxtpaper_guard`:

```powershell
.\gradlew.bat testDebugUnitTest lintDebug assembleDebug --max-workers=1 --no-parallel --console=plain
```

From the repository root, run `python -m unittest -q`. Shell regressions need Git for Windows `sh.exe` and use fake Android commands; they do not operate the phone. [FINDINGS.md](FINDINGS.md) distinguishes historical results from current beta checks.

The public beta.1, beta.2 and beta.3 APKs share a signing certificate and support an
in-place update. Older development and private acceptance copies use a different
certificate and need a coordinated migration that protects existing app data.
Release builds require the permanent private key, which is stored outside Git.
See [release/signing and acceptance gates](docs/RELEASE.md), [release notes](RELEASE_NOTES.md)
and [tester-experience handoff](HANDOFF/tasks/tester-experience-2026-11-07.md).

The existing [GitHub repository](https://github.com/arazi-hash/AnalogAnchor_NXTPAPER_E-Ink-Pre-Commitment-Mode) is the release source. GitHub prerelease and ShizuCoreFetch are the first intended channels; metadata alone does not mean the app is listed. IzzyOnDroid eligibility is separate because of its current AI-code policy. Source is [Apache-2.0](LICENSE); dependencies retain their [own notices](THIRD_PARTY_NOTICES.md).


## Original USB-connected PC demo (historical evidence)

The following sections describe the separate PC demo and its recorded October
2026 trials. They do not replace the Android beta evidence above. Current PC
native commands use the shared compatibility registry and require a matching
local qualification from the phone's guided setup.
Run one controller at a time. Complete or stop the on-phone guard through its
supported route before starting the PC demo; preserve an unknown live controller.

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

The phone's existing switch configuration must already select Max Ink with immediate switching. The controller verifies that configuration, refuses missing/ambiguous controls or stale qualification, and stops if the configuration changes during a session. It does not change your selected apps or native defaults. The Analog Anchor app does not need to be among the apps selected for Max Ink because this controller runs on the PC.

Python 3.10+ and Android Platform Tools (ADB) are required. No third-party Python packages, Android Studio or root access are needed for the PC runtime. The original trials did not require a phone app; the current native-command gates additionally require the matching guided qualification described above.

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

The historical October PC/diagnostic baseline had **73 tests**, and the 1.0.3 standalone checkpoint recorded **153 Python + eight Android tests**. These are historical counts; [FINDINGS.md](FINDINGS.md) records later beta verification separately. In the corrected 60-second PC trial, the original deadline stayed fixed through an injected native exit. Max Ink fully recovered in about 13 seconds, the expiry command was about 0.11 seconds after the deadline, and Normal fully settled 5.68 seconds after that command with the physical slider still ON.

An idle monitor-failure trial on an earlier controller revision also detected a terminated input stream, attempted native normal restoration, confirmed normal mode, and exited with a failure status. It began in Ready/normal mode and did not start a commitment session.

The historical 1.0.3 standalone APK's full five-minute entry, expiry and post-expiry physical Normal trial passed. The original USB-connected PC controller's full five-minute trial remains pending. The 7 November Android beta trials added brief sleep/wake and delayed-exit evidence, but do not establish sustained hours, twenty consecutive recoveries, USB-loss behavior, active-session process crashes, reboot recovery or calling. The earlier idle monitor-failure trial does not establish those outcomes either.

This project is separate from the landing-page repository. Its existing [arazi-hash GitHub repository](https://github.com/arazi-hash/AnalogAnchor_NXTPAPER_E-Ink-Pre-Commitment-Mode) is configured as `origin`. [HANDOFF/LATEST.md](HANDOFF/LATEST.md) records current source, verification and publication status; old task snapshots do not establish the current Git state. To work on the second PC, clone that existing repository and pull the latest published source:

```powershell
git clone https://github.com/arazi-hash/AnalogAnchor_NXTPAPER_E-Ink-Pre-Commitment-Mode.git AnalogAnchor_NXTPAPER_Demo
cd AnalogAnchor_NXTPAPER_Demo
python nxtpaper_diag.py doctor
```

The original PC is ready; no downloads are needed there. On the second Windows PC:

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

Keep private captures, unreviewed screenshots, extracted APKs, observations, virtual environments, and PC-specific configuration in ignored local folders. Handset QA screenshots belong under `captures/`; the existing `current_phone_screen*.png` files are also ignored. Only privacy-reviewed publication screenshots belong in the tracked Fastlane image folders. Do not publish native launcher captures containing personal app selections. Required launcher PNGs, Android source, scripts, wrapper files, and tests are tracked source assets. Review `git status` and the source diff before committing; the latest changes become available to the other PC after they are committed and pushed to the existing repository.
