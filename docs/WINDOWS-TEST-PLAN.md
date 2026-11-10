# Windows manual acceptance checklist (not performed by this kit's author)

**Use a disposable Windows 10/11 test VM with a snapshot.** Do not assume a successful Actions build means the Spotube v6 GUI, login or runtime state is portable. Use Process Monitor/Process Explorer as an auditor, not as a component of the distributed launcher. Close the installed Spotube before portable tests.

## Before first launch

1. Download your builder repository's release ZIP and verify SHA-256 against `SHA256SUMS.txt`. Extract `SpotubePortable` into a disposable drive/folder with a space and Unicode character.
2. Take a fresh **baseline snapshot** of `%APPDATA%`, `%LOCALAPPDATA%`, `%USERPROFILE%`, Downloads, Documents, Desktop, `%PROGRAMDATA%`, `%TEMP%`, HKCU relevant keys, Start Menu shortcuts and recent shell state. Do not wipe any existing profile.
3. Check that `SpotubePortable.exe` is the root binary and `App\Spotube\spotube.exe` is genuine, both Windows x64 PE. Confirm adjacent DLLs/resources and source/AGPL license.
4. On a different VM with conventional Spotube installed, verify that ambiguous pre-existing `Spotube` / `org.spotube.spotube` profile candidates are protected and the portable launcher refuses unsafe coexistence without moving or deleting anything.

## Runtime

5. Launch root `SpotubePortable.exe` directly, not `App\Spotube\spotube.exe`, on Windows 10 and Windows 11. Check opening UI, source/plugin selection, browsing, seeking, playback, pause, queue, lyrics, settings, login and optional downloading.
6. Verify settings, plugin data, login/session, cookies/WebView state, cache and downloads persist after quitting and reopening. Note intended user downloads outside Data; they should not be harvested without permission.
7. Check tray-close behavior. Fully exit from tray, allow child processes to stop, and confirm the portable launcher eventually exits. Do not force-quit while backups are active.
8. Compare before/during/after changes. Investigate the exact source of any new Spotube-owned files in Roaming, Local, LocalLow, ProgramData and profile root; also check WebView2/Windows WebView and VLC caches. Confirm `Data\Roaming`, `Data\Local`, `Data\TraceGuard\Recovered` contain intended persistent state. Check completely empty directories and nested empty directory trees.
9. Verify built-in notifications and click-to-open. Record any Start Menu shortcuts, CLSID/AUMID, URL protocols or registry writes with ownership evidence. **Do not delete preexisting entries to make a trace scan pass**.
10. Verify no uncontrolled original Spotube update/install startup, elevation, setup wizard, firewall/driver/service registration or unrelated host mutation was triggered by the extracted application.

## Safety and failure behavior

11. Relocate the entire portable folder to a different drive letter/path. Confirm settings and login remain usable, and inspect persisted absolute paths for legitimate user files.
12. Repeat from an arbitrary working directory with command-line arguments. Confirm the root launcher still resolves relative resources correctly.
13. Test a **separate disposable fixture** with prior host-owned files and nested empty directories; confirm refusal/retention, exact backup verification and no deletion of unrelated files.
14. Terminate the launcher/app in a disposable VM at several points to test interrupted transactions, then review `Data\TraceGuard\active.txt`, `.during-run-backup` and `.incomplete` directories. Retry only after verifying ownership. An unmarked first-run host directory **may require manual review**; automatic deletion would be unsafe.
15. Try locked files/junctions in the watched paths (in an isolated VM); ensure launch/recovery fails closed and keeps data rather than following links or silently dropping files.
16. Test installed Spotube after portable launch: user settings and installed shortcuts, services and registry must remain unchanged. Simultaneous installed/portable operation is **not claimed supported**.

## Installer (separate from ZIP)

17. Run the **custom-NSIS** `.paf.exe` installer on a disposable VM; confirm the destination is a new `SpotubePortable` folder and metadata/icon/launcher remain correct. This is NOT the official PortableApps.com Installer.
18. Check installer-only changes before launching the app. Confirm no unexpected shortcuts, registry edits or auto-start. Validate actual installer user behavior; 7-Zip listing and PE header alone are insufficient.
19. Write settings through the portable app, then run a later build's installer **over the same folder**. Confirm **Data** (including empty directories/recovery state/backups) is unchanged, obsolete managed App/Other files are replaced, and rollback occurs on simulated failure.
20. Check PortableApps Platform recognition/menu refresh, first run, repeated launch and proper exit after upgrade.

## Report results independently

Record for each item: `SOURCE-INSPECTED`, `STATIC-VALIDATED`, `WINDOWS-COMPILED`, `AUTOMATED-RUNTIME-TESTED`, `MANUAL-WINDOWS-TESTED`, `USER-CONFIRMED`, `NOT YET VERIFIED`, or `FAILED/BLOCKED`. Also capture version, upstream commit, exact package file SHA-256 and VM snapshot identifier. If any persistent host path is not under a verified rule, treat full portability as **NOT YET VERIFIED**, even if playback succeeds.
