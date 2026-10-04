"""USB-connected five-minute native Max Ink commitment demonstration."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from enum import Enum
import json
from pathlib import Path
import sys
import threading
import time

from nxtpaper_diag import DiagnosticError, connect, new_capture, utc_now
from nxtpaper_control import TclAdapter, PhysicalSwitchMonitor, ModeState, SwitchEvent


class Phase(str, Enum):
    READY = "ready"
    STARTING = "starting"
    COMMITTED = "committed"
    RESTORING = "restoring"
    WAIT_OFF = "wait_for_slider_off"


@dataclass
class Decision:
    commands: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    completed: bool = False


class Commitment:
    """Pure state machine. Deadlines are monotonic and never renewed on exit."""

    def __init__(self, duration=300, transition_timeout=25):
        if duration <= 0:
            raise ValueError("Duration must be positive")
        self.duration = duration
        self.transition_timeout = transition_timeout
        self.phase = Phase.READY
        self.deadline = None
        self.physical_on = None
        self.transition_started = None
        self.recovery_started = None
        self.reset_for_reentry = False
        self.wrong_mode_since = None
        self.wrong_mode_signature = None
        self.sessions = 0

    def tick(self, now: float, state: ModeState, events: list[SwitchEvent]):
        decision = Decision()
        for event in events:
            self.physical_on = event.on
            if self.phase == Phase.WAIT_OFF and not event.on:
                self.phase = Phase.READY
                decision.messages.append("Slider returned to normal. Ready for a new Ink transition.")
            elif self.phase == Phase.READY and event.on:
                self.phase = Phase.STARTING
                self.transition_started = now
                decision.messages.append("Physical Ink entry detected. Waiting for native Max Ink confirmation.")
            elif self.phase == Phase.COMMITTED and not event.on:
                decision.messages.append("Early slider exit detected; the original deadline remains unchanged.")

        if self.phase == Phase.READY:
            if not state.normal and not events:
                raise DiagnosticError("Mode changed without a physical Ink entry. Stop and restart in normal mode.")
            return decision

        if self.phase == Phase.WAIT_OFF:
            return decision

        if self.phase == Phase.STARTING:
            if state.max_ink:
                self.phase = Phase.COMMITTED
                self.deadline = now + self.duration
                self.sessions += 1
                self.transition_started = None
                decision.messages.append(f"Native Max Ink confirmed. {self.duration:g}-second commitment started.")
            elif now - self.transition_started > self.transition_timeout:
                raise DiagnosticError("Native Max Ink did not start within the transition timeout.")
            else:
                # A rapid physical reversal before native entry must not cancel
                # the initial entry. The timer still starts only after confirmation.
                if state.tswt == 0:
                    decision.commands.append("enter")
                return decision

        if self.phase == Phase.COMMITTED:
            if now >= self.deadline:
                self.phase = Phase.RESTORING
                self.transition_started = now
                self.reset_for_reentry = False
                self.recovery_started = None
                decision.messages.append("Commitment finished. Restoring normal mode.")
                # The snapshot was read before draining raw slider events. Even
                # a normal snapshot can precede a queued physical ON transition.
                # Establish the native OFF edge now; only a later read confirms it.
                decision.commands.append("normal")
                return decision
            else:
                if self.recovery_started is not None and now - self.recovery_started > self.transition_timeout:
                    raise DiagnosticError("Max Ink recovery did not fully settle; stopping enforcement and restoring normal.")
                if state.max_ink and state.tswt == 1:
                    self.wrong_mode_since = None
                    self.wrong_mode_signature = None
                    if state.settled and self.recovery_started is not None:
                        elapsed = now - self.recovery_started
                        decision.messages.append(f"Native Max Ink fully settled after recovery in {elapsed:.2f}s.")
                        self.recovery_started = None
                    return decision
                if self.recovery_started is None:
                    self.recovery_started = now
                if self.reset_for_reentry:
                    if state.tswt == 0 and state.normal and state.settled:
                        self.reset_for_reentry = False
                        decision.commands.append("enter")
                elif state.tswt == 0:
                    # Native SystemUI reconciles this desired ON state once an
                    # ongoing OEM transition ends. Avoid repeatedly cycling it.
                    decision.commands.append("enter")
                    self.wrong_mode_since = None
                    self.wrong_mode_signature = None
                elif state.settled and not state.max_ink:
                    # Repeating ON while ON is ineffective. Make a native OFF
                    # edge, let it finish, then re-enter without renewing time.
                    # OEM transitions briefly expose both flags=0 between
                    # stages (for example ink2/book0 before book1). Only repair
                    # a genuinely stable wrong mode, never this intermediate seam.
                    signature = (state.ink_style, state.book_style)
                    if self.wrong_mode_signature != signature:
                        self.wrong_mode_signature = signature
                        self.wrong_mode_since = now
                    elif now - self.wrong_mode_since >= 2:
                        self.reset_for_reentry = True
                        self.wrong_mode_since = None
                        self.wrong_mode_signature = None
                        decision.commands.append("normal")
                else:
                    self.wrong_mode_since = None
                    self.wrong_mode_signature = None
                return decision

        if self.phase == Phase.RESTORING:
            if state.normal and state.tswt == 0 and state.settled:
                elapsed = now - self.transition_started
                self.phase = Phase.READY if self.physical_on is False else Phase.WAIT_OFF
                self.deadline = None
                self.transition_started = None
                decision.completed = True
                decision.messages.append(f"Normal mode fully restored in {elapsed:.2f}s.")
                if self.phase == Phase.WAIT_OFF:
                    decision.messages.append("Move the slider to normal before another session can start.")
            elif now - self.transition_started > self.transition_timeout:
                raise DiagnosticError("Normal restoration timed out. Use the physical Ink -> normal slider sequence.")
            elif state.tswt == 1:
                decision.commands.append("normal")
        return decision


class Journal:
    def __init__(self, folder):
        self.handle = (folder / "session.jsonl").open("w", encoding="utf-8", buffering=1)
        self.failed = False

    def write(self, kind, **data):
        # Losing local evidence must never prevent emergency phone restoration.
        if self.failed:
            return
        try:
            self.handle.write(json.dumps({"utc": utc_now(), "monotonic": time.monotonic(),
                                         "kind": kind, **data}) + "\n")
        except OSError:
            self.failed = True
            try:
                print("Session evidence could not be saved; mode restoration remains active.", file=sys.stderr)
            except OSError:
                pass

    def close(self):
        try:
            self.handle.close()
        except OSError:
            self.failed = True


class DemoLock:
    """The OS releases this local lock if the controller crashes."""

    def __init__(self, folder):
        self.path = Path(folder) / "controller.lock"
        self.handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+b")
        self.handle.seek(0, 2)
        if self.handle.tell() == 0:
            self.handle.write(b"0")
            self.handle.flush()
        self.handle.seek(0)
        try:
            if sys.platform == "win32":
                import msvcrt
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            self.handle.close()
            self.handle = None
            raise DiagnosticError("Another controller is already running on this PC.") from error
        return self

    def __exit__(self, *_):
        if self.handle:
            self.handle.close()


def restore_before_exit(adapter, journal, timeout=25):
    print("\nRestoring normal mode before stopping...", flush=True)
    start = time.monotonic()
    try:
        adapter.restore_normal()
        while time.monotonic() - start <= timeout:
            state = adapter.read_state(check_configuration=False)
            if state.normal and state.tswt == 0 and state.settled:
                journal.write("shutdown_restored", elapsed=time.monotonic() - start)
                print("Normal mode restored.", flush=True)
                return True
            time.sleep(0.25)
    except (DiagnosticError, OSError, KeyboardInterrupt) as error:
        journal.write("shutdown_restore_failed", error=str(error))
    print("Automatic restoration could not be confirmed. Keep the phone unlocked and slide to Ink, then back to normal.", flush=True)
    journal.write("manual_recovery_required")
    return False


def listen_for_stop(stop):
    try:
        for line in sys.stdin:
            if line.strip().lower() in {"stop", "quit", "exit"}:
                stop.set()
                return
    except (OSError, ValueError):
        pass


def run_demo(args):
    adb = connect(args)
    adapter = TclAdapter(adb)
    profile = adapter.validate()
    initial = adapter.read_state()
    if not initial.normal or not initial.settled:
        raise DiagnosticError("Start with the phone in fully settled normal mode, then run the demo again.")
    with DemoLock(args.output):
        folder = new_capture(args.output, "demo")
        journal = Journal(folder)
        monitor = PhysicalSwitchMonitor(adb, folder)
        machine = Commitment(args.duration)
        stop = threading.Event()
        armed, completed, exit_code = False, False, 0
        last_state, last_status, last_status_time = None, None, 0
        journal.write("start", profile=profile, duration=args.duration, serial=adb.serial)
        try:
            monitor.start()
            armed = True
            threading.Thread(target=listen_for_stop, args=(stop,), daemon=True).start()
            print(f"Ready. Session duration: {args.duration:g} seconds.", flush=True)
            print("Move the physical slider to Ink. If it is already there, move it to normal first.", flush=True)
            print("Type stop + Enter, or press Ctrl+C, to restore normal and stop.", flush=True)
            print(f"Local session evidence: {folder}", flush=True)
            while not stop.is_set():
                monitor.check_alive()
                state = adapter.read_state()
                events = monitor.drain()
                now = time.monotonic()
                for event in events:
                    journal.write("physical_slider", on=event.on, received_monotonic=event.at)
                if state != last_state:
                    journal.write("native_state", state=asdict(state))
                    last_state = state
                decision = machine.tick(now, state, events)
                for message in decision.messages:
                    print("\n" + message, flush=True)
                    journal.write("status", message=message, phase=machine.phase.value,
                                  deadline=machine.deadline)
                for command in decision.commands:
                    journal.write("native_command", action=command, deadline=machine.deadline)
                    if command == "enter":
                        adapter.enter_max_ink()
                    else:
                        adapter.restore_normal()
                if decision.completed:
                    completed = True
                    journal.write("completed", sessions=machine.sessions)
                    if args.once:
                        break
                status = machine.phase.value
                if machine.deadline is not None:
                    remaining = max(0, machine.deadline - now)
                    status += f" | {remaining:6.1f}s remaining"
                if status != last_status and now - last_status_time >= 1:
                    print("\r" + status.ljust(75), end="", flush=True)
                    last_status, last_status_time = status, now
                stop.wait(0.25)
        except KeyboardInterrupt:
            print("\nOperator stop requested.", flush=True)
            exit_code = 130
            journal.write("operator_stop")
        except (DiagnosticError, OSError) as error:
            print(f"\nController stopped: {error}", file=sys.stderr, flush=True)
            journal.write("failure", error=str(error))
            exit_code = 2
        finally:
            try:
                try:
                    monitor.close()
                except KeyboardInterrupt:
                    exit_code = 130
                    journal.write("operator_stop_during_cleanup")
                except (DiagnosticError, OSError) as error:
                    journal.write("monitor_cleanup_failed", error=str(error))
                    exit_code = 2
            finally:
                try:
                    if armed and not (completed and args.once and exit_code == 0):
                        if not restore_before_exit(adapter, journal):
                            exit_code = 2
                finally:
                    try:
                        journal.write("exit", exit_code=exit_code)
                    finally:
                        journal.close()
        print("\nController stopped.", flush=True)
        return exit_code


def build_parser():
    parser = argparse.ArgumentParser(description="USB native Max Ink commitment demo for the verified TCL T807D firmware.")
    parser.add_argument("--adb", help="Path to adb.exe")
    parser.add_argument("--serial", help="Select your physical TCL phone")
    parser.add_argument("--output", default=str(Path(__file__).resolve().parent / "logs"))
    parser.add_argument("--duration", type=float, default=300, help="5-300 seconds; default 300")
    parser.add_argument("--once", action="store_true", help="Stop after one completed session")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not 5 <= args.duration <= 300:
        print("Duration must be between 5 and 300 seconds.", file=sys.stderr)
        return 2
    try:
        return run_demo(args)
    except (DiagnosticError, OSError, ValueError) as error:
        print(f"Cannot start demo: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
