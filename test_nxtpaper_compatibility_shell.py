"""Execute real compatibility/command gates with fake Android observations."""

import hashlib
import unittest

import test_nxtpaper_guard as fixtures


def runtime_binding(**changes):
    values = dict(line.split("=", 1) for line in fixtures.PROFILE.read_text().splitlines()
                  if line and not line.startswith("#"))
    values.update(schema="2", qualification="maintainer-tested", adapter="tcl-slider-v1",
                  adapter_revision="1", keylayout_sha256="a" * 64,
                  systemui_version="1", launcher_version="2", manager_version="3",
                  controller_sha256="b" * 64)
    values.update(changes)
    return "".join(f"{key}={values[key]}\n" for key in sorted(values))


LOAD_RUNTIME = '''
PROFILE_LOADED=0
NXTPAPER_PROFILE_DATA=$(cat "$GUARD_TEST_DIR/runtime.profile")
guard_profile_load || exit 12
'''


@unittest.skipUnless(fixtures.SHELL, "A POSIX shell is required")
class CompatibilityShellTests(unittest.TestCase):
    run_controller = fixtures.GuardShellTests.run_controller

    def test_runtime_binding_digest_is_canonical_across_comments_and_order(self):
        binding = runtime_binding()
        data = "# local binding data\n" + "\n".join(reversed(binding.splitlines())) + "\n"
        lines = self.run_controller(LOAD_RUNTIME + 'printf "%s\\n" "$PROFILE_BINDING_SHA"\n',
                                    {"runtime.profile": data})
        self.assertEqual(lines, [hashlib.sha256(binding.encode("ascii")).hexdigest()])

    def test_schema_two_rejects_missing_fields_conflicting_keys_and_invalid_values(self):
        for replacement in ({"adapter_revision": "2"}, {"enter_key": "344"}, {"enter_key": "32768"},
                            {"manager_version": "0"}, {"keylayout": "/data/local/tmp/injected.kl"},
                            {"keylayout_sha256": "bad"}):
            with self.subTest(replacement=replacement):
                lines = self.run_controller('PROFILE_LOADED=0\nNXTPAPER_PROFILE_DATA=$(cat "$GUARD_TEST_DIR/runtime.profile")\nif guard_profile_load; then exit 12; fi\nprintf "rejected\\n"\n',
                                            {"runtime.profile": runtime_binding(**replacement)})
                self.assertEqual(lines, ["rejected"])

    def test_unknown_binding_symbols_must_round_trip_and_match_frozen_codes(self):
        prefix = LOAD_RUNTIME + '''
NXTPAPER_SYMBOL_APK=/data/app/test/base.apk
app_process() { cat "$GUARD_TEST_DIR/symbols"; }
'''
        symbols = "symbol_on=KEYCODE_TSWT_ON\nsymbol_off=KEYCODE_TSWT_OFF\nenter_key=401\nexit_key=402\nresolved_on=KEYCODE_TSWT_ON\nresolved_off=KEYCODE_TSWT_OFF\n"
        binding = runtime_binding(qualification="experimental", fingerprint="TCL/T807D_EEA/Frida:16/test/NEW:user/release-keys", enter_key="401", exit_key="402")
        for observed, expected in ((symbols, "resolved"), (symbols.replace("resolved_on=KEYCODE_TSWT_ON", "resolved_on=401"), "rejected"),
                                   (symbols.replace("enter_key=401", "enter_key=403"), "rejected")):
            with self.subTest(expected=expected, observed=observed):
                lines = self.run_controller(prefix + 'if guard_symbols_match; then printf "resolved\\n"; else printf "rejected\\n"; fi\n',
                                            {"runtime.profile": binding, "symbols": observed})
                self.assertEqual(lines, [expected])

    def test_missing_or_stale_qualification_never_unlocks_runtime_binding(self):
        lines = self.run_controller(LOAD_RUNTIME + '''
guard_identity_matches() { :; }
if guard_validate; then exit 12; fi
printf '%s\\n' "$ERROR_CODE"
printf 'schema=1\\nbinding_sha256=stale\\ncontroller_sha256=%s\\ntrial_id=1-2-3\\nowner_confirmed=1\\nresult=passed\\n' "$PROFILE_CONTROLLER_SHA" > "$QUALIFICATION_FILE"
if guard_qualification_matches; then exit 12; fi
result
''', {"runtime.profile": runtime_binding()})
        self.assertEqual(lines[0], "SETUP_REQUIRED")
        self.assertEqual(lines[-1], "commands=")

    def test_current_active_layout_must_belong_to_single_tswt_device(self):
        base = "  1: tswt\n    Path: /dev/input/event9\n    KeyLayoutFile: /vendor/usr/keylayout/tswt.kl\n"
        for value, expected in ((base, "/vendor/usr/keylayout/tswt.kl"),
                                (base + base, "rejected"),
                                (base.replace("event9", "event10"), "rejected")):
            lines = self.run_controller('SWITCH_NODE=/dev/input/event9\ndumpsys() { cat "$GUARD_TEST_DIR/input"; }\nif result_layout=$(guard_active_layout); then printf "%s\\n" "$result_layout"; else printf "rejected\\n"; fi\n', {"input": value})
            self.assertEqual(lines, [expected])

    def test_duplicate_reverse_symbol_mapping_is_unsupported(self):
        lines = self.run_controller('printf "key 700 TSWT_ON\\n" >> "$KEYLAYOUT_PATH"\nif guard_discover; then exit 12; fi\nresult\n')
        self.assertEqual(lines[-1], "commands=")

    def test_guard_start_preserves_live_or_unknown_setup(self):
        lines = self.run_controller('printf "unknown-trial\\n" > "$SETUP_PID_FILE"\nif guard_main start; then exit 12; fi\ncat "$SETUP_PID_FILE"\nresult\n', protocol=True)
        self.assertEqual(lines[0], "ERROR:0:0:0:0:UNKNOWN:SETUP_IN_PROGRESS:300")
        self.assertEqual(lines[1], "unknown-trial")
        self.assertEqual(lines[-1], "commands=")

    def test_fresh_binding_discovery_cannot_replace_monitor_node(self):
        lines = self.run_controller('SWITCH_NODE=/dev/input/event9\nguard_identity_matches() { SWITCH_NODE=/dev/input/event10; }\nguard_discover() { SWITCH_NODE=/dev/input/event10; }\nif guard_command_gate; then exit 12; fi\nprintf "%s\\n" "$ERROR_CODE"\nresult\n')
        self.assertEqual(lines[0], "PHYSICAL_SWITCH_CHANGED")
        self.assertEqual(lines[-1], "commands=")

    def test_layout_flags_require_another_reviewed_protocol(self):
        lines = self.run_controller('printf "key 592 TSWT_ON VIRTUAL\\nkey 593 TSWT_OFF\\n" > "$KEYLAYOUT_PATH"\nif guard_discover; then exit 12; fi\nresult\n')
        self.assertEqual(lines[-1], "commands=")

    def test_explicit_guard_recovery_clears_only_proven_previous_boot_monitor(self):
        lines = self.run_controller('''
printf '123:50:previous-boot\\n' > "$PID_FILE"
printf 'old-monitor\\n' > "$GETEVENT_PID_FILE"
printf 'retained-qualification\\n' > "$QUALIFICATION_FILE"
guard_init() { printf 'UNSAFE INITIALIZATION\\n'; }
guard_duration_load() { printf 'UNSAFE DURATION\\n'; }
settings() { printf 'UNSAFE NATIVE READ\\n'; }
kill() { printf 'UNSAFE SIGNAL\\n'; }
guard_main reset-stale
[ ! -e "$PID_FILE" ] && [ ! -d "$LOCK_DIR" ] || exit 12
cat "$QUALIFICATION_FILE"
printf 'commands='; cat "$COMMANDS"
''', protocol=True, exit_protocol=True)
        self.assertEqual(lines, ["STOPPED:0:0:0:0:UNKNOWN::300:0:0", "retained-qualification", "commands="])

    def test_guard_recovery_preserves_current_boot_unknown_or_missing_identity(self):
        for token in ("123:50:test-boot", "malformed", None):
            prepare = '' if token is None else f'printf "{token}\\n" > "$PID_FILE"\n'
            lines = self.run_controller(prepare + '''
printf 'untouched-monitor\\n' > "$GETEVENT_PID_FILE"
if guard_main reset-stale; then exit 12; fi
cat "$GETEVENT_PID_FILE"
[ -d "$LOCK_DIR" ] || exit 12
printf 'commands='; cat "$COMMANDS"
''', protocol=True, exit_protocol=True)
            self.assertEqual(lines, ["ERROR:0:0:0:0:UNKNOWN:CONTROLLER_IDENTITY_UNAVAILABLE:300:0:0", "untouched-monitor", "commands="])

    def test_guard_recovery_never_overlaps_unknown_trial(self):
        lines = self.run_controller('''
printf '123:50:previous-boot\\n' > "$PID_FILE"
printf 'unknown-trial\\n' > "$SETUP_PID_FILE"
if guard_main reset-stale; then exit 12; fi
cat "$PID_FILE"
cat "$SETUP_PID_FILE"
''', protocol=True, exit_protocol=True)
        self.assertEqual(lines, ["ERROR:0:0:0:0:UNKNOWN:SETUP_IN_PROGRESS:300:0:0", "123:50:previous-boot", "unknown-trial"])

    def test_guard_recovery_preserves_unrecognized_lock_contents(self):
        lines = self.run_controller('''
printf '123:50:previous-boot\\n' > "$PID_FILE"
printf 'unknown-owner\\n' > "$LOCK_DIR/unknown"
if guard_main reset-stale; then exit 12; fi
cat "$PID_FILE"
cat "$LOCK_DIR/unknown"
''', protocol=True, exit_protocol=True)
        self.assertEqual(lines, ["ERROR:0:0:0:0:UNKNOWN:CONTROLLER_LOCK_UNRECOGNIZED:300:0:0", "123:50:previous-boot", "unknown-owner"])

    def test_guard_recovery_can_clear_previous_boot_deployment_mutex_without_pid(self):
        lines = self.run_controller('''
rmdir "$LOCK_DIR"
mkdir "$OPERATION_LOCK"
printf 'previous-boot\\n' > "$OPERATION_LOCK/boot"
guard_main reset-stale
[ ! -d "$OPERATION_LOCK" ] || exit 12
''', protocol=True, exit_protocol=True)
        self.assertEqual(lines, ["STOPPED:0:0:0:0:UNKNOWN::300:0:0"])

    def test_operation_recovery_rereads_owner_after_claim_and_preserves_current_owner(self):
        lines = self.run_controller('''
mkdir "$OPERATION_LOCK"
printf 'previous-boot\\n' > "$OPERATION_LOCK/boot"
mkdir() {
 if [ "$1" = "$OPERATION_LOCK/recovery.claim" ]; then printf 'test-boot\\n' > "$OPERATION_LOCK/boot"; fi
 command mkdir "$@"
}
if guard_operation_recover_previous_boot; then exit 12; fi
cat "$OPERATION_LOCK/boot"
[ ! -d "$OPERATION_LOCK/recovery.claim" ] || exit 12
''')
        self.assertEqual(lines, ["test-boot"])

    def test_operation_recovery_does_not_release_another_recovery_claim(self):
        lines = self.run_controller('''
mkdir "$OPERATION_LOCK"
printf 'previous-boot\\n' > "$OPERATION_LOCK/boot"
mkdir "$OPERATION_LOCK/recovery.claim"
if guard_operation_recover_previous_boot; then exit 12; fi
cat "$OPERATION_LOCK/boot"
[ -d "$OPERATION_LOCK/recovery.claim" ] || exit 12
''')
        self.assertEqual(lines, ["previous-boot"])

    def test_report_is_independent_of_daemon_writes_and_preserves_evidence(self):
        lines = self.run_controller(r'''
printf 'keep-me\n' > "$PID_FILE"
guard_log() { printf 'UNSAFE LOG\n'; }
guard_publish() { printf 'UNSAFE PUBLICATION\n'; }
guard_duration_load() { printf 'UNSAFE DURATION\n'; }
guard_main check-compatibility
[ ! -e "$STATE_FILE" ] && [ ! -e "$DURATION_FILE" ] || exit 12
cat "$PID_FILE"
printf 'commands='; cat "$COMMANDS"
''')
        self.assertEqual(lines, ["VERIFIED:t807d-eea-amd9", "keep-me", "commands="])

    def test_unknown_firmware_report_does_not_probe_native_controls(self):
        lines = self.run_controller(r'''
getprop() { printf 'new-firmware\n'; }
settings() { printf 'UNSAFE NATIVE READ\n'; }
guard_main check-compatibility
result
''')
        self.assertEqual(lines[0], "UNVERIFIED_BUILD:UNSUPPORTED_FIRMWARE")
        self.assertEqual(lines[-1], "commands=")

    def test_missing_shell_privilege_is_distinct(self):
        lines = self.run_controller("id() { printf '10234\\n'; }\nguard_main check-compatibility\nresult\n")
        self.assertEqual(lines[0], "PRIVILEGE_UNAVAILABLE:SHELL_PRIVILEGE_REQUIRED")
        self.assertEqual(lines[-1], "commands=")

    def test_malformed_profiles_fail_without_executing_data(self):
        for suffix in ("schema=1", "new_key=value", "id=$(touch /bad)", "id=bad name", "badline", "schema=1\r"):
            with self.subTest(suffix=suffix):
                escaped = suffix.replace("'", "'\\''")
                lines = self.run_controller(f"PROFILE_LOADED=0\nNXTPAPER_PROFILE_DATA=\"$NXTPAPER_PROFILE_DATA\n\"'{escaped}'\nguard_main check-compatibility\nresult\n")
                self.assertEqual(lines[0], "CAPABILITY_MISSING:PROFILE_INVALID")
                self.assertEqual(lines[-1], "commands=")

    def test_loaded_profile_does_not_change_mid_controller(self):
        lines = self.run_controller("NXTPAPER_PROFILE_DATA='invalid replacement'\nguard_main check-compatibility\n")
        self.assertEqual(lines, ["VERIFIED:t807d-eea-amd9"])

    def test_preset_and_missing_native_field_are_classified(self):
        for secure, reason in (
            (fixtures.NORMAL_SETTINGS.replace("tct_nxtpaper_mode_select=3", "tct_nxtpaper_mode_select=1"), "NATIVE_PRESET_MISMATCH"),
            (fixtures.NORMAL_SETTINGS.replace("nxtpaper_animation_state=0\n", ""), "NATIVE_STATE_READ_FAILED"),
        ):
            with self.subTest(reason=reason):
                lines = self.run_controller("guard_main check-compatibility\n", {"secure": secure})
                self.assertEqual(lines, ["CAPABILITY_MISSING:" + reason])

    def test_both_entry_and_restore_reject_firmware_drift_after_validation(self):
        for key, purpose in ((343, "ENTER"), (344, "EXIT"), (343, "RESTORE_ON"), (344, "RESET")):
            with self.subTest(key=key, purpose=purpose):
                lines = self.run_controller(f'''
guard_validate || exit 12
getprop() {{ printf 'changed\\n'; }}
NOW=20; TSWT=1; INK=2; BOOK=1; APPLYING=0; ANIMATION=0
RESTORE_REASON=STOP
if guard_issue {key} {purpose}; then exit 12; fi
printf '%s\\n' "$ERROR_CODE"
result
''')
                self.assertEqual(lines[0], "UNSUPPORTED_FIRMWARE")
                self.assertEqual(lines[-1], "commands=")

    def test_changed_keylayout_prevents_command(self):
        lines = self.run_controller(r'''
guard_validate || exit 12
printf 'key 592 TSWT_OFF\nkey 593 TSWT_ON\n' > "$KEYLAYOUT_PATH"
NOW=20; TSWT=0; INK=0; BOOK=0; APPLYING=0; ANIMATION=0
if guard_issue 343 ENTER; then exit 12; fi
printf '%s\n' "$ERROR_CODE"
result
''')
        self.assertEqual(lines[0], "PHYSICAL_SWITCH_UNAVAILABLE")
        self.assertEqual(lines[-1], "commands=")

    def test_changed_native_snapshot_waits_instead_of_using_stale_state(self):
        lines = self.run_controller(r'''
NOW=20; TSWT=0; INK=0; BOOK=0; APPLYING=0; ANIMATION=0; STABLE=1
guard_issue 343 ENTER || exit 12
printf 'stable=%s error=%s\n' "$STABLE" "$ERROR_CODE"
result
''', {"secure": fixtures.NORMAL_SETTINGS.replace("nxtpaper_animation_state=0", "nxtpaper_animation_state=1")})
        self.assertEqual(lines[0], "stable=0 error=")
        self.assertEqual(lines[-1], "commands=")

    def test_native_test_refuses_even_ambiguous_controller_evidence(self):
        lines = self.run_controller(r'''
rmdir "$LOCK_DIR"
printf 'unreadable-old-controller-identity\n' > "$PID_FILE"
guard_main test-ink
cat "$PID_FILE"
result
''')
        self.assertEqual(lines[:2], ["CAPABILITY_MISSING:CONTROLLER_NOT_STOPPED", "unreadable-old-controller-identity"])
        self.assertEqual(lines[-1], "commands=")

    def test_stopped_native_test_reports_only_command_dispatched(self):
        for action, key in (("test-ink", 343), ("test-normal", 344)):
            with self.subTest(action=action):
                lines = self.run_controller(f'rmdir "$LOCK_DIR"\nguard_main {action}\nresult\n')
                self.assertEqual(lines[0], "COMMAND_SENT:t807d-eea-amd9")
                self.assertEqual(lines[-1], f"commands=0 {key},")

    def test_unknown_boot_state_is_observable_but_native_tests_refuse_it(self):
        lines = self.run_controller('rmdir "$LOCK_DIR"\nguard_main check-compatibility\nguard_main test-normal\nresult\n',
                                    {"secure": fixtures.NORMAL_SETTINGS.replace("TSWT_state=0", "TSWT_state=-1")})
        self.assertEqual(lines[:2], ["VERIFIED:t807d-eea-amd9", "CAPABILITY_MISSING:NATIVE_STATE_NOT_SETTLED"])
        self.assertEqual(lines[-1], "commands=")

    def test_unknown_process_identity_blocks_start_and_stop_without_cleanup(self):
        lines = self.run_controller(r'''
printf 'not-a-valid-token\n' > "$PID_FILE"
guard_live_pid() { return 1; }
if guard_main start; then exit 12; fi
if guard_stop; then exit 12; fi
cat "$PID_FILE"
[ -d "$LOCK_DIR" ] || exit 12
result
''', protocol=True)
        self.assertEqual(lines[0], "ERROR:0:0:0:0:UNKNOWN:CONTROLLER_IDENTITY_UNAVAILABLE:300")
        self.assertEqual(lines[1], lines[0])
        self.assertEqual(lines[2], "not-a-valid-token")
        self.assertEqual(lines[-1], "commands=")

    def test_current_boot_inspection_denied_is_not_proof_of_absence(self):
        lines = self.run_controller(r'''
PROC_ROOT=$GUARD_TEST_DIR/proc
printf '999999:50:test-boot\n' > "$PID_FILE"
if guard_controller_absent; then exit 12; fi
printf 'possibly-live\n'
''', {"proc/sys/kernel/random/boot_id": "test-boot\n", "proc/999999/unreadable": "", "proc/1/present": ""})
        self.assertEqual(lines, ["possibly-live"])

    def test_valid_previous_boot_identity_can_be_proven_absent(self):
        lines = self.run_controller(r'''
PROC_ROOT=$GUARD_TEST_DIR/proc
printf '999999:50:previous-boot\n' > "$PID_FILE"
guard_controller_absent || exit 12
printf 'previous-boot-absent\n'
''', {"proc/sys/kernel/random/boot_id": "current-boot\n"})
        self.assertEqual(lines, ["previous-boot-absent"])


if __name__ == "__main__":
    unittest.main()
