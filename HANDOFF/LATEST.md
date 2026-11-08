# Latest checkpoint — beta.2 published, CoreFetch sync checking

8 November 2026, Bahrain. `v1.0.6-beta.2` / code 8 is live on GitHub at tagged commit `445f361`. Its public direct download and public API copy matched APK SHA256 `a3c291cc62c7eabc9655b836d3150a0b8bb3659c695339d253a6d4fe4f465a81`. Existing repository About text and catalog descriptions match the founder's wording. The exact Android and manifest display name is NXTPAPER_E-Ink-Pre-Commitment-Mode. The GitHub repository address remains the established one.

Phone acceptance and signing-mismatch diagnosis are recorded in [the release task](tasks/corefetch-beta2-release-2026-11-08.md) and FINDINGS.md. The matching private copy is installed and qualified on the reference AMD9 phone. Public beta.1 and beta.2 share the permanent signer.

Default branch was pushed. The first automatic check hit a transient HTTP 504 from GitHub's APK download route. Corrected the checker to verify the exact same public uploaded asset through GitHub's API after a gateway/network error. Mocked failures and the real beta.2 signer/name/version check passed. The latest CoreFetch read still showed beta.1. Push the checker fix and watch the new workflow run and catalog before recording sync completion.
