"""Reviewed firmware data and read-only, shareable compatibility observations.

This module imports neither the controller nor diagnostic CLI. An ADB-like reader
is injected; only its read(args, timeout=...) method is used. A report observes
capabilities and never authorizes a subsequent mode command.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
from types import MappingProxyType
from typing import Mapping


ROOT = Path(__file__).resolve().parent
PROFILE_DIRECTORY = ROOT / "compatibility" / "profiles"
PROFILE_PATH = PROFILE_DIRECTORY / "t807d-eea-amd9.properties"
PROFILE_KEYS = frozenset("""schema id qualification model device android sdk fingerprint
input_name linux_on linux_off raw_on raw_off keylayout layout_on layout_off
enter_key exit_key tswt_key ink_key book_key applying_key animation_key preset_key
preset immediate_key immediate evidence""".split())

# Schema 1 implements exactly this reviewed native protocol. New semantics need
# adapter code and qualification, not an unchecked set of replacement numbers.
SCHEMA_ONE = {
    "schema": "1", "qualification": "verified", "input_name": "tswt",
    "linux_on": "592", "linux_off": "593", "raw_on": "KEY_BRIGHTNESS_MIN",
    "raw_off": "KEY_BRIGHTNESS_MAX", "keylayout": "/system/usr/keylayout/Generic.kl",
    "layout_on": "TSWT_ON", "layout_off": "TSWT_OFF", "enter_key": "343",
    "exit_key": "344", "tswt_key": "TSWT_state", "ink_key": "nxtpaper_ink_style_state",
    "book_key": "nxtpaper_book_style_state", "applying_key": "nxtpaper_is_applying_theme",
    "animation_key": "nxtpaper_animation_state", "preset_key": "tct_nxtpaper_mode_select",
    "preset": "3", "immediate_key": "tct_nxtpaper_switch_imm", "immediate": "1",
}
IDENTITY_PROPERTIES = {
    "model": "ro.product.model", "device": "ro.product.device",
    "android": "ro.build.version.release", "sdk": "ro.build.version.sdk",
    "fingerprint": "ro.build.fingerprint",
}
NATIVE_PACKAGES = (
    "com.android.systemui", "com.tcl.android.launcher", "com.tct.onetouchbooster",
    "com.tcl.fota.system", "com.analoganchor.nxtpaperguard", "moe.shizuku.privileged.api",
)
DEVICE_BLOCK = re.compile(r"^add device \d+: (?P<node>/dev/input/event\d+)\s*$", re.MULTILINE)
HASH = re.compile(r"[0-9a-f]{64}\Z")


class CompatibilityError(ValueError):
    """An observation or local profile cannot safely support native commands."""


@dataclass(frozen=True)
class FirmwareProfile:
    values: Mapping[str, str]

    def __getitem__(self, key):
        return self.values[key]

    @property
    def identity(self):
        return {name: self[name] for name in IDENTITY_PROPERTIES}

    @property
    def state_keys(self):
        return {name: self[name + "_key"] for name in ("tswt", "ink", "book", "applying", "animation")}


def parse_profile(text):
    """Parse a strict data-only subset shared with the phone's shell parser."""
    if "\r" in text or "\x00" in text or text.startswith("\ufeff"):
        raise CompatibilityError("Profile must be UTF-8 without BOM, with LF line endings.")
    values = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if (not separator or key not in PROFILE_KEYS or key in values or not value
                or not re.fullmatch(r"[A-Za-z0-9_./:+-]+", value)):
            raise CompatibilityError("Malformed, duplicate, or unsupported profile field.")
        values[key] = value
    if values.keys() != PROFILE_KEYS:
        raise CompatibilityError("Firmware profile has missing fields.")
    if any(values[key] != expected for key, expected in SCHEMA_ONE.items()):
        raise CompatibilityError("Profile requires an unimplemented native adapter or qualification.")
    if (not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", values["id"])
            or not re.fullmatch(r"[A-Za-z0-9_-]+", values["model"])
            or not re.fullmatch(r"[A-Za-z0-9_-]+", values["device"])
            or not re.fullmatch(r"[1-9][0-9]*", values["android"])
            or not re.fullmatch(r"[1-9][0-9]*", values["sdk"])
            or ":" not in values["fingerprint"] or "/" not in values["fingerprint"]
            or ".." in values["evidence"] or values["evidence"].startswith("/")):
        raise CompatibilityError("Invalid profile identity or evidence reference.")
    return FirmwareProfile(MappingProxyType(values))


def load_profile(path=None):
    return parse_profile(Path(path or PROFILE_PATH).read_bytes().decode("utf-8"))


def load_profiles(directory=None):
    paths = sorted(Path(directory or PROFILE_DIRECTORY).glob("*.properties"))
    if not paths:
        raise CompatibilityError("No reviewed firmware profiles are available.")
    profiles = tuple(load_profile(path) for path in paths)
    if len({p["id"] for p in profiles}) != len(profiles) or len({p["fingerprint"] for p in profiles}) != len(profiles):
        raise CompatibilityError("Firmware profiles have ambiguous identifiers or fingerprints.")
    return profiles


def validate_identity(identity, profile):
    for name, expected in profile.identity.items():
        if identity.get(name) != expected:
            raise CompatibilityError(f"Unsupported TCL firmware/profile: {name} differs from the reviewed profile.")


def read_native_state(text, profile, *, check_configuration=True):
    keys = profile.state_keys
    required = set(keys.values())
    if check_configuration:
        required |= {profile["preset_key"], profile["immediate_key"]}
    values = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if key not in required:
            continue
        if not separator or key in values:
            raise CompatibilityError("Malformed or duplicated NXTPAPER native setting.")
        values[key] = value
    if values.keys() != required:
        raise CompatibilityError("Required NXTPAPER native settings are missing.")
    if check_configuration and (values[profile["preset_key"]] != profile["preset"]
                                or values[profile["immediate_key"]] != profile["immediate"]):
        raise CompatibilityError("Native switch configuration must select Max Ink with immediate switching. No settings were changed.")
    allowed = {"tswt": {"-1", "0", "1"}, "ink": {"0", "1", "2"},
               "book": {"0", "1"}, "applying": {"0", "1"}, "animation": {"0", "1"}}
    if any(values[keys[name]] not in accepted for name, accepted in allowed.items()):
        raise CompatibilityError("Unsupported NXTPAPER native state value.")
    return {name: int(values[key]) for name, key in keys.items()}


def discover_switch(capabilities, profile):
    matches = list(DEVICE_BLOCK.finditer(capabilities))
    candidates = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(capabilities)
        block = capabilities[match.end():end]
        name = re.search(r'^\s*name:\s*"([^"\r\n]+)"\s*$', block, re.MULTILINE)
        if name and name.group(1) == profile["input_name"]:
            candidates.append((match.group("node"), block))
    if len(candidates) != 1:
        raise CompatibilityError("Expected exactly one reviewed tswt input device.")
    node, block = candidates[0]
    if not all(re.search(rf"\b{re.escape(profile[key])}\b", block) for key in ("raw_on", "raw_off")):
        raise CompatibilityError("The tswt device lacks the reviewed physical switch capabilities.")
    return node


def validate_keylayout(text, profile):
    expected = {profile["linux_on"]: profile["layout_on"], profile["linux_off"]: profile["layout_off"]}
    mappings = {}
    for line in text.splitlines():
        fields = line.partition("#")[0].split()
        if len(fields) >= 3 and fields[0] == "key" and fields[1] in expected:
            if fields[1] in mappings:
                raise CompatibilityError("Ambiguous physical-switch keylayout.")
            mappings[fields[1]] = fields[2]
    if mappings != expected:
        raise CompatibilityError("Unsupported physical-switch keylayout mapping.")


def _read(adb, command, *, timeout=5, allow_empty=False, strip=True):
    try:
        result = adb.read(command, timeout=timeout)
    except Exception as error:
        raise CompatibilityError("Read-only device observation failed.") from error
    if result.returncode != 0 or result.timed_out or (not allow_empty and not result.stdout.strip()):
        raise CompatibilityError("Read-only device observation unavailable or denied.")
    return result.stdout.strip() if strip else result.stdout


def _package_summary(text):
    summary = {}
    for name in ("versionCode", "versionName"):
        match = re.search(rf"\b{name}=([^\s]+)", text)
        if match and re.fullmatch(r"[A-Za-z0-9_.+-]+", match.group(1)):
            summary[name] = match.group(1)
    users = {}
    for match in re.finditer(r"User (\d+):[^\n]*\n?[^\n]*", text):
        line = match.group(0)
        if "installed=" not in line:
            continue
        user = {key: item.group(1) for key in ("installed", "hidden", "suspended", "enabled")
                if (item := re.search(rf"\b{key}=([A-Za-z0-9]+)", line))}
        users[match.group(1)] = user
    if users:
        summary["users"] = users
    return summary


def _controller_observation(adb):
    observed = {"live": "unknown", "note": "A state file or version marker alone does not prove a live controller."}
    try:
        marker = _read(adb, ("shell", "cat", "/data/local/tmp/nxtpaper_guard.version"))
        version, separator, digest = marker.partition(":")
        if separator and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) and HASH.fullmatch(digest):
            observed.update({"deployed_version": version, "marker_sha256": digest})
    except CompatibilityError:
        pass
    try:
        digest = _read(adb, ("shell", "sha256sum", "/data/local/tmp/nxtpaper_guard.sh")).split()[0]
        if HASH.fullmatch(digest):
            observed["deployed_sha256"] = digest
    except CompatibilityError:
        pass
    try:
        local = ROOT / "nxtpaper_guard.sh"
        script_bytes = local.read_bytes()
        profile_bytes = PROFILE_PATH.read_bytes()
        observed["local_source_sha256"] = hashlib.sha256(script_bytes).hexdigest()
        observed["local_profile_sha256"] = hashlib.sha256(profile_bytes).hexdigest()
        observed["local_bundle_sha256"] = hashlib.sha256(script_bytes + b"\x00" + profile_bytes).hexdigest()
    except OSError:
        pass
    marker_version = observed.get("deployed_version")
    if marker_version == "1.0.5":
        observed["marker_hash_scheme"] = "script-NUL-profile"
        expected_marker = observed.get("local_bundle_sha256")
    elif marker_version in {"1.0.0", "1.0.1", "1.0.2", "1.0.3", "1.0.4"}:
        observed["marker_hash_scheme"] = "legacy-script"
        expected_marker = observed.get("local_source_sha256")
    else:
        observed["marker_hash_scheme"] = "unknown"
        expected_marker = None
    observed["marker_matches_local_reference"] = (
        observed.get("marker_sha256") == expected_marker if expected_marker else None)
    observed["marker_limit"] = "A matching marker is not proof that deployed script/profile bytes or a live process match it."
    try:
        token = _read(adb, ("shell", "cat", "/data/local/tmp/nxtpaper_guard.pid"))
        pid, started, boot = token.split(":")
        if not re.fullmatch(r"[1-9][0-9]*", pid) or not started.isdecimal() or not re.fullmatch(r"[A-Za-z0-9-]+", boot):
            raise CompatibilityError("Invalid controller identity.")
        stat = _read(adb, ("shell", "cat", f"/proc/{pid}/stat"))
        fields = stat.rsplit(") ", 1)[1].split()
        boot_now = _read(adb, ("shell", "cat", "/proc/sys/kernel/random/boot_id"))
        command = _read(adb, ("shell", "cat", f"/proc/{pid}/cmdline"))
        if fields[19] != started or boot != boot_now or "/data/local/tmp/nxtpaper_guard.sh" not in command.split("\x00"):
            raise CompatibilityError("Controller identity is stale.")
        state = _read(adb, ("shell", "cat", "/data/local/tmp/nxtpaper_guard.state"))
        values = state.split(":")
        uptime = float(_read(adb, ("shell", "cat", "/proc/uptime")).split()[0])
        phases = {"INITIALIZING", "WAIT_SWITCH", "WAIT_OFF", "IDLE", "STARTING", "COMMITTED", "EXTENDED", "RESTORING", "ERROR"}
        if len(values) not in (8, 10) or values[0] not in phases or not values[4].isdecimal() or not 0 <= uptime - int(values[4]) <= 10:
            raise CompatibilityError("Controller heartbeat is not fresh.")
        observed.update({"live": "observed", "phase": values[0]})
    except (CompatibilityError, ValueError, IndexError):
        pass
    digest = observed.get("deployed_sha256")
    observed["differs_from_local_source"] = bool(digest and observed.get("local_source_sha256") and digest != observed["local_source_sha256"])
    return observed


def observe_compatibility(adb, profile=None):
    """Observe only. A VERIFIED report is not permission for a future command."""
    profiles = (profile,) if profile is not None else load_profiles()
    reference = profiles[0]
    checks = []
    identity = {}

    def check(name, reader):
        try:
            value = reader()
            checks.append({"name": name, "status": "pass"})
            return value
        except CompatibilityError as error:
            checks.append({"name": name, "status": "fail", "detail": str(error)})
            return None

    uid = check("shell_privilege", lambda: _read(adb, ("shell", "id", "-u")))
    if uid is not None and uid != "2000":
        checks[-1].update({"status": "fail", "detail": "The reviewed adapter requires ADB shell UID 2000."})
    for name, prop in IDENTITY_PROPERTIES.items():
        value = check("identity_" + name, lambda prop=prop: _read(adb, ("shell", "getprop", prop)))
        if value is not None:
            identity[name] = value
    selected = next((item for item in profiles if item.identity == identity), None)
    checks.append({"name": "qualified_profile", "status": "pass" if selected else "fail",
                   "detail": "Historical firmware qualification; current handset trials are separate." if selected
                   else "This build has no matching reviewed profile. Matching field names do not qualify native behavior."})
    adapter = selected or reference
    state = check("native_state_and_configuration", lambda: read_native_state(
        _read(adb, ("shell", "settings", "list", "secure"), strip=False), adapter))
    node = check("physical_input", lambda: discover_switch(_read(adb, ("shell", "getevent", "-lp")), adapter))
    check("physical_keylayout", lambda: validate_keylayout(_read(adb, ("shell", "cat", adapter["keylayout"])), adapter))

    required_failures = any(item["status"] == "fail" for item in checks if item["name"] != "qualified_profile")
    if uid != "2000":
        classification = "PRIVILEGE_UNAVAILABLE"
        action = "Restore authorized USB debugging/ADB access. ADB access does not establish the guard app's Shizuku authorization."
    elif len(identity) != len(IDENTITY_PROPERTIES):
        classification = "CAPABILITY_MISSING"
        action = "Restore reliable read-only identity access before investigating native controls."
    elif selected is None:
        classification = "UNVERIFIED_BUILD"
        action = "Keep automatic enforcement off. Review native differences and qualify a candidate profile only in a separately authorized handset trial."
    elif required_failures:
        classification = "CAPABILITY_MISSING"
        action = "Do not send native commands. Repair the failed capability; use the phone's native controls for manual recovery."
    else:
        classification = "VERIFIED"
        action = "This matches historically qualified firmware and observed structure. Recheck at every command; controller/version and handset acceptance remain separate."

    observations = {"native_state": state, "input_node": node}
    try:
        flag = _read(adb, ("shell", "settings", "get", "global", "ota_disable_automatic_update"))
        observations["automatic_update_setting"] = flag if flag in ("0", "1", "null") else "unknown"
    except CompatibilityError:
        observations["automatic_update_setting"] = "unknown"
    observations["update_setting_limit"] = "This setting alone does not prove that TCL/manual/staged updates are blocked."
    observations["packages"] = {}
    for package in NATIVE_PACKAGES:
        try:
            summary = _package_summary(_read(adb, ("shell", "dumpsys", "package", package), allow_empty=True))
            observations["packages"][package] = summary or {"availability": "unknown"}
        except CompatibilityError:
            observations["packages"][package] = {"availability": "unknown"}
    observations["controller"] = _controller_observation(adb)
    issues = []
    if observations["controller"]["differs_from_local_source"]:
        issues.append({"code": "CONTROLLER_SOURCE_MISMATCH",
                       "detail": "The deployed script differs from local source. This is separate from firmware compatibility; do not replace a possible live commitment."})
    return {
        "schema": 1, "generated_utc": datetime.now(timezone.utc).isoformat(),
        "classification": classification, "profile_id": selected["id"] if selected else None,
        "identity": identity, "checks": checks, "recovery_action": action,
        "observations": observations, "issues": issues,
        "limits": ["Observation only; no phone state was changed.",
                   "VERIFIED means matching historical firmware qualification and current structural checks, not a new handset acceptance test.",
                   "A report is never authorization for a later mode command.",
                   "ADB shell availability does not establish Shizuku startup or app authorization.",
                   "Input capability enumeration does not prove that an ongoing raw-event stream can be opened and retained.",
                   "APK/source copies are not a restorable Android firmware image."],
    }
