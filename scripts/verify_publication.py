"""Validate local beta metadata and, optionally, the exact public APK.

The schema is supplied explicitly so validation records which upstream snapshot
was used. This tool never publishes, installs, or contacts a phone.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "local" / "publication-tools"))
VERSION = "1.0.6-beta.2"
CODE = 8
PACKAGE = "com.analoganchor.nxtpaperguard"
REPOSITORY = "https://github.com/arazi-hash/AnalogAnchor_NXTPAPER_E-Ink-Pre-Commitment-Mode"
APK_NAME = f"E-Ink-Precommitment-Mode-{VERSION}.apk"
OLD_DEBUG_CERT = "bb57ddf958f90324e214020a7f65e5aba9f4e3dd7ba1ebd6454868af8cb41d2e"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def run(command):
    result = subprocess.run([str(part) for part in command], capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=90)
    require(result.returncode == 0, f"Artifact inspection failed: {Path(command[0]).name}: {result.stderr.strip()}")
    return result.stdout


def metadata(schema_path, require_screenshots):
    try:
        import jsonschema
    except ImportError as error:
        raise ValueError("Install jsonschema for this build tool: python -m pip install --target local/publication-tools jsonschema") from error
    schema_bytes = schema_path.read_bytes()
    schema = json.loads(schema_bytes)
    manifest = json.loads((ROOT / "shizu_store.json").read_text(encoding="utf-8"))
    jsonschema.Draft7Validator.check_schema(schema)
    jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker()).validate(manifest)
    require(manifest["package_name"] == PACKAGE, "Store package differs")
    require(manifest["version_name"] == VERSION and manifest["version_code"] == CODE, "Store version differs")
    require(manifest["download_url"] == f"{REPOSITORY}/releases/download/v{VERSION}/{APK_NAME}", "Store APK URL must use the exact beta tag")
    require(manifest["requires_shizuku"] is True and manifest["license"] == "Apache-2.0" and manifest["open_source"] is True, "Store requirements/license differ")
    require("categories" not in manifest and "category" in manifest, "Use singular category")
    require(not require_screenshots or bool(manifest.get("screenshots")), "Real beta screenshots are still required")
    for locale in ("en-US", "ar"):
        base = ROOT / "fastlane" / "metadata" / "android" / locale
        for name in ("title.txt", "short_description.txt", "full_description.txt", f"changelogs/{CODE}.txt"):
            require((base / name).is_file() and bool((base / name).read_text(encoding="utf-8").strip()), f"Missing Fastlane {locale}/{name}")
        require(len((base / "title.txt").read_text(encoding="utf-8").strip()) <= 30, f"Fastlane title too long: {locale}")
        require(len((base / "short_description.txt").read_text(encoding="utf-8").strip()) <= 80, f"Fastlane short description too long: {locale}")
        require((base / "images/icon.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), f"Fastlane icon is not PNG: {locale}")
        if require_screenshots:
            require(any((base / "images/phoneScreenshots").glob("*.png")), f"Real beta screenshots missing: {locale}")
    return {"schema_sha256": hashlib.sha256(schema_bytes).hexdigest(), "metadata": "passed",
            "metadata_version": VERSION, "metadata_version_code": CODE,
            "screenshots_required": require_screenshots}


def inspect_apk(apk, sdk, expected_certificate, version=VERSION, code=CODE):
    tools = sdk / "build-tools" / "36.0.0"
    badging = run([tools / "aapt2.exe", "dump", "badging", apk])
    require(re.search(r"package: name='" + re.escape(PACKAGE) + r"' versionCode='" + str(code) +
                      r"' versionName='" + re.escape(version) + "'", badging), "APK package/version differs")
    require("application-debuggable" not in badging, "Public APK is debuggable")
    tree = run([tools / "aapt2.exe", "dump", "xmltree", apk, "--file", "AndroidManifest.xml"])
    for flag in ("debuggable", "testOnly"):
        require(not re.search(r"android:" + flag + r"\([^\n]*\)=\(type 0x12\)0xffffffff", tree), f"Public APK {flag} is true")
    require("android.permission.INTERNET" not in tree, "Unexpected INTERNET permission")
    signer = run([tools / "apksigner.bat", "verify", "--verbose", "--print-certs", apk])
    match = re.search(r"Signer #1 certificate SHA-256 digest: ([0-9a-fA-F]+)", signer)
    require(match is not None, "Cannot identify APK signing certificate")
    certificate = match.group(1).lower()
    require(certificate != OLD_DEBUG_CERT, "Public APK has historical debug signer")
    require(certificate == expected_certificate.lower().replace(":", ""), "Public signer differs from the independently recorded permanent certificate")
    expected = {"nxtpaper_guard.sh": ROOT / "nxtpaper_guard.sh",
                "nxtpaper_setup.sh": ROOT / "nxtpaper_setup.sh",
                "nxtpaper_firmware.properties": ROOT / "compatibility/profiles/t807d-eea-amd9.properties"}
    for folder in ("profiles", "adapters"):
        for path in (ROOT / "compatibility" / folder).glob("*.properties"):
            expected[f"compatibility/{folder}/{path.name}"] = path
    with zipfile.ZipFile(apk) as archive:
        names = set(archive.namelist())
        for name, path in expected.items():
            require(archive.read("assets/" + name) == path.read_bytes(), f"APK asset differs: {name}")
        bundled_registry = {name.removeprefix("assets/") for name in names if name.startswith("assets/compatibility/") and name.endswith(".properties")}
        require(bundled_registry == {name for name in expected if name.startswith("compatibility/")}, "APK registry contains stale or missing entries")
        for name in ("APACHE-2.0.txt", "SHIZUKU-API-MIT.txt", "NOTICE.txt"):
            require("assets/licenses/" + name in names, f"Missing bundled notice: {name}")
        require(not any(name.lower().endswith((".jks", ".keystore", ".p12", ".pfx", "signing.properties")) for name in names), "APK contains signing material")
    return {"apk": apk.name, "bytes": apk.stat().st_size,
            "sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
            "certificate_sha256": certificate, "debuggable": False, "test_only": False,
            "package": PACKAGE, "version": version, "version_code": code,
            "bundled_assets": "equal", "physical_acceptance": "requires recorded handset results"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--require-screenshots", action="store_true")
    parser.add_argument("--apk", type=Path)
    parser.add_argument("--apk-version", default=VERSION, help="Expected local APK version; store metadata is checked separately")
    parser.add_argument("--apk-version-code", type=int, default=CODE, help="Expected local APK version code")
    parser.add_argument("--certificate", help="Independently recorded permanent public certificate SHA256")
    parser.add_argument("--sdk", type=Path, default=Path(os.environ.get("LOCALAPPDATA", "")) / "Android/Sdk")
    args = parser.parse_args()
    try:
        report = metadata(args.schema, args.require_screenshots)
        if args.apk:
            require(bool(args.certificate), "--certificate is required for public APK verification")
            require(args.apk_version_code > 0, "APK version code must be positive")
            report.update(inspect_apk(args.apk, args.sdk, args.certificate, args.apk_version, args.apk_version_code))
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except (ValueError, OSError, zipfile.BadZipFile, KeyError) as error:
        parser.exit(1, f"Publication verification failed: {error}\n")


if __name__ == "__main__":
    main()
