"""Host-only regression tests; no ADB process or handset is used."""

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import nxtpaper_diag as diag


def result(stdout="value\n", stderr="", returncode=0, timed_out=False):
    return diag.Result(["fake-adb", "read"], "2026-10-03T00:00:00+00:00",
                       0.1, returncode, timed_out, stdout, stderr)


class FakeAdb:
    serial = "TCL-USB-TEST"

    def __init__(self, responses=None):
        self.responses = responses or {}

    def command(self, args):
        return ["fake-adb", "-s", self.serial, *args]

    def read(self, args, timeout=20):
        response = self.responses.get(tuple(args), result())
        if isinstance(response, Exception):
            raise response
        return response


class FakeClock:
    def __init__(self, interrupt=False):
        self.current = 0.0
        self.interrupt = interrupt

    def monotonic(self):
        return self.current

    def sleep(self, seconds):
        self.current += seconds
        if self.interrupt:
            self.interrupt = False
            raise KeyboardInterrupt


class FakeProcess:
    def __init__(self, returncode=None, cleanup_timeout=False):
        self.returncode = returncode
        self.cleanup_timeout = cleanup_timeout
        self.killed = False

    def poll(self):
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -1

    def wait(self, timeout=None):
        if self.cleanup_timeout:
            raise subprocess.TimeoutExpired("fake-adb", timeout)
        return self.returncode


class DeviceAndCommandTests(unittest.TestCase):
    def test_device_parser_ignores_headers_and_daemon_messages(self):
        listing = "* daemon started successfully *\nList of devices attached\nTCL device product:nxt\nother unauthorized\nemulator-5554 device\n"
        self.assertEqual(diag.parse_devices(listing),
                         {"TCL": "device", "other": "unauthorized", "emulator-5554": "device"})

    def test_selected_serial_never_falls_back(self):
        with self.assertRaisesRegex(diag.DiagnosticError, "No other device"):
            diag.select_device({"OTHER": "device"}, "MISSING-TCL")
        with self.assertRaisesRegex(diag.DiagnosticError, "unauthorized"):
            diag.select_device({"TCL": "unauthorized", "OTHER": "device"}, "TCL")

    def test_selection_requires_unambiguous_authorized_physical_phone(self):
        for devices in ({}, {"TCL": "offline"}, {"TCL": "device", "OTHER": "device"},
                        {"emulator-5554": "device"}):
            with self.subTest(devices=devices), self.assertRaises(diag.DiagnosticError):
                diag.select_device(devices)
        self.assertEqual(diag.select_device({"TCL": "device", "emulator-5554": "device"}), "TCL")

    def test_adb_arguments_preserve_executable_spaces_and_serial(self):
        adb = diag.Adb(r"C:\Program Files\Android\adb.exe", "TCL-USB")
        self.assertEqual(adb.command(("shell", "getprop", "ro.product.model")),
                         [r"C:\Program Files\Android\adb.exe", "-s", "TCL-USB", "shell", "getprop", "ro.product.model"])

    def test_timeout_preserves_partial_output_and_stderr(self):
        error = subprocess.TimeoutExpired("fake-adb", 1, output=b"partial\xff", stderr=b"timeout evidence")
        with patch.object(diag.subprocess, "run", side_effect=error) as run:
            captured = diag.run_command(["fake-adb", "read"], timeout=1)
        self.assertTrue(captured.timed_out)
        self.assertIsNone(captured.returncode)
        self.assertEqual(captured.stdout, "partial\ufffd")
        self.assertEqual(captured.stderr, "timeout evidence")
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertEqual(run.call_args.kwargs["stdin"], subprocess.DEVNULL)

    def test_invalid_labels_cannot_create_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            for label in ("", "../escape", "a/b", "a\\b", "a:b", "-bad", "a" * 65):
                with self.subTest(label=label), self.assertRaises(diag.DiagnosticError):
                    diag.new_capture(temporary, label)
            self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_settings_values_preserve_equals_signs(self):
        self.assertEqual(diag.parse_settings("key=a=b=c\nempty=\nnot_a_setting\n"),
                         {"key": "a=b=c", "empty": ""})


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.console = io.StringIO()
        self.errors = io.StringIO()
        self.addCleanup(patch.stopall)

    def metadata(self):
        folders = list(self.root.iterdir())
        self.assertEqual(len(folders), 1)
        return folders[0], json.loads((folders[0] / "metadata.json").read_text(encoding="utf-8"))

    def run_main(self, argv, adb):
        with patch.object(diag, "connect", return_value=adb), redirect_stdout(self.console), redirect_stderr(self.errors):
            return diag.main(["--output", str(self.root), *argv])

    def test_optional_permission_failure_preserves_usable_snapshot(self):
        adb = FakeAdb({diag.SNAPSHOT_COMMANDS["input_capabilities"]:
                       result("", "Permission denied\n", returncode=1)})
        self.assertEqual(self.run_main(["snapshot", "normal"], adb), 0)
        folder, metadata = self.metadata()
        self.assertTrue(metadata["usable"])
        self.assertEqual(metadata["results"]["input_capabilities"]["returncode"], 1)
        self.assertEqual((folder / "input_capabilities.stderr.txt").read_text(), "Permission denied\n")
        self.assertIn("input_capabilities", self.console.getvalue())

    def test_failed_firmware_identity_makes_snapshot_error_without_losing_logs(self):
        adb = FakeAdb({diag.SNAPSHOT_COMMANDS["fingerprint"]:
                       result("partial", "USB disconnected", returncode=None, timed_out=True)})
        self.assertEqual(self.run_main(["snapshot", "normal"], adb), 2)
        folder, metadata = self.metadata()
        self.assertFalse(metadata["usable"])
        self.assertEqual(metadata["identity_failures"], ["fingerprint"])
        self.assertTrue(metadata["results"]["fingerprint"]["timed_out"])
        self.assertEqual((folder / "fingerprint.stderr.txt").read_text(), "USB disconnected")
        self.assertTrue((folder / "settings_system.txt").is_file())

    def test_empty_identity_read_is_an_error(self):
        adb = FakeAdb({diag.SNAPSHOT_COMMANDS["model"]: result("\n")})
        self.assertEqual(self.run_main(["snapshot", "normal"], adb), 2)
        _, metadata = self.metadata()
        self.assertEqual(metadata["identity_failures"], ["model"])

    def test_launch_failures_are_saved_for_each_snapshot_read(self):
        adb = FakeAdb({command: diag.DiagnosticError("ADB launch failed")
                       for command in diag.SNAPSHOT_COMMANDS.values()})
        self.assertEqual(self.run_main(["snapshot", "normal"], adb), 2)
        folder, metadata = self.metadata()
        self.assertFalse(metadata["usable"])
        self.assertEqual(len(metadata["results"]), len(diag.SNAPSHOT_COMMANDS))
        self.assertIn("ADB launch failed", (folder / "fingerprint.stderr.txt").read_text())

    def install_watch(self, processes, interrupt=False):
        clock = FakeClock(interrupt)
        handles = []
        pending = iter(processes)

        def launch(command, **kwargs):
            handles.extend([kwargs["stdout"], kwargs["stderr"]])
            process = next(pending)
            if isinstance(process, Exception):
                raise process
            kwargs["stdout"].write(b"captured evidence\n")
            if process.returncode is not None:
                kwargs["stderr"].write(b"Permission denied\n")
            return process

        patch.object(diag.subprocess, "Popen", side_effect=launch).start()
        patch.object(diag.time, "monotonic", side_effect=clock.monotonic).start()
        patch.object(diag.time, "sleep", side_effect=clock.sleep).start()
        return handles

    def test_expected_watch_duration_is_success_and_closes_all_clients(self):
        clients = [FakeProcess(), FakeProcess()]
        handles = self.install_watch(clients)
        self.assertEqual(self.run_main(["watch", "--seconds", "1"], FakeAdb()), 0)
        folder, metadata = self.metadata()
        self.assertEqual(metadata["stop_reason"], "capture_window_completed")
        self.assertTrue(metadata["usable"])
        self.assertTrue(all(client.killed for client in clients))
        self.assertTrue(all(handle.closed for handle in handles))
        self.assertTrue(all(row["available"] for row in metadata["results"].values()))
        self.assertEqual((folder / "logcat.txt").read_text(), "captured evidence\n")

    def test_partial_denied_stream_warns_and_keeps_useful_capture(self):
        clients = [FakeProcess(returncode=1), FakeProcess()]
        self.install_watch(clients)
        self.assertEqual(self.run_main(["watch", "--seconds", "1"], FakeAdb()), 0)
        folder, metadata = self.metadata()
        self.assertFalse(metadata["results"]["input"]["available"])
        self.assertTrue(metadata["results"]["logcat"]["available"])
        self.assertTrue(metadata["usable"])
        self.assertIn("input stream exited early", self.console.getvalue())
        self.assertIn("Unavailable/failed streams", self.console.getvalue())
        self.assertEqual((folder / "input.stderr.txt").read_text(), "Permission denied\n")

    def test_partial_launch_failure_still_captures_other_stream(self):
        self.install_watch([OSError("simulated input launch failure"), FakeProcess()])
        self.assertEqual(self.run_main(["watch", "--seconds", "1"], FakeAdb()), 0)
        _, metadata = self.metadata()
        self.assertFalse(metadata["results"]["input"]["available"])
        self.assertTrue(metadata["results"]["logcat"]["available"])
        self.assertIn("simulated input launch failure", metadata["results"]["input"]["error"])

    def test_total_launch_failure_is_nonzero_and_preserves_metadata(self):
        handles = self.install_watch([OSError("first failed"), OSError("second failed")])
        self.assertEqual(self.run_main(["watch", "--seconds", "1"], FakeAdb()), 2)
        _, metadata = self.metadata()
        self.assertEqual(metadata["stop_reason"], "start_or_capture_failed")
        self.assertFalse(metadata["usable"])
        self.assertTrue(all(handle.closed for handle in handles))

    def test_all_streams_exiting_early_is_nonzero_even_with_zero_returncode(self):
        self.install_watch([FakeProcess(returncode=0), FakeProcess(returncode=1)])
        self.assertEqual(self.run_main(["watch", "--seconds", "1"], FakeAdb()), 2)
        _, metadata = self.metadata()
        self.assertEqual(metadata["stop_reason"], "all_streams_exited")
        self.assertFalse(metadata["usable"])

    def test_operator_interrupt_returns_130_after_evidence_and_cleanup(self):
        clients = [FakeProcess(), FakeProcess()]
        handles = self.install_watch(clients, interrupt=True)
        self.assertEqual(self.run_main(["watch", "--seconds", "1"], FakeAdb()), 130)
        _, metadata = self.metadata()
        self.assertEqual(metadata["stop_reason"], "operator_interrupt")
        self.assertTrue(all(client.killed for client in clients))
        self.assertTrue(all(handle.closed for handle in handles))

    def test_cleanup_failure_does_not_skip_other_clients_handles_or_metadata(self):
        clients = [FakeProcess(cleanup_timeout=True), FakeProcess()]
        handles = self.install_watch(clients)
        self.assertEqual(self.run_main(["watch", "--seconds", "1"], FakeAdb()), 2)
        _, metadata = self.metadata()
        self.assertTrue(all(client.killed for client in clients))
        self.assertTrue(all(handle.closed for handle in handles))
        self.assertIn("input", metadata["cleanup_errors"])
        self.assertFalse(metadata["results"]["input"]["available"])
        self.assertTrue(metadata["results"]["logcat"]["available"])


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def fixture(self, name, serial="TCL-USB", fingerprint="firmware-A", settings="mode=0\ncontent=a=b\n", usable=True):
        folder = self.root / name
        folder.mkdir()
        metadata = {"kind": "snapshot", "serial": serial, "usable": usable,
                    "results": {"fingerprint": {"returncode": 0, "timed_out": False}}}
        (folder / "fingerprint.txt").write_text(fingerprint, encoding="utf-8")
        for namespace in ("system", "secure", "global"):
            key = "settings_" + namespace
            metadata["results"][key] = {"returncode": 0, "timed_out": False}
            (folder / (key + ".txt")).write_text(settings, encoding="utf-8")
        diag.write_json(folder / "metadata.json", metadata)
        return folder

    def test_different_device_or_firmware_is_rejected(self):
        before = self.fixture("normal")
        for name, serial, fingerprint in (("other-device", "OTHER", "firmware-A"),
                                          ("other-build", "TCL-USB", "firmware-B")):
            ink = self.fixture(name, serial, fingerprint)
            with self.subTest(name=name), self.assertRaisesRegex(diag.DiagnosticError, "different devices or firmware"):
                diag.compare(self.root / "reports", before, ink)
        self.assertFalse((self.root / "reports").exists())

    def test_unusable_identity_cannot_be_compared(self):
        before = self.fixture("normal")
        ink = self.fixture("ink", usable=False)
        with self.assertRaisesRegex(diag.DiagnosticError, "identity is incomplete"):
            diag.compare(self.root / "reports", before, ink)

    def test_three_way_comparison_preserves_values_and_baseline_return(self):
        before = self.fixture("normal")
        ink = self.fixture("ink", settings="mode=1\ncontent=c=d=e\n")
        after = self.fixture("after")
        with redirect_stdout(io.StringIO()):
            destination = diag.compare(self.root / "reports", before, ink, after)
        report = json.loads(destination.read_text(encoding="utf-8"))
        changes = {row["key"]: row for row in report["settings"]["system"]["changes"]}
        self.assertEqual(changes["content"]["normal_before"], "a=b")
        self.assertEqual(changes["content"]["ink"], "c=d=e")
        self.assertTrue(changes["mode"]["returned_to_baseline"])
        self.assertIn("correlations", report["warning"])

    def test_non_object_metadata_is_rejected_cleanly(self):
        folder = self.root / "malformed"
        folder.mkdir()
        diag.write_json(folder / "metadata.json", [])
        with self.assertRaises(diag.DiagnosticError):
            diag.load_snapshot(folder)


if __name__ == "__main__":
    unittest.main()
