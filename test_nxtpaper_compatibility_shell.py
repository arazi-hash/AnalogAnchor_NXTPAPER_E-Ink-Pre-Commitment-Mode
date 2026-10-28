"""Execute real compatibility/command gates with fake Android observations."""

import unittest

import test_nxtpaper_guard as fixtures


@unittest.skipUnless(fixtures.SHELL, "A POSIX shell is required")
class CompatibilityShellTests(unittest.TestCase):
    run_controller = fixtures.GuardShellTests.run_controller

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
