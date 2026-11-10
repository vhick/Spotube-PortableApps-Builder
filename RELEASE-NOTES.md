# b1r2 – upstream license formatting fix (November 10, 2026)

- Fix first reported GitHub Actions failure: `FAILED: Missing upstream AGPL license` after successfully checking out `v6.0.0` at commit `8925b1b9351c3af2fd672db898d8d899badc1cb9`.
- Replace byte-exact first-character `startswith` check with UTF-8 BOM-tolerant `verify_agpl_license` validation. It accepts only harmless leading whitespace and still requires the actual complete AGPL version 3, terms and end marker; it does not disable or weaken license/provenance checks.
- Log upstream LICENSE byte count and SHA-256, preserving the original file bytes in the generated package.
- Add controlled regression tests for plain UTF-8, UTF-8 BOM, BOM plus initial whitespace, truncated text, incorrect license, and invalid UTF-8.
- Keep both pinned shared action versions and existing PORTABLEAPPS-only packaging architecture unchanged.
- The installer-only workflow recognizes checksum-validated b1r1 or b1r2 upstream ZIP build identities.
- Evidence: inspected user GitHub Actions logs; offline regression suite. Windows build, installer extraction, runtime/GUI and release publication remain unverified until a new GitHub run.

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
