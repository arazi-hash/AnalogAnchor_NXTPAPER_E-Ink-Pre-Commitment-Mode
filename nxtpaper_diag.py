"""Read-only ADB diagnostics for a personal TCL NXTPAPER handset.

No mode-changing commands are implemented. Establish the handset's native
entry/exit controls before building the commitment controller.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent
LABEL_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
PROPERTIES = {
    "model": "ro.product.model",
    "manufacturer": "ro.product.manufacturer",
    "android_version": "ro.build.version.release",
    "sdk": "ro.build.version.sdk",
    "fingerprint": "ro.build.fingerprint",
}
# This is an exact allowlist, not an arbitrary shell-command interface.
SNAPSHOT_COMMANDS = {
    **{name: ("shell", "getprop", prop) for name, prop in PROPERTIES.items()},
    "kernel": ("shell", "uname", "-a"),
    "settings_system": ("shell", "settings", "list", "system"),
    "settings_secure": ("shell", "settings", "list", "secure"),
    "settings_global": ("shell", "settings", "list", "global"),
    "input_devices": ("shell", "cat", "/proc/bus/input/devices"),
    "input_capabilities": ("shell", "getevent", "-lp"),
    "input_state": ("shell", "dumpsys", "input"),
    "window": ("shell", "dumpsys", "window", "windows"),
    "activities": ("shell", "dumpsys", "activity", "activities"),
    "display": ("shell", "dumpsys", "display"),
    "packages": ("shell", "pm", "list", "packages", "-f"),
    "services": ("shell", "service", "list"),
    "input_sysfs": ("shell", "ls", "-l", "/sys/class/input/"),
    "switch_sysfs": ("shell", "ls", "-l", "/sys/class/switch/"),
    "vendor_keylayouts": ("shell", "ls", "-l", "/vendor/usr/keylayout/"),
    "system_keylayouts": ("shell", "ls", "-l", "/system/usr/keylayout/"),
}
WATCH_COMMANDS = {
    "input": ("shell", "getevent", "-lt"),
    "logcat": ("logcat", "-b", "main", "-b", "system", "-v", "threadtime", "-T", "1"),
}


class DiagnosticError(Exception):
    pass


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def decode_output(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


@dataclass
class Result:
    command: list[str]
    started_utc: str
    elapsed_seconds: float
    returncode: int | None
    timed_out: bool
    stdout: str
    stderr: str


def run_command(command, timeout=20):
    start_utc, start = utc_now(), time.monotonic()
    try:
        result = subprocess.run(
            command, stdin=subprocess.DEVNULL, capture_output=True,
            encoding="utf-8", errors="replace", timeout=timeout, shell=False,
        )
        return Result(list(command), start_utc, time.monotonic() - start,
                      result.returncode, False, result.stdout, result.stderr)
    except subprocess.TimeoutExpired as error:
        # subprocess.run kills and drains its child before raising.
        return Result(list(command), start_utc, time.monotonic() - start,
                      None, True, decode_output(error.stdout), decode_output(error.stderr))
    except OSError as error:
        raise DiagnosticError(f"Could not run ADB: {error}") from error


def find_adb(explicit=None):
    if explicit or os.environ.get("NXTPAPER_ADB"):
        candidate = Path(explicit or os.environ["NXTPAPER_ADB"]).expanduser()
        if not candidate.is_file():
            raise DiagnosticError(f"ADB executable does not exist: {candidate}")
        return str(candidate.resolve())
    on_path = shutil.which("adb")
    if on_path:
        return on_path
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidate = Path(local_appdata) / "Android/Sdk/platform-tools/adb.exe"
        if candidate.is_file():
            return str(candidate)
    raise DiagnosticError("ADB was not found. Supply --adb with your platform-tools/adb.exe path.")


def parse_devices(output):
    devices = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[1] in {"device", "unauthorized", "offline", "recovery", "sideload", "bootloader"}:
            devices[fields[0]] = fields[1]
    return devices


def select_device(devices, requested=None):
    if requested:
        if requested not in devices:
            raise DiagnosticError("The selected phone is not connected. No other device will be used.")
        serial = requested
    else:
        physical = {serial: state for serial, state in devices.items() if not serial.startswith("emulator-")}
        if not physical:
            raise DiagnosticError("No phone detected. Unlock it, enable USB debugging, reconnect, and accept 'Allow USB debugging?'.")
        if len(physical) != 1:
            raise DiagnosticError("Multiple phones are connected. Choose your TCL with --serial SERIAL.")
        serial = next(iter(physical))
    if serial.startswith("emulator-"):
        raise DiagnosticError("This investigation requires the physical TCL phone, not an emulator.")
    if devices[serial] != "device":
        raise DiagnosticError(f"Phone connection is {devices[serial]}. Check the phone's USB debugging authorization.")
    return serial


class Adb:
    def __init__(self, executable, serial):
        self.executable, self.serial = executable, serial

    def command(self, args):
        return [self.executable, "-s", self.serial, *args]

    def read(self, args, timeout=20):
        return run_command(self.command(args), timeout)


def connect(args):
    executable = find_adb(args.adb)
    listing = run_command([executable, "devices", "-l"])
    if listing.returncode != 0 or listing.timed_out:
        raise DiagnosticError(f"Could not list devices: {listing.stderr.strip() or 'ADB timed out'}")
    return Adb(executable, select_device(parse_devices(listing.stdout), args.serial))


def new_capture(output, label):
    if not LABEL_PATTERN.fullmatch(label):
        raise DiagnosticError("Use a label of 1-64 letters, numbers, underscores, or hyphens; start with a letter or number.")
    base = Path(output).expanduser().resolve()
    destination = base / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "-" + label)
    destination.mkdir(parents=True, exist_ok=False)
    return destination


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def snapshot(adb, output, label, observation=""):
    folder = new_capture(output, label)
    metadata = {"kind": "snapshot", "label": label, "serial": adb.serial,
                "started_utc": utc_now(), "observation": observation, "results": {}}
    identity_success = {}
    def collect(item):
        name, command = item
        started_utc, started = utc_now(), time.monotonic()
        try:
            result = adb.read(command)
        except DiagnosticError as error:
            result = Result(adb.command(command), started_utc,
                            time.monotonic() - started, None, False, "", str(error))
        (folder / f"{name}.txt").write_text(result.stdout, encoding="utf-8")
        (folder / f"{name}.stderr.txt").write_text(result.stderr, encoding="utf-8")
        information = asdict(result)
        information.pop("stdout")
        information.pop("stderr")
        valid = result.returncode == 0 and not result.timed_out and bool(result.stdout.strip())
        return name, information, valid
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            for name, information, valid in executor.map(collect, SNAPSHOT_COMMANDS.items()):
                metadata["results"][name] = information
                if name in PROPERTIES:
                    identity_success[name] = valid
    finally:
        metadata["identity_failures"] = [name for name in PROPERTIES if not identity_success.get(name)]
        metadata["usable"] = not metadata["identity_failures"]
        metadata["ended_utc"] = utc_now()
        write_json(folder / "metadata.json", metadata)
    failed = [name for name, result in metadata["results"].items()
              if result["returncode"] != 0 or result["timed_out"]]
    print(f"Snapshot saved: {folder}")
    if failed:
        print("Unavailable/failed reads (preserved as evidence): " + ", ".join(failed))
    if not metadata["usable"]:
        raise DiagnosticError("Snapshot identity is incomplete: " + ", ".join(metadata["identity_failures"])
                              + f". Evidence remains at {folder}.")
    return folder


def watch(adb, output, seconds, kind):
    folder = new_capture(output, "watch")
    names = list(WATCH_COMMANDS) if kind == "both" else [kind]
    metadata = {"kind": "watch", "serial": adb.serial, "started_utc": utc_now(), "results": {}}
    processes, handles, cleanup_errors = {}, [], []
    start, cap = time.monotonic(), 10 * 1024 * 1024
    stop_reason = "capture_window_completed"
    try:
        for name in names:
            command = adb.command(WATCH_COMMANDS[name])
            metadata["results"][name] = {"command": command, "started_utc": utc_now()}
            try:
                stdout = (folder / f"{name}.txt").open("wb")
                handles.append(stdout)
                stderr = (folder / f"{name}.stderr.txt").open("wb")
                handles.append(stderr)
                processes[name] = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                                   stdout=stdout, stderr=stderr, shell=False)
            except OSError as error:
                metadata["results"][name]["error"] = str(error)
                print(f"Unavailable stream: {name}; {error}", flush=True)
        if not processes:
            stop_reason = "start_or_capture_failed"
        else:
            print(f"Capture ACTIVE for {seconds:g} seconds. Move the slider now; leave it in the target mode.", flush=True)
        warned = set()
        while processes and time.monotonic() - start < seconds:
            for name, process in processes.items():
                if process.poll() is not None and name not in warned:
                    warned.add(name)
                    metadata["results"][name]["ended_early"] = True
                    print(f"Warning: {name} stream exited early; its output and stderr are preserved.", flush=True)
            if all(process.poll() is not None for process in processes.values()):
                stop_reason = "all_streams_exited"
                break
            if any((folder / f"{name}{suffix}.txt").stat().st_size >= cap
                   for name in processes for suffix in ("", ".stderr")):
                stop_reason = "output_limit_reached"
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        stop_reason = "operator_interrupt"
    except OSError as error:
        stop_reason = "start_or_capture_failed"
        metadata["error"] = str(error)
    finally:
        try:
            for name, process in processes.items():
                information = metadata["results"][name]
                stopped = False
                try:
                    stopped = process.poll() is None
                    if stopped:
                        process.kill()
                    process.wait(timeout=10)
                except (OSError, subprocess.TimeoutExpired, KeyboardInterrupt) as error:
                    information.setdefault("cleanup_errors", []).append(str(error) or "Operator interrupted cleanup")
                    cleanup_errors.append(name)
                    if isinstance(error, KeyboardInterrupt):
                        stop_reason = "operator_interrupt"
                    # Retry only this owned ADB client, then continue cleaning up the others.
                    try:
                        if process.poll() is None:
                            process.kill()
                        process.wait(timeout=2)
                    except (OSError, subprocess.TimeoutExpired, KeyboardInterrupt) as retry_error:
                        information["cleanup_errors"].append(str(retry_error) or "Operator interrupted cleanup")
                        if isinstance(retry_error, KeyboardInterrupt):
                            stop_reason = "operator_interrupt"
                finally:
                    information.update({"returncode": process.returncode,
                        "stopped_by_tool": stopped, "ended_utc": utc_now()})
        finally:
            for handle in handles:
                try:
                    handle.close()
                except (OSError, KeyboardInterrupt) as error:
                    cleanup_errors.append(str(error) or "Operator interrupted file closure")
                    if isinstance(error, KeyboardInterrupt):
                        stop_reason = "operator_interrupt"
            for name, information in metadata["results"].items():
                information["available"] = (name in processes and information.get("stopped_by_tool", False)
                    and not information.get("ended_early", False) and not information.get("cleanup_errors")
                    and stop_reason != "start_or_capture_failed")
            metadata.update({"stop_reason": stop_reason, "elapsed_seconds": time.monotonic() - start,
                             "ended_utc": utc_now(), "cleanup_errors": cleanup_errors,
                             "usable": any(result["available"] for result in metadata["results"].values())})
            write_json(folder / "metadata.json", metadata)
    print(f"Capture saved: {folder} ({stop_reason})")
    failed = [name for name, result in metadata["results"].items() if not result["available"]]
    if failed:
        print("Unavailable/failed streams (preserved as evidence): " + ", ".join(failed))
    if stop_reason == "operator_interrupt":
        raise KeyboardInterrupt
    if cleanup_errors or metadata.get("error") or not metadata["usable"]:
        raise DiagnosticError(f"Capture did not complete successfully. Evidence remains at {folder}.")
    if stop_reason == "output_limit_reached":
        print("Warning: capture stopped at the local output size limit.")
    return folder


def parse_settings(text):
    values = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if separator and key:
            values[key] = value
    return values


def load_snapshot(folder):
    folder = Path(folder).expanduser().resolve()
    metadata_path = folder / "metadata.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise DiagnosticError(f"Cannot read snapshot metadata at {folder}: {error}") from error
    if not isinstance(metadata, dict) or metadata.get("kind") != "snapshot":
        raise DiagnosticError(f"This is not a snapshot: {folder}")
    if metadata.get("usable") is False:
        raise DiagnosticError(f"Snapshot identity is incomplete; capture again: {folder}")
    return folder, metadata


def successful_read(folder, metadata, name):
    result = metadata.get("results", {}).get(name, {})
    if result.get("returncode") != 0 or result.get("timed_out"):
        return None
    return (folder / f"{name}.txt").read_text(encoding="utf-8").strip()


def compare(output, before, ink, after=None):
    snapshots = [load_snapshot(before), load_snapshot(ink)]
    if after:
        snapshots.append(load_snapshot(after))
    identities = [(meta.get("serial"), successful_read(folder, meta, "fingerprint"))
                  for folder, meta in snapshots]
    if any(not serial or not fingerprint for serial, fingerprint in identities):
        raise DiagnosticError("Each snapshot needs a successful firmware identity read before comparison.")
    if len(set(identities)) != 1:
        raise DiagnosticError("Snapshots belong to different devices or firmware builds; capture again on the same handset.")
    report = {"warning": "Changed keys are correlations, not verified native mode controls.",
              "snapshots": [str(folder) for folder, _ in snapshots], "settings": {}}
    for namespace in ("system", "secure", "global"):
        readings = [successful_read(folder, meta, f"settings_{namespace}") for folder, meta in snapshots]
        if any(reading is None for reading in readings):
            report["settings"][namespace] = {"available": False}
            continue
        values = [parse_settings(reading) for reading in readings]
        differences = []
        for key in sorted(set(values[0]) | set(values[1])):
            old, new = values[0].get(key), values[1].get(key)
            if old != new:
                row = {"key": key, "normal_before": old, "ink": new}
                if after:
                    row.update({"normal_after": values[2].get(key),
                                "returned_to_baseline": values[2].get(key) == old})
                differences.append(row)
        report["settings"][namespace] = {"available": True, "changes": differences}
        print(f"{namespace}: {len(differences)} changed keys")
    destination = new_capture(output, "comparison") / "settings_diff.json"
    write_json(destination, report)
    print(f"Comparison saved: {destination}")
    print(report["warning"])
    return destination


def build_parser():
    parser = argparse.ArgumentParser(description="Read-only NXTPAPER USB diagnostics. No mode changes, root, or installs.")
    parser.add_argument("--adb", help="Path to adb.exe; also supports NXTPAPER_ADB")
    parser.add_argument("--serial", help="Select a specific attached physical phone")
    parser.add_argument("--output", default=str(ROOT / "logs"), help="Local capture folder (default: project logs)")
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("doctor", help="Check ADB, phone authorization, and model")
    capture = commands.add_parser("snapshot", help="Save read-only state with a label")
    capture.add_argument("label")
    capture.add_argument("--observation", default="", help="Your observed mode and physical slider position")
    live = commands.add_parser("watch", help="Bounded observation while you manually move the slider")
    live.add_argument("--seconds", type=float, default=20)
    live.add_argument("--kind", choices=("both", "input", "logcat"), default="both")
    difference = commands.add_parser("compare", help="Compare local snapshots; no phone required")
    difference.add_argument("before")
    difference.add_argument("ink")
    difference.add_argument("--after")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.action == "compare":
            compare(args.output, args.before, args.ink, args.after)
            return 0
        if args.action == "watch" and not 1 <= args.seconds <= 120:
            raise DiagnosticError("Capture duration must be between 1 and 120 seconds.")
        if args.action == "snapshot" and not LABEL_PATTERN.fullmatch(args.label):
            raise DiagnosticError("Invalid snapshot label. Use letters, numbers, underscores, or hyphens.")
        adb = connect(args)
        if args.action == "doctor":
            print(f"ADB: {adb.executable}")
            print("Phone connected and authorized.")
            for name, property_name in PROPERTIES.items():
                result = adb.read(("shell", "getprop", property_name))
                if result.returncode != 0 or result.timed_out or not result.stdout.strip():
                    raise DiagnosticError(f"Phone identity read failed: {name}; {result.stderr.strip()}")
                print(f"{name}: {result.stdout.strip()}")
        elif args.action == "snapshot":
            snapshot(adb, args.output, args.label, args.observation)
        elif args.action == "watch":
            watch(adb, args.output, args.seconds, args.kind)
        return 0
    except (DiagnosticError, OSError, ValueError) as error:
        print(f"Diagnostic stopped: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Diagnostic stopped by operator. No phone settings were changed.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
