"""Firmware-pinned native TCL controls and a raw physical-slider monitor.

Only keyevents 343/344 change phone mode. The physical monitor reads kernel
events, so those framework injections cannot pretend that the slider moved.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from queue import Empty, Queue
import re
import subprocess
import threading
import time

from nxtpaper_diag import Adb, DiagnosticError, connect, find_adb
from nxtpaper_compatibility import (
    CompatibilityError, discover_switch, load_profile, read_native_state,
    validate_keylayout,
)


FIRMWARE_PROFILE = load_profile()
SUPPORTED_MODEL = FIRMWARE_PROFILE["model"]
SUPPORTED_ANDROID = FIRMWARE_PROFILE["android"]
SUPPORTED_SDK = FIRMWARE_PROFILE["sdk"]
SUPPORTED_FINGERPRINT = FIRMWARE_PROFILE["fingerprint"]
KEY_ENTER_MAX_INK = int(FIRMWARE_PROFILE["enter_key"])
KEY_RESTORE_NORMAL = int(FIRMWARE_PROFILE["exit_key"])
NATIVE_TIMEOUT_SECONDS = 3
MODE_PRESET_KEY = FIRMWARE_PROFILE["preset_key"]
IMMEDIATE_SWITCH_KEY = FIRMWARE_PROFILE["immediate_key"]
KEYLAYOUT_PATH = FIRMWARE_PROFILE["keylayout"]

STATE_KEYS = {
    "tswt": FIRMWARE_PROFILE["tswt_key"],
    "ink_style": FIRMWARE_PROFILE["ink_key"],
    "book_style": FIRMWARE_PROFILE["book_key"],
    "applying": FIRMWARE_PROFILE["applying_key"],
    "animation": FIRMWARE_PROFILE["animation_key"],
}
PROFILE_PROPERTIES = {
    "model": ("ro.product.model", SUPPORTED_MODEL),
    "device": ("ro.product.device", FIRMWARE_PROFILE["device"]),
    "android_version": ("ro.build.version.release", SUPPORTED_ANDROID),
    "sdk": ("ro.build.version.sdk", SUPPORTED_SDK),
    "fingerprint": ("ro.build.fingerprint", SUPPORTED_FINGERPRINT),
}
DEVICE_BLOCK = re.compile(r"^add device \d+: (?P<node>/dev/input/event\d+)\s*$", re.MULTILINE)
SWITCH_EVENT = re.compile(
    r"^\s*\[\s*\d+\.\d+\]\s+(?:(?P<node>/dev/input/event\d+):\s+)?"
    r"EV_KEY\s+(?P<key>KEY_BRIGHTNESS_MIN|KEY_BRIGHTNESS_MAX)\s+DOWN\s*$"
)


@dataclass(frozen=True)
class ModeState:
    tswt: int
    ink_style: int
    book_style: int
    applying: bool
    animation: bool

    @property
    def normal(self):
        return self.ink_style == 0 and self.book_style == 0

    @property
    def max_ink(self):
        return self.ink_style == 2 and self.book_style == 1

    @property
    def settled(self):
        return not self.applying and not self.animation


@dataclass(frozen=True)
class SwitchEvent:
    on: bool
    at: float


def _require_physical(adb):
    if not adb.serial or adb.serial.startswith("emulator-"):
        raise DiagnosticError("Native NXTPAPER controls require the physical TCL phone, not an emulator.")


def _checked_read(adb, command):
    captured = adb.read(command, timeout=NATIVE_TIMEOUT_SECONDS)
    if captured.timed_out or captured.returncode != 0:
        detail = captured.stderr.strip() or ("ADB command timed out" if captured.timed_out else "ADB command failed")
        raise DiagnosticError(f"TCL command failed: {' '.join(command)}; {detail}")
    return captured.stdout


def _required_settings(text, required):
    values = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if key not in required:
            continue
        if not separator or key in values:
            raise DiagnosticError(f"Malformed or duplicated NXTPAPER setting: {key}")
        values[key] = value
    missing = sorted(set(required) - values.keys())
    if missing:
        raise DiagnosticError("Missing NXTPAPER settings: " + ", ".join(missing))
    return values


def _number(values, key, allowed):
    raw = values[key]
    if raw not in {str(value) for value in allowed}:
        raise DiagnosticError(f"Unsupported NXTPAPER state: {key}={raw!r}; expected {sorted(allowed)}.")
    return int(raw)


def _validate_presets(values):
    if values[MODE_PRESET_KEY] != "3" or values[IMMEDIATE_SWITCH_KEY] != "1":
        raise DiagnosticError("Native switch configuration must already have Max Ink preset "
                              f"{MODE_PRESET_KEY}=3 and {IMMEDIATE_SWITCH_KEY}=1. No settings were changed.")


class TclAdapter:
    def __init__(self, adb: Adb):
        self.adb = adb
        self._validated = False
        # Freeze reviewed data for this adapter's lifetime. A file edited while
        # a commitment is active cannot silently alter its commands.
        self.profile = FIRMWARE_PROFILE

    def validate(self):
        """Verify this handset profile and its existing native Max Ink preset."""
        self._validated = False
        _require_physical(self.adb)
        profile = {}
        for name, (property_name, expected) in PROFILE_PROPERTIES.items():
            actual = _checked_read(self.adb, ("shell", "getprop", property_name)).strip()
            if actual != expected:
                raise DiagnosticError(f"Unsupported TCL firmware/profile: {name}={actual!r}; expected {expected!r}.")
            profile[name] = actual
        values = _required_settings(
            _checked_read(self.adb, ("shell", "settings", "list", "secure")),
            {MODE_PRESET_KEY, IMMEDIATE_SWITCH_KEY},
        )
        _validate_presets(values)
        self._validated = True
        return profile

    def read_state(self, *, check_configuration=True):
        _require_physical(self.adb)
        try:
            values = read_native_state(_checked_read(self.adb, ("shell", "settings", "list", "secure")),
                                       self.profile, check_configuration=check_configuration)
        except CompatibilityError as error:
            raise DiagnosticError(str(error)) from error
        return ModeState(values["tswt"], values["ink"], values["book"],
                         bool(values["applying"]), bool(values["animation"]))

    def _keyevent(self, key):
        if not self._validated:
            raise DiagnosticError("Validate the supported phone and native preset before sending mode controls.")
        # Never use a successful startup check as authorization for a later
        # command. Restoration has no compatibility bypass either.
        self.validate()
        if _checked_read(self.adb, ("shell", "id", "-u")).strip() != "2000":
            raise DiagnosticError("Shell privilege unavailable; no native mode command was sent.")
        discover_switch_node(_checked_read(self.adb, ("shell", "getevent", "-lp")))
        validate_switch_keylayout(_checked_read(self.adb, ("shell", "cat", KEYLAYOUT_PATH)))
        if key not in (int(self.profile["enter_key"]), int(self.profile["exit_key"])):
            raise DiagnosticError("Unreviewed native command refused.")
        state = self.read_state()
        if state.tswt == -1 or not state.settled:
            raise DiagnosticError("Native mode is unknown or changing; no native command was sent. Normal is not confirmed.")
        _checked_read(self.adb, ("shell", "input", "keyevent", str(key)))

    def enter_max_ink(self):
        self._keyevent(KEY_ENTER_MAX_INK)

    def restore_normal(self):
        self._keyevent(KEY_RESTORE_NORMAL)


def discover_switch_node(capabilities):
    """Identify the driver by name and capabilities, never by boot-dependent number."""
    try:
        return discover_switch(capabilities, FIRMWARE_PROFILE)
    except CompatibilityError as error:
        raise DiagnosticError(str(error)) from error


def validate_switch_keylayout(text):
    """The tested firmware maps Linux MIN/592 to ON, and MAX/593 to OFF."""
    try:
        validate_keylayout(text, FIRMWARE_PROFILE)
    except CompatibilityError as error:
        raise DiagnosticError(str(error)) from error


def parse_switch_event(line, at, device_path=None):
    match = SWITCH_EVENT.fullmatch(line)
    if not match or (match.group("node") and device_path and match.group("node") != device_path):
        return None
    return SwitchEvent(on=match.group("key") == "KEY_BRIGHTNESS_MIN", at=at)


class PhysicalSwitchMonitor:
    def __init__(self, adb: Adb, output_folder):
        self.adb = adb
        self.output_folder = Path(output_folder) if output_folder is not None else None
        self.device_path = None
        self.raw_log = None
        self.stderr_log = None
        self._raw_handle = None
        self._stderr_handle = None
        self._process = None
        self._thread = None
        self._events = Queue()
        self._stopping = threading.Event()
        self._error = None
        self._started = False
        self._closed = False

    def start(self):
        if self._started or self._closed:
            raise DiagnosticError("The physical-switch monitor can only be started once.")
        _require_physical(self.adb)
        capabilities = _checked_read(self.adb, ("shell", "getevent", "-lp"))
        self.device_path = discover_switch_node(capabilities)
        layout = _checked_read(self.adb, ("shell", "cat", KEYLAYOUT_PATH))
        validate_switch_keylayout(layout)
        try:
            if self.output_folder is not None:
                self.output_folder.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
                self.raw_log = self.output_folder / f"physical_switch_{stamp}.log"
                self.stderr_log = self.output_folder / f"physical_switch_{stamp}.stderr.log"
                self._raw_handle = self.raw_log.open("x", encoding="utf-8")
                self._stderr_handle = self.stderr_log.open("xb")
            self._process = subprocess.Popen(
                self.adb.command(("shell", "getevent", "-lt", self.device_path)),
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=self._stderr_handle if self._stderr_handle is not None else subprocess.DEVNULL,
                text=True, encoding="utf-8", errors="replace", bufsize=1, shell=False,
            )
            self._started = True
            self._thread = threading.Thread(target=self._read_events, name="nxtpaper-physical-switch", daemon=True)
            self._thread.start()
        except (OSError, RuntimeError) as error:
            try:
                self.close()
            except DiagnosticError:
                pass
            raise DiagnosticError(f"Could not start physical-switch monitoring: {error}") from error
        return self

    def _read_events(self):
        try:
            for line in self._process.stdout:
                received_at = time.monotonic()
                if self._raw_handle is not None:
                    self._raw_handle.write(line)
                    self._raw_handle.flush()
                event = parse_switch_event(line, received_at, self.device_path)
                if event is not None:
                    self._events.put(event)
            if not self._stopping.is_set():
                self._error = "Physical-switch input stream ended unexpectedly."
        except (OSError, ValueError) as error:
            if not self._stopping.is_set():
                self._error = f"Could not read the physical-switch input stream: {error}"
        finally:
            if self._raw_handle is not None:
                try:
                    self._raw_handle.close()
                except OSError as error:
                    if not self._stopping.is_set():
                        self._error = f"Could not save the physical-switch raw log: {error}"

    def drain(self):
        events = []
        while True:
            try:
                events.append(self._events.get_nowait())
            except Empty:
                return events

    def check_alive(self):
        if not self._started or self._closed:
            raise DiagnosticError("The physical-switch monitor is not running.")
        if self._error or self._process.poll() is not None or not self._thread.is_alive():
            detail = self._error or "Physical-switch ADB client stopped."
            if self.stderr_log is not None:
                detail += f" See local stderr: {self.stderr_log}"
            raise DiagnosticError(detail)

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._stopping.set()
        errors = []
        if self._process is not None:
            try:
                if self._process.poll() is None:
                    self._process.kill()
                self._process.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired) as error:
                errors.append(str(error))
                try:
                    if self._process.poll() is None:
                        self._process.kill()
                    self._process.wait(timeout=1)
                except (OSError, subprocess.TimeoutExpired) as retry_error:
                    errors.append(str(retry_error))
        if self._thread is not None and self._thread.ident is not None:
            self._thread.join(timeout=2)
            if self._thread.is_alive():
                errors.append("Physical-switch reader did not stop within two seconds.")
        # Closing stdout while its reader is blocked can itself block on an IO lock.
        reader_stopped = self._thread is None or not self._thread.is_alive()
        handles = [self._stderr_handle]
        if reader_stopped:
            handles.append(self._raw_handle)
            if self._process is not None:
                handles.append(self._process.stdout)
        for handle in handles:
            if handle is not None:
                try:
                    handle.close()
                except OSError as error:
                    errors.append(str(error))
        if errors:
            raise DiagnosticError("Physical-switch cleanup failed: " + "; ".join(errors))
