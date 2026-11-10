# b1r3 – Shared custom-NSIS `running-exe` Windows path (November 10, 2026)

- Inspected uploaded GitHub Actions logs (`logs_116028650785.zip`): Spotube v6.0.0 upstream release/AGPL, official Windows package, compiled MSVC x64 launcher, independent ZIP verification and Windows synthetic launch fixture all completed successfully; the release publisher uploaded the ZIP at `portable-spotube-v6.0.0-8925b1b935-b1r2`.
- Identified exact shared-action error in `scripts/common.ps1` `Test-RelativeEXE` (from `Portable-Package-Builder@v1.0.0`): `running-exe must be a relative Windows .exe file inside the portable folder`. Prior workflows passed `App/Spotube/spotube.exe` with POSIX separators; the pinned regex permits only `\` separators in relative paths.
- Both full-build and installer-only workflows now pass `running-exe: 'App\Spotube\spotube.exe'`, preserving the actual staged app location and all pinned action versions.
- Add offline regression test ensuring both workflows use the permitted value and rejecting the previously failing slash form.
- Expand installer-only trust allowlist for validated `b1r3` builds while retaining explicit acceptance of the already-published `b1r2` ZIP. It performs **no upstream rebuild** when repairing that earlier ZIP.
- Recommended workflow: `Spotube - Installer Only from Validated Release ZIP`, `source_release_tag=portable-spotube-v6.0.0-8925b1b935-b1r2`, `installer_revision=r1`.
- Evidence: uploaded real CI logs, pinned action `common.ps1` and `build.ps1`, local static regression tests. **Installer compilation/installation and real GUI portability are not yet verified**.

# b1r2 – upstream license formatting fix (November 10, 2026)

- Fix first reported GitHub Actions failure: `FAILED: Missing upstream AGPL license` after successfully checking out `v6.0.0` at commit `8925b1b9351c3af2fd672db898d8d899badc1cb9`.
- Replace byte-exact first-character `startswith` check with UTF-8 BOM-tolerant `verify_agpl_license` validation. It accepts only harmless leading whitespace and still requires the actual complete AGPL version 3, terms and end marker; it does not disable or weaken license/provenance checks.
- Log upstream LICENSE byte count and SHA-256, preserving the original file bytes in the generated package.
- Add controlled regression tests for plain UTF-8, UTF-8 BOM, BOM plus initial whitespace, truncated text, incorrect license, and invalid UTF-8.
- Keep both pinned shared action versions and existing PORTABLEAPPS-only packaging architecture unchanged.
- The installer-only workflow recognizes checksum-validated b1r1 or b1r2 upstream ZIP build identities.
- Subsequent uploaded b1r2 GitHub Actions logs confirm this license check, official installer extraction, MSVC launcher compilation, ZIP checks, synthetic fixture, and ZIP publication succeeded. Custom NSIS installer remained blocked by incorrect running-exe input before b1r3.

# b1r1 – initial application-specific builder kit

- Mode: PORTABLEAPPS x64 only. No NATIVE branch.
- Official Spotube v6+ stable Windows installer extraction without running setup; default stable release selected using numeric semver.
- Official asset hash verification (GitHub `digest`, with a reviewed v6.0.0 pin), exact tagged upstream source and commit SHA, build provenance identity.
- MSVC compiled root executable with scoped environment, bounded evidence-candidate TraceGuard and job-based descendant shutdown.
- Preserves external pre-existing Spotube profiles by refusing ambiguous launches, not by broad cleanup.
- PortableApps structure, real official icon and licence, ZIP-first validation, pinned custom-NSIS installer, pinned release publisher.
- Two unattended GitHub Actions workflows: full build and installer-only from a previously validated published ZIP.
- Offline tests and Windows synthetic launcher fixture; separate manual Windows acceptance plan.

Known limitations: No real Spotube v6 executable built/tested in this environment; source-specific native WebView and AppDirs writes are not exhaustively identified. Actual CI, GUI/audio, notification, installer execution, installed-app coexistence and full portability tests remain unverified until run.
