"""Check the public APK and observe CoreFetch's independent GitHub indexing."""

import argparse
import gzip
from hashlib import sha256
import json
from pathlib import Path
import re
from ssl import PEM_cert_to_DER_cert
import subprocess
from tempfile import TemporaryDirectory
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


CATALOG = "https://corefetch.siwane.xyz/?action="
ROOT = Path(__file__).resolve().parents[1]


def public_bytes(url, timeout, max_bytes):
    request = Request(url, headers={"User-Agent": "AnalogAnchor-CoreFetch-sync-check", "Accept-Encoding": "gzip"})
    with urlopen(request, timeout=timeout) as response:
        if response.headers.get("Content-Encoding", "").lower() == "gzip":
            with gzip.GzipFile(fileobj=response) as body:
                data = body.read(max_bytes + 1)
        else:
            data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("Public response exceeds the inspection size limit")
    return data


def release_identity(manifest):
    repo = urlsplit(manifest["repo_url"])
    if (repo.scheme, repo.netloc) != ("https", "github.com") or repo.query or repo.fragment:
        raise ValueError("Store repo_url must be a public GitHub repository URL")
    if not re.fullmatch(r"/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo.path):
        raise ValueError("Store repo_url must identify one GitHub owner and repository")
    repo_id = repo.path[1:]
    tag = "v" + manifest["version_name"]
    apk_url = manifest["download_url"]
    prefix = f"https://github.com/{repo_id}/releases/download/{tag}/"
    if not apk_url.startswith(prefix) or not re.fullmatch(r"[A-Za-z0-9_.-]+\.apk", apk_url[len(prefix):]):
        raise ValueError("Store download_url must identify an APK under the exact versioned GitHub release")
    return repo_id, tag


def verify_apk(manifest, aapt2, apksigner):
    release = ROOT / "release"
    expected_certificate = (release / "public-signing-certificate.sha256").read_text(encoding="ascii").strip().lower()
    certificate = PEM_cert_to_DER_cert((release / "public-signing-certificate.pem").read_text(encoding="ascii"))
    if sha256(certificate).hexdigest() != expected_certificate:
        raise ValueError("Recorded permanent signing certificate and SHA-256 fingerprint differ")
    # The APK comes from the same anonymous URL CoreFetch installs from.
    data = public_bytes(manifest["download_url"], timeout=30, max_bytes=100 * 1024 * 1024)
    with TemporaryDirectory() as temp:
        apk = Path(temp) / "release.apk"
        apk.write_bytes(data)
        signing = subprocess.run([apksigner, "verify", "--print-certs", str(apk)], check=True,
                                 capture_output=True, encoding="utf-8", timeout=30)
        fingerprints = re.findall(r"(?m)^Signer #\d+ certificate SHA-256 digest: ([0-9a-fA-F]{64})$", signing.stdout)
        if [fingerprint.lower() for fingerprint in fingerprints] != [expected_certificate]:
            raise ValueError("Public APK signer differs from the permanent signing certificate")
        result = subprocess.run([aapt2, "dump", "badging", str(apk)], check=True,
                                capture_output=True, encoding="utf-8", timeout=30)
    expected = (manifest["package_name"], str(manifest["version_code"]), manifest["version_name"])
    actual = re.search(r"(?m)^package: name='([^']*)' versionCode='([^']*)' versionName='([^']*)'", result.stdout)
    if not actual or actual.groups() != expected:
        raise ValueError("Public APK package, version name or version code differs from shizu_store.json")
    label = re.search(r"(?m)^application-label:'(.*)'$", result.stdout)
    if not label or label[1] != manifest["app_name"]:
        raise ValueError("Public APK default display name differs from shizu_store.json")


def description(value):
    return value.replace("\r\n", "\n").strip() if isinstance(value, str) else value


def catalog_differences(listing, details, manifest, repo_id, tag):
    if not isinstance(listing, list) or not isinstance(details, dict):
        raise ValueError("CoreFetch returned an unexpected catalog format")
    matches = [row for row in listing if isinstance(row, dict) and str(row.get("id", "")).casefold() == repo_id.casefold()]
    detail = details.get(repo_id.casefold())
    if len(matches) != 1 or not isinstance(detail, dict):
        return ["one listing and one details record for this repository"], False
    entry = matches[0]
    differences = []
    for field, expected in {
        "packageName": manifest["package_name"], "versionTag": tag,
        "apkUrl": manifest["download_url"], "hasJsonStore": True,
    }.items():
        if entry.get(field) != expected:
            differences.append(field)
    if description(entry.get("description")) != description(manifest["short_description"]):
        differences.append("short description")
    detailed = description(manifest["detailed_description"])
    if (description(detail.get("longDescription")) != detailed
            or ("longDescription" in entry and description(entry["longDescription"]) != detailed)):
        differences.append("detailed description")
    # Older catalog responses use the GitHub slug as `name`. Compare a title
    # only when CoreFetch supplies an application title rather than that slug.
    slug = repo_id.split("/", 1)[1].casefold()
    names = [entry.get("appName"), detail.get("appName"), entry.get("name")]
    titles = [name for name in names if isinstance(name, str) and name and name.casefold() != slug]
    if any(title != manifest["app_name"] for title in titles):
        differences.append("app display name")
    return differences, bool(titles)


def poll_catalog(manifest, repo_id, tag, wait_seconds, interval_seconds):
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            records = [json.loads(public_bytes(CATALOG + action,
                                  timeout=max(1, min(20, deadline - time.monotonic())),
                                  max_bytes=32 * 1024 * 1024)) for action in ("list", "details")]
            differences, title_present = catalog_differences(*records, manifest, repo_id, tag)
            if not differences:
                return title_present
            pending = "Waiting for CoreFetch to match " + ", ".join(differences)
        except (OSError, ValueError, EOFError) as error:
            pending = f"CoreFetch read failed ({type(error).__name__})"
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"CoreFetch did not match within {wait_seconds}s. {pending}.")
        print(pending, flush=True)
        time.sleep(min(interval_seconds, remaining))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aapt2", required=True, help="Path to Android SDK build-tools aapt2 executable")
    parser.add_argument("--apksigner", required=True, help="Path to Android SDK build-tools apksigner")
    parser.add_argument("--wait-seconds", type=int, default=600)
    parser.add_argument("--interval-seconds", type=int, default=30)
    args = parser.parse_args()
    if args.wait_seconds < 0 or args.interval_seconds <= 0:
        parser.error("wait must be nonnegative and interval must be positive")
    try:
        manifest = json.loads((ROOT / "shizu_store.json").read_text(encoding="utf-8"))
        repo_id, tag = release_identity(manifest)
        verify_apk(manifest, args.aapt2, args.apksigner)
        print(f"Verified public APK identity and permanent signer for {tag}.", flush=True)
        title_present = poll_catalog(manifest, repo_id, tag, args.wait_seconds, args.interval_seconds)
    except (OSError, ValueError, EOFError, KeyError, subprocess.SubprocessError) as error:
        parser.exit(1, f"{error}\n")
    print(f"CoreFetch catalog and details match {tag}.")
    if not title_present:
        print("CoreFetch did not expose a separate app title. The APK display name was verified separately.")


if __name__ == "__main__":
    main()
