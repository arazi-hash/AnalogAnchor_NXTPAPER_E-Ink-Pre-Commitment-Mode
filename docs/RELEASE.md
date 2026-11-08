# NXTPAPER_E-Ink-Pre-Commitment-Mode release and signing

The release target is `1.0.6-beta.3`, version code `9`, at Git tag
`v1.0.6-beta.3`. Consult [FINDINGS.md](../FINDINGS.md) for recorded handset checks
and [the handoff](../HANDOFF/LATEST.md) for publication status.

The 7 November beta.1 phone trials used a private acceptance copy signed with the
installation's existing identity. Its APK contents matched the published
`1.0.6-beta.1` / code `7` apart from signing metadata.
The public beta.1, beta.2 and beta.3 APKs use the same package and permanent public
certificate. Beta.3 supports an in-place update from either earlier public beta.
Migration from private or development copies is documented below.

## Build on either PC

Use JDK 17, Android SDK 36/build-tools 36.0.0 and the Gradle wrapper. Each PC keeps
its SDK path in ignored `nxtpaper_guard/local.properties`.

The permanent public signing key is stored privately outside the repository.
The default private configuration is
`~/.android/analoganchor-nxtpaper-release/signing.properties`; alternatively set
`NXTPAPER_SIGNING_PROPERTIES` to another private properties file. Required keys:
`storeFile`, `storePassword`, `keyAlias`, `keyPassword`. Never commit this file,
the PKCS12 key or passwords. The local location-only note is under ignored
`local/release-signing-location.txt`. A verified private backup exists on this PC;
and a private transfer folder is ready on the work PC. Copy the entire folder by
USB or private storage and run its installer on the other PC. Keep both copies
outside the project.

From `nxtpaper_guard`, run:

```powershell
.\gradlew.bat testDebugUnitTest lintDebug assembleRelease --max-workers=1 --no-parallel --console=plain
```

Release builds are non-debuggable. The build fails if release signing is missing;
it must never silently substitute the debug key or emit an unsigned public APK.
Debug checks do not require the permanent key. Verify the final APK certificate,
package/version, debug/testOnly flags, hashes and packaged controller/registry.

Permanent public certificate SHA256:
`434a6ec4f84e1720f8f05e826fe2ccc0d148c47df73e561eac02d1b6f0845202`.
The public certificate is committed under `release/`; it contains no private key.
The historical debug certificate starts `bb57ddf9` and is not the public signer.

Validate metadata using the recorded upstream schema snapshot:

```powershell
python -m pip install --target local/publication-tools jsonschema
python scripts/verify_publication.py --schema logs/shizu-store-schema-2026-11-07.json
```

Obtain the schema on another PC from
https://raw.githubusercontent.com/elhizazi1/shizu-store-docs/main/schema.json .
Verify the beta.3 public APK against the permanent public certificate. The
verifier reports the schema and APK hashes. Add `--require-screenshots` once the
reviewed captures are ready.

```powershell
python scripts/verify_publication.py --schema logs/shizu-store-schema-2026-11-07.json --apk PATH --certificate 434a6ec4f84e1720f8f05e826fe2ccc0d148c47df73e561eac02d1b6f0845202
```

Before publishing, confirm that the metadata refers to the beta.3 tag and APK URL
and run the final publication checks against that metadata and artifact.

## Existing development installation migration

Android requires a matching signing certificate for ordinary updates. Historical
development APKs and private acceptance copies may show **Update incompatible**
when installing the public release over them. An uninstall erases app-local
data. Preserve the existing APK/private key and inspect the actual installed
signer, all affected Android profiles and the live controller before migration.

Before a later coordinated migration, finish the old commitment or use its
supported Stop and confirm the controller is actually stopped. An IDLE snapshot
can race with a new physical switch movement. Record desired UI settings and
explain any app-local data reset before the founder chooses a migration. Phone
personal data and TCL's selected Max Ink apps must be preserved. Never claim a
public signing identity was installed when testing a differently signed copy.

For release-behavior testing while preserving the existing installation, a
private acceptance copy can be signed with the installed development identity.
It must remain non-debuggable, and every APK ZIP entry except signature metadata
must match the public release byte-for-byte. Record both hashes and certificates.
This tests the release implementation while leaving public-key migration separate;
it does not claim the permanent public signer was installed on the founder's phone.
Never attach this private acceptance copy to a public release.

## Physical acceptance gate

For beta.3, the website destination follows the current app language. Verify
both website locales. The native controller and compatibility data match beta.2
byte-for-byte, so the native handset evidence below continues to describe that
controller. Record any direct beta.3 handset tap separately.

For beta.2, verify the English and Arabic setup explanations, enlarged text,
report preview with Shizuku unavailable or permission denied, successful-test
reporting, clipboard copy, Android sharing and the browser form handoff. Check
that reports label cached observations and unperformed checks, and that opening
or sharing a report leaves qualification and mode control untouched. Then verify
Shizuku reconnection and the guided setup presentation on the actual handset.
Record new results separately from the beta.1 evidence in FINDINGS.md.

Record the public release APK SHA256 and signing fingerprint. On the founder's
phone, use either that APK after an explicitly chosen migration or the verified
private acceptance copy described above, with the signer distinction recorded.
Cover:

1. Shizuku authorization and visible EN/AR setup/report controls.
2. Passive physical Normal → Max Ink → Normal with genuine raw events and the
   actual native launcher/app restrictions.
3. Supervised programmatic exit while the switch remains Ink, and re-entry while
   it is Normal, followed by confirmed Normal restoration.
4. Immediate trial cancel, app hiding/reopening, screen sleep, interrupted setup,
   and unsuccessful tests never enabling commitments.
5. Default five-minute commitment, actual early physical recovery without timer
   renewal, ordinary expiry/extended reading, actual delayed Stop and Continue.
6. English/Arabic layout, enlarged text and user-previewed redacted reports.

Keep reboot/Shizuku loss and sustained 2/4/6/12-hour use as separate evidence.
Do not perform an OTA just to test update handling. Simulate changed identities
in local regressions and qualify real future firmware only when available.

## Publication assets and metadata

`shizu_store.json` uses the upstream singular `category` and exact versioned APK
URL. Its English/Arabic text states experimental support and Shizuku/setup
requirements. Fastlane uses `NXTPAPER E-Ink Pre-Commitment` to fit its 30-character
title limit. Use privacy-reviewed handset captures in the Fastlane image folders.
Beta.3 reuses the accepted beta.2 captures at the new tag because the website
destination is the only UI behavior change and the screens are identical.

Keep PRIVACY.md, LICENSE, NOTICE and THIRD_PARTY_NOTICES.md current. The app does
not send diagnostics automatically. A user can preview and explicitly share a
redacted report. Do not add unsupported privacy fields to Shizu metadata.

## GitHub and ShizuCoreFetch

The existing repository is
https://github.com/arazi-hash/AnalogAnchor_NXTPAPER_E-Ink-Pre-Commitment-Mode .
Do not create a duplicate. Source/release notes must identify the exact reviewed
commit. After verifying the changed behavior and the signed artifact, publish a
GitHub prerelease at `v1.0.6-beta.3`. Attach only:

- `E-Ink-Precommitment-Mode-1.0.6-beta.3.apk`
- Its SHA256 sidecar and release notes/public signing fingerprint.

Do not attach the private recovery kit, development APKs, signing material, raw
logs or personal screenshots. Do not use `/releases/latest/download/` for this
beta; its URL includes the actual tag.

For future updates, publish the signed APK on its exact GitHub release tag, then
push the `shizu_store.json` update to the default branch. Preserve the existing
GitHub About description and catalog text when updating release fields.
ShizuCoreFetch reads GitHub automatically. The **Verify CoreFetch sync** action
runs after a default-branch listing update. It checks the public APK's package,
name, version and permanent signer, then polls the store for up to ten minutes.
The action records when the catalog matches and reports a timeout if indexing
takes longer. A phone can show a cached listing until its next refresh.

IzzyOnDroid is not a launch promise: its current AI-code policy conflicts with
this project's development history. Keep that transparent. See
https://izzyondroid.org/docs/general/AppInclusionPolicy/#ai-policy .
