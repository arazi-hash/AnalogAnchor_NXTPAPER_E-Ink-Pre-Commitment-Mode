"""Bounded handset checks; native-key trials do not prove physical-slider input.

Start a commitment with the actual slider before running recovery trials. Output
contains only guard/native mode evidence and stays in the ignored logs directory.
"""

import argparse
import json
from pathlib import Path
import subprocess
import time


NATIVE_KEYS = (
    "TSWT_state", "nxtpaper_ink_style_state", "nxtpaper_book_style_state",
    "nxtpaper_is_applying_theme", "nxtpaper_animation_state",
    "tct_nxtpaper_mode_select", "tct_nxtpaper_switch_imm",
)


class Device:
    def __init__(self, adb, serial, output):
        self.base = [adb, "-s", serial]
        self.output = output
        self.output.parent.mkdir(parents=True, exist_ok=True)

    def shell(self, *args):
        run = subprocess.run(self.base + ["shell", *args], capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=15)
        if run.returncode:
            raise RuntimeError(run.stderr.strip() or run.stdout.strip())
        return run.stdout.strip()

    def record(self, event, **data):
        item = {"monotonic": round(time.monotonic(), 3), "event": event, **data}
        with self.output.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(item, ensure_ascii=False) + "\n")
        if event != "sample":
            print(json.dumps(item, ensure_ascii=False), flush=True)

    def sample(self):
        raw = self.shell("settings", "list", "secure")
        settings = dict(line.split("=", 1) for line in raw.splitlines() if "=" in line)
        native = {key: settings.get(key) for key in NATIVE_KEYS}
        # The verified controller checks PID identity and heartbeat here. A cached
        # COMMITTED file alone must never count as evidence of a live guard.
        state = self.shell("/system/bin/sh", "/data/local/tmp/nxtpaper_guard.sh", "status")
        parts = state.split(":")
        phase = parts[0]
        deadline = int(parts[3]) if len(parts) >= 4 else 0
        applying = native["nxtpaper_is_applying_theme"]
        animation = native["nxtpaper_animation_state"]
        settled = applying == animation == "0"
        ink = settled and [native[key] for key in NATIVE_KEYS[:3]] == ["1", "2", "1"]
        normal = settled and [native[key] for key in NATIVE_KEYS[:3]] == ["0", "0", "0"]
        item = {"phase": phase, "state": state, "deadline": deadline,
                "native": native, "ink": ink, "normal": normal}
        self.record("sample", **item)
        return item

    def wait(self, predicate, timeout, *, deadline=None):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            item = self.sample()
            if item["phase"] == "ERROR":
                raise RuntimeError("Controller entered ERROR: " + item["state"])
            if deadline is not None and item["deadline"] != deadline:
                raise RuntimeError("Original commitment deadline changed: " + item["state"])
            if predicate(item):
                return item
            time.sleep(1)
        raise TimeoutError("Handset condition not reached within " + str(timeout) + " seconds")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adb", required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--output", type=Path, default=Path("logs/device-qa.jsonl"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("snapshot")
    recovery = commands.add_parser("recovery")
    recovery.add_argument("--count", type=int, default=1, choices=range(1, 21))
    watch = commands.add_parser("watch")
    watch.add_argument("--seconds", type=int, default=60)
    args = parser.parse_args()
    device = Device(args.adb, args.serial, args.output)
    if args.command == "snapshot":
        device.record("snapshot", **device.sample())
    elif args.command == "watch":
        if not 1 <= args.seconds <= 7200:
            parser.error("watch duration must be between 1 and 7200 seconds")
        end = time.monotonic() + args.seconds
        while time.monotonic() < end:
            device.sample()
            time.sleep(2)
        device.record("watch_complete")
    elif args.command == "recovery":
        item = device.wait(lambda x: x["phase"] == "COMMITTED" and x["ink"], 45)
        deadline = item["deadline"]
        for trial in range(1, args.count + 1):
            before = time.monotonic()
            device.record("native_exit_requested", trial=trial, deadline=deadline)
            device.shell("input", "keyevent", "344")
            # Require observable departure before counting a subsequent Ink sample.
            device.wait(lambda x: not x["ink"], 15, deadline=deadline)
            device.wait(lambda x: x["phase"] == "COMMITTED" and x["ink"],
                        45, deadline=deadline)
            device.record("native_exit_recovered", trial=trial, deadline=deadline,
                          elapsed=round(time.monotonic() - before, 2))
            # Include the controller's two-second stable-state confirmation before
            # another exit; visible native Ink alone can precede acknowledgment.
            time.sleep(4)
        device.record("recovery_complete", count=args.count, deadline=deadline)


if __name__ == "__main__":
    main()
