# Beta.2 GitHub and CoreFetch release

8 November 2026, Bahrain. The founder authorized GitHub publication, asked for
automatic CoreFetch sync on future pushes, and set the exact display name to
`NXTPAPER_E-Ink-Pre-Commitment-Mode`. Preserve the existing GitHub About text,
repository address and English and Arabic catalog descriptions.

## Device and compatibility evidence

- Android reproduced a signing mismatch against the retained private beta.1
  package record. Both public APKs have the permanent public certificate.
  The matching private beta.2 test copy installed in the owner profile with the
  historical signer. The retained clone-profile data was preserved.
- The owner removed the magnetic holder. Physical Max Ink restrictions,
  software entry and restoration, and fresh guided qualification passed on
  the 70 Pro T807D/Frida AMD9. The guard stayed stopped.
- The tested report workflow included EN/AR, Arabic enlarged text, permission
  denial and restoration, Android share chooser and GitHub issue templates.
  Phone font, locale and Shizuku authorization were restored. See FINDINGS.md.
- No measured success rate exists for other models. A device needs the reviewed
  slider protocol, native Max Ink, Shizuku access and its own completed setup.

## Exact release build

- Version `1.0.6-beta.2`, code `8`. Public APK SHA256
  `a3c291cc62c7eabc9655b836d3150a0b8bb3659c695339d253a6d4fe4f465a81`.
- Permanent public signer SHA256
  `434a6ec4f84e1720f8f05e826fe2ccc0d148c47df73e561eac02d1b6f0845202`.
- 56 Android tests passed. Release lint has zero errors and 19 existing warnings.
  Verified package, exact Android label, version, flags, certificate and bundled
  controller/registry. Earlier unchanged Python suite passed 276 tests.
- Exact-name private copy is payload-identical apart from signing metadata.
  Installed in place without uninstall or data clear. Qualification remains ready.
- `dist/tester-experience-1.0.6-beta.2/` holds public APK, checksum, notes and
  verification. `dist/private-acceptance/` is private. Raw phone captures are
  ignored. Only reviewed screenshots go into the tagged Fastlane paths.

## Sync and next steps

`shizu_store.json` contains the exact name and beta.2 download URL. The workflow
checks the version, package, name and permanent signing certificate, then polls
CoreFetch for catalog and details. Indexing is owned by CoreFetch. Its current
header uses the repository slug. Fastlane titles use the shorter form for the
30-character limit. CoreFetch already showed the founder's edited beta.1 copy.

Review final screenshots, verify metadata and assets, commit reviewed source,
push the annotated release tag, publish and verify anonymous APK download, then
push the default branch so CoreFetch sees an already live URL. Verify the action
and catalog. Initial remote default HEAD was 5450f34. Saved GitHub authorization
was verified for the intended owner with push and workflow permissions. Preserve
pre-existing local history files. No tag or publication at this checkpoint.
