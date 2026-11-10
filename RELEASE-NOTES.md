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
