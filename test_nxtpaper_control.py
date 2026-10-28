"""Firmware-control and raw-slider tests using host-only fake ADB/streams."""

from pathlib import Path
from queue import Queue
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import nxtpaper_control as control
from nxtpaper_diag import Adb, DiagnosticError, Result


CAPABILITIES = '''add device 1: /dev/input/event1
  name:     "gpio-keys"
  events:
    KEY (0001): KEY_POWER
add device 2: /dev/input/event9
  name:     "tswt"
  events:
    KEY (0001): KEY_BRIGHTNESS_MIN    KEY_BRIGHTNESS_MAX
  input props:
    <none>
'''
KEYLAYOUT = "# tested native mapping\nkey 592 TSWT_ON\nkey 593 TSWT_OFF\n"
NORMAL_SETTINGS = """TSWT_state=0
nxtpaper_ink_style_state=0
nxtpaper_book_style_state=0
nxtpaper_is_applying_theme=0
nxtpaper_animation_state=0
tct_nxtpaper_mode_select=3
tct_nxtpaper_switch_imm=1
unrelated=content=with=equals
"""
ON_LINE = "[  112231.904238] /dev/input/event9: EV_KEY KEY_BRIGHTNESS_MIN DOWN\n"
OFF_LINE = "[  112232.904238] EV_KEY KEY_BRIGHTNESS_MAX DOWN\n"


def captured(text="", returncode=0, timed_out=False, stderr=""):
    return Result(["fake-adb"], "2026-10-03T00:00:00+00:00", 0.01,
                  returncode, timed_out, text, stderr)


class FakeAdb(Adb):
    def __init__(self, overrides=None, serial="TCL-USB"):
        super().__init__(r"C:\Program Files\Android\adb.exe", serial)
        self.calls = []
        self.responses = {
            ("shell", "getprop", prop): captured(expected)
            for prop, expected in control.PROFILE_PROPERTIES.values()
        }
        self.responses.update({
            ("shell", "id", "-u"): captured("2000"),
            ("shell", "settings", "list", "secure"): captured(NORMAL_SETTINGS),
            ("shell", "getevent", "-lp"): captured(CAPABILITIES),
            ("shell", "cat", control.KEYLAYOUT_PATH): captured(KEYLAYOUT),
        })
        self.responses.update(overrides or {})

    def read(self, args, timeout=20):
        self.calls.append((tuple(args), timeout))
        response = self.responses.get(tuple(args), captured())
        if isinstance(response, Exception):
            raise response
        return response


class AdapterTests(unittest.TestCase):
    def test_profile_and_presets_are_verified_without_writes(self):
        adb = FakeAdb()
        profile = control.TclAdapter(adb).validate()
        self.assertEqual(profile["model"], "T807D")
        self.assertEqual(profile["fingerprint"], control.SUPPORTED_FINGERPRINT)
        self.assertTrue(all(command[:2] in (("shell", "getprop"), ("shell", "settings"))
                            for command, _ in adb.calls))

    def test_wrong_model_android_sdk_or_build_is_rejected(self):
        for name, (prop, _) in control.PROFILE_PROPERTIES.items():
            with self.subTest(name=name), self.assertRaisesRegex(DiagnosticError, "Unsupported TCL firmware/profile"):
                control.TclAdapter(FakeAdb({("shell", "getprop", prop): captured("wrong")})).validate()

    def test_configuration_changes_allow_observation_but_never_bypass_restore_gate(self):
        adb = FakeAdb()
        adapter = control.TclAdapter(adb)
        adapter.validate()
        changed = NORMAL_SETTINGS.replace("tct_nxtpaper_mode_select=3", "tct_nxtpaper_mode_select=1")
        adb.responses[("shell", "settings", "list", "secure")] = captured(changed)
        with self.assertRaisesRegex(DiagnosticError, "Native switch configuration"):
            adapter.read_state()
        self.assertTrue(adapter.read_state(check_configuration=False).normal)
        with self.assertRaisesRegex(DiagnosticError, "Native switch configuration"):
            adapter.restore_normal()
        self.assertFalse(any(command[:2] == ("shell", "input") for command, _ in adb.calls))

    def test_immediate_switch_guard_is_enforced(self):
        changed = NORMAL_SETTINGS.replace("tct_nxtpaper_switch_imm=1", "tct_nxtpaper_switch_imm=0")
        with self.assertRaisesRegex(DiagnosticError, "Native switch configuration"):
            control.TclAdapter(FakeAdb({("shell", "settings", "list", "secure"): captured(changed)})).validate()

    def test_key_controls_require_validation_and_send_only_exact_native_events(self):
        adb = FakeAdb()
        adapter = control.TclAdapter(adb)
        with self.assertRaisesRegex(DiagnosticError, "Validate"):
            adapter.enter_max_ink()
        self.assertEqual(adb.calls, [])
        adapter.validate()
        adb.calls.clear()
        adapter.enter_max_ink()
        adapter.restore_normal()
        injected = [(command, timeout) for command, timeout in adb.calls if command[:2] == ("shell", "input")]
        self.assertEqual(injected, [(("shell", "input", "keyevent", "343"), 3),
                                   (("shell", "input", "keyevent", "344"), 3)])
        self.assertEqual(sum(command[:2] == ("shell", "getprop") for command, _ in adb.calls),
                         2 * len(control.PROFILE_PROPERTIES))
        self.assertEqual(sum(command == ("shell", "getevent", "-lp") for command, _ in adb.calls), 2)
        self.assertEqual(adb.command(injected[0][0]),
                         [r"C:\Program Files\Android\adb.exe", "-s", "TCL-USB", "shell", "input", "keyevent", "343"])

    def test_firmware_change_after_successful_validation_blocks_both_commands(self):
        for operation in ("enter_max_ink", "restore_normal"):
            with self.subTest(operation=operation):
                adb = FakeAdb()
                adapter = control.TclAdapter(adb)
                adapter.validate()
                adb.responses[("shell", "getprop", "ro.build.fingerprint")] = captured("new-firmware")
                with self.assertRaisesRegex(DiagnosticError, "Unsupported TCL firmware/profile"):
                    getattr(adapter, operation)()
                self.assertFalse(any(command[:2] == ("shell", "input") for command, _ in adb.calls))

    def test_lost_privilege_changed_layout_or_input_blocks_both_commands(self):
        changes = (
            {("shell", "id", "-u"): captured("0")},
            {("shell", "getevent", "-lp"): captured(returncode=1)},
            {("shell", "cat", control.KEYLAYOUT_PATH): captured(KEYLAYOUT.replace("TSWT_ON", "OTHER"))},
        )
        for change in changes:
            for operation in ("enter_max_ink", "restore_normal"):
                with self.subTest(change=change, operation=operation):
                    adb = FakeAdb()
                    adapter = control.TclAdapter(adb)
                    adapter.validate()
                    adb.responses.update(change)
                    with self.assertRaises(DiagnosticError):
                        getattr(adapter, operation)()
                    self.assertFalse(any(command[:2] == ("shell", "input") for command, _ in adb.calls))

    def test_unknown_or_transition_snapshot_never_authorizes_mode_command(self):
        for state in (NORMAL_SETTINGS.replace("TSWT_state=0", "TSWT_state=-1"),
                      NORMAL_SETTINGS.replace("nxtpaper_animation_state=0", "nxtpaper_animation_state=1")):
            with self.subTest(state=state):
                adb = FakeAdb({("shell", "settings", "list", "secure"): captured(state)})
                adapter = control.TclAdapter(adb)
                adapter.validate()
                with self.assertRaisesRegex(DiagnosticError, "unknown or changing"):
                    adapter.restore_normal()
                self.assertFalse(any(command[:2] == ("shell", "input") for command, _ in adb.calls))

    def test_transport_errors_and_timeouts_stop_control(self):
        for response in (captured(returncode=1, stderr="device disconnected"),
                         captured(returncode=None, timed_out=True), DiagnosticError("transport failed")):
            with self.subTest(response=response):
                adb = FakeAdb()
                adapter = control.TclAdapter(adb)
                adapter.validate()
                adb.responses[("shell", "input", "keyevent", "343")] = response
                with self.assertRaises(DiagnosticError):
                    adapter.enter_max_ink()

    def test_strict_state_parser_rejects_missing_duplicate_or_malformed_values(self):
        variants = (
            NORMAL_SETTINGS.replace("TSWT_state=0\n", ""),
            NORMAL_SETTINGS + "TSWT_state=0\n",
            NORMAL_SETTINGS.replace("TSWT_state=0", "TSWT_state=00"),
            NORMAL_SETTINGS.replace("nxtpaper_ink_style_state=0", "nxtpaper_ink_style_state=9"),
            NORMAL_SETTINGS.replace("nxtpaper_book_style_state=0", "nxtpaper_book_style_state=-1"),
            NORMAL_SETTINGS.replace("nxtpaper_is_applying_theme=0", "nxtpaper_is_applying_theme=true"),
            NORMAL_SETTINGS.replace("nxtpaper_animation_state=0", "nxtpaper_animation_state=0 "),
        )
        for text in variants:
            with self.subTest(text=text), self.assertRaises(DiagnosticError):
                control.TclAdapter(FakeAdb({("shell", "settings", "list", "secure"): captured(text)})).read_state()

    def test_mode_properties_preserve_transition_flags_and_software_state(self):
        text = NORMAL_SETTINGS.replace("TSWT_state=0", "TSWT_state=1").replace(
            "nxtpaper_ink_style_state=0", "nxtpaper_ink_style_state=2").replace(
            "nxtpaper_book_style_state=0", "nxtpaper_book_style_state=1").replace(
            "nxtpaper_animation_state=0", "nxtpaper_animation_state=1")
        state = control.TclAdapter(FakeAdb({("shell", "settings", "list", "secure"): captured(text)})).read_state()
        self.assertEqual(state, control.ModeState(1, 2, 1, False, True))
        self.assertTrue(state.max_ink)
        self.assertFalse(state.normal)
        self.assertFalse(state.settled)
        self.assertTrue(control.ModeState(1, 0, 0, False, False).normal)

    def test_emulators_are_rejected_before_any_adb_call(self):
        adb = FakeAdb(serial="emulator-5554")
        adapter = control.TclAdapter(adb)
        for operation in (adapter.validate, adapter.read_state, control.PhysicalSwitchMonitor(adb, None).start):
            with self.assertRaisesRegex(DiagnosticError, "physical TCL"):
                operation()
        self.assertEqual(adb.calls, [])


class SwitchParserTests(unittest.TestCase):
    def test_driver_is_identified_dynamically(self):
        self.assertEqual(control.discover_switch_node(CAPABILITIES), "/dev/input/event9")
        self.assertEqual(control.discover_switch_node(CAPABILITIES.replace("event9", "event42")), "/dev/input/event42")

    def test_missing_ambiguous_or_incomplete_tswt_driver_is_rejected(self):
        duplicate = CAPABILITIES + CAPABILITIES.replace("event9", "event8")
        for text in (CAPABILITIES.replace('"tswt"', '"other"'), duplicate,
                     CAPABILITIES.replace("KEY_BRIGHTNESS_MAX", "KEY_POWER")):
            with self.subTest(text=text), self.assertRaises(DiagnosticError):
                control.discover_switch_node(text)

    def test_real_keylayout_polarity_is_required(self):
        control.validate_switch_keylayout(KEYLAYOUT)
        control.validate_switch_keylayout("key 592 TSWT_ON WAKE # comment\nkey 593 TSWT_OFF\n")
        for text in (KEYLAYOUT.replace("TSWT_ON", "OTHER"),
                     "key 592 TSWT_OFF\nkey 593 TSWT_ON\n", KEYLAYOUT + "key 592 TSWT_ON\n"):
            with self.subTest(text=text), self.assertRaises(DiagnosticError):
                control.validate_switch_keylayout(text)

    def test_min_is_on_max_is_off_and_receipt_time_is_used(self):
        self.assertEqual(control.parse_switch_event(ON_LINE, 7.5, "/dev/input/event9"), control.SwitchEvent(True, 7.5))
        self.assertEqual(control.parse_switch_event(OFF_LINE, 8.5, "/dev/input/event9"), control.SwitchEvent(False, 8.5))

    def test_release_repeat_sync_framework_keys_and_other_devices_are_ignored(self):
        for text in (ON_LINE.replace("DOWN", "UP"), ON_LINE.replace("DOWN", "REPEAT"),
                     ON_LINE.replace("EV_KEY", "EV_SYN"), ON_LINE.replace("event9", "event2"),
                     ON_LINE.replace("KEY_BRIGHTNESS_MIN", "KEYCODE_TSWT_ON"),
                     "input keyevent 343\n", "[ 123.456] EV_KEY 343 DOWN\n"):
            with self.subTest(text=text):
                self.assertIsNone(control.parse_switch_event(text, 7.5, "/dev/input/event9"))


class QueueTextStream:
    """Blocking fake stdout with an acknowledgement after each delivered line."""
    def __init__(self):
        self.queue = Queue()
        self.closed = False
        self.condition = threading.Condition()
        self.consumed = 0
        self.pending = False

    def __iter__(self):
        return self

    def __next__(self):
        with self.condition:
            if self.pending:
                self.consumed += 1
                self.pending = False
                self.condition.notify_all()
        value = self.queue.get()
        if value is None:
            raise StopIteration
        if isinstance(value, Exception):
            raise value
        self.pending = True
        return value

    def write_line(self, line):
        self.queue.put(line)

    def end(self):
        self.queue.put(None)

    def close(self):
        self.closed = True
        self.end()

    def wait_consumed(self, count):
        with self.condition:
            return self.condition.wait_for(lambda: self.consumed >= count, timeout=1)


class FakeProcess:
    def __init__(self, timeout=False):
        self.stdout = QueueTextStream()
        self.returncode = None
        self.killed = False
        self.timeout = timeout

    def poll(self):
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -1
        self.stdout.end()

    def wait(self, timeout=None):
        if self.timeout:
            raise subprocess.TimeoutExpired("fake-adb", timeout)
        return self.returncode


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name)
        self.adb = FakeAdb()

    def test_monitor_records_raw_events_pins_serial_and_ignores_framework_injection(self):
        process = FakeProcess()
        monitor = control.PhysicalSwitchMonitor(self.adb, self.output)
        with patch.object(control.subprocess, "Popen", return_value=process) as launch:
            started_at = time.monotonic()
            monitor.start()
            try:
                monitor.check_alive()
                process.stdout.write_line(ON_LINE)
                process.stdout.write_line(ON_LINE.replace("DOWN", "UP"))
                process.stdout.write_line(OFF_LINE)
                self.assertTrue(process.stdout.wait_consumed(3))
                events = monitor.drain()
                self.assertEqual([event.on for event in events], [True, False])
                self.assertTrue(all(started_at <= event.at <= time.monotonic() for event in events))
                self.assertEqual(monitor.drain(), [])
                adapter = control.TclAdapter(self.adb)
                adapter.validate()
                adapter.enter_max_ink()
                adapter.restore_normal()
                self.assertEqual(monitor.drain(), [])
                self.assertIn(ON_LINE, monitor.raw_log.read_text(encoding="utf-8"))
            finally:
                monitor.close()
        self.assertEqual(launch.call_args.args[0],
                         [self.adb.executable, "-s", "TCL-USB", "shell", "getevent", "-lt", "/dev/input/event9"])
        self.assertFalse(launch.call_args.kwargs["shell"])
        self.assertEqual(launch.call_args.kwargs["encoding"], "utf-8")
        self.assertTrue(process.killed)
        self.assertTrue(process.stdout.closed)
        self.assertTrue(monitor._stderr_handle.closed)
        self.assertFalse(monitor._thread.is_alive())

    def test_wrong_keylayout_prevents_monitor_start(self):
        self.adb.responses[("shell", "cat", control.KEYLAYOUT_PATH)] = captured("key 592 TSWT_OFF\nkey 593 TSWT_ON\n")
        with patch.object(control.subprocess, "Popen") as launch:
            with self.assertRaisesRegex(DiagnosticError, "keylayout"):
                control.PhysicalSwitchMonitor(self.adb, self.output).start()
        launch.assert_not_called()

    def test_eof_and_reader_error_are_reported(self):
        for terminal in (None, OSError("USB stream failed")):
            with self.subTest(terminal=terminal):
                process = FakeProcess()
                monitor = control.PhysicalSwitchMonitor(self.adb, None)
                with patch.object(control.subprocess, "Popen", return_value=process):
                    monitor.start()
                process.stdout.queue.put(terminal)
                monitor._thread.join(timeout=1)
                try:
                    with self.assertRaises(DiagnosticError):
                        monitor.check_alive()
                finally:
                    monitor.close()

    def test_start_failure_closes_open_local_logs(self):
        monitor = control.PhysicalSwitchMonitor(self.adb, self.output)
        with patch.object(control.subprocess, "Popen", side_effect=OSError("could not launch")):
            with self.assertRaisesRegex(DiagnosticError, "Could not start"):
                monitor.start()
        self.assertTrue(monitor._raw_handle.closed)
        self.assertTrue(monitor._stderr_handle.closed)

    def test_reader_thread_start_failure_closes_client_and_open_logs(self):
        process = FakeProcess()
        monitor = control.PhysicalSwitchMonitor(self.adb, self.output)
        with patch.object(control.subprocess, "Popen", return_value=process), \
                patch.object(control.threading.Thread, "start", side_effect=RuntimeError("thread unavailable")):
            with self.assertRaisesRegex(DiagnosticError, "Could not start"):
                monitor.start()
        self.assertTrue(process.killed)
        self.assertTrue(process.stdout.closed)
        self.assertTrue(monitor._raw_handle.closed)
        self.assertTrue(monitor._stderr_handle.closed)

    def test_cleanup_timeout_still_joins_reader_closes_logs_and_reports_failure(self):
        process = FakeProcess(timeout=True)
        monitor = control.PhysicalSwitchMonitor(self.adb, self.output)
        with patch.object(control.subprocess, "Popen", return_value=process):
            monitor.start()
        with self.assertRaisesRegex(DiagnosticError, "cleanup failed"):
            monitor.close()
        self.assertFalse(monitor._thread.is_alive())
        self.assertTrue(process.stdout.closed)
        self.assertTrue(monitor._raw_handle.closed)
        self.assertTrue(monitor._stderr_handle.closed)
        monitor.close()  # Repeated shutdown is harmless.

    def test_optional_output_and_unstarted_close_do_not_create_logs(self):
        monitor = control.PhysicalSwitchMonitor(self.adb, None)
        monitor.close()
        self.assertIsNone(monitor.raw_log)
        self.assertIsNone(monitor.stderr_log)
        with self.assertRaises(DiagnosticError):
            monitor.start()


if __name__ == "__main__":
    unittest.main()
