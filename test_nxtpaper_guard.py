"""Execute the shipped Android shell controller with fake commands (no phone).

Linux /bin/sh and Git for Windows usr/bin/sh.exe are supported. These tests
source the actual APK asset's functions rather than a second state-machine model.
"""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("nxtpaper_guard.sh")


def find_shell():
    for name in ("sh", "dash", "bash"):
        candidate = shutil.which(name)
        if candidate:
            return candidate
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    home = Path.home()
    for root in (local / "Programs/Git", Path("C:/Program Files/Git"),
                 home / ".cache/codex-runtimes/codex-primary-runtime/dependencies/native/git"):
        candidate = root / "usr/bin/sh.exe"
        if candidate.is_file():
            return str(candidate)
    return None


SHELL = find_shell()
PRELUDE = r'''
PATH=/usr/bin:/bin:$PATH
export NXTPAPER_GUARD_SOURCE_ONLY=1
. "$1"
BASE=$GUARD_TEST_DIR/guard
PID_FILE=$BASE.pid
STATE_FILE=$BASE.state
LOG_FILE=$BASE.log
LANGUAGE_FILE=$BASE.language
LOCK_DIR=$BASE.lock
PHYSICAL_FILE=$LOCK_DIR/physical
GETEVENT_PID_FILE=$LOCK_DIR/getevent.pid
READER_PID_FILE=$LOCK_DIR/reader.pid
WRITER_PID_FILE=$LOCK_DIR/writer.pid
MONITOR_ERROR_FILE=$LOCK_DIR/monitor.error
DURATION_FILE=$BASE.duration
DURATION_REQUEST=$BASE.duration.request
DURATION_ACK=$BASE.duration.ack
DURATION_COMMAND_LOCK=$BASE.duration.command.lock
KEYLAYOUT_PATH=$GUARD_TEST_DIR/Generic.kl
mkdir -p "$LOCK_DIR"
printf 'key 592 TSWT_ON\nkey 593 TSWT_OFF\n' > "$KEYLAYOUT_PATH"
COMMANDS=$GUARD_TEST_DIR/commands
: > "$COMMANDS"
NOW=0
guard_init
guard_duration_boot() { printf '%s\n' "${TEST_BOOT:-test-boot}"; }
input() { printf '%s %s\n' "$NOW" "$2" >> "$COMMANDS"; }
cmd() { :; }
settings() {
  if [ "$1 $2" = 'list secure' ]; then cat "$GUARD_TEST_DIR/secure";
  elif [ "$1 $2 $3" = 'get system nxtpaper_guard_duration' ]; then printf '%s\n' "${FAKE_DURATION:-300}";
  fi
}
tick() {
  NOW=$1
  read -r TSWT INK BOOK APPLYING ANIMATION <<EOF
$2
EOF
  guard_tick
}
raw() {
  printf '%s:%s:%s:%s:%s:%s:%s\n' "$1" "$2" "$NOW" "$3" "$4" "$NOW" "$5" > "$PHYSICAL_FILE"
  guard_physical_read
}
commit() {
  tick 0 '0 0 0 0 0'
  raw 1 OFF 1 0 1
  tick 1 '0 0 0 0 0'
  raw 2 ON 1 2 1
  tick 2 '1 2 1 1 1'
  tick 6 '1 2 1 0 0'
  tick 8 '1 2 1 0 0'
}
result() {
  guard_state
  printf 'commands='; tr '\n' ',' < "$COMMANDS"; printf '\n'
}
'''

NORMAL_SETTINGS = """TSWT_state=0
nxtpaper_ink_style_state=0
nxtpaper_book_style_state=0
nxtpaper_is_applying_theme=0
nxtpaper_animation_state=0
tct_nxtpaper_mode_select=3
tct_nxtpaper_switch_imm=1
"""
CAPABILITIES = """add device 1: /dev/input/event1
  name:     "gpio-keys"
  events:
    KEY (0001): KEY_POWER
add device 2: /dev/input/event9
  name:     "tswt"
  events:
    KEY (0001): KEY_BRIGHTNESS_MIN    KEY_BRIGHTNESS_MAX
  input props:
    <none>
"""


@unittest.skipUnless(SHELL, "A POSIX shell is required (Git for Windows includes one)")
class GuardShellTests(unittest.TestCase):
    def run_controller(self, scenario, files=None, protocol=False):
        with tempfile.TemporaryDirectory(prefix="nxtpaper-guard-test-") as folder:
            for name, content in (files or {}).items():
                path = Path(folder, name)
                path.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(content, bytes):
                    path.write_bytes(content)
                else:
                    path.write_text(content, encoding="utf-8", newline="\n")
            environment = os.environ.copy()
            environment["GUARD_TEST_DIR"] = Path(folder).as_posix()
            run = subprocess.run([SHELL, "-c", PRELUDE + scenario, "guard-test", SCRIPT.as_posix()],
                                 text=True, encoding="utf-8", capture_output=True, env=environment, timeout=45)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertEqual(run.stderr, "", run.stderr)
            lines = run.stdout.strip().splitlines()
            if not protocol:
                # Older assertions exercise the original seven-field prefix.
                lines = [line.rsplit(":", 1)[0] if line.count(":") == 7 else line for line in lines]
            return lines

    def test_default_deadline_begins_only_after_settled_native_entry(self):
        lines = self.run_controller("commit\nresult\n")
        self.assertEqual(lines, ["COMMITTED:300:8:308:8:ON:", "commands="])

    def test_framework_tswt_never_supplies_initial_physical_position(self):
        lines = self.run_controller("tick 0 '1 2 1 0 0'\ntick 20 '1 2 1 0 0'\nresult\n")
        self.assertEqual(lines, ["WAIT_SWITCH:0:0:0:20:UNKNOWN:", "commands="])

    def test_initial_fresh_on_without_off_starts_commitment(self):
        lines = self.run_controller("raw 1 ON 0 1 0\ntick 1 '1 2 1 0 0'\ntick 9 '1 2 1 0 0'\ntick 11 '1 2 1 0 0'\nresult\n")
        self.assertEqual(lines[0], "COMMITTED:300:11:311:11:ON:")
        self.assertEqual(lines[1], "commands=")

    def test_off_on_off_between_polls_preserves_real_entry(self):
        lines = self.run_controller("raw 3 OFF 3 2 1\ntick 3 '0 0 0 0 0'\nresult\n")
        self.assertEqual(lines[0], "STARTING:0:0:0:3:OFF:")

    def test_recovery_does_not_renew_deadline_or_impersonate_slider(self):
        lines = self.run_controller("""
commit
raw 3 OFF 3 2 1
tick 20 '0 0 0 1 1'
tick 25 '0 0 0 0 0'
tick 27 '0 0 0 0 0'
tick 28 '1 2 0 1 1'
tick 35 '1 2 1 0 0'
tick 37 '1 2 1 0 0'
result
""")
        self.assertEqual(lines, ["COMMITTED:271:8:308:37:OFF:", "commands=27 343,"])

    def test_returning_physical_on_continues_reading_after_original_deadline(self):
        lines = self.run_controller("""
commit
raw 3 OFF 3 2 1
tick 20 '0 0 0 0 0'
tick 22 '0 0 0 0 0'
tick 30 '1 2 1 0 0'
tick 32 '1 2 1 0 0'
raw 4 ON 3 4 1
tick 180 '1 2 1 0 0'
tick 308 '1 2 1 0 0'
tick 900 '1 2 1 0 0'
result
""")
        self.assertEqual(lines, ["EXTENDED:0:8:308:900:ON:", "commands=22 343,"])

    def test_extended_native_animation_never_ends_reading(self):
        lines = self.run_controller("""
commit
tick 308 '1 2 1 0 0'
tick 309 '1 0 0 1 1'
tick 311 '1 2 0 0 0'
tick 312 '1 2 1 1 1'
tick 314 '1 2 1 0 0'
tick 316 '1 2 1 0 0'
result
""")
        self.assertEqual(lines, ["EXTENDED:0:8:308:316:ON:", "commands="])

    def test_extended_exit_requires_real_physical_off_and_settled_normal(self):
        lines = self.run_controller("""
commit
tick 308 '1 2 1 0 0'
raw 3 OFF 3 2 1
tick 309 '1 2 1 0 0'
tick 310 '0 0 0 1 1'
guard_state
tick 315 '0 0 0 0 0'
tick 317 '0 0 0 0 0'
result
""")
        self.assertEqual(lines, ["RESTORING:0:8:308:310:OFF:", "IDLE:0:0:0:317:OFF:", "commands=309 344,"])

    def test_fresh_on_with_stale_normal_snapshot_wins_at_deadline(self):
        lines = self.run_controller("""
commit
raw 3 OFF 3 2 1
tick 307 '0 0 0 0 0'
printf '4:ON:308:3:4:308:1\n' > "$PHYSICAL_FILE"
tick 308 '0 0 0 0 0'
tick 309 '0 0 0 0 0'
result
""")
        self.assertEqual(lines, ["EXTENDED:0:8:308:309:ON:", "commands=309 343,"])

    def test_fresh_on_immediately_before_off_injection_cancels_exit(self):
        lines = self.run_controller("""
commit
PHYSICAL=OFF
RESTORE_REASON=EXPIRED
PHASE=RESTORING
printf '3:ON:308:1:3:308:1\n' > "$PHYSICAL_FILE"
NOW=308
guard_issue 344 EXIT
result
""")
        self.assertEqual(lines, ["EXTENDED:0:8:308:308:ON:", "commands="])

    def test_reentry_during_off_transition_waits_for_it_to_settle(self):
        lines = self.run_controller("""
commit
tick 308 '1 2 1 0 0'
raw 3 OFF 3 2 1
tick 310 '1 2 1 0 0'
raw 4 ON 3 4 1
tick 311 '0 0 0 1 1'
tick 313 '0 0 0 1 1'
tick 316 '0 0 0 0 0'
tick 318 '0 0 0 0 0'
result
""")
        self.assertEqual(lines, ["EXTENDED:0:8:308:318:ON:", "commands=310 344,318 343,"])

    def test_wrong_mode_repair_is_serialized_and_rate_limited(self):
        lines = self.run_controller("""
commit
tick 20 '1 0 0 0 0'
tick 22 '1 0 0 0 0'
tick 23 '0 0 0 1 1'
tick 25 '0 0 0 0 0'
tick 27 '0 0 0 0 0'
tick 28 '1 2 0 0 0'
tick 30 '1 2 0 0 0'
tick 33 '1 2 1 0 0'
tick 35 '1 2 1 0 0'
result
""")
        self.assertEqual(lines, ["COMMITTED:273:8:308:35:ON:", "commands=22 344,27 343,"])

    def test_duration_is_frozen_for_active_session(self):
        lines = self.run_controller("NEXT_DURATION=60\ncommit\nNEXT_DURATION=900\ntick 30 '1 2 1 0 0'\nresult\n")
        self.assertEqual(lines[0], "COMMITTED:38:8:68:30:ON:")

    def test_invalid_or_octal_like_public_duration_is_rejected(self):
        lines = self.run_controller("""
for invalid_duration in 0 -1 null 900 030 9999999999999999999999999999; do
  guard_set_duration "$invalid_duration"
done
""")
        self.assertEqual(lines, ["ERROR:0:0:0:0:UNKNOWN:DURATION_INVALID"] * 6)

    def test_deadline_with_raw_off_waits_for_existing_entry_to_settle(self):
        lines = self.run_controller("""
commit
raw 3 OFF 3 2 1
tick 305 '0 0 0 0 0'
tick 307 '0 0 0 0 0'
tick 308 '1 2 0 1 1'
tick 313 '1 2 1 0 0'
tick 315 '1 2 1 0 0'
result
""")
        self.assertEqual(lines, ["RESTORING:0:8:308:315:OFF:", "commands=307 343,315 344,"])

    def test_explicit_stop_overrides_physical_on_and_waits_for_settling(self):
        lines = self.run_controller("""
commit
STOP_REQUESTED=1
NOW=20
guard_begin_restore STOP
tick 20 '1 2 1 0 0'
tick 21 '0 0 0 1 1'
guard_state
tick 25 '0 0 0 0 0'
tick 27 '0 0 0 0 0'
result
""")
        self.assertEqual(lines, ["RESTORING:0:8:308:21:ON:", "STOPPED:0:0:0:27:ON:", "commands=20 344,"])

    def test_transition_timeout_fails_visibly_without_command_spam(self):
        lines = self.run_controller("""
commit
tick 20 '1 0 0 1 1'
if tick 66 '1 0 0 1 1'; then exit 12; fi
printf '%s\n' "$ERROR_CODE"
result
""")
        self.assertEqual(lines[0], "NATIVE_RECOVERY_TIMEOUT")
        self.assertEqual(lines[-1], "commands=")

    def test_real_raw_reader_ignores_framework_keys_release_and_repeat(self):
        lines = self.run_controller(r'''
guard_clock() { NOW=123; }
guard_raw_reader <<EOF
[ 100.0] /dev/input/event9: EV_KEY KEY_BRIGHTNESS_MIN UP
[ 100.1] EV_KEY KEY_BRIGHTNESS_MIN REPEAT
input keyevent 343
[ 100.2] EV_KEY 343 DOWN
[ 100.3] EV_SYN SYN_REPORT 00000000
[ 100.4] /dev/input/event9: EV_KEY KEY_BRIGHTNESS_MAX DOWN
[ 100.5] EV_KEY KEY_BRIGHTNESS_MIN DOWN
EOF
guard_physical_read
printf '%s:%s:%s:%s:%s\n' "$RAW_SEQ" "$PHYSICAL" "$OFF_SEQ" "$ON_SEQ" "$FIRST_OFF_SEQ"
''')
        self.assertEqual(lines, ["2:ON:1:2:1"])

    def test_discovers_boot_dependent_node_by_name_and_capabilities(self):
        lines = self.run_controller("getevent() { cat \"$GUARD_TEST_DIR/caps\"; }\nguard_discover\nprintf '%s\\n' \"$SWITCH_NODE\"\n",
                                    {"caps": CAPABILITIES.replace("event9", "event17")})
        self.assertEqual(lines, ["/dev/input/event17"])

    def test_missing_ambiguous_or_incompatible_driver_is_rejected(self):
        for text in (CAPABILITIES.replace('"tswt"', '"other"'),
                     CAPABILITIES + CAPABILITIES,
                     CAPABILITIES.replace("KEY_BRIGHTNESS_MAX", "KEY_VOLUMEUP")):
            with self.subTest(capabilities=text):
                self.run_controller("getevent() { cat \"$GUARD_TEST_DIR/caps\"; }\nif guard_discover; then exit 12; fi\n", {"caps": text})

    def test_reversed_keylayout_is_rejected(self):
        self.run_controller("""
getevent() { cat "$GUARD_TEST_DIR/caps"; }
printf 'key 592 TSWT_OFF\nkey 593 TSWT_ON\n' > "$KEYLAYOUT_PATH"
if guard_discover; then exit 12; fi
""", {"caps": CAPABILITIES})

    def test_required_native_flags_and_presets_are_validated(self):
        valid = self.run_controller("guard_native_read\nprintf '%s %s %s %s %s\\n' \"$TSWT\" \"$INK\" \"$BOOK\" \"$APPLYING\" \"$ANIMATION\"\n", {"secure": NORMAL_SETTINGS})
        self.assertEqual(valid, ["0 0 0 0 0"])
        for bad in (NORMAL_SETTINGS.replace("nxtpaper_animation_state=0\n", ""),
                    NORMAL_SETTINGS + "TSWT_state=0\n",
                    NORMAL_SETTINGS.replace("tct_nxtpaper_mode_select=3", "tct_nxtpaper_mode_select=1"),
                    NORMAL_SETTINGS.replace("nxtpaper_is_applying_theme=0", "nxtpaper_is_applying_theme=null")):
            self.run_controller("if guard_native_read; then exit 12; fi\n", {"secure": bad})

    def test_uptime_clock_ignores_wall_time_and_includes_sleep(self):
        lines = self.run_controller("PROC_ROOT=$GUARD_TEST_DIR/proc\nguard_clock\nprintf '%s\\n' \"$NOW\"\n", {"proc/uptime": "900.42 155.11\n"})
        self.assertEqual(lines, ["900"])

    def test_cached_commitment_without_live_pid_reports_stopped(self):
        lines = self.run_controller("printf 'COMMITTED:300:8:308:8:ON:\\n' > \"$STATE_FILE\"\nguard_status\n")
        self.assertEqual(lines, ["STOPPED:0:0:0:0:UNKNOWN:"])

    def test_stop_without_daemon_acknowledges_error_without_mode_command(self):
        lines = self.run_controller("""
printf 'ERROR:0:0:0:0:UNKNOWN:PHYSICAL_MONITOR_FAILED\n' > "$STATE_FILE"
guard_stop
guard_status
printf 'commands='; cat "$COMMANDS"
""")
        self.assertEqual(lines, ["STOPPED:0:0:0:0:UNKNOWN:", "STOPPED:0:0:0:0:UNKNOWN:", "commands="])

    def test_countdown_notifications_are_limited_to_phase_and_minute_changes(self):
        lines = self.run_controller("""
cmd() { printf '%s\n' "$*" >> "$GUARD_TEST_DIR/notifications"; }
commit
guard_notify
NOW=9; guard_notify
NOW=10; guard_notify
NOW=69; guard_notify
cat "$GUARD_TEST_DIR/notifications"
""")
        self.assertEqual(len(lines), 3)
        self.assertIn("5m 0s remaining", lines[0])
        self.assertIn("4m 59s remaining", lines[1])
        self.assertIn("3m 59s remaining", lines[2])

    def test_full_startup_failure_is_visible_and_sends_no_mode_command(self):
        lines = self.run_controller("""
guard_clock() { NOW=10; }
guard_tools() { return 0; }
guard_process_identity() { process_started=50; process_boot=boot-test; }
id() { printf '2000\n'; }
getprop() { printf 'unsupported\n'; }
sleep() { :; }
if guard_main start; then exit 12; fi
guard_status
printf 'commands='; cat "$COMMANDS"
""")
        self.assertEqual(lines, ["ERROR:0:0:0:10:UNKNOWN:UNSUPPORTED_FIRMWARE",
                                 "ERROR:0:0:0:10:UNKNOWN:UNSUPPORTED_FIRMWARE", "commands="])

    def test_missing_android_tool_is_an_explicit_startup_error(self):
        lines = self.run_controller("""
command() { [ "$2" != awk ]; }
if guard_tools; then exit 12; fi
printf '%s\n' "$ERROR_CODE"
""")
        self.assertEqual(lines, ["REQUIRED_TOOL_UNAVAILABLE_awk"])

    def test_initializing_replaces_old_cached_session_before_validation(self):
        lines = self.run_controller("""
printf 'COMMITTED:300:8:308:8:ON:\n' > "$STATE_FILE"
guard_initializing
cat "$STATE_FILE"
""")
        self.assertEqual(lines, ["INITIALIZING:0:0:0:0:UNKNOWN:"])

    def test_full_startup_ended_monitor_is_visible_and_cleans_pid(self):
        lines = self.run_controller("""
guard_clock() { NOW=10; }
guard_tools() { return 0; }
guard_process_identity() { process_started=50; process_boot=boot-test; }
guard_validate() { SWITCH_NODE=/dev/input/event9; return 0; }
guard_stream_writer() { return 1; }
guard_stream_reader() { return 1; }
sleep() { [ -z "$READER_PID" ] || wait "$READER_PID" 2>/dev/null; }
mkfifo() { printf 'FORBIDDEN FIFO\n'; exit 13; }
if guard_main start; then exit 12; fi
guard_status
[ ! -e "$PID_FILE" ] || exit 13
printf 'commands='; cat "$COMMANDS"
""")
        self.assertEqual(lines, ["ERROR:0:0:0:10:UNKNOWN:PHYSICAL_MONITOR_FAILED",
                                 "ERROR:0:0:0:10:UNKNOWN:PHYSICAL_MONITOR_FAILED", "commands="])

    def test_anonymous_pipeline_delivers_raw_events_without_named_fifo(self):
        lines = self.run_controller("""
guard_stream_writer() { printf '[ 1.0] EV_KEY KEY_BRIGHTNESS_MAX DOWN\n[ 2.0] EV_KEY KEY_BRIGHTNESS_MIN DOWN\n'; }
guard_stream_reader() { guard_raw_reader; }
guard_monitor_alive() { return 0; }
guard_clock() { NOW=123; }
sleep() { :; }
mkfifo() { printf 'FORBIDDEN FIFO\n'; exit 13; }
guard_start_monitor
wait "$READER_PID"
guard_physical_read
printf '%s:%s:%s:%s\n' "$RAW_SEQ" "$PHYSICAL" "$OFF_SEQ" "$ON_SEQ"
""")
        self.assertEqual(lines, ["2:ON:1:2"])

    def test_locale_change_refreshes_notification_without_changing_deadline(self):
        lines = self.run_controller("""
cmd() { printf '%s\n' "$*" >> "$GUARD_TEST_DIR/notifications"; }
commit
printf 'en\n' > "$LANGUAGE_FILE"
guard_notify
printf 'ar\n' > "$LANGUAGE_FILE"
guard_notify
guard_notify
guard_state
cat "$GUARD_TEST_DIR/notifications"
""")
        self.assertEqual(lines[0], "COMMITTED:300:8:308:8:ON:")
        self.assertEqual(len(lines), 3)
        self.assertIn("E-Ink Pre-commitment Mode", lines[1])
        self.assertIn("E-Ink Pre-commitment Mode", lines[2])
        self.assertIn("الوقت المتبقي", lines[2])

    def test_monitor_cleanup_checks_pid_start_time_boot_and_command(self):
        stat = "42 (getevent) S " + " ".join(["0"] * 18) + " 999 0\n"
        base_files = {"proc/42/stat": stat,
                      "proc/42/cmdline": b"getevent\x00-lt\x00/dev/input/event9\x00",
                      "proc/sys/kernel/random/boot_id": "boot-test\n"}
        for token, expected in (("42:999:boot-test:/dev/input/event9", "-0 42\n-TERM 42"),
                                ("42:888:boot-test:/dev/input/event9", ""),
                                ("42:999:old-boot:/dev/input/event9", ""),
                                ("42:999:boot-test:/dev/input/event2", "")):
            with self.subTest(token=token):
                lines = self.run_controller("""
PROC_ROOT=$GUARD_TEST_DIR/proc
kill() { printf '%s\n' "$*"; return 0; }
cat "$GUARD_TEST_DIR/token" > "$GETEVENT_PID_FILE"
guard_monitor_signal "$GETEVENT_PID_FILE" getevent
""", {**base_files, "token": token + "\n"})
                self.assertEqual("\n".join(lines), expected)

    def test_monitor_health_requires_all_three_processes(self):
        lines = self.run_controller("""
guard_monitor_valid() { [ "$2" != reader ]; }
if guard_monitor_alive; then exit 12; fi
guard_monitor_valid() { return 0; }
guard_monitor_alive || exit 13
printf 'healthy\n'
""")
        self.assertEqual(lines, ["healthy"])

    def test_stale_heartbeat_reports_error_even_with_live_process(self):
        lines = self.run_controller("""
guard_live_pid() { return 0; }
guard_clock() { NOW=100; }
printf 'COMMITTED:300:8:308:8:ON:\n' > "$STATE_FILE"
guard_status
""")
        self.assertEqual(lines, ["ERROR:0:0:0:100:UNKNOWN:DAEMON_UNRESPONSIVE"])

    def test_pid_reuse_or_wrong_command_is_never_killed(self):
        stat = "42 (sh) S " + " ".join(["0"] * 18) + " 999 0\n"
        files = {"proc/42/stat": stat, "proc/42/cmdline": b"/system/bin/sh\x00/other/script.sh\x00",
                 "proc/sys/kernel/random/boot_id": "boot-test\n"}
        lines = self.run_controller("""
PROC_ROOT=$GUARD_TEST_DIR/proc
printf '42:999:boot-test\n' > "$PID_FILE"
kill() { printf 'UNSAFE KILL\n'; return 0; }
guard_stop
""", files)
        self.assertEqual(lines, ["STOPPED:0:0:0:0:UNKNOWN:"])

    def test_saved_pid_start_ticks_must_match(self):
        stat = "42 (sh with spaces) S " + " ".join(["0"] * 18) + " 999 0\n"
        files = {"proc/42/stat": stat,
                 "proc/42/cmdline": b"/system/bin/sh\x00/data/local/tmp/nxtpaper_guard.sh\x00start\x00",
                 "proc/sys/kernel/random/boot_id": "boot-test\n"}
        lines = self.run_controller("""
PROC_ROOT=$GUARD_TEST_DIR/proc
printf '42:888:boot-test\n' > "$PID_FILE"
kill() { printf 'UNSAFE KILL\n'; return 0; }
guard_stop
""", files)
        self.assertEqual(lines, ["STOPPED:0:0:0:0:UNKNOWN:"])

    def test_first_on_then_off_between_polls_preserves_entry(self):
        lines = self.run_controller("""
raw 2 OFF 2 1 2
tick 3 '0 0 0 0 0'
tick 5 '0 0 0 0 0'
tick 7 '0 0 0 0 0'
tick 8 '1 2 1 0 0'
tick 10 '1 2 1 0 0'
result
""")
        self.assertEqual(lines, ["COMMITTED:300:10:310:10:OFF:", "commands=7 343,"])

    def test_slow_native_acknowledgment_is_not_interrupted(self):
        lines = self.run_controller("""
commit
tick 20 '0 0 0 0 0'
tick 22 '0 0 0 0 0'
tick 30 '1 2 0 0 0'
tick 32 '1 2 0 0 0'
tick 33 '1 2 1 0 0'
tick 35 '1 2 1 0 0'
result
""")
        self.assertEqual(lines, ["COMMITTED:273:8:308:35:ON:", "commands=22 343,"])

    def test_dropped_enter_retries_twice_then_overall_timeout_wins(self):
        lines = self.run_controller("""
commit
tick 20 '0 0 0 0 0'
tick 22 '0 0 0 0 0'
tick 25 '0 0 0 0 0'
tick 37 '0 0 0 0 0'
tick 40 '0 0 0 0 0'
tick 52 '0 0 0 0 0'
tick 55 '0 0 0 0 0'
tick 65 '0 0 0 0 0'
if tick 66 '0 0 0 0 0'; then exit 12; fi
printf '%s:%s:%s\n' "$ERROR_CODE" "$REPAIR_CYCLES" "$DEADLINE"
result
""")
        self.assertEqual(lines[0], "NATIVE_RECOVERY_TIMEOUT:2:308")
        self.assertEqual(lines[-1], "commands=22 343,37 343,52 343,")

    def test_stalled_partial_enter_uses_serialized_reset_without_renewing_time(self):
        lines = self.run_controller("""
commit
tick 20 '0 0 0 0 0'
tick 22 '0 0 0 0 0'
tick 30 '1 2 0 0 0'
tick 37 '1 2 0 0 0'
tick 42 '0 0 0 0 0'
tick 44 '0 0 0 0 0'
tick 52 '1 2 1 0 0'
tick 54 '1 2 1 0 0'
result
""")
        self.assertEqual(lines, ["COMMITTED:254:8:308:54:ON:", "commands=22 343,37 344,44 343,"])

    def test_dropped_reset_retries_after_grace_and_waits_for_normal_ack(self):
        lines = self.run_controller("""
commit
tick 20 '1 0 0 0 0'
tick 22 '1 0 0 0 0'
tick 23 '1 0 0 0 0'
tick 37 '1 0 0 0 0'
tick 40 '0 0 0 0 0'
tick 42 '0 0 0 0 0'
tick 49 '1 2 1 0 0'
tick 51 '1 2 1 0 0'
result
""")
        self.assertEqual(lines[-1], "commands=22 344,37 344,42 343,")
        self.assertEqual(lines[0], "COMMITTED:257:8:308:51:ON:")

    def test_dropped_exit_retries_are_bounded_during_emergency_stop(self):
        lines = self.run_controller("""
commit
STOP_REQUESTED=1
NOW=20; guard_begin_restore STOP
tick 20 '1 2 1 0 0'
tick 23 '1 2 1 0 0'
tick 35 '1 2 1 0 0'
tick 38 '1 2 1 0 0'
tick 50 '1 2 1 0 0'
tick 53 '1 2 1 0 0'
if tick 66 '1 2 1 0 0'; then exit 12; fi
printf '%s:%s\n' "$ERROR_CODE" "$REPAIR_CYCLES"
result
""")
        self.assertEqual(lines[0], "NORMAL_RESTORE_TIMEOUT:2")
        self.assertEqual(lines[-1], "commands=20 344,35 344,50 344,")

    def test_stalled_exit_repairs_desired_off_with_serialized_on_off(self):
        lines = self.run_controller("""
commit
STOP_REQUESTED=1
NOW=20; guard_begin_restore STOP
tick 20 '1 2 1 0 0'
tick 28 '0 2 0 0 0'
tick 30 '0 2 0 0 0'
tick 35 '0 2 0 0 0'
tick 41 '1 2 1 0 0'
tick 43 '1 2 1 0 0'
tick 49 '0 0 0 0 0'
tick 51 '0 0 0 0 0'
result
""")
        self.assertEqual(lines, ["STOPPED:0:0:0:51:ON:", "commands=20 344,35 343,43 344,"])

    def test_all_public_durations_are_one_shot_and_default_returns(self):
        for seconds in (300, 7200, 14400, 21600, 43200):
            with self.subTest(seconds=seconds):
                lines = self.run_controller(f"NEXT_DURATION={seconds}\ncommit\nguard_state\ncat \"$DURATION_FILE\"\n", protocol=True)
                self.assertEqual(lines, [f"COMMITTED:{seconds}:8:{8 + seconds}:8:ON::300", "test-boot:300"])

    def test_full_length_deadline_recovery_expiry_and_next_session_default(self):
        lines = self.run_controller("""
NEXT_DURATION=43200
commit
raw 3 OFF 3 2 1
tick 20 '0 0 0 0 0'
tick 22 '0 0 0 0 0'
tick 30 '1 2 1 0 0'
tick 32 '1 2 1 0 0'
tick 43208 '1 2 1 0 0'
tick 43214 '0 0 0 0 0'
tick 43216 '0 0 0 0 0'
raw 4 ON 3 4 1
tick 43217 '1 2 1 0 0'
tick 43220 '1 2 1 0 0'
tick 43222 '1 2 1 0 0'
result
""")
        self.assertEqual(lines[0], "COMMITTED:300:43222:43522:43222:ON:")
        self.assertEqual(lines[-1], "commands=22 343,43208 344,")

    def test_stopped_selection_survives_same_boot_but_not_reboot(self):
        lines = self.run_controller("""
guard_process_info() { process_started=50; process_boot=test-boot; }
guard_set_duration 7200
guard_duration_load; guard_status
TEST_BOOT=new-boot
guard_duration_load; guard_status
""", protocol=True)
        self.assertEqual(lines, ["STOPPED:0:0:0:0:UNKNOWN::7200", "STOPPED:0:0:0:0:UNKNOWN::7200", "STOPPED:0:0:0:0:UNKNOWN::300"])

    def test_running_duration_mailbox_returns_acknowledged_state(self):
        lines = self.run_controller("""
PHASE=IDLE; PHYSICAL=OFF
guard_live_pid() { return 0; }
guard_process_info() { process_started=50; process_boot=test-boot; }
sleep() { guard_duration_request; }
guard_set_duration 14400
guard_duration_load
printf '%s\n' "$NEXT_DURATION"
[ ! -e "$DURATION_COMMAND_LOCK" ] || exit 12
""", protocol=True)
        self.assertEqual(lines, ["IDLE:0:0:0:0:OFF::14400", "14400"])

    def test_active_mailbox_rejection_preserves_phase_deadline_and_duration(self):
        lines = self.run_controller("""
commit
printf '1-8:test-boot:7200\n' > "$DURATION_REQUEST"
DURATION_BOOT=test-boot
guard_duration_request
cat "$DURATION_ACK"
guard_state
""", protocol=True)
        self.assertEqual(lines, ["1-8:ERROR:0:0:0:8:ON:DURATION_BUSY:300", "COMMITTED:300:8:308:8:ON::300"])

    def test_stale_boot_and_invalid_mailbox_requests_do_not_change_next_choice(self):
        lines = self.run_controller("""
PHASE=IDLE; DURATION_BOOT=test-boot; NEXT_DURATION=7200
printf '1-0:old-boot:14400\n' > "$DURATION_REQUEST"
guard_duration_request; cat "$DURATION_ACK"
printf '2-0:test-boot:600\n' > "$DURATION_REQUEST"
guard_duration_request; cat "$DURATION_ACK"
guard_state
""", protocol=True)
        self.assertEqual(lines, ["1-0:ERROR:0:0:0:0:UNKNOWN:DURATION_STALE:7200", "2-0:ERROR:0:0:0:0:UNKNOWN:DURATION_INVALID:7200", "IDLE:0:0:0:0:UNKNOWN::7200"])

    def test_mailbox_timeout_cancels_only_own_request_and_releases_lock(self):
        lines = self.run_controller("""
guard_live_pid() { return 0; }
guard_process_info() { process_started=50; process_boot=test-boot; }
sleep() { :; }
guard_set_duration 7200
[ ! -e "$DURATION_REQUEST" ] && [ ! -e "$DURATION_COMMAND_LOCK" ] || exit 12
guard_state
""", protocol=True)
        self.assertEqual(lines, ["ERROR:0:0:0:0:UNKNOWN:DURATION_TIMEOUT:300", "WAIT_SWITCH:0:0:0:0:UNKNOWN::300"])

    def test_stop_clears_unconsumed_duration(self):
        lines = self.run_controller("NEXT_DURATION=7200\nguard_stop\ncat \"$DURATION_FILE\"\n", protocol=True)
        self.assertEqual(lines, ["STOPPED:0:0:0:0:UNKNOWN::300", "test-boot:300"])

    def test_native_read_distinguishes_known_wrong_preset_from_missing_snapshot(self):
        for settings, expected in (
                (NORMAL_SETTINGS.replace("nxtpaper_animation_state=0\n", ""), "1"),
                (NORMAL_SETTINGS.replace("tct_nxtpaper_mode_select=3", "tct_nxtpaper_mode_select=1"), "2"),
                (NORMAL_SETTINGS.replace("nxtpaper_animation_state=0\n", "").replace("tct_nxtpaper_mode_select=3", "tct_nxtpaper_mode_select=1"), "2")):
            with self.subTest(expected=expected):
                lines = self.run_controller("guard_native_read\nprintf '%s\\n' \"$?\"\n", {"secure": settings})
                self.assertEqual(lines, [expected])

    def test_startup_retries_two_unavailable_reads_then_validates(self):
        lines = self.run_controller("""
id() { printf '2000\n'; }
getprop() {
  case "$1" in
    ro.product.model) printf 'T807D\n' ;;
    ro.build.version.release) printf '16\n' ;;
    ro.build.version.sdk) printf '36\n' ;;
    *) printf 'TCL/T807D_EEA/Frida:16/BP2A.250605.031.A3/AMD9:user/release-keys\n' ;;
  esac
}
reads=0
guard_native_read() { reads=$((reads + 1)); [ "$reads" -ge 3 ]; }
guard_discover() { printf 'discovered\n'; }
sleep() { :; }
guard_validate || exit 12
printf 'reads=%s\n' "$reads"
result
""")
        self.assertEqual(lines, ["discovered", "reads=3", "WAIT_SWITCH:0:0:0:0:UNKNOWN:", "commands="])

    def test_startup_third_failed_read_and_known_preset_failure_are_explicit(self):
        for result_code, expected_reads, error in ((1, 3, "NATIVE_STATE_READ_FAILED"), (2, 1, "NATIVE_PRESET_MISMATCH")):
            with self.subTest(result_code=result_code):
                lines = self.run_controller(f"""
id() {{ printf '2000\\n'; }}
getprop() {{
  case "$1" in
    ro.product.model) printf 'T807D\\n' ;;
    ro.build.version.release) printf '16\\n' ;;
    ro.build.version.sdk) printf '36\\n' ;;
    *) printf 'TCL/T807D_EEA/Frida:16/BP2A.250605.031.A3/AMD9:user/release-keys\\n' ;;
  esac
}}
reads=0
guard_native_read() {{ reads=$((reads + 1)); return {result_code}; }}
guard_discover() {{ printf 'UNSAFE DISCOVERY\\n'; }}
sleep() {{ :; }}
if guard_validate; then exit 12; fi
printf '%s:%s\\n' "$reads" "$ERROR_CODE"
result
""")
                self.assertEqual(lines[0], f"{expected_reads}:{error}")
                self.assertEqual(lines[-1], "commands=")

    def test_runtime_unavailable_snapshots_never_reach_native_control(self):
        lines = self.run_controller("""
guard_clock() { NOW=$((NOW + 1)); }
guard_tools() { return 0; }
guard_process_identity() { process_started=50; process_boot=test-boot; }
guard_validate() { SWITCH_NODE=/dev/input/event9; }
guard_start_monitor() { return 0; }
guard_monitor_alive() { return 0; }
guard_monitor_cleanup() { :; }
reads=0; ticks=0
guard_native_read() { reads=$((reads + 1)); [ "$reads" -ge 3 ]; }
guard_tick() { ticks=$((ticks + 1)); STOP_REQUESTED=1; }
sleep() { :; }
guard_main start || exit 12
printf 'reads=%s ticks=%s\n' "$reads" "$ticks"
printf 'commands='; cat "$COMMANDS"
""")
        self.assertTrue(lines[0].startswith("STOPPED:"), lines)
        self.assertEqual(lines[1:], ["reads=3 ticks=1", "commands="])

    def test_runtime_third_failed_read_ends_guard_and_clears_choice(self):
        lines = self.run_controller("""
NEXT_DURATION=7200; guard_duration_save
guard_clock() { NOW=$((NOW + 1)); }
guard_tools() { return 0; }
guard_process_identity() { process_started=50; process_boot=test-boot; }
guard_validate() { SWITCH_NODE=/dev/input/event9; }
guard_start_monitor() { return 0; }
guard_monitor_alive() { return 0; }
guard_monitor_cleanup() { :; }
reads=0
guard_native_read() { reads=$((reads + 1)); return 1; }
guard_tick() { printf 'UNSAFE TICK\n'; }
sleep() { :; }
if guard_main start; then exit 12; fi
printf 'reads=%s\n' "$reads"
cat "$DURATION_FILE"
printf 'commands='; cat "$COMMANDS"
""", protocol=True)
        self.assertIn(":UNKNOWN:NATIVE_STATE_READ_FAILED:300", lines[0])
        self.assertEqual(lines[1:], ["reads=3", "test-boot:300", "commands="])

    def test_stopped_status_reads_choice_instead_of_old_stopped_cache(self):
        lines = self.run_controller("""
printf 'STOPPED:0:0:0:0:UNKNOWN::300\n' > "$STATE_FILE"
printf 'test-boot:21600\n' > "$DURATION_FILE"
guard_clock() { NOW=10; }
guard_main status
""", protocol=True)
        self.assertEqual(lines, ["STOPPED:0:0:0:0:UNKNOWN::21600"])

    def test_fresh_entry_wins_over_concurrent_duration_request(self):
        lines = self.run_controller("""
NEXT_DURATION=7200
raw 1 ON 0 1 0
printf '1-0:test-boot:43200\n' > "$DURATION_REQUEST"
tick 1 '1 2 1 1 1'
guard_duration_request
cat "$DURATION_ACK"
tick 7 '1 2 1 0 0'
tick 9 '1 2 1 0 0'
guard_state
""", protocol=True)
        self.assertEqual(lines, ["1-0:ERROR:0:0:0:1:ON:DURATION_BUSY:300", "COMMITTED:7200:9:7209:9:ON::300"])

    def test_duplicate_start_preserves_active_session_deadline(self):
        lines = self.run_controller("""
printf 'COMMITTED:7198:8:7208:10:OFF::300\n' > "$STATE_FILE"
guard_live_pid() { return 0; }
guard_clock() { NOW=10; }
guard_main start
cat "$STATE_FILE"
""", protocol=True)
        self.assertEqual(lines, ["COMMITTED:7198:8:7208:10:OFF::300"] * 2)

    def test_live_mailbox_owner_is_not_removed_or_signaled(self):
        lines = self.run_controller("""
mkdir "$DURATION_COMMAND_LOCK"
printf '42:50:test-boot\n' > "$DURATION_COMMAND_LOCK/owner"
guard_process_info() { process_started=50; process_boot=test-boot; }
kill() { printf 'UNSAFE KILL\n'; }
guard_set_duration 7200
cat "$DURATION_COMMAND_LOCK/owner"
""", protocol=True)
        self.assertEqual(lines, ["ERROR:0:0:0:0:UNKNOWN:DURATION_BUSY:300", "42:50:test-boot"])

    def test_stale_mailbox_owner_is_reclaimed_without_signaling_process(self):
        lines = self.run_controller("""
mkdir "$DURATION_COMMAND_LOCK"
printf '42:49:old-boot\n' > "$DURATION_COMMAND_LOCK/owner"
guard_process_info() { process_started=50; process_boot=test-boot; }
kill() { printf 'UNSAFE KILL\n'; }
guard_set_duration 7200
[ ! -e "$DURATION_COMMAND_LOCK" ] || exit 12
""", protocol=True)
        self.assertEqual(lines, ["STOPPED:0:0:0:0:UNKNOWN::7200"])

    def test_startup_failure_discards_unconsumed_long_choice(self):
        lines = self.run_controller("""
NEXT_DURATION=43200; guard_duration_save
guard_clock() { NOW=10; }
guard_tools() { return 0; }
guard_process_identity() { process_started=50; process_boot=test-boot; }
guard_validate() { guard_fail UNSUPPORTED_FIRMWARE; }
sleep() { :; }
if guard_main start; then exit 12; fi
cat "$DURATION_FILE"
""", protocol=True)
        self.assertEqual(lines, ["ERROR:0:0:0:10:UNKNOWN:UNSUPPORTED_FIRMWARE:300", "test-boot:300"])

    def test_legacy_seven_field_live_status_is_still_readable(self):
        lines = self.run_controller("""
guard_live_pid() { return 0; }
guard_clock() { NOW=10; }
printf 'COMMITTED:298:8:308:10:OFF:\n' > "$STATE_FILE"
guard_status
""", protocol=True)
        self.assertEqual(lines, ["COMMITTED:298:8:308:10:OFF:"])

    def test_dropped_restore_on_retries_before_real_acknowledgment(self):
        lines = self.run_controller("""
commit
STOP_REQUESTED=1
NOW=20; guard_begin_restore STOP
tick 20 '1 2 1 0 0'
tick 28 '0 2 0 0 0'
tick 30 '0 2 0 0 0'
tick 35 '0 2 0 0 0'
tick 38 '0 2 0 0 0'
tick 50 '0 2 0 0 0'
tick 55 '1 2 1 0 0'
tick 57 '1 2 1 0 0'
tick 60 '0 0 0 0 0'
tick 62 '0 0 0 0 0'
result
grep 'acknowledged purpose=RESTORE_ON' "$LOG_FILE"
""")
        self.assertEqual(lines[:2], ["STOPPED:0:0:0:62:ON:", "commands=20 344,35 343,50 343,57 344,"])
        self.assertEqual(lines[2], "[uptime=57] native acknowledged purpose=RESTORE_ON elapsed=7 deadline=308")

    def test_duration_write_failure_is_parseable_feedback_with_unchanged_choice(self):
        lines = self.run_controller("""
guard_process_info() { process_started=50; process_boot=test-boot; }
guard_duration_save() { return 1; }
guard_set_duration 7200 || exit 12
guard_state
""", protocol=True)
        self.assertEqual(lines, ["ERROR:0:0:0:0:UNKNOWN:DURATION_WRITE_FAILED:300", "WAIT_SWITCH:0:0:0:0:UNKNOWN::300"])

    def test_live_stop_returns_reset_duration_after_daemon_clears_persisted_choice(self):
        lines = self.run_controller("""
NEXT_DURATION=7200; guard_duration_save
daemon_alive=1
guard_live_pid() { live_pid=42; [ "$daemon_alive" = 1 ]; }
kill() {
    daemon_alive=0
    printf 'test-boot:300\n' > "$DURATION_FILE"
}
guard_stop
printf '%s\n' "$NEXT_DURATION"
""", protocol=True)
        self.assertEqual(lines, ["STOPPED:0:0:0:0:UNKNOWN::300", "300"])

    def test_legitimate_boot_unknown_starts_monitor_without_commands_or_inference(self):
        lines = self.run_controller("""
guard_clock() { NOW=$((NOW + 1)); }
guard_tools() { return 0; }
guard_process_identity() { process_started=50; process_boot=test-boot; }
id() { printf '2000\n'; }
getprop() {
  case "$1" in
    ro.product.model) printf 'T807D\n' ;;
    ro.build.version.release) printf '16\n' ;;
    ro.build.version.sdk) printf '36\n' ;;
    *) printf 'TCL/T807D_EEA/Frida:16/BP2A.250605.031.A3/AMD9:user/release-keys\n' ;;
  esac
}
getevent() { cat "$GUARD_TEST_DIR/caps"; }
guard_start_monitor() { printf 'monitor started\n'; }
guard_monitor_cleanup() { :; }
monitor_checks=0
guard_monitor_alive() {
    monitor_checks=$((monitor_checks + 1))
    [ "$monitor_checks" -lt 3 ] || STOP_REQUESTED=1
    return 0
}
sleep() { :; }
guard_main start || exit 12
printf 'checks=%s\n' "$monitor_checks"
printf 'commands='; cat "$COMMANDS"
""", {"secure": NORMAL_SETTINGS.replace("TSWT_state=0", "TSWT_state=-1").replace("nxtpaper_ink_style_state=0", "nxtpaper_ink_style_state=2").replace("nxtpaper_book_style_state=0", "nxtpaper_book_style_state=1"), "caps": CAPABILITIES}, protocol=True)
        self.assertEqual(lines[0], "monitor started")
        self.assertTrue(lines[1].startswith("STOPPED:"), lines)
        self.assertIn(":UNKNOWN::300", lines[1])
        self.assertEqual(lines[2:], ["checks=3", "commands="])

    def test_boot_unknown_resolves_after_fresh_physical_on_before_commitment(self):
        lines = self.run_controller("""
tick 0 '-1 2 1 0 0'
raw 1 ON 0 1 0
tick 1 '-1 2 1 0 0'
tick 10 '-1 2 1 0 0'
guard_state
tick 12 '1 2 1 0 0'
tick 14 '1 2 1 0 0'
result
""")
        self.assertEqual(lines, ["STARTING:0:0:0:10:ON:", "COMMITTED:300:14:314:14:ON:", "commands="])

    def test_starting_unknown_never_issues_commands_and_times_out_honestly(self):
        lines = self.run_controller("""
raw 1 ON 0 1 0
tick 1 '-1 2 1 0 0'
tick 3 '-1 2 1 0 0'
tick 20 '-1 2 1 0 0'
if tick 47 '-1 2 1 0 0'; then exit 12; fi
printf '%s:%s:%s\n' "$ERROR_CODE" "$SESSION_START" "$DEADLINE"
result
""")
        self.assertEqual(lines[0], "NATIVE_RECOVERY_TIMEOUT:0:0")
        self.assertEqual(lines[-1], "commands=")

    def test_active_unknown_never_repairs_or_renews_deadline_and_times_out(self):
        lines = self.run_controller("""
commit
tick 20 '-1 2 1 0 0'
tick 22 '-1 2 1 0 0'
tick 35 '-1 2 1 0 0'
if tick 66 '-1 2 1 0 0'; then exit 12; fi
printf '%s:%s:%s\n' "$ERROR_CODE" "$REPAIR_CYCLES" "$DEADLINE"
result
""")
        self.assertEqual(lines[0], "NATIVE_RECOVERY_TIMEOUT:0:308")
        self.assertEqual(lines[-1], "commands=")

    def test_restore_unknown_issues_no_commands_and_has_bounded_timeout(self):
        lines = self.run_controller("""
commit
STOP_REQUESTED=1
NOW=20; guard_begin_restore STOP
tick 20 '-1 2 1 0 0'
tick 22 '-1 2 1 0 0'
tick 35 '-1 2 1 0 0'
if tick 66 '-1 2 1 0 0'; then exit 12; fi
printf '%s:%s\n' "$ERROR_CODE" "$REPAIR_CYCLES"
result
""")
        self.assertEqual(lines[0], "NORMAL_RESTORE_TIMEOUT:0")
        self.assertEqual(lines[-1], "commands=")

    def test_only_exact_boot_sentinel_is_added_to_native_snapshot_contract(self):
        for value, expected in (("-1", "0"), ("-2", "1"), ("01", "1"), ("-01", "1"), ("null", "1")):
            with self.subTest(value=value):
                lines = self.run_controller("guard_native_read\nprintf '%s\\n' \"$?\"\n", {"secure": NORMAL_SETTINGS.replace("TSWT_state=0", f"TSWT_state={value}")})
                self.assertEqual(lines, [expected])

    def test_all_corrective_command_paths_are_fenced_when_desired_mode_unknown(self):
        lines = self.run_controller("""
TSWT=-1
NOW=20
RESTORE_REASON=STOP
guard_issue 343 ENTER
guard_issue 344 EXIT
guard_repair 343 RESTORE_ON
guard_repair 344 RESET
printf 'repairs=%s pending=%s\n' "$REPAIR_CYCLES" "$PENDING"
result
""")
        self.assertEqual(lines[0], "repairs=0 pending=")
        self.assertEqual(lines[-1], "commands=")


if __name__ == "__main__":
    unittest.main()
