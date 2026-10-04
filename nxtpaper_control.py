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


SUPPORTED_MODEL = "T807D"
SUPPORTED_ANDROID = "16"
SUPPORTED_SDK = "36"
SUPPORTED_FINGERPRINT = "TCL/T807D_EEA/Frida:16/BP2A.250605.031.A3/AMD9:user/release-keys"
KEY_ENTER_MAX_INK = 343
KEY_RESTORE_NORMAL = 344
NATIVE_TIMEOUT_SECONDS = 3
MODE_PRESET_KEY = "tct_nxtpaper_mode_select"
IMMEDIATE_SWITCH_KEY = "tct_nxtpaper_switch_imm"
KEYLAYOUT_PATH = "/system/usr/keylayout/Generic.kl"

STATE_KEYS = {
    "tswt": "TSWT_state",
    "ink_style": "nxtpaper_ink_style_state",
    "book_style": "nxtpaper_book_style_state",
    "applying": "nxtpaper_is_applying_theme",
    "animation": "nxtpaper_animation_state",
}
PROFILE_PROPERTIES = {
    "model": ("ro.product.model", SUPPORTED_MODEL),
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
        required = set(STATE_KEYS.values())
        if check_configuration:
            required |= {MODE_PRESET_KEY, IMMEDIATE_SWITCH_KEY}
        values = _required_settings(
            _checked_read(self.adb, ("shell", "settings", "list", "secure")),
            required,
        )
        if check_configuration:
            _validate_presets(values)
        return ModeState(
            tswt=_number(values, STATE_KEYS["tswt"], {0, 1}),
            ink_style=_number(values, STATE_KEYS["ink_style"], {0, 1, 2}),
            book_style=_number(values, STATE_KEYS["book_style"], {0, 1}),
            applying=bool(_number(values, STATE_KEYS["applying"], {0, 1})),
            animation=bool(_number(values, STATE_KEYS["animation"], {0, 1})),
        )

    def _keyevent(self, key):
        if not self._validated:
            raise DiagnosticError("Validate the supported phone and native preset before sending mode controls.")
        _checked_read(self.adb, ("shell", "input", "keyevent", str(key)))

    def enter_max_ink(self):
        self._keyevent(KEY_ENTER_MAX_INK)

    def restore_normal(self):
        self._keyevent(KEY_RESTORE_NORMAL)


def discover_switch_node(capabilities):
    """Identify the driver by name and capabilities, never by boot-dependent number."""
    matches = list(DEVICE_BLOCK.finditer(capabilities))
    candidates = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(capabilities)
        block = capabilities[match.end():end]
        name = re.search(r'^\s*name:\s*"([^"\r\n]+)"\s*$', block, re.MULTILINE)
        if name and name.group(1) == "tswt":
            candidates.append((match.group("node"), block))
    if len(candidates) != 1:
        raise DiagnosticError(f"Expected exactly one tswt input device; found {len(candidates)}.")
    node, block = candidates[0]
    if not all(re.search(rf"\b{label}\b", block) for label in ("KEY_BRIGHTNESS_MIN", "KEY_BRIGHTNESS_MAX")):
        raise DiagnosticError("The tswt device lacks the expected brightness MIN/MAX switch capabilities.")
    return node


def validate_switch_keylayout(text):
    """The tested firmware maps Linux MIN/592 to ON, and MAX/593 to OFF."""
    mappings = {}
    for line in text.splitlines():
        fields = line.partition("#")[0].split()
        if len(fields) >= 3 and fields[0] == "key" and fields[1] in {"592", "593"}:
            if fields[1] in mappings:
                raise DiagnosticError(f"Ambiguous switch keylayout mapping for Linux key {fields[1]}.")
            mappings[fields[1]] = fields[2]
    if mappings != {"592": "TSWT_ON", "593": "TSWT_OFF"}:
        raise DiagnosticError("Unsupported physical-switch keylayout; expected key592 TSWT_ON and key593 TSWT_OFF.")


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
