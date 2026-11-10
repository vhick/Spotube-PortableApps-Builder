# Pinned shared GitHub Actions interfaces (inspected 2026-11-10)

Shared Package Builder: https://raw.githubusercontent.com/vhick/Portable-Package-Builder/v1.0.0/action.yml

| Input | Required | Used here |
|---|---|---|
| `source-dir` | yes | `staging/SpotubePortable` |
| `output-dir` | yes | `out/installers` |
| `engine` | no, default custom-nsis | `custom-nsis` |
| `running-exe` | no | `App/Spotube/spotube.exe` |
| `timeout-seconds` | no | `1200` |
| `package-revision` | no | `b1r2` (main) or installer revision |
| `official-tool-url` | only when official engine | unused |
| `official-tool-sha256` | only when official engine | unused |

Outputs: `installer-file`, `installer-sha256`, `app-id`, `app-version`.

Validated against source: `v1.0.0/scripts/build.ps1`, `v1.0.0/scripts/common.ps1`, `v1.0.0/nsis/community-installer.nsi`.

The shared NSIS source sets `RequestExecutionLevel user`, uses a standalone installer, does NOT bundle or touch `Data` on install, stages managed `App`, `Other`, root launcher, and rollback, and does not create registry entries. A path is only considered installed after actual installer execution in Windows; CI's NSIS compilation does NOT prove that execution.

Shared Release Publisher: https://raw.githubusercontent.com/vhick/portable-release-publisher/v1.1.1/action.yml

| Input | Used here |
|---|---|
| `files` | `out/*.zip;out/installers/*.paf.exe` |
| `tag` | `portable-spotube-v<VERSION>-<COMMIT10>-b1r2` or installer-only suffix |
| `release-title` | identified upstream Spotube version |
| `tag-prefix` | `portable-` |
| `keep-releases` | `3` |
| `prune` | `false` |
| `dry-run` | `true` before `false` |

The publisher uses the caller's `github.token` and `github.repository`. The workflow sets `contents: write`. No PATs, extra credentials, or private actions are needed. The publisher checks release identity and avoids overwriting different existing managed/unmanaged assets.

**Immutable SHA caveat:** the two user-selected tag versions are pinned *by requested tag*, not verified action commit SHA. The kit deliberately does not invent SHAs. They should be reviewed and pinned to immutable commits in a later revision if reproducibility against mutable tags becomes a priority.
