"""Run the shipped setup state machine with mocked Android observations."""
from pathlib import Path
import unittest
import test_nxtpaper_guard as fixtures

SETUP = Path(__file__).with_name('nxtpaper_setup.sh')
SETUP_PRELUDE = '''
NXTPAPER_SETUP_SOURCE_ONLY=1
NXTPAPER_CONTROLLER_SCRIPT="$1"
. "''' + SETUP.as_posix() + '''"
BASE=$GUARD_TEST_DIR/setup
PID_FILE=$BASE.pid
STATE_FILE=$BASE.state
LOG_FILE=$BASE.log
LOCK_DIR=$BASE.lock
PHYSICAL_FILE=$LOCK_DIR/physical
GETEVENT_PID_FILE=$LOCK_DIR/getevent.pid
READER_PID_FILE=$LOCK_DIR/reader.pid
WRITER_PID_FILE=$LOCK_DIR/writer.pid
MONITOR_ERROR_FILE=$LOCK_DIR/monitor.error
REQUEST_FILE=$BASE.request
ABORT_FILE=$BASE.abort
STATE_TIME_FILE=$BASE.state-time
QUALIFICATION_FILE=$GUARD_TEST_DIR/guard.qualification
OPERATION_LOCK=$GUARD_TEST_DIR/operation.lock
GUARD_PID_FILE=$GUARD_TEST_DIR/guard.pid
GUARD_LOCK_DIR=$GUARD_TEST_DIR/guard.lock
PROFILE_LOADED=0
guard_profile_load || exit 92
PROFILE_SCHEMA=2
PROFILE_BINDING_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
PROFILE_CONTROLLER_SHA=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
PROFILE_ENTER_KEY=343
PROFILE_EXIT_KEY=344
guard_clock() { :; }
guard_duration_boot() { printf '%s\\n' "${TEST_BOOT:-test-boot}"; }
timeout() { [ "$1" = 5 ] || return 125; shift; "$@"; }
VALID_PRIVILEGE=1
guard_process_identity() { process_started=50; process_boot=test-boot; return 0; }
guard_command_gate() { [ "$VALID_PRIVILEGE" = 1 ] || { ERROR_CODE=SHELL_PRIVILEGE_REQUIRED; return 1; }; }
NOW=0
setup_init
TRIAL_ID=123-0-1
step() {
 NOW=$1; PHYSICAL=$2; RAW_SEQ=$3; OFF_SEQ=$4; ON_SEQ=$5
 read -r TSWT INK BOOK APPLYING ANIMATION <<EOF
$6
EOF
 STABLE=1
 setup_tick
}
proof() {
 step 1 OFF 1 1 0 '0 0 0 0 0'
 step 2 ON 2 1 2 '1 2 1 0 0'
 step 3 OFF 3 3 2 '0 0 0 0 0'
}
confirm() {
 printf '%s:confirm-native\\n' "$TRIAL_ID" > "$REQUEST_FILE"
 step 4 OFF 3 3 2 '0 0 0 0 0'
}
software() {
 step 5 ON 4 3 4 '1 2 1 0 0'
 step 6 ON 4 3 4 '1 2 1 0 0'
 step 7 ON 4 3 4 '0 0 0 0 0'
 step 8 OFF 5 5 4 '0 0 0 0 0'
 step 9 OFF 5 5 4 '0 0 0 0 0'
 step 10 OFF 5 5 4 '1 2 1 0 0'
 step 11 OFF 5 5 4 '1 2 1 0 0'
 step 12 OFF 5 5 4 '0 0 0 0 0'
}
show() { printf '%s:%s\\n' "$PHASE" "$REASON"; printf 'commands='; tr '\\n' ',' < "$COMMANDS"; printf '\\n'; }
'''

@unittest.skipUnless(fixtures.SHELL, 'POSIX shell required')
class SetupShellTests(unittest.TestCase):
    run_controller = fixtures.GuardShellTests.run_controller

    def run_setup(self, scenario, files=None):
        return self.run_controller(SETUP_PRELUDE + scenario, files, protocol=True, exit_protocol=True)

    def test_passive_physical_sequence_never_sends_commands(self):
        self.assertEqual(self.run_setup('proof\nshow\n'), ['WAIT_OWNER_CONFIRM:', 'commands='])

    def test_native_state_alone_and_unknown_boot_state_do_not_prove_physical_switch(self):
        lines = self.run_setup("step 1 UNKNOWN 0 0 0 '-1 0 0 0 0'\nstep 2 UNKNOWN 0 0 0 '0 0 0 0 0'\nstep 3 ON 1 0 1 '1 2 1 0 0'\nshow\n")
        self.assertEqual(lines, ['WAIT_NORMAL:', 'commands='])

    def test_unordered_physical_events_cannot_skip_passive_proof(self):
        lines = self.run_setup("step 1 OFF 1 1 0 '0 0 0 0 0'\nstep 2 OFF 3 3 2 '0 0 0 0 0'\nshow\n")
        self.assertEqual(lines, ['WAIT_PHYSICAL_INK:', 'commands='])

    def test_no_software_commands_until_owner_confirms_native_experience(self):
        lines = self.run_setup("proof\nstep 4 ON 4 3 4 '1 2 1 0 0'\nshow\n")
        self.assertEqual(lines, ['WAIT_OWNER_CONFIRM:', 'commands='])

    def test_software_exit_reentry_restoration_passes_without_commitment(self):
        lines = self.run_setup('proof\nconfirm\nsoftware\n[ ! -e "$QUALIFICATION_FILE" ] || exit 12\nshow\nprintf "deadline=%s\\n" "$DEADLINE"\n')
        self.assertEqual(lines, ['PASSED:', 'commands=6 344,9 343,11 344,', 'deadline=0'])

    def test_passed_does_not_qualify_until_fresh_normal_owner_acknowledgement(self):
        lines = self.run_setup('proof\nconfirm\nsoftware\nprintf "%s:qualify\\n" "$TRIAL_ID" > "$REQUEST_FILE"\nstep 13 OFF 5 5 4 "0 0 0 0 0"\nshow\ncat "$QUALIFICATION_FILE"\n')
        self.assertEqual(lines[:2], ['QUALIFIED:', 'commands=6 344,9 343,11 344,'])
        self.assertIn('result=passed', lines)
        self.assertIn('owner_confirmed=1', lines)

    def test_failed_or_interrupted_trial_cannot_mint_qualification(self):
        lines = self.run_setup('PHASE=FAILED\nPHYSICAL=OFF\nTSWT=0; INK=0; BOOK=0; STABLE=1\nif setup_finish_qualification; then exit 12; fi\n[ ! -e "$QUALIFICATION_FILE" ] || exit 12\nshow\n')
        self.assertEqual(lines, ['FAILED:', 'commands='])

    def test_physical_on_prevents_final_qualification(self):
        lines = self.run_setup('proof\nconfirm\nsoftware\nPHYSICAL=ON\nif setup_finish_qualification; then exit 12; fi\n[ ! -e "$QUALIFICATION_FILE" ] || exit 12\nshow\n')
        self.assertEqual(lines[0], 'PASSED:')

    def test_cancel_restores_immediately_without_five_minute_delay(self):
        lines = self.run_setup('proof\nconfirm\nstep 5 ON 4 3 4 "1 2 1 0 0"\nprintf "%s\\n" "$TRIAL_ID" > "$ABORT_FILE"\nstep 6 ON 4 3 4 "1 2 1 0 0"\nstep 7 OFF 5 5 4 "0 0 0 0 0"\nshow\n[ ! -e "$QUALIFICATION_FILE" ] || exit 12\n')
        self.assertEqual(lines, ['ABORTED:CANCELLED', 'commands=6 344,'])

    def test_failed_restoration_is_incomplete(self):
        lines = self.run_setup('PHASE=ABORTING; PHASE_AT=0; ISSUED=1; REQUESTED_FAILURE=CANCELLED\nstep 45 ON 1 0 1 "1 2 1 0 0"\nshow\n[ ! -e "$QUALIFICATION_FILE" ] || exit 12\n')
        self.assertEqual(lines, ['FAILED:RESTORATION_FAILED', 'commands='])

    def test_lost_privilege_blocks_software_test_command(self):
        lines = self.run_setup('proof\nconfirm\nstep 5 ON 4 3 4 "1 2 1 0 0"\nVALID_PRIVILEGE=0\nif step 6 ON 4 3 4 "1 2 1 0 0"; then exit 12; fi\nprintf "%s\\n" "$ERROR_CODE"\nshow\n')
        self.assertEqual(lines, ['SHELL_PRIVILEGE_REQUIRED', 'EXIT_TEST:', 'commands='])

    def test_hung_native_dispatch_timeout_cannot_pass_or_qualify(self):
        lines = self.run_setup('proof\nconfirm\nstep 5 ON 4 3 4 "1 2 1 0 0"\ntimeout() { [ "$1" = 5 ] || exit 12; return 124; }\nif step 6 ON 4 3 4 "1 2 1 0 0"; then exit 12; fi\nprintf "%s\\n" "$ERROR_CODE"\n[ ! -e "$QUALIFICATION_FILE" ] || exit 12\nshow\n')
        self.assertEqual(lines, ['NATIVE_COMMAND_TIMEOUT', 'EXIT_TEST:', 'commands='])

    def test_live_or_unknown_guard_evidence_is_preserved_without_probe(self):
        lines = self.run_setup('printf "unknown-controller\\n" > "$GUARD_PID_FILE"\nguard_compatibility_check() { printf "UNSAFE PREFLIGHT\\n"; }\nif setup_main start; then exit 12; fi\ncat "$GUARD_PID_FILE"\nshow\n')
        self.assertEqual(lines, ['FAILED:CONTROLLER_NOT_STOPPED:0::', 'unknown-controller', 'WAIT_NORMAL:', 'commands='])

    def test_failed_new_setup_invalidates_previous_ticket_after_guard_absence(self):
        lines = self.run_setup('rmdir "$GUARD_LOCK_DIR"\nprintf "old-ticket\\n" > "$QUALIFICATION_FILE"\nguard_compatibility_check() { COMPAT_REASON=CAPABILITY_CHANGED; return 1; }\nsetup_main start || :\n[ ! -e "$QUALIFICATION_FILE" ] || exit 12\nshow\n')
        self.assertTrue(lines[0].startswith('FAILED:CAPABILITY_CHANGED:0:'), lines)
        self.assertEqual(lines[1:], ['FAILED:CAPABILITY_CHANGED', 'commands='])

    def test_initializing_is_published_before_preflight_without_mode_commands(self):
        lines = self.run_setup('rmdir "$GUARD_LOCK_DIR"\nguard_compatibility_check() { grep -q "^INITIALIZING:" "$STATE_FILE" || exit 12; [ -s "$PID_FILE" ] || exit 12; COMPAT_REASON=CAPABILITY_CHANGED; return 1; }\nsetup_main start || :\n[ ! -e "$PID_FILE" ] || exit 12\nshow\n')
        self.assertTrue(lines[0].startswith('FAILED:CAPABILITY_CHANGED:0:'), lines)
        self.assertEqual(lines[1:], ['FAILED:CAPABILITY_CHANGED', 'commands='])

    def test_orphaned_passed_state_is_interrupted_and_read_only(self):
        lines = self.run_setup('rmdir "$GUARD_LOCK_DIR"\nprintf "PASSED::20:123-0-1:%s\\n" "$PROFILE_BINDING_SHA" > "$STATE_FILE"\nsetup_live() { return 1; }\nsetup_status\n[ ! -e "$QUALIFICATION_FILE" ] || exit 12\nshow\n')
        self.assertEqual(lines[0], 'FAILED:TRIAL_INTERRUPTED:20:123-0-1:' + 'a' * 64)
        self.assertEqual(lines[1:], ['WAIT_NORMAL:', 'commands='])

    def test_explicit_retry_cleans_only_previous_boot_trial(self):
        lines = self.run_setup('rmdir "$GUARD_LOCK_DIR"\nmkdir "$LOCK_DIR"\nprintf "123:50:previous-boot\\n" > "$PID_FILE"\nprintf "old-monitor-token\\n" > "$GETEVENT_PID_FILE"\nsetup_main reset-stale\n[ ! -e "$PID_FILE" ] && [ ! -d "$LOCK_DIR" ] || exit 12\nshow\n')
        self.assertEqual(lines, ['STOPPED::0::', 'WAIT_NORMAL:', 'commands='])

    def test_explicit_retry_preserves_same_boot_or_unknown_identity(self):
        for token in ('123:50:test-boot', 'unknown'):
            lines = self.run_setup('rmdir "$GUARD_LOCK_DIR"\nmkdir "$LOCK_DIR"\nprintf "' + token + '\\n" > "$PID_FILE"\nif setup_main reset-stale; then exit 12; fi\ncat "$PID_FILE"\n[ -d "$LOCK_DIR" ] || exit 12\nshow\n')
            self.assertEqual(lines, ['FAILED:TRIAL_IDENTITY_UNAVAILABLE:0::', token, 'WAIT_NORMAL:', 'commands='])

    def test_stale_trial_retry_never_replaces_unknown_guard(self):
        lines = self.run_setup('mkdir "$LOCK_DIR"\nprintf "123:50:previous-boot\\n" > "$PID_FILE"\nprintf "unknown-live-guard\\n" > "$GUARD_PID_FILE"\nif setup_main reset-stale; then exit 12; fi\ncat "$PID_FILE"\ncat "$GUARD_PID_FILE"\nshow\n')
        self.assertEqual(lines, ['FAILED:CONTROLLER_NOT_STOPPED:0::', '123:50:previous-boot', 'unknown-live-guard', 'WAIT_NORMAL:', 'commands='])

    def test_explicit_retry_recovers_known_previous_boot_operation_mutex(self):
        lines = self.run_setup('rmdir "$GUARD_LOCK_DIR"\nmkdir "$OPERATION_LOCK"\nprintf "previous-boot\\n" > "$OPERATION_LOCK/boot"\nsetup_main reset-stale\n[ ! -d "$OPERATION_LOCK" ] || exit 12\nshow\n')
        self.assertEqual(lines, ['STOPPED::0::', 'WAIT_NORMAL:', 'commands='])

if __name__ == '__main__':
    unittest.main()
