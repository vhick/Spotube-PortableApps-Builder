# Troubleshooting, upgrade and rollback

## GitHub Actions build

**No suitable release asset:** only official, stable `vX.Y.Z` releases with `Spotube-windows-x86_64-setup.exe` are supported. The source-backed recipe requires v6 or newer. Don't silently use a beta, source from main or a Flutter-era v5 setup.

**GitHub API fails 401/403/429/5xx:** inspect token permissions, rate limit, and GitHub availability. Only an expected 404 for explicitly requested release is handled as not found. Never treat authentication/rate-limit errors as an unpublished release.

**Checksum mismatch:** stop. Do not run or repackage the installer. Confirm GitHub's release digest / reviewed v6 pin. Do not disable the checksum test.

**Can't unpack official setup:** Spotube's upstream installer layout may have changed. The builder expects one x64 `spotube.exe` and nearby libraries after 7-Zip extraction (possibly inside `app-64.7z`). Inspect build logs and adjust only after source/installer audit. Do not run upstream setup to 'extract' a portable binary.

**Icon missing:** v6 desktop icon path comes from upstream `composeApp/build.gradle.kts`: `composeApp/icons/stable/icon.ico`. When upstream changes path, review Gradle and update the kit with a new builder revision.

**MSVC compile fails:** inspect the initial `rc.exe` or `cl.exe` error. Windows Desktop C++ tools are selected via `ilammy/msvc-dev-cmd@v1`. Do not replace root launcher with CMD or rename a script `.exe`.

**Installer failure but ZIP passed:** the main workflow deliberately keeps and may publish the validated ZIP, then returns a failure. Fix the cause; use `Spotube - Installer Only from Validated Release ZIP` with the original release tag. Its release tag is separate; do not overwrite an unrelated release.

**Publisher refuses duplicate tag:** it deliberately guards against different bits for the same release identity. Bump builder revision if source/launcher behavior changed. A matching existing release is skipped safely; an unrelated tag is not replaced.

## Portable run

**Conventional Spotube profile detected:** the launcher refuses to touch it. This protects installed application data but means simultaneous coexistence is not supported. Do **not** delete the installed profile, registry entries or shortcuts to bypass the safety check. Test on a separate clean Windows account/VM if desired.

**'Another Spotube Portable instance':** close the previous portable application, including tray/background children, before attempting again. The app's normal update/upgrade procedure must not race the running launcher.

**Portability data saved unexpectedly in AppData:** capture exact paths and parent process from Process Monitor before extending TraceGuard. Some Kotlin/JNA/WebView native calls may ignore child APPDATA/LOCALAPPDATA. Never add a generic sweep of `%APPDATA%`, `%LOCALAPPDATA%`, `%TEMP%`, ProgramData, Edge/WebView, Desktop or registry trees.

**TraceGuard interrupted or failed:** inspect `Data\TraceGuard\launcher.log`, `active.txt`, `Recovered\...`, `.during-run-backup` and `.incomplete`. Do not remove source host files or incomplete recovery backups. Reconcile with a verified manual copy, keeping both versions until fingerprinted/byte-compared. Reparse points, conflicting files and changed host profiles must remain untouched.

**Drive movement:** portable local Data usually moves with the root folder; user-chosen downloads and some third-party plugin paths may retain absolute paths. Repair them from within the app after backing up settings. Never silently rewrite unrelated paths or Windows shortcuts.

**Unexpected toast shortcut/registry entry:** attribute it first to the upstream application, its Compose/JNA framework, third-party WebView, Windows shell, or the *custom* installer. Do not apply Electron-only `setAppUserModelId`/`setToastActivatorCLSID` assumptions to this Compose version.

## Preserving data during upgrades

With the app closed, copy the **entire portable folder** as a backup. The pinned custom NSIS script builds a new `App`, `Other` and root launcher transactionally; it deliberately does not bundle/replace `Data`. If NSIS reports `.__UPB_Stage` or `.__UPB_Backup` leftovers, inspect those carefully. Never wipe `Data`, `Data\TraceGuard`, nested empty folders, recovered files or partially completed recovery files.

For manual ZIP upgrades, copy `App/`, `Other/` and `SpotubePortable.exe` over a backed-up folder only while all processes are stopped, preserving `Data/` exactly. Rollback may require restoring BOTH previous app binaries and their matching Data snapshot because application data schemas can migrate.
