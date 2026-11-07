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
ADAPTER_PATH = ROOT / "compatibility" / "adapters" / "tcl-slider-v1.properties"
PROFILE_KEYS = frozenset("""schema id qualification model device android sdk fingerprint
input_name linux_on linux_off raw_on raw_off keylayout layout_on layout_off
enter_key exit_key tswt_key ink_key book_key applying_key animation_key preset_key
preset immediate_key immediate evidence""".split())
BINDING_KEYS = PROFILE_KEYS | frozenset("""adapter adapter_revision keylayout_sha256
systemui_version launcher_version manager_version controller_sha256""".split())
QUALIFICATION_KEYS = frozenset("schema binding_sha256 controller_sha256 trial_id owner_confirmed result".split())
KEYLAYOUT_PATH_PATTERN = re.compile(r"/(?:system|system_ext|vendor|product|odm)/usr/keylayout/[A-Za-z0-9_.+-]+\.kl\Z")

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
# This narrow vendor alias is observed only on the reviewed AMD9 image.
# Adding registry entries cannot grant another build this exception.
AMD9_IDENTITY = MappingProxyType({
    "model": "T807D", "device": "Frida", "android": "16", "sdk": "36",
    "fingerprint": "TCL/T807D_EEA/Frida:16/BP2A.250605.031.A3/AMD9:user/release-keys",
})
NATIVE_PACKAGES = (
    "com.android.systemui", "com.tcl.android.launcher", "com.tct.onetouchbooster",
    "com.tcl.fota.system", "com.analoganchor.nxtpaperguard", "moe.shizuku.privileged.api",
)
DEVICE_BLOCK = re.compile(r"^add device \d+: (?P<node>/dev/input/event\d+)\s*$", re.MULTILINE)
HASH = re.compile(r"[0-9a-f]{64}\Z")


class CompatibilityError(ValueError):
    """An observation or local profile cannot safely support native commands."""


class SymbolHelperUnavailable(CompatibilityError):
    """The read-only helper or both requested framework symbols are unavailable."""


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

    @property
    def is_runtime_binding(self):
        return self["schema"] == "2"

    @property
    def digest(self):
        return hashlib.sha256(canonical_profile(self).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class NativeAdapter:
    values: Mapping[str, str]

    def __getitem__(self, key):
        return self.values[key]


@dataclass(frozen=True)
class SupportAssessment:
    support_level: str
    reasons: tuple[str, ...]
    binding: FirmwareProfile | None = None
    setup_state: str = "REQUIRED"


@dataclass(frozen=True)
class DeviceQualification:
    values: Mapping[str, str]

    def matches(self, binding):
        return (binding.is_runtime_binding
                and self.values["binding_sha256"] == binding.digest
                and self.values["controller_sha256"] == binding["controller_sha256"])


def canonical_profile(profile):
    """Canonical binding bytes: ASCII key order, LF, one final newline."""
    return "".join(f"{key}={profile[key]}\n" for key in sorted(profile.values))


def _parse_data(text, allowed):
    if "\r" in text or "\x00" in text or text.startswith("\ufeff"):
        raise CompatibilityError("Data must be UTF-8 without BOM, with LF line endings.")
    values = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if (not separator or key not in allowed or key in values or not value
                or not re.fullmatch(r"[A-Za-z0-9_./:+-]+", value)):
            raise CompatibilityError("Malformed, duplicate, or unsupported data field.")
        values[key] = value
    return values


def load_adapter(path=None):
    expected = {
        key: value for key, value in SCHEMA_ONE.items()
        if key not in {"schema", "qualification", "keylayout", "enter_key", "exit_key"}
    }
    expected.update({"schema": "1", "id": "tcl-slider-v1", "revision": "1",
                     "feature": "vendor.software.support.tcl_switch",
                     "symbol_on": "KEYCODE_TSWT_ON", "symbol_off": "KEYCODE_TSWT_OFF",
                     "evidence": "FINDINGS.md"})
    values = _parse_data(Path(path or ADAPTER_PATH).read_bytes().decode("utf-8"), expected.keys())
    if values != expected:
        raise CompatibilityError("Adapter requires an unimplemented protocol revision.")
    return NativeAdapter(MappingProxyType(values))


def parse_qualification(text):
    values = _parse_data(text, QUALIFICATION_KEYS)
    if (values.keys() != QUALIFICATION_KEYS or values.get("schema") != "1"
            or values.get("result") != "passed" or values.get("owner_confirmed") != "1"
            or not HASH.fullmatch(values.get("binding_sha256", ""))
            or not HASH.fullmatch(values.get("controller_sha256", ""))
            or not re.fullmatch(r"[1-9][0-9]*-[0-9]+-[0-9]+", values.get("trial_id", ""))):
        raise CompatibilityError("No completed owner-confirmed setup is available.")
    return DeviceQualification(MappingProxyType(values))


def parse_profile(text):
    """Parse a strict data-only subset shared with the phone's shell parser."""
    if "\r" in text or "\x00" in text or text.startswith("\ufeff"):
        raise CompatibilityError("Profile must be UTF-8 without BOM, with LF line endings.")
    values = _parse_data(text, BINDING_KEYS)
    schema = values.get("schema")
    expected_keys = PROFILE_KEYS if schema == "1" else BINDING_KEYS if schema == "2" else None
    if expected_keys is None or values.keys() != expected_keys:
        raise CompatibilityError("Firmware profile has missing fields.")
    fixed = SCHEMA_ONE if schema == "1" else {
        key: value for key, value in SCHEMA_ONE.items()
        if key not in {"schema", "qualification", "keylayout", "enter_key", "exit_key"}
    }
    if any(values[key] != expected for key, expected in fixed.items()):
        raise CompatibilityError("Profile requires an unimplemented native adapter or qualification.")
    if schema == "2":
        if (values["adapter"] != "tcl-slider-v1" or values["adapter_revision"] != "1"
                or values["qualification"] not in {"maintainer-tested", "experimental"}
                or not KEYLAYOUT_PATH_PATTERN.fullmatch(values["keylayout"])
                or ".." in values["keylayout"]
                or not HASH.fullmatch(values["keylayout_sha256"])
                or not HASH.fullmatch(values["controller_sha256"])
                or any(not re.fullmatch(r"[1-9][0-9]*", values[key]) for key in (
                    "systemui_version", "launcher_version", "manager_version"))
                or any(not re.fullmatch(r"[1-9][0-9]*", values[key]) or not 1 <= int(values[key]) <= 32767
                       for key in ("enter_key", "exit_key"))
                or values["enter_key"] == values["exit_key"]):
            raise CompatibilityError("Invalid runtime binding or unsupported protocol.")
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
        if (len(fields) >= 3 and fields[0] == "key" and fields[2] in expected.values()
                and fields[1] not in expected):
            raise CompatibilityError("Ambiguous physical-switch symbolic keylayout.")
        if len(fields) >= 3 and fields[0] == "key" and fields[1] in expected:
            if len(fields) != 3:
                raise CompatibilityError("Physical-switch keylayout flags require a reviewed adapter.")
            if fields[1] in mappings:
                raise CompatibilityError("Ambiguous physical-switch keylayout.")
            mappings[fields[1]] = fields[2]
    if mappings != expected:
        raise CompatibilityError("Unsupported physical-switch keylayout mapping.")


def select_profile(identity, profiles=None):
    """No first-match fallback: a registry must identify one exact build."""
    matches = [item for item in (profiles if profiles is not None else load_profiles())
               if item.identity == identity]
    if len(matches) > 1:
        raise CompatibilityError("Firmware registry is ambiguous for this build.")
    return matches[0] if matches else None


def active_keylayout(input_dump, node, input_name="tswt"):
    """Read EventHub's selected file, not an arbitrary Generic.kl."""
    starts = list(re.finditer(r"^[ \t]+[0-9]+: ([^\r\n]+)$", input_dump, re.MULTILINE))
    matches = []
    for index, start in enumerate(starts):
        if start.group(1).strip() != input_name:
            continue
        end = starts[index + 1].start() if index + 1 < len(starts) else len(input_dump)
        block = input_dump[start.end():end]
        paths = re.findall(r"^\s+Path: (/dev/input/event[0-9]+)\s*$", block, re.MULTILINE)
        layouts = re.findall(r"^\s+KeyLayoutFile: (\S+)\s*$", block, re.MULTILINE)
        if paths == [node] and len(layouts) == 1:
            path = layouts[0]
            if not KEYLAYOUT_PATH_PATTERN.fullmatch(path) or ".." in path:
                raise CompatibilityError("The active input layout path is unsupported.")
            matches.append(path)
        else:
            raise CompatibilityError("The active input device/layout is ambiguous.")
    if len(matches) != 1:
        raise CompatibilityError("The active physical input layout could not be identified.")
    return matches[0]


def parse_symbols(text):
    fields = frozenset("symbol_on enter_key resolved_on symbol_off exit_key resolved_off".split())
    values = _parse_data(text, fields)
    if (values.keys() != fields
            or values.get("symbol_on") != "KEYCODE_TSWT_ON"
            or values.get("resolved_on") != "KEYCODE_TSWT_ON"
            or values.get("symbol_off") != "KEYCODE_TSWT_OFF"
            or values.get("resolved_off") != "KEYCODE_TSWT_OFF"
            or any(not re.fullmatch(r"[1-9][0-9]*", values.get(key, ""))
                   or not 1 <= int(values[key]) <= 32767 for key in ("enter_key", "exit_key"))
            or values["enter_key"] == values["exit_key"]):
        raise CompatibilityError("RUNTIME_SYMBOL_MAPPING_UNRESOLVED")
    return int(values["enter_key"]), int(values["exit_key"])


def _runtime_symbols(adb, *, reviewed_amd9=False):
    try:
        paths = _read(adb, ("shell", "pm", "path", "com.analoganchor.nxtpaperguard")).splitlines()
    except CompatibilityError as error:
        raise SymbolHelperUnavailable("SYMBOL_HELPER_UNAVAILABLE") from error
    bases = [line[len("package:"):] for line in paths if line.startswith("package:") and line.endswith("/base.apk")]
    if (len(bases) != 1 or not re.fullmatch(r"/data/app/[A-Za-z0-9_./~+=-]+/base\.apk", bases[0])
            or ".." in bases[0]):
        raise SymbolHelperUnavailable("SYMBOL_HELPER_UNAVAILABLE")
    try:
        output = _read(adb, ("shell", "env", "CLASSPATH=" + bases[0], "app_process", "/",
                             "com.analoganchor.nxtpaperguard.KeySymbolProbe"))
    except CompatibilityError as error:
        raise SymbolHelperUnavailable("SYMBOL_HELPER_UNAVAILABLE") from error
    unavailable = {
        "symbol_on": "KEYCODE_TSWT_ON", "enter_key": "0", "resolved_on": "KEYCODE_UNKNOWN",
        "symbol_off": "KEYCODE_TSWT_OFF", "exit_key": "0", "resolved_off": "KEYCODE_UNKNOWN",
    }
    observed = _parse_data(output, unavailable.keys())
    if observed == unavailable:
        # Exact historical AMD9 has an independently reviewed numeric pair.
        # This exception never authorizes an unfamiliar build or partial pair.
        raise SymbolHelperUnavailable("SYMBOL_MAPPING_UNAVAILABLE")
    amd9_aliases = {
        "symbol_on": "KEYCODE_TSWT_ON", "enter_key": "343", "resolved_on": "KEYCODE_FP_LIFT_UP",
        "symbol_off": "KEYCODE_TSWT_OFF", "exit_key": "344", "resolved_off": "KEYCODE_FP_LONGPRESS",
    }
    if reviewed_amd9 and observed == amd9_aliases:
        return 343, 344
    return parse_symbols(output)


def build_runtime_binding(identity, *, keylayout, keylayout_sha256, keycodes, versions,
                          controller_sha256, profiles=None, adapter=None):
    """Build data only after the caller has established the current protocol."""
    adapter = adapter or load_adapter()
    known = select_profile(identity, profiles)
    reference = known or load_profile()
    values = dict(reference.values)
    values.update(identity)
    values.update({"schema": "2", "adapter": adapter["id"], "adapter_revision": adapter["revision"],
                   "id": known["id"] if known else "tcl-slider-experimental",
                   "qualification": "maintainer-tested" if known else "experimental",
                   "keylayout": keylayout, "keylayout_sha256": keylayout_sha256,
                   "enter_key": str(keycodes[0]), "exit_key": str(keycodes[1]),
                   "systemui_version": versions["systemui_version"],
                   "launcher_version": versions["launcher_version"],
                   "manager_version": versions["manager_version"],
                   "controller_sha256": controller_sha256})
    return parse_profile("".join(f"{key}={values[key]}\n" for key in sorted(values)))


def assess_support(adb, profiles=None, *, controller_sha256=None):
    """Public eligibility and setup are separate from historical qualification."""
    try:
        profiles = tuple(profiles if profiles is not None else load_profiles())
        if (not profiles or len({p["id"] for p in profiles}) != len(profiles)
                or len({p["fingerprint"] for p in profiles}) != len(profiles)):
            raise CompatibilityError("REGISTRY_AMBIGUOUS")
        adapter = load_adapter()
        uid = _read(adb, ("shell", "id", "-u"))
        if uid != "2000":
            return SupportAssessment("UNSUPPORTED", ("SHELL_PRIVILEGE_UNAVAILABLE",), setup_state="ACCESS_REQUIRED")
        identity = {name: _read(adb, ("shell", "getprop", prop)) for name, prop in IDENTITY_PROPERTIES.items()}
        known = select_profile(identity, profiles)
        reviewed_amd9 = bool(known is not None and known["id"] == "t807d-eea-amd9"
                             and known.identity == AMD9_IDENTITY
                             and known["enter_key"] == "343" and known["exit_key"] == "344")
        manufacturer = _read(adb, ("shell", "getprop", "ro.product.manufacturer"))
        if manufacturer.lower() != "tcl":
            raise CompatibilityError("TCL_PHONE_REQUIRED")
        push_control = _read(adb, ("shell", "getprop", "sys.tct.support_ui_switch_button"), allow_empty=True)
        if push_control not in {"", "0", "false"}:
            raise CompatibilityError("PUSH_BUTTON_PROTOCOL_UNSUPPORTED")
        features = {re.sub(r"=[0-9]+$", "", line)
                    for line in _read(adb, ("shell", "pm", "list", "features")).splitlines()}
        if "feature:" + adapter["feature"] not in features or "feature:android.hardware.telephony" not in features:
            raise CompatibilityError("SLIDER_PHONE_FEATURE_REQUIRED")
        reference = known or profiles[0]
        try:
            read_native_state(_read(adb, ("shell", "settings", "list", "secure"), strip=False), reference)
        except CompatibilityError as error:
            raise CompatibilityError("NATIVE_SETTINGS_UNAVAILABLE") from error
        try:
            node = discover_switch(_read(adb, ("shell", "getevent", "-lp")), reference)
            _read(adb, ("shell", "test", "-r", node), allow_empty=True)
        except CompatibilityError as error:
            raise CompatibilityError("PHYSICAL_INPUT_UNAVAILABLE") from error
        try:
            layout = active_keylayout(_read(adb, ("shell", "dumpsys", "input"), strip=False), node, adapter["input_name"])
            validate_keylayout(_read(adb, ("shell", "cat", layout), strip=False), reference)
            layout_hash = _read(adb, ("shell", "sha256sum", layout)).split()[0]
        except CompatibilityError as error:
            raise CompatibilityError("ACTIVE_LAYOUT_OR_MAPPING_UNAVAILABLE") from error
        if not HASH.fullmatch(layout_hash):
            raise CompatibilityError("ACTIVE_LAYOUT_HASH_UNAVAILABLE")
        try:
            keycodes = _runtime_symbols(adb, reviewed_amd9=reviewed_amd9)
        except SymbolHelperUnavailable:
            if not reviewed_amd9:
                raise
            keycodes = int(known["enter_key"]), int(known["exit_key"])
        if known is not None and keycodes != (int(known["enter_key"]), int(known["exit_key"])):
            raise CompatibilityError("REVIEWED_SYMBOL_MAPPING_CHANGED")
        versions = {}
        for field, package in (("systemui_version", "com.android.systemui"),
                               ("launcher_version", "com.tcl.android.launcher"),
                               ("manager_version", "com.tct.onetouchbooster")):
            version = _package_summary(_read(adb, ("shell", "dumpsys", "package", package))).get("versionCode")
            if not version or not re.fullmatch(r"[1-9][0-9]*", version):
                raise CompatibilityError("NATIVE_COMPONENT_VERSION_UNAVAILABLE")
            versions[field] = version
        digest = controller_sha256 or hashlib.sha256((ROOT / "nxtpaper_guard.sh").read_bytes()).hexdigest()
        binding = build_runtime_binding(identity, keylayout=layout, keylayout_sha256=layout_hash,
                                        keycodes=keycodes, versions=versions,
                                        controller_sha256=digest, profiles=profiles, adapter=adapter)
        state = "REQUIRED"
        try:
            approval = parse_qualification(_read(adb, ("shell", "cat", "/data/local/tmp/nxtpaper_guard.qualification"), strip=False))
            state = "PASSED" if approval.matches(binding) else "STALE"
        except CompatibilityError:
            pass
        return SupportAssessment("MAINTAINER_TESTED" if known else "EXPERIMENTAL_ELIGIBLE", (), binding, state)
    except (CompatibilityError, OSError, ValueError, KeyError) as error:
        # Do not leak raw ADB errors, paths, tokens, or settings into reports.
        reason = str(error) if isinstance(error, CompatibilityError) and re.fullmatch(r"[A-Z_]+", str(error)) else "REQUIRED_EVIDENCE_UNAVAILABLE"
        return SupportAssessment("UNSUPPORTED", (reason,), setup_state="UNAVAILABLE")


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
        if separator and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.]+)?", version) and HASH.fullmatch(digest):
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
    elif marker_version == "1.0.6-beta.1":
        observed["marker_hash_scheme"] = "script"
        # The runtime binding/qualification are checked independently; the
        # Android status marker identifies this controller's source bytes.
        expected_marker = observed.get("local_source_sha256")
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
    public = assess_support(adb, profiles)
    public_support = {
        "level": public.support_level, "setup_state": public.setup_state,
        "adapter_id": public.binding["adapter"] if public.binding else None,
        "binding_sha256": public.binding.digest if public.binding else None,
        "reasons": list(public.reasons),
        "limit": "Historical model support, local setup, privilege and live protection are separate facts.",
    }
    if public.binding is not None:
        public_support["control_mapping"] = {
            key: public.binding[key] for key in ("adapter_revision", "linux_on", "linux_off", "enter_key", "exit_key",
                                                 "keylayout", "keylayout_sha256", "systemui_version",
                                                 "launcher_version", "manager_version")
        }
    if public.binding is not None:
        action = ("Current recognized controls are eligible for guided setup. Complete or repeat the local phone test "
                  "before enabling commitments; an unfamiliar build is experimental, not permanently rejected.")
    issues = []
    if observations["controller"]["differs_from_local_source"]:
        issues.append({"code": "CONTROLLER_SOURCE_MISMATCH",
                       "detail": "The deployed script differs from local source. This is separate from firmware compatibility; do not replace a possible live commitment."})
    return {
        "schema": 1, "generated_utc": datetime.now(timezone.utc).isoformat(),
        "classification": classification, "profile_id": selected["id"] if selected else None,
        "identity": identity, "checks": checks, "recovery_action": action,
        "public_support": public_support,
        "observations": observations, "issues": issues,
        "limits": ["Observation only; no phone state was changed.",
                   "VERIFIED means matching historical firmware qualification and current structural checks, not a new handset acceptance test.",
                   "A report is never authorization for a later mode command.",
                   "ADB shell availability does not establish Shizuku startup or app authorization.",
                   "Input capability enumeration does not prove that an ongoing raw-event stream can be opened and retained.",
                   "APK/source copies are not a restorable Android firmware image."],
    }
