# Spotube upstream audit and verification status (2026-11-10)

Upstream: https://github.com/team-spotube/spotube

**Mode:** PORTABLEAPPS. The v6.0.0 official Windows x64 `Spotube-windows-x86_64-setup.exe` is a setup package, not proof of native portability. Unlike NATIVE, PORTABLEAPPS permits using verified official release binaries, so the builder extracts the official setup *without running it*, then adds a compiled portable launcher. This avoids a high-memory Gradle/GraalVM/Rust native-image rebuild on a GitHub Free runner.

**Source-inspected evidence:**
- `v6.0.0/composeApp/build.gradle.kts`: `val bundleId = "org.spotube.spotube"`; `val version = "6.0.0"`; `windows { iconFile.set(project.file("$desktopIconDir/icon.ico")); shortcut=true; menu=true; perUserInstall=true; }`.
- `v6.0.0/.github/workflows/spotube-release-binary.yml`: official Windows CI builds `:composeApp:packageGraalvmExe`, names artifact `Spotube-windows-x86_64-setup.exe`. The Windows build uses JDK 21, Rust, MSVC and GraalVM; upstream webview is prepared from a separately pinned source commit.
- `v6.0.0/composeApp/build.gradle.kts`: Windows/macOS bundle VLC; desktop native image `spotube` plus adjacent runtime resources/libraries; licence `../LICENSE`.
- `v6.0.0/gradle/libs.versions.toml`: Kotlin/Compose, JNA, AppDirs, vlcj, Zipline, native webview dependencies. Dependencies with framework-defined storage and OS integration require runtime validation.
- `v6.0.0/LICENSE`: GNU Affero General Public License v3 (or later as described by source headers).
- Official release expanded assets `v6.0.0`: `Spotube-windows-x86_64-setup.exe` SHA-256 `d7e073ead0707fcdfcc50074e88721b7df38dc10248eadafc346867e156c6e8d`.
- Last Flutter stable `v5.1.2` has its own `pubspec.yaml`, installer and `.nupkg`; **not compatible** with this launcher without a different audit.

Source references:
- https://github.com/team-spotube/spotube/releases/expanded_assets/v6.0.0
- https://raw.githubusercontent.com/team-spotube/spotube/v6.0.0/composeApp/build.gradle.kts
- https://raw.githubusercontent.com/team-spotube/spotube/v6.0.0/.github/workflows/spotube-release-binary.yml
- https://raw.githubusercontent.com/team-spotube/spotube/v6.0.0/gradle/libs.versions.toml
- https://raw.githubusercontent.com/team-spotube/spotube/v6.0.0/LICENSE

**Shared actions audited**:
- `vhick/Portable-Package-Builder@v1.0.0/action.yml` uses `source-dir`, `output-dir`, `engine`, `running-exe`, `timeout-seconds`, `package-revision`; outputs `installer-file`, `installer-sha256`, `app-id`, `app-version`. The script `scripts/build.ps1` verifies PE and archive and emits a checksum. It uses a separate installer output folder. The pinned action may install NSIS via Chocolatey.
- `vhick/portable-release-publisher@v1.1.1/action.yml` uses `files`, `tag`, `release-title`, `tag-prefix`, `keep-releases`, `prune`, `dry-run`. Its script checks ZIP/PE, SHA256SUMS, detects duplicate owned tags, and protects unrelated existing releases.
- Tags were examined, but exact immutable action SHAs were **not** independently confirmed in this kit.

## Mode-specific findings table

| Finding | Evidence label / source | Exact path or Windows integration | Responsible component | NATIVE remedy (not selected) | PORTABLEAPPS remedy | Safety / functionality / test / limitation |
|---|---|---|---|---|---|---|
| UI framework changed | SOURCE-INSPECTED Gradle + release notes | Installed EXE + adjacent DLLs | Compose/GraalVM | Requires source-level path patch | Extract verified official setup; retain all adjacent files | No GUI test in builder environment; Windows acceptance required |
| App identification | SOURCE-INSPECTED `build.gradle.kts` | Bundle ID `org.spotube.spotube` | Spotube | App source-level data root | Watch the ID-named Roaming/Local folders as *inferred candidates*, not proven paths | Any pre-existing unowned directory blocks startup, protecting installed profile |
| Roaming/local storage | INFERRED from AppDirs/JNA dependencies, not runtime-proven | Child `%APPDATA%`, `%LOCALAPPDATA%` | Spotube/third-party library | Source-level custom storage resolution | Scoped child environment to Data folders; bounded candidate TraceGuard | Known-folder API can bypass environment; validate with ProcMon manually |
| Downloads | INFERRED user actions | User-selected Downloads path | Spotube user action | Explicit user choice | Preserve user's chosen output location, do not harvest | Not inherently an unwanted trace; check resulting path in manual test |
| Native WebView | SOURCE-INSPECTED dependency and upstream WebView-native preparation | WebView data/cookies/cache locations **not yet established** | ComposeNativeWebview/Windows WebView | Source-level WebView path control | Child environment only until actual source/runtime path established | Not proven portable. Do not broadly move Edge/Windows caches |
| VLC/player children | SOURCE-INSPECTED bundler and dependencies | Adjacent VLC library resources, child process lifecycle | vlcj/Spotube | Embedded runtime and shutdown logic | Keep upstream payload; use Job object to wait for child processes | Real tray/audio shutdown not tested |
| Installed shortcuts | SOURCE-INSPECTED `windows { shortcut=true; menu=true }` | Start Menu/installer registration when upstream setup is **executed** | Upstream installer | Don't create installer entries | **Do not execute upstream installer**, extract files only | Installer-generated state excluded; live app shell writes still untested |
| Notifications/protocols | INFERRED from desktop runtime | AUMID, toasts, COM/shortcut registration not proven | Framework/Windows | Source adaptation if needed | No destructive ShellGuard without evidence | Manual toast/click-to-open and shell before/after required |
| Registry and services | NOT YET VERIFIED | No proved app-owned registry paths | Spotube/dependencies/Windows | Source audit needed | No speculative registry mutations | Do not assert zero registry/shell traces |
| Crash recovery | STATIC-VALIDATED launcher design only | `Data/TraceGuard` and narrow candidate folders | Launcher | Not applicable | Transaction marker, staging, verified recursive backups | Interrupted first-run with unmarked external folder is **blocked** until manual review |

## Validation evidence and honest claims

- SOURCE-INSPECTED: repository build definitions, release asset manifest, pinned action definitions, licensing.
- STATIC-VALIDATED: Python and C++ source-level structure; offline test fixtures and archive validator scripts.
- WINDOWS-COMPILED: **NOT YET VERIFIED** (requires your GitHub Actions run).
- AUTOMATED-RUNTIME-TESTED: **NOT YET VERIFIED** for launcher and real app.
- MANUAL-WINDOWS-TESTED: **NOT YET VERIFIED** for GUI/tray/audio/login/notifications, residual host state or installer behavior.
- USER-CONFIRMED: **NOT YET VERIFIED**.

The builder's ZIP packaging and action wiring are designed but are not evidence that this v6 Compose runtime stays wholly within `Data`. Real Windows manual testing is mandatory to establish this.
