# Spotube PortableApps Builder b1r2

**Independent, unofficial builder repository.** Mode: **PORTABLEAPPS ONLY** for official Windows x64 Spotube **v6+** releases. No upstream fork, local compiler, manually downloaded files or private actions needed. Upstream Spotube v6 has switched from Flutter to Compose Multiplatform; the v5 release cannot be passed to this v6 recipe.

## b1r2 fix (November 10, 2026)

Corrects the first observed GitHub Actions error `FAILED: Missing upstream AGPL license` at Spotube v6.0.0 source checkout. The actual license is present; the strict exact-prefix verification was brittle. The new validator accepts a UTF-8 BOM and leading whitespace while retaining full AGPLv3 checks and original-file redistribution. The patched code is covered by offline regression fixtures; a successful Windows build is **not yet confirmed**.

Suggested GitHub Desktop commit summary: `Fix Spotube AGPL license validation (b1r2)`.

## Quick start (GitHub Desktop)

1. On GitHub, create a **new empty repository** named e.g. `Spotube-PortableApps-Builder`. Choose **Private** if you want only yourself to see its releases, or Public if you intend to publish them. **Do not fork Spotube.**
2. Click **Code > Open with GitHub Desktop** on your new repository (or use **File > Clone repository** in GitHub Desktop). Clone it to a clean folder.
3. Open the ZIP of **this builder kit**, and extract **all** its contents into your newly cloned builder repository root. Confirm the hidden `.github/workflows/` folder exists in the repository. There must be no extra nested builder-kit directory.
4. In GitHub Desktop, write a commit summary such as `Add Spotube PortableApps builder b1r2`, click **Commit to main**, then **Push origin**. No manual `git init` or upstream fork is necessary.
5. In GitHub, select **Actions > Spotube - Build PortableApps ZIP and Installer > Run workflow**. Leave version blank for the latest supported stable official x64 installer, or specify `6.0.0`. `publish` defaults to true.
6. Read each step in Actions. If **Resolve source...**, **installer**, or **publisher** fails, inspect the first error and download the logs. The workflow does not pretend GUI tests succeeded.
7. Open **Releases** in your own builder repository and download `SpotubePortable_<version>_<commit>_b1r2.zip`, or the separately generated `*.paf.exe` installer. Verify each against the published `SHA256SUMS.txt`.
8. For ZIP, extract the entire `SpotubePortable` folder, then run **`SpotubePortable.exe`**. For installer, select a PortableApps location, install, refresh the PortableApps Platform menu and launch it there.
9. **Upgrade:** exit Spotube completely, back up the entire portable folder, then use the new installer over the existing folder (after manual installer-behavior testing), or replace the `App` and root launcher while preserving **all of `Data`**. Never wipe `Data\TraceGuard` (especially recovery manifests/backups) or replace the whole folder blindly.
10. **Rollback:** close all Spotube/tray processes; restore the last known-good binaries and matching backed-up `Data`. Newer storage schemas may make older apps incompatible, so retain a matching backup.

## What the build actually does

1. Query official GitHub releases. Select the latest *numerically* sorted stable `vX.Y.Z` with the exact Windows x64 setup asset (or requested stable version). Reject beta, nightly, invalid tags, and versions below v6.
2. Clone **only the official release tag**, record its 40-character commit SHA and its Gradle version/dependency identities. The official source is used for the genuine icon and AGPL license.
3. Download the official Windows installer from GitHub. Verify its GitHub-published SHA-256 digest, plus a locally reviewed digest pin for v6.0.0. If a future release provides neither a verified release SHA-256 digest nor a reviewed pinned digest, fail closed. No installer execution.
4. Extract the verified installer using 7-Zip on a hosted Windows runner. Detect an optional `app-64.7z` nested payload. Require exactly one `spotube.exe` (Windows x64 PE) with adjacent application resources. If upstream changes installer format, fail instead of guessing or silently running the setup EXE.
5. Compile the readable C++ `SpotubePortable.exe` with MSVC, add the authentic upstream icon, build PortableApps `appinfo.ini`, and package `App/Spotube`, `Data`, and `Other/Source`. Validate ZIP including CRC/paths and PE structures.
6. Pass **only already verified staging** to `vhick/Portable-Package-Builder@v1.0.0`, `engine: custom-nsis`. Inspect installer PE, 7-Zip payload listing and SHA-256. If installer fails, preserve the independently validated ZIP and report the workflow failure after optional ZIP release publication.
7. Call `vhick/portable-release-publisher@v1.1.1` with `dry-run: 'true'` then `dry-run: 'false'` (only if publication selected); `keep-releases: '3'`, `prune: 'false'`. Only builder-owned tags are used. Release checksums are provided by the publisher.

The builder deliberately does not run the original setup installer on your real computer or in CI. It does not use the experimental official PortableApps.com installer engine. This is an *unofficial PortableApps-style* package, not PortableApps.com-certified.

## Intended ZIP layout

```text
SpotubePortable/
  SpotubePortable.exe        (compiled C++ Windows PE x64)
  App/
    AppInfo/
      appinfo.ini
      appicon.ico
      appicon_16.png
      appicon_32.png
    Spotube/
      spotube.exe            (verified official upstream binary)
      ...                   (all original adjacent libraries/resources)
  Data/
    Roaming/
    Local/
    TraceGuard/
      Recovered/
  Other/
    Source/
      SpotubePortable.cpp
      LICENSE-Spotube.txt
      BUILD-IDENTITY.json
      SOURCE-STORAGE-CANDIDATES.json
      SOURCE-OFFER.txt
  README.txt
```

## How portability is implemented

The compiled launcher obtains its root from **its own executable**, not the working directory. It sets `APPDATA` and `LOCALAPPDATA` for its child process only, pointing to `Data\Roaming` and `Data\Local`. It passes CLI arguments, starts the official application in `App\Spotube`, and waits for its entire Windows Job process tree (including child/tray processes) before any recovery. Nothing changes the user's global environment variables, system PATH or registry.

Because Spotube v6 is a newly rewritten Compose Multiplatform application, some JNA/AppDirs or WebView operations might use Windows **Known Folder** APIs rather than those two environment variables. The launcher therefore includes a narrow, transparent candidate-folder **TraceGuard** for `Spotube` and `org.spotube.spotube` directly under user Roaming and Local AppData. These paths are *conservative candidates from app name and product ID*, **not proven exhaustive source-inspected storage paths**. It will **refuse startup if any candidate folder already exists without its own marker** rather than risk disturbing a conventionally installed Spotube profile. Completely empty directories are preserved by recursive folder copying. Files are compared byte-for-byte before owned-tree deletion; reparse points are rejected. An active transaction journal and backup folders support restart recovery.

This is a **safety-first, best-effort implementation, not proof of full portability**. The first-run recovery of a newly created host folder cannot definitively attribute a concurrent installed-app write; do not run installed Spotube alongside this portable edition. If any unexpected host state exists, the launcher errs on retaining it and reports a warning. Never manually delete host profiles or `.during-run-backup`/`.incomplete` data without examining them.

The software may still use Windows-managed files, OS media-session/notification caches, Shell integrations, Windows known folders, GPU/WebView caches, or the selected user's Downloads directory. No registry or Start Menu cleanup is done unless separately proven necessary; broad cleanup is prohibited. Native Windows notifications and activation are **not yet interactive-tested**, and disabling them merely for a cleaner trace scan is not part of this build.

## Packaging-only workflow

If upstream retrieval/build is already successful but shared installer packaging fails, fix/upgrade this *builder source* with a new builder revision as needed, then run **Actions > Spotube - Installer Only from Validated Release ZIP**. Provide the original published release tag, e.g. `portable-spotube-v6.0.0-<commit10>-b1r2`, and new installer revision `r1`. The workflow retrieves the earlier **exact ZIP and `SHA256SUMS.txt` from this same repository**, independently checks checksum, ZIP paths, binary checksums, product identity and builder revision; it never rebuilds upstream. It produces a **new** installer-only release tag with `-installer-r1` suffix so prior publications are never silently overwritten.

## Limitations that matter

- Static/builder tests can be run anywhere: `python -m unittest discover -s tests -v`. Actual upstream binary extraction and C++ compiler tests execute on hosted Windows **only once you run Actions**; GUI/tray and real Windows-storage behavior require a hands-on test.
- Does **not** support v5.1.2 Flutter binaries: they use a different installer/storage architecture. Use a separately audited v5-specific builder if needed.
- The project may refuse to start when an installed Spotube profile exists. That is deliberate host protection, **not demonstrated compatible simultaneous installed+portable operation**.
- C++ `Job` assignment fails closed if Windows or another launcher prevents tree tracking. No background process is forcibly killed on normal close.
- The upstream AGPL-3.0-or-later license applies to redistributed Spotube binaries; preserve license/source attribution and satisfy source availability obligations. Upstream logos and trademarks remain with their respective holders.
- GitHub shared actions are pinned to the *requested release tags*, not to immutable action commit SHAs. Their `action.yml` interfaces were inspected. Use immutable SHAs in a later reviewed revision if exact tag commits are verified.
- No Windows installer actual execution or installed-app coexistence has been confirmed. The custom NSIS installer may behave differently across upgrades. Perform the manual acceptance checks before depending on unattended upgrades.

Read `docs/SOURCE-AUDIT.md`, `docs/WINDOWS-TEST-PLAN.md`, and `docs/TROUBLESHOOTING.md` for source evidence, safety expectations, and recovery.

## Tagged-source candidate scan

The build also searches the **exact upstream tag checkout** for storage, AppDirs, DataStore, WebView, download, tray, process, integration and updater API references. It ships `Other/Source/SOURCE-STORAGE-CANDIDATES.json` with source paths and lines. This is a reproducible audit starting point, **not proof of exhaustive coverage**. Review the findings and Windows Process Monitor results before asserting full portability.
