"""Trial cancellation must survive startup and uncertain native dispatch.

These regressions execute the shipped shell state machine with Android commands
mocked by the existing controller fixture. They never access a handset.
"""

import unittest

import test_nxtpaper_guard as guard_fixtures
import test_nxtpaper_setup as setup_fixtures


@unittest.skipUnless(guard_fixtures.SHELL, "POSIX shell required")
class TrialAbortRegressionTests(unittest.TestCase):
    # Reuse helpers without inheriting another TestCase and discovering its
    # tests a second time.
    run_controller = guard_fixtures.GuardShellTests.run_controller
    run_setup = setup_fixtures.SetupShellTests.run_setup

    def test_enter_timeout_after_delivery_attempts_normal_before_failing(self):
        lines = self.run_setup(r'''
PHASE=ENTER_TEST
PHASE_AT=0
timeout() {
    [ "$1" = 5 ] || exit 12
    shift
    if [ "$3" = 343 ]; then
        # Android received entry, but the command process did not acknowledge it.
        printf '%s %s\n' "$NOW" "$3" >> "$COMMANDS"
        TSWT=1; INK=2; BOOK=1; APPLYING=0; ANIMATION=0
        return 124
    fi
    "$@"
}
step 1 OFF 5 5 4 '0 0 0 0 0'
dispatch_result=$?
[ "$dispatch_result" != 0 ] || exit 12
setup_handle_result "$dispatch_result"
[ "$PHASE" = ABORTING ] || exit 12
[ "$REQUESTED_FAILURE" = NATIVE_COMMAND_TIMEOUT ] || exit 12
step 2 OFF 5 5 4 '1 2 1 0 0'
setup_handle_result "$?"
step 3 OFF 5 5 4 '0 0 0 0 0'
setup_handle_result "$?"
[ ! -e "$QUALIFICATION_FILE" ] || exit 12
if setup_finish_qualification; then exit 12; fi
show
printf 'deadline=%s\n' "$DEADLINE"
''')
        self.assertEqual(lines, [
            "FAILED:NATIVE_COMMAND_TIMEOUT",
            "commands=1 343,2 344,",
            "deadline=0",
        ])

    def test_failed_restoration_command_terminates_without_another_restore_cycle(self):
        lines = self.run_setup(r'''
setup_restore ORIGINAL_TEST_FAILURE
timeout() { [ "$1" = 5 ] || exit 12; return 1; }
step 1 OFF 5 5 4 '1 2 1 0 0'
restore_result=$?
[ "$restore_result" != 0 ] || exit 12
setup_handle_result "$restore_result"
[ ! -e "$QUALIFICATION_FILE" ] || exit 12
show
''')
        self.assertEqual(lines, ["FAILED:NATIVE_COMMAND_DENIED", "commands="])

    def test_failed_fresh_restore_gate_cannot_reset_the_restoration_bound(self):
        lines = self.run_setup(r'''
setup_restore ORIGINAL_TEST_FAILURE
guard_command_gate() { guard_fail SHELL_PRIVILEGE_REQUIRED; return 1; }
step 1 OFF 5 5 4 '1 2 1 0 0'
restore_result=$?
[ "$restore_result" != 0 ] || exit 12
[ "$PHASE" = ABORTING ] || exit 12
setup_handle_result "$restore_result"
[ ! -e "$QUALIFICATION_FILE" ] || exit 12
show
''')
        self.assertEqual(lines, ["FAILED:SHELL_PRIVILEGE_REQUIRED", "commands="])

    def test_cancel_queued_during_preflight_is_acknowledged_without_native_entry(self):
        lines = self.run_setup(r'''
rmdir "$GUARD_LOCK_DIR"
sha256sum() { printf '%s  controller\n' "$PROFILE_CONTROLLER_SHA"; }
guard_compatibility_check() {
    grep -q '^INITIALIZING:' "$STATE_FILE" || exit 12
    printf '%s\n' "$TRIAL_ID" > "$ABORT_FILE"
    TSWT=0; INK=0; BOOK=0; APPLYING=0; ANIMATION=0
    return 0
}
guard_start_monitor() { [ -s "$ABORT_FILE" ] || exit 12; }
guard_monitor_alive() { return 0; }
guard_physical_read() { PHYSICAL=OFF; RAW_SEQ=1; OFF_SEQ=1; ON_SEQ=0; return 0; }
guard_stability() { STABLE=1; }
setup_main start
[ ! -e "$PID_FILE" ] || exit 12
[ ! -e "$QUALIFICATION_FILE" ] || exit 12
show
''')
        self.assertTrue(lines[0].startswith("ABORTED:CANCELLED:0:"), lines)
        self.assertEqual(lines[1:], ["ABORTED:CANCELLED", "commands="])


if __name__ == "__main__":
    unittest.main()
