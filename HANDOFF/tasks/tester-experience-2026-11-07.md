# NXTPAPER beta.2 tester experience

Updated 8 November 2026, Bahrain. Local implementation and verification complete.

## Objective and accepted scope

The founder supplied NXTPAPER Analog Anchor Compatibility.pdf and asked to use it
to refine the current build. Reviewed the recent compatibility discussion, PDF,
actual source and relevant primary sources. The PDF incorrectly identifies AMD9
as incompatible, confuses Linux 592/593 with Android 343/344 and proposes replacing
capabilities already implemented. It does not supply verified new firmware mappings.

Founder chose improved tester experience and explicitly said the handset is
disconnected while working remotely. Then authorized implementation of the plan.
Target is local candidate 1.0.6-beta.2 / code 8 with the existing permanent public
signer. Handset acceptance and publication are pending. New model adapters and
firmware changes are outside this task.

## Implemented

- Shared EN/AR guidance for Shizuku startup/permission, switch/layout/mapping,
  native settings, occupied controller, interrupted test and restoration failures.
- A bounded allowlisted report formatter, independent of compatibility success.
  Basic Android identity and firmware/security patch are available without Shizuku.
  Shell assessment and setup observations have separate cache labels and ages.
  Failed observation attempts never receive a successful observation timestamp.
- Scrollable report preview with selectable technical text and vertical Copy,
  Share and Open GitHub report form buttons. Browser URL has only the template
  selection. Missing external app/clipboard actions receive localized feedback.
- Fresh read-only diagnosis hands its actual assessment to the report dialog.
  Report operations do not call the controller, deploy files, write preferences
  or grant qualification. Existing setup/commitment gates remain authoritative.
- Updated support docs, existing issue form, privacy notes, release notes and
  EN/AR changelog 8. Published beta.1 catalog metadata remains pinned to the
  published artifact. Candidate verifier accepts explicit APK version overrides.

## Files

Android changes are CompatibilityReport.kt, SetupGuidance.kt, MainActivity.kt,
GuardRuntime.kt, NativeAdapter.kt, dialog_compatibility_report.xml, EN/AR strings,
app/build.gradle.kts and report/guidance tests. Support files are README.md,
docs/COMPATIBILITY.md, docs/RELEASE.md, PRIVACY.md, RELEASE_NOTES.md,
.github/ISSUE_TEMPLATE/compatibility.yml and fastlane changelogs/8.txt.
scripts/verify_publication.py verifies local candidate version/code independently
of the existing published metadata.

## Final checks

- Python full suite passed 276 tests in 249.937 seconds.
- Final Android suite passed 56 tests with zero failures/errors.
- First lint analysis crashed inside GestureBackNavDetector / Kotlin UAST. Source
  had been edited while that pass was running. A fresh --no-daemon frozen-source
  verification passed in 3m23s. After removing five obsolete strings and resolving
  the new URI-style warning, final test/lint/debug/release verification passed in
  2m20s. Both lint variants have zero errors and 19 pre-existing warnings. No lint
  rule was disabled.
- YAML issue form parses with PyYAML installed only under ignored
  local/publication-tools. EN/AR translatable resource coverage and report layout
  wrapping/scrolling checks passed. git diff --check passed.
- No emulator is installed and the handset is unavailable. Actual rendering,
  large-font behavior, clipboard/share/browser interactions, Shizuku reconnection
  and guided-setup presentation on a phone await acceptance.

Logs are under ignored logs/tester-experience-*-2026-11-08.txt. Native shell
controller, guided-test script, adapter registry and shizu_store.json have no diff.

## Candidate delivery

Ignored folder `dist/tester-experience-1.0.6-beta.2/` contains the signed APK,
SHA256 sidecar, release notes and VERIFICATION.json. APK size is 5,104,547 bytes.

- APK SHA256 `417e00fa1421746a2586cbd45633bf399a9614527107a41c96cdf992825a99cc`.
- Public certificate SHA256 `434a6ec4f84e1720f8f05e826fe2ccc0d148c47df73e561eac02d1b6f0845202`.
- Package/version/code, non-debuggable/non-testOnly flags, absence of INTERNET
  permission/private signing material, and exact bundled asset equality passed.
- The verifier accepted beta.2/code8 overrides and rejected the default beta.1
  expectation for this APK. Published beta.1 metadata passed its cached upstream
  schema separately. Old publication screenshots do not establish beta.2 UI QA.
- Final checksum and baseline native script/adapter byte equality were checked.

Use the public-signer candidate only through the documented signing procedure.
The founder's historical test installation has a different certificate, so a
direct install-over is not its migration path. No private acceptance copy was
created during this task.

## Working tree and continuity

Started on codex/nxtpaper-demo at 5450f34 with a clean tracked tree and six existing
untracked historical handoff files. Preserve all those historical files. Root owns
all files now. Subagents finished their edits and then hit usage limits during
review. No source commit, push, phone change or beta.2 publication has occurred.

## Next action

When a handset is available, follow docs/RELEASE.md for coordinated signing and
phone acceptance. Check EN/AR and enlarged text, reports before/after Shizuku,
copy/share/browser handoff, fresh versus cached results, reconnect and guided
setup. Preserve any live controller and existing data. Record results before
publication. Source changes are ready for commit review, and have not been
committed or pushed. Transfer ignored APK artifacts explicitly if needed on the
other PC. No running build or test remains.
