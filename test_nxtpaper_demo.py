"""Pure commitment and host-only supervisor failure/recovery regression tests."""

import argparse
from contextlib import nullcontext, redirect_stderr, redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import nxtpaper_demo as demo
from nxtpaper_control import ModeState, SwitchEvent
from nxtpaper_diag import DiagnosticError


NORMAL = ModeState(0, 0, 0, False, False)
MAX_INK = ModeState(1, 2, 1, False, False)
INK_TRANSITION = ModeState(1, 2, 1, True, True)
OFF_TRANSITION = ModeState(0, 0, 0, True, True)
NORMAL_WITH_DESIRED_ON = ModeState(1, 0, 0, False, False)


class CommitmentTests(unittest.TestCase):
    def committed(self, duration=300, confirmed_at=10):
        machine = demo.Commitment(duration)
        machine.tick(confirmed_at, MAX_INK, [SwitchEvent(True, confirmed_at)])
        self.assertEqual(machine.phase, demo.Phase.COMMITTED)
        return machine

    def test_timer_requires_raw_entry_and_native_mode_confirmation(self):
        machine = demo.Commitment()
        machine.tick(2, NORMAL, [])
        self.assertIsNone(machine.deadline)
        decision = machine.tick(3, OFF_TRANSITION, [SwitchEvent(True, 2.9)])
        self.assertEqual(machine.phase, demo.Phase.STARTING)
        self.assertEqual(decision.commands, ["enter"])
        self.assertIsNone(machine.deadline)
        machine.tick(7, NORMAL_WITH_DESIRED_ON, [])
        self.assertIsNone(machine.deadline)
        machine.tick(8, INK_TRANSITION, [])
        self.assertEqual(machine.deadline, 308)
        self.assertEqual(machine.sessions, 1)
        self.assertEqual(machine.phase, demo.Phase.COMMITTED)

    def test_software_mode_change_without_raw_entry_does_not_start_session(self):
        machine = demo.Commitment()
        with self.assertRaisesRegex(DiagnosticError, "without a physical"):
            machine.tick(5, MAX_INK, [])
        self.assertIsNone(machine.deadline)
        self.assertEqual(machine.sessions, 0)

    def test_rapid_raw_reversal_still_waits_for_native_entry(self):
        machine = demo.Commitment()
        decision = machine.tick(1, NORMAL, [SwitchEvent(True, 0.8), SwitchEvent(False, 0.9)])
        self.assertEqual(machine.phase, demo.Phase.STARTING)
        self.assertFalse(machine.physical_on)
        self.assertEqual(decision.commands, ["enter"])
        machine.tick(4, MAX_INK, [])
        self.assertEqual(machine.deadline, 304)

    def test_repeated_early_exits_keep_original_deadline(self):
        machine = self.committed()
        original = machine.deadline
        for off_at in (20, 70, 140):
            decision = machine.tick(off_at, NORMAL, [SwitchEvent(False, off_at)])
            self.assertEqual(decision.commands, ["enter"])
            self.assertEqual(machine.deadline, original)
            machine.tick(off_at + 2, INK_TRANSITION, [])
            machine.tick(off_at + 7, MAX_INK, [SwitchEvent(True, off_at + 6)])
            self.assertEqual(machine.deadline, original)
        self.assertEqual(machine.sessions, 1)

    def test_on_screen_exit_uses_native_off_then_on_without_renewal(self):
        machine = self.committed()
        deadline = machine.deadline
        first = machine.tick(20, NORMAL_WITH_DESIRED_ON, [])
        self.assertEqual(first.commands, [])
        self.assertEqual(machine.tick(21.9, NORMAL_WITH_DESIRED_ON, []).commands, [])
        stable = machine.tick(22, NORMAL_WITH_DESIRED_ON, [])
        self.assertEqual(stable.commands, ["normal"])
        self.assertTrue(machine.reset_for_reentry)
        waiting = machine.tick(23, OFF_TRANSITION, [])
        self.assertEqual(waiting.commands, [])
        ready = machine.tick(26, NORMAL, [])
        self.assertEqual(ready.commands, ["enter"])
        machine.tick(32, MAX_INK, [])
        self.assertEqual(machine.deadline, deadline)
        self.assertFalse(machine.reset_for_reentry)

    def test_deadline_wins_during_recovery_and_native_animation(self):
        machine = self.committed(duration=10)
        machine.tick(17, NORMAL_WITH_DESIRED_ON, [])
        machine.tick(19, NORMAL_WITH_DESIRED_ON, [])
        self.assertTrue(machine.reset_for_reentry)
        decision = machine.tick(20, INK_TRANSITION, [SwitchEvent(False, 19.9)])
        self.assertEqual(machine.phase, demo.Phase.RESTORING)
        self.assertEqual(decision.commands, ["normal"])
        self.assertFalse(machine.reset_for_reentry)
        self.assertIsNone(machine.recovery_started)
        self.assertEqual(machine.deadline, 20)

    def test_queued_native_transition_seam_never_triggers_wrong_mode_off_pulse(self):
        machine = self.committed()
        deadline = machine.deadline
        trace = (
            (20, OFF_TRANSITION, [SwitchEvent(False, 20)], ["enter"]),
            (21, ModeState(1, 0, 0, True, True), [], []),
            (25, ModeState(1, 2, 0, False, False), [], []),
            (25.3, INK_TRANSITION, [], []),
            (30, MAX_INK, [], []),
        )
        for now, state, events, commands in trace:
            with self.subTest(now=now):
                decision = machine.tick(now, state, events)
                self.assertEqual(decision.commands, commands)
                self.assertEqual(machine.phase, demo.Phase.COMMITTED)
                self.assertEqual(machine.deadline, deadline)
        self.assertIsNone(machine.recovery_started)

    def test_wrong_mode_signature_changes_restart_stability_window(self):
        machine = self.committed()
        seam = ModeState(1, 2, 0, False, False)
        self.assertEqual(machine.tick(20, NORMAL_WITH_DESIRED_ON, []).commands, [])
        self.assertEqual(machine.tick(21.5, seam, []).commands, [])
        self.assertEqual(machine.tick(22.1, seam, []).commands, [])
        stable = machine.tick(23.5, seam, [])
        self.assertEqual(stable.commands, ["normal"])
        self.assertTrue(machine.reset_for_reentry)
        self.assertEqual(machine.deadline, 310)

    def test_transition_flags_restart_wrong_mode_stability_window(self):
        machine = self.committed()
        self.assertEqual(machine.tick(20, NORMAL_WITH_DESIRED_ON, []).commands, [])
        self.assertEqual(machine.tick(21.9, ModeState(1, 0, 0, True, False), []).commands, [])
        self.assertEqual(machine.tick(22, NORMAL_WITH_DESIRED_ON, []).commands, [])
        self.assertEqual(machine.tick(23.9, NORMAL_WITH_DESIRED_ON, []).commands, [])
        self.assertEqual(machine.tick(24, NORMAL_WITH_DESIRED_ON, []).commands, ["normal"])

    def test_native_confirmation_clears_previous_wrong_mode_window(self):
        machine = self.committed()
        machine.tick(20, NORMAL_WITH_DESIRED_ON, [])
        machine.tick(21, MAX_INK, [])
        self.assertEqual(machine.tick(22, NORMAL_WITH_DESIRED_ON, []).commands, [])
        self.assertEqual(machine.tick(24, NORMAL_WITH_DESIRED_ON, []).commands, ["normal"])

    def test_deadline_wins_even_if_recovery_timeout_also_elapsed(self):
        machine = self.committed(duration=40)
        machine.tick(11, NORMAL, [SwitchEvent(False, 11)])
        decision = machine.tick(50, INK_TRANSITION, [])
        self.assertEqual(machine.phase, demo.Phase.RESTORING)
        self.assertEqual(decision.commands, ["normal"])

    def test_recovery_timeout_applies_even_after_mode_flags_arrive(self):
        machine = self.committed()
        machine.tick(20, NORMAL, [SwitchEvent(False, 20)])
        machine.tick(21, INK_TRANSITION, [])
        with self.assertRaisesRegex(DiagnosticError, "did not fully settle"):
            machine.tick(46, INK_TRANSITION, [])

    def test_expiry_restores_normal_for_either_physical_position(self):
        for physical_on in (True, False):
            with self.subTest(physical_on=physical_on):
                machine = self.committed(duration=5)
                machine.tick(12, MAX_INK, [SwitchEvent(physical_on, 12)])
                expiry = machine.tick(15, INK_TRANSITION, [])
                self.assertEqual(expiry.commands, ["normal"])
                self.assertEqual(machine.phase, demo.Phase.RESTORING)
                self.assertFalse(machine.tick(19, OFF_TRANSITION, []).completed)
                restored = machine.tick(21, NORMAL, [])
                self.assertTrue(restored.completed)
                self.assertIsNone(machine.deadline)
                expected = demo.Phase.WAIT_OFF if physical_on else demo.Phase.READY
                self.assertEqual(machine.phase, expected)

    def test_expiry_normal_snapshot_with_fresh_raw_on_requires_off_and_later_verification(self):
        machine = self.committed(duration=5)
        machine.tick(12, MAX_INK, [SwitchEvent(False, 12)])
        expiry = machine.tick(15, NORMAL, [SwitchEvent(True, 14.99)])
        self.assertEqual(expiry.commands, ["normal"])
        self.assertFalse(expiry.completed)
        self.assertEqual(machine.phase, demo.Phase.RESTORING)
        self.assertEqual(machine.deadline, 15)
        later = machine.tick(15.25, NORMAL, [])
        self.assertEqual(later.commands, [])
        self.assertTrue(later.completed)
        self.assertEqual(machine.phase, demo.Phase.WAIT_OFF)

    def test_expiry_off_command_is_not_duplicated_while_desired_off_transition_runs(self):
        machine = self.committed(duration=5)
        expiry = machine.tick(15, MAX_INK, [])
        self.assertEqual(expiry.commands, ["normal"])
        still_ink_desired_off = ModeState(0, 2, 1, True, True)
        waiting = machine.tick(16, still_ink_desired_off, [])
        self.assertEqual(waiting.commands, [])
        self.assertFalse(waiting.completed)
        self.assertEqual(machine.deadline, 15)
        self.assertTrue(machine.tick(21, NORMAL, []).completed)

    def test_restored_phone_with_slider_on_requires_raw_off_before_rearming(self):
        machine = self.committed(duration=5)
        machine.tick(15, MAX_INK, [])
        machine.tick(20, NORMAL, [])
        self.assertEqual(machine.phase, demo.Phase.WAIT_OFF)
        machine.tick(21, NORMAL, [])
        machine.tick(22, NORMAL, [SwitchEvent(True, 22)])
        self.assertEqual(machine.phase, demo.Phase.WAIT_OFF)
        self.assertIsNone(machine.deadline)
        machine.tick(23, NORMAL, [SwitchEvent(False, 23)])
        self.assertEqual(machine.phase, demo.Phase.READY)
        machine.tick(24, MAX_INK, [SwitchEvent(True, 24)])
        self.assertEqual(machine.deadline, 29)
        self.assertEqual(machine.sessions, 2)

    def test_raw_off_during_restoration_does_not_arm_until_normal_settles(self):
        machine = self.committed(duration=5)
        machine.tick(15, MAX_INK, [])
        machine.tick(16, OFF_TRANSITION, [SwitchEvent(False, 16)])
        self.assertEqual(machine.phase, demo.Phase.RESTORING)
        self.assertFalse(machine.tick(17, OFF_TRANSITION, []).completed)
        self.assertEqual(machine.phase, demo.Phase.RESTORING)
        self.assertTrue(machine.tick(20, NORMAL, []).completed)
        self.assertEqual(machine.phase, demo.Phase.READY)

    def test_start_and_restore_timeout_fail_instead_of_stalling(self):
        machine = demo.Commitment()
        machine.tick(0, NORMAL_WITH_DESIRED_ON, [SwitchEvent(True, 0)])
        with self.assertRaisesRegex(DiagnosticError, "did not start"):
            machine.tick(26, NORMAL_WITH_DESIRED_ON, [])
        machine = self.committed(duration=5)
        machine.tick(15, MAX_INK, [])
        with self.assertRaisesRegex(DiagnosticError, "restoration timed out"):
            machine.tick(41, OFF_TRANSITION, [])


class MemoryJournal:
    def __init__(self, folder=None):
        self.entries = []
        self.closed = False

    def write(self, kind, **data):
        self.entries.append((kind, data))

    def close(self):
        self.closed = True


class FakeAdapter:
    def __init__(self, states=None, restore_error=None):
        self.states = list(states or [NORMAL, NORMAL, NORMAL])
        self.restore_error = restore_error
        self.operations = []
        self.read_checks = []

    def validate(self):
        return {"model": "T807D", "fingerprint": "verified"}

    def read_state(self, *, check_configuration=True):
        self.read_checks.append(check_configuration)
        state = self.states.pop(0) if self.states else NORMAL
        if isinstance(state, BaseException):
            raise state
        return state

    def enter_max_ink(self):
        self.operations.append("enter")

    def restore_normal(self):
        self.operations.append("normal")
        if self.restore_error:
            raise self.restore_error


class FakeMonitor:
    def __init__(self, event_batches=None, alive_error=None, close_error=None):
        self.event_batches = list(event_batches or [[]])
        self.alive_error = alive_error
        self.close_error = close_error
        self.started = False
        self.closed = False

    def start(self):
        self.started = True

    def check_alive(self):
        if self.alive_error:
            raise self.alive_error

    def drain(self):
        return self.event_batches.pop(0) if self.event_batches else []

    def close(self):
        self.closed = True
        if self.close_error:
            raise self.close_error


class FakeStop:
    def __init__(self, stop_after_wait=1):
        self.value = False
        self.waits = 0
        self.stop_after_wait = stop_after_wait

    def is_set(self):
        return self.value

    def set(self):
        self.value = True

    def wait(self, seconds):
        self.waits += 1
        if self.stop_after_wait is not None and self.waits >= self.stop_after_wait:
            self.value = True
        return self.value


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name)
        self.args = argparse.Namespace(adb="fake-adb", serial="TCL-USB", output=str(self.output), duration=5, once=False)
        self.stdout, self.stderr = io.StringIO(), io.StringIO()

    def run_fake(self, adapter, monitor, stop=None, journal=None, clock=None):
        stop = stop or FakeStop()
        journal = journal or MemoryJournal()
        adb = Mock(serial="TCL-USB")
        thread = Mock()
        with patch.object(demo, "connect", return_value=adb) as connect, \
                patch.object(demo, "TclAdapter", return_value=adapter) as factory, \
                patch.object(demo, "PhysicalSwitchMonitor", return_value=monitor), \
                patch.object(demo, "Journal", return_value=journal), \
                patch.object(demo, "DemoLock", return_value=nullcontext()), \
                patch.object(demo.threading, "Event", return_value=stop), \
                patch.object(demo.threading, "Thread", return_value=thread), \
                redirect_stdout(self.stdout), redirect_stderr(self.stderr):
            if clock is None:
                code = demo.run_demo(self.args)
            else:
                with patch.object(demo.time, "monotonic", side_effect=clock):
                    code = demo.run_demo(self.args)
        self.assertEqual(connect.call_count, 1)
        factory.assert_called_once_with(adb)
        return code, journal

    def test_typed_operator_stop_closes_monitor_and_verifies_normal(self):
        adapter, monitor = FakeAdapter(), FakeMonitor()
        code, journal = self.run_fake(adapter, monitor)
        self.assertEqual(code, 0)
        self.assertEqual(adapter.operations, ["normal"])
        self.assertEqual(adapter.read_checks, [True, True, False])
        self.assertTrue(monitor.closed)
        self.assertTrue(journal.closed)
        self.assertIn("shutdown_restored", [kind for kind, _ in journal.entries])

    def test_ctrl_c_returns_130_after_normal_restoration(self):
        adapter = FakeAdapter()
        monitor = FakeMonitor(alive_error=KeyboardInterrupt())
        code, journal = self.run_fake(adapter, monitor)
        self.assertEqual(code, 130)
        self.assertEqual(adapter.operations, ["normal"])
        self.assertTrue(monitor.closed)
        self.assertTrue(journal.closed)

    def test_wrong_configuration_or_unknown_native_state_fails_and_restores(self):
        for message in ("Native switch configuration changed", "Unsupported NXTPAPER state"):
            with self.subTest(message=message):
                adapter = FakeAdapter([NORMAL, DiagnosticError(message), NORMAL])
                code, journal = self.run_fake(adapter, FakeMonitor())
                self.assertEqual(code, 2)
                self.assertEqual(adapter.operations, ["normal"])
                self.assertEqual(adapter.read_checks, [True, True, False])
                self.assertTrue(journal.closed)

    def test_usb_failure_attempts_restore_reports_manual_recovery_and_never_reconnects(self):
        disconnected = DiagnosticError("Selected TCL serial disconnected; no other device will be used")
        adapter = FakeAdapter([NORMAL, disconnected], restore_error=disconnected)
        monitor = FakeMonitor()
        code, journal = self.run_fake(adapter, monitor)
        self.assertEqual(code, 2)
        self.assertEqual(adapter.operations, ["normal"])
        self.assertTrue(monitor.closed)
        self.assertTrue(journal.closed)
        self.assertIn("manual_recovery_required", [kind for kind, _ in journal.entries])

    def test_monitor_cleanup_failure_still_restores_phone_and_closes_journal(self):
        for error in (DiagnosticError("cleanup failed"), OSError("cleanup IO failed")):
            with self.subTest(error=error):
                adapter = FakeAdapter()
                code, journal = self.run_fake(adapter, FakeMonitor(close_error=error))
                self.assertEqual(code, 2)
                self.assertEqual(adapter.operations, ["normal"])
                self.assertTrue(journal.closed)

    def test_ctrl_c_during_monitor_cleanup_preserves_130_and_still_restores(self):
        adapter = FakeAdapter()
        monitor = FakeMonitor(close_error=KeyboardInterrupt())
        code, journal = self.run_fake(adapter, monitor)
        self.assertEqual(code, 130)
        self.assertEqual(adapter.operations, ["normal"])
        self.assertEqual(adapter.read_checks, [True, True, False])
        self.assertTrue(monitor.closed)
        self.assertTrue(journal.closed)
        self.assertIn("operator_stop_during_cleanup", [kind for kind, _ in journal.entries])
        self.assertEqual(journal.entries[-1], ("exit", {"exit_code": 130}))

    def test_once_finishes_after_verified_normal_without_extra_shutdown_toggle(self):
        self.args.once = True
        adapter = FakeAdapter([NORMAL, MAX_INK, INK_TRANSITION, NORMAL])
        monitor = FakeMonitor([[SwitchEvent(True, 0)], [], []])
        code, journal = self.run_fake(adapter, monitor, FakeStop(None), clock=[0, 5, 6])
        self.assertEqual(code, 0)
        self.assertEqual(adapter.operations, ["normal"])
        self.assertEqual(adapter.read_checks, [True, True, True, True])
        self.assertTrue(monitor.closed)
        self.assertIn("completed", [kind for kind, _ in journal.entries])

    def test_once_does_not_exit_on_pre_switch_normal_snapshot_at_deadline(self):
        self.args.once = True
        adapter = FakeAdapter([NORMAL, MAX_INK, MAX_INK, NORMAL, NORMAL])
        monitor = FakeMonitor([[SwitchEvent(True, 0)], [SwitchEvent(False, 1)],
                               [SwitchEvent(True, 4.99)], []])
        code, journal = self.run_fake(adapter, monitor, FakeStop(None), clock=[0, 1, 5, 6])
        self.assertEqual(code, 0)
        self.assertEqual(adapter.operations, ["normal"])
        self.assertEqual(len(adapter.read_checks), 5)
        self.assertTrue(journal.closed)
        completions = [data for kind, data in journal.entries if kind == "completed"]
        self.assertEqual(completions, [{"sessions": 1}])

    def test_unsettled_start_rejected_before_monitor_or_mode_commands(self):
        adapter = FakeAdapter([OFF_TRANSITION])
        with patch.object(demo, "connect", return_value=Mock(serial="TCL-USB")), \
                patch.object(demo, "TclAdapter", return_value=adapter), \
                patch.object(demo, "PhysicalSwitchMonitor") as factory:
            with self.assertRaisesRegex(DiagnosticError, "fully settled normal"):
                demo.run_demo(self.args)
        self.assertEqual(adapter.operations, [])
        factory.assert_not_called()

    def test_stop_listener_accepts_stop_quit_or_exit(self):
        for keyword in ("STOP", "quit", " exit "):
            stop = FakeStop(None)
            with self.subTest(keyword=keyword), patch.object(demo.sys, "stdin", io.StringIO(keyword + "\n")):
                demo.listen_for_stop(stop)
            self.assertTrue(stop.is_set())

    def test_invalid_durations_are_rejected_before_device_access(self):
        for value in ("0", "4.99", "300.01", "nan", "inf", "-inf"):
            with self.subTest(value=value), patch.object(demo, "run_demo") as run, redirect_stderr(self.stderr):
                self.assertEqual(demo.main(["--duration=" + value]), 2)
                run.assert_not_called()
        self.assertEqual(demo.build_parser().parse_args([]).duration, 300)

    def test_journal_disk_failure_does_not_raise_or_repeat_warning(self):
        class FailingHandle:
            def write(self, _):
                raise OSError("disk full")

            def close(self):
                raise OSError("cannot flush")

        journal = demo.Journal(self.output)
        journal.handle.close()
        journal.handle = FailingHandle()
        with redirect_stderr(self.stderr):
            journal.write("first")
            journal.write("second")
            journal.close()
        self.assertTrue(journal.failed)
        self.assertEqual(self.stderr.getvalue().count("could not be saved"), 1)
        adapter = FakeAdapter([NORMAL])
        with redirect_stdout(self.stdout):
            self.assertTrue(demo.restore_before_exit(adapter, journal))
        self.assertEqual(adapter.operations, ["normal"])
        self.assertEqual(adapter.read_checks, [False])


if __name__ == "__main__":
    unittest.main()
