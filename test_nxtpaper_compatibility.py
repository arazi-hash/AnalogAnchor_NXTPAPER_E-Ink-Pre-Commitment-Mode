"""Host-only profile, observation, privacy, and CLI regression tests."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import nxtpaper_compatibility as compatibility
import nxtpaper_diag as diag


PROFILE_TEXT = compatibility.PROFILE_PATH.read_bytes().decode("utf-8")
PROFILE = compatibility.load_profile()
CAPABILITIES = '''add device 1: /dev/input/event2
  name: "tswt"
  events:
    KEY (0001): KEY_BRIGHTNESS_MIN KEY_BRIGHTNESS_MAX
'''
KEYLAYOUT = "key 592 TSWT_ON\nkey 593 TSWT_OFF\n"
SETTINGS = """TSWT_state=0
nxtpaper_ink_style_state=0
nxtpaper_book_style_state=0
nxtpaper_is_applying_theme=0
nxtpaper_animation_state=0
tct_nxtpaper_mode_select=3
tct_nxtpaper_switch_imm=1
private_account=not-for-sharing
"""


def captured(text="", returncode=0, timed_out=False):
    return diag.Result(["fake-adb"], "2026-10-28T00:00:00+00:00", 0.01,
                       returncode, timed_out, text, "private-serial-in-stderr")


class FakeAdb:
    serial = "PRIVATE-HANDSET-SERIAL"

    def __init__(self, changes=None):
        self.calls = []
        self.responses = {
            ("shell", "getprop", prop): captured(PROFILE[name] + "\n")
            for name, prop in compatibility.IDENTITY_PROPERTIES.items()
        }
        self.responses.update({
            ("shell", "id", "-u"): captured("2000\n"),
            ("shell", "settings", "list", "secure"): captured(SETTINGS),
            ("shell", "getevent", "-lp"): captured(CAPABILITIES),
            ("shell", "cat", PROFILE["keylayout"]): captured(KEYLAYOUT),
            ("shell", "settings", "get", "global", "ota_disable_automatic_update"): captured("1\n"),
        })
        self.responses.update(changes or {})

    def read(self, command, timeout=20):
        self.calls.append(tuple(command))
        result = self.responses.get(tuple(command), captured(returncode=1))
        if isinstance(result, Exception):
            raise result
        return result


class ProfileTests(unittest.TestCase):
    def test_canonical_profile_is_complete_and_immutable(self):
        self.assertEqual(set(PROFILE.values), compatibility.PROFILE_KEYS)
        self.assertEqual(PROFILE["id"], "t807d-eea-amd9")
        self.assertEqual(PROFILE.identity["fingerprint"], PROFILE["fingerprint"])
        with self.assertRaises(TypeError):
            PROFILE.values["enter_key"] = "1"

    def test_invalid_encoding_duplicates_unknown_missing_and_shell_text_are_rejected(self):
        variants = (
            "\ufeff" + PROFILE_TEXT,
            PROFILE_TEXT.replace("\n", "\r\n"),
            PROFILE_TEXT + "model=T807D\n",
            PROFILE_TEXT + "extra=1\n",
            PROFILE_TEXT.replace("device=Frida\n", ""),
            PROFILE_TEXT.replace("model=T807D", "model=T807D;reboot"),
            PROFILE_TEXT.replace("model=T807D", "model=$(reboot)"),
            PROFILE_TEXT.replace("id=t807d-eea-amd9", "id=bad id"),
            PROFILE_TEXT.replace("evidence=FINDINGS.md", "evidence=../FINDINGS.md"),
            PROFILE_TEXT.replace("model=T807D", "model=T807D\x00"),
        )
        for value in variants:
            with self.subTest(value=value), self.assertRaises(compatibility.CompatibilityError):
                compatibility.parse_profile(value)

    def test_new_semantics_cannot_be_enabled_by_changing_profile_numbers(self):
        for old, new in (("enter_key=343", "enter_key=400"), ("preset=3", "preset=2"),
                         ("qualification=verified", "qualification=candidate"),
                         ("schema=1", "schema=2")):
            with self.subTest(old=old), self.assertRaises(compatibility.CompatibilityError):
                compatibility.parse_profile(PROFILE_TEXT.replace(old, new))

    def test_ambiguous_registry_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            with self.assertRaises(compatibility.CompatibilityError):
                compatibility.load_profiles(directory)
            (directory / "a.properties").write_bytes(PROFILE_TEXT.encode("utf-8"))
            (directory / "b.properties").write_bytes(PROFILE_TEXT.encode("utf-8"))
            with self.assertRaisesRegex(compatibility.CompatibilityError, "ambiguous"):
                compatibility.load_profiles(directory)

    def test_exact_identity_includes_hardware_device_and_build(self):
        compatibility.validate_identity(PROFILE.identity, PROFILE)
        for name in compatibility.IDENTITY_PROPERTIES:
            identity = {**PROFILE.identity, name: "changed"}
            with self.subTest(name=name), self.assertRaises(compatibility.CompatibilityError):
                compatibility.validate_identity(identity, PROFILE)

    def test_native_boot_sentinel_is_valid_observation_not_physical_position(self):
        state = compatibility.read_native_state(SETTINGS.replace("TSWT_state=0", "TSWT_state=-1"), PROFILE)
        self.assertEqual(state["tswt"], -1)
        self.assertNotIn("physical", state)

    def test_native_snapshot_rejects_duplicates_missing_or_malformed_fields(self):
        for text in (SETTINGS + "TSWT_state=0\n", SETTINGS.replace("TSWT_state=0\n", ""),
                     SETTINGS.replace("nxtpaper_book_style_state=0", "nxtpaper_book_style_state=00"),
                     SETTINGS.replace("tct_nxtpaper_switch_imm=1", "tct_nxtpaper_switch_imm=1 ")):
            with self.subTest(text=text), self.assertRaises(compatibility.CompatibilityError):
                compatibility.read_native_state(text, PROFILE)


class ObservationTests(unittest.TestCase):
    def observe(self, changes=None):
        adb = FakeAdb(changes)
        return compatibility.observe_compatibility(adb), adb

    def test_known_profile_passes_without_claiming_new_handset_acceptance(self):
        report, _ = self.observe()
        self.assertEqual(report["classification"], "VERIFIED")
        self.assertEqual(report["profile_id"], PROFILE["id"])
        self.assertIn("historical", " ".join(report["limits"]))
        self.assertEqual(report["observations"]["native_state"]["ink"], 0)

    def test_report_observes_only_allowlisted_read_commands(self):
        _, adb = self.observe()
        allowed_prefixes = {("shell", "id"), ("shell", "getprop"), ("shell", "settings"),
                            ("shell", "getevent"), ("shell", "cat"), ("shell", "dumpsys"),
                            ("shell", "sha256sum")}
        self.assertTrue(all(call[:2] in allowed_prefixes for call in adb.calls))
        self.assertEqual([call for call in adb.calls if call[:2] == ("shell", "settings")],
                         [("shell", "settings", "list", "secure"),
                          ("shell", "settings", "get", "global", "ota_disable_automatic_update")])
        self.assertEqual([call for call in adb.calls if call[:2] == ("shell", "getevent")],
                         [("shell", "getevent", "-lp")])

    def test_new_fingerprint_with_matching_structure_stays_unverified(self):
        report, _ = self.observe({("shell", "getprop", "ro.build.fingerprint"): captured("TCL/new:16/build/new:user/release-keys")})
        self.assertEqual(report["classification"], "UNVERIFIED_BUILD")
        self.assertIsNone(report["profile_id"])
        self.assertIn("separately authorized", report["recovery_action"])

    def test_same_marketing_model_with_different_device_stays_unverified(self):
        report, _ = self.observe({("shell", "getprop", "ro.product.device"): captured("DifferentHardware")})
        self.assertEqual(report["classification"], "UNVERIFIED_BUILD")

    def test_missing_native_state_input_or_layout_blocks_known_profile(self):
        variants = (
            {("shell", "settings", "list", "secure"): captured(SETTINGS.replace("TSWT_state=0\n", ""))},
            {("shell", "getevent", "-lp"): captured(returncode=1)},
            {("shell", "getevent", "-lp"): captured(CAPABILITIES + CAPABILITIES.replace("event2", "event3"))},
            {("shell", "cat", PROFILE["keylayout"]): captured(KEYLAYOUT.replace("TSWT_ON", "OTHER"))},
        )
        for changes in variants:
            with self.subTest(changes=changes):
                report, _ = self.observe(changes)
                self.assertEqual(report["classification"], "CAPABILITY_MISSING")

    def test_unavailable_or_wrong_privilege_is_not_firmware_failure(self):
        for value in (captured("0"), captured(returncode=1), OSError("private error")):
            report, _ = self.observe({("shell", "id", "-u"): value})
            self.assertEqual(report["classification"], "PRIVILEGE_UNAVAILABLE")

    def test_identity_read_failure_is_not_a_verified_match(self):
        report, _ = self.observe({("shell", "getprop", "ro.build.fingerprint"): captured(returncode=1)})
        self.assertEqual(report["classification"], "CAPABILITY_MISSING")

    def test_dynamic_input_node_number_does_not_change_support(self):
        report, _ = self.observe({("shell", "getevent", "-lp"): captured(CAPABILITIES.replace("event2", "event42"))})
        self.assertEqual(report["classification"], "VERIFIED")
        self.assertEqual(report["observations"]["input_node"], "/dev/input/event42")

    def test_package_and_update_observations_are_not_guarantees(self):
        report, _ = self.observe({("shell", "dumpsys", "package", "com.tcl.fota.system"): captured(
            "versionCode=123 minSdk=35\nversionName=v9.0\nUser 0: ceDataInode=987 installed=true hidden=false suspended=false\nenabled=0 private=secret\n")})
        updater = report["observations"]["packages"]["com.tcl.fota.system"]
        self.assertEqual(updater["versionCode"], "123")
        self.assertEqual(updater["users"]["0"]["enabled"], "0")
        self.assertIn("does not prove", report["observations"]["update_setting_limit"])

    def test_private_serial_settings_errors_and_inode_are_not_in_shareable_report(self):
        report, _ = self.observe({("shell", "dumpsys", "package", "com.tcl.fota.system"): captured(
            "versionCode=123\nUser 0: ceDataInode=987654321 installed=true enabled=0\n")})
        encoded = json.dumps(report)
        for private in (FakeAdb.serial, "not-for-sharing", "private_account", "private-serial-in-stderr", "987654321"):
            self.assertNotIn(private, encoded)

    def test_deployed_controller_mismatch_is_separate_from_firmware_support(self):
        report, _ = self.observe({("shell", "sha256sum", "/data/local/tmp/nxtpaper_guard.sh"): captured("f" * 64 + "  /data/local/tmp/nxtpaper_guard.sh")})
        self.assertEqual(report["classification"], "VERIFIED")
        self.assertEqual(report["issues"][0]["code"], "CONTROLLER_SOURCE_MISMATCH")
        self.assertEqual(report["observations"]["controller"]["live"], "unknown")

    def test_new_marker_uses_bundle_hash_and_unknown_version_does_not_infer_equality(self):
        baseline, _ = self.observe()
        expected = baseline["observations"]["controller"]["local_bundle_sha256"]
        report, _ = self.observe({("shell", "cat", "/data/local/tmp/nxtpaper_guard.version"):
                                  captured("1.0.5:" + expected)})
        marker = report["observations"]["controller"]
        self.assertEqual(marker["marker_hash_scheme"], "script-NUL-profile")
        self.assertTrue(marker["marker_matches_local_reference"])
        unknown, _ = self.observe({("shell", "cat", "/data/local/tmp/nxtpaper_guard.version"):
                                   captured("9.0.0:" + expected)})
        self.assertEqual(unknown["observations"]["controller"]["marker_hash_scheme"], "unknown")
        self.assertIsNone(unknown["observations"]["controller"]["marker_matches_local_reference"])

    def test_live_controller_requires_identity_and_fresh_heartbeat_without_exposing_pid_or_boot(self):
        fields = ["S"] + ["0"] * 18 + ["50"]
        changes = {
            ("shell", "cat", "/data/local/tmp/nxtpaper_guard.pid"): captured("123:50:private-boot"),
            ("shell", "cat", "/proc/123/stat"): captured("123 (sh) " + " ".join(fields)),
            ("shell", "cat", "/proc/sys/kernel/random/boot_id"): captured("private-boot"),
            ("shell", "cat", "/proc/123/cmdline"): captured("sh\x00/data/local/tmp/nxtpaper_guard.sh\x00"),
            ("shell", "cat", "/data/local/tmp/nxtpaper_guard.state"): captured("IDLE:0:0:0:100:OFF::300"),
            ("shell", "cat", "/proc/uptime"): captured("101.5 200.0"),
        }
        report, _ = self.observe(changes)
        self.assertEqual(report["observations"]["controller"]["live"], "observed")
        self.assertEqual(report["observations"]["controller"]["phase"], "IDLE")
        self.assertNotIn("private-boot", json.dumps(report))
        changes[("shell", "cat", "/proc/uptime")] = captured("200.0 200.0")
        stale, _ = self.observe(changes)
        self.assertEqual(stale["observations"]["controller"]["live"], "unknown")


class CompatibilityCliTests(unittest.TestCase):
    def test_json_cli_does_not_create_output_folder_or_change_phone(self):
        adb = FakeAdb()
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "must-not-exist"
            console = io.StringIO()
            with patch.object(diag, "connect", return_value=adb), redirect_stdout(console), redirect_stderr(io.StringIO()):
                code = diag.main(["--output", str(output), "compatibility", "--json"])
            self.assertEqual(code, 0)
            self.assertFalse(output.exists())
            self.assertEqual(json.loads(console.getvalue())["classification"], "VERIFIED")

    def test_unverified_cli_returns_nonzero_with_valid_json(self):
        adb = FakeAdb({("shell", "getprop", "ro.build.fingerprint"): captured("changed")})
        console = io.StringIO()
        with patch.object(diag, "connect", return_value=adb), redirect_stdout(console):
            code = diag.main(["compatibility", "--json"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(console.getvalue())["classification"], "UNVERIFIED_BUILD")

    def test_no_authorized_phone_still_returns_valid_redacted_json(self):
        console, errors = io.StringIO(), io.StringIO()
        with patch.object(diag, "connect", side_effect=diag.DiagnosticError("private-serial")), \
                redirect_stdout(console), redirect_stderr(errors):
            code = diag.main(["compatibility", "--json"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(console.getvalue())["classification"], "PRIVILEGE_UNAVAILABLE")
        self.assertNotIn("private-serial", console.getvalue())
        self.assertEqual(errors.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
