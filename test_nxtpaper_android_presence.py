"""Run the actual Android runtime's embedded presence check against fake /proc."""

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

import test_nxtpaper_guard as fixtures


RUNTIME = Path(__file__).parent / "nxtpaper_guard/app/src/main/java/com/analoganchor/nxtpaperguard/GuardRuntime.kt"
SOURCE = RUNTIME.read_text(encoding="utf-8")
PRESENCE = re.search(r'private fun livePidCheck\(\) = """(.*?)"""\.trimIndent\(\)', SOURCE, re.S).group(1)
PRESENCE = (PRESENCE.replace("${'$'}", "$").replace("$PID", '"$PRESENCE_PID_FILE"')
            .replace("$SCRIPT", "/data/local/tmp/nxtpaper_guard.sh")
            .replace("/proc/", '"$PRESENCE_PROC_ROOT"/'))


@unittest.skipUnless(fixtures.SHELL, "A POSIX shell is required")
class AndroidPresenceTests(unittest.TestCase):
    def presence(self, token=None, *, process=True, readable=True, alive=True,
                 boot="current-boot", start="50", command=b"sh\x00/data/local/tmp/nxtpaper_guard.sh\x00"):
        with tempfile.TemporaryDirectory(prefix="nxtpaper-presence-") as folder:
            root = Path(folder)
            proc = root / "proc"
            (proc / "1").mkdir(parents=True)
            (proc / "sys/kernel/random").mkdir(parents=True)
            (proc / "sys/kernel/random/boot_id").write_text(boot + "\n", encoding="utf-8")
            if token is not None:
                (root / "guard.pid").write_text(token + "\n", encoding="utf-8")
            if process:
                (proc / "42").mkdir()
                if readable:
                    (proc / "42/stat").write_text("42 (sh) " + " ".join(["S"] + ["0"] * 18 + [start]) + "\n", encoding="utf-8")
                    (proc / "42/cmdline").write_bytes(command)
            env = dict(os.environ, PRESENCE_PID_FILE=(root / "guard.pid").as_posix(), PRESENCE_PROC_ROOT=proc.as_posix())
            prefix = "PATH=/usr/bin:/bin:$PATH\nkill() { [ \"$1\" = -0 ] || exit 99; return " + ("0" if alive else "1") + "; }\n"
            result = subprocess.run([fixtures.SHELL, "-c", prefix + PRESENCE + '\nprintf "%s:%s\\n" "$live" "$live_known"'],
                                    env=env, capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout.strip()

    def test_no_controller_evidence_is_absent(self):
        self.assertEqual(self.presence(None, process=False, alive=False), "0:0")

    def test_current_process_requires_matching_start_boot_and_command(self):
        self.assertEqual(self.presence("42:50:current-boot"), "1:1")

    def test_denied_inspection_remains_possibly_live(self):
        self.assertEqual(self.presence("42:50:current-boot", readable=False), "1:0")

    def test_malformed_existing_evidence_is_not_absence(self):
        self.assertEqual(self.presence("not-a-token"), "1:0")
        self.assertEqual(self.presence("42:bad:wrong-boot", readable=False), "1:0")

    def test_previous_boot_token_is_safely_stale(self):
        self.assertEqual(self.presence("42:50:old-boot", readable=False), "0:0")

    def test_reused_pid_or_different_command_is_stale(self):
        self.assertEqual(self.presence("42:50:current-boot", start="60"), "0:0")
        self.assertEqual(self.presence("42:50:current-boot", command=b"unrelated\x00"), "0:0")

    def test_missing_process_with_visible_proc_and_failed_liveness_is_absent(self):
        self.assertEqual(self.presence("42:50:current-boot", process=False, alive=False), "0:0")

    def test_legacy_pid_alone_is_not_fully_identified(self):
        self.assertEqual(self.presence("42"), "1:0")


if __name__ == "__main__":
    unittest.main()
