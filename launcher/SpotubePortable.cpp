// Spotube Portable (unofficial) - transparent Windows x64 launcher.
// Application code/binaries belong to team-spotube/spotube (AGPL-3.0-or-later).
// This launcher keeps its own filesystem operations under Data plus four narrow
// candidate external application folders. It never modifies Windows registry.
#include <windows.h>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <array>
#include <algorithm>
#include <chrono>
#include <thread>
#include <functional>
#include <stdexcept>
#include <cwctype>
namespace fs = std::filesystem;

static void alert(const std::wstring& s) {
    // CI fixtures must never depend on an interactive desktop or modal prompt.
    wchar_t flag[8]{};
    GetEnvironmentVariableW(L"SPOTUBE_PORTABLE_SILENT_ERRORS", flag, 8);
    if (wcscmp(flag,L"1")==0) { OutputDebugStringW(s.c_str()); return; }
    MessageBoxW(nullptr, s.c_str(), L"Spotube Portable", MB_OK | MB_ICONWARNING);
}
static std::wstring getenvw(const wchar_t* name) {
    DWORD size = GetEnvironmentVariableW(name, nullptr, 0);
    if (!size) return L"";
    std::wstring val(size, L'\0');
    DWORD got = GetEnvironmentVariableW(name, val.data(), size);
    if (!got || got >= size) return L"";
    val.resize(got); return val;
}
static void logline(const fs::path& file, const std::wstring& message) {
    std::wofstream log(file, std::ios::app);
    if (log) log << message << L"\n";
}
static bool same_file(const fs::path& a, const fs::path& b) {
    if (!fs::is_regular_file(a) || !fs::is_regular_file(b) || fs::file_size(a) != fs::file_size(b)) return false;
    std::ifstream x(a, std::ios::binary), y(b, std::ios::binary);
    std::array<char, 65536> ax{}, ay{};
    for (;;) {
        x.read(ax.data(), ax.size()); y.read(ay.data(), ay.size());
        if (x.gcount() != y.gcount() || !std::equal(ax.begin(), ax.begin() + x.gcount(), ay.begin())) return false;
        if (!x.gcount()) return true;
    }
}
static bool safe_tree(const fs::path& base) {
    if (!fs::exists(base)) return true;
    if (fs::is_symlink(fs::symlink_status(base)) || !fs::is_directory(base)) return false;
    for (const auto& it : fs::recursive_directory_iterator(base, fs::directory_options::none)) {
        auto st = it.symlink_status();
        if (fs::is_symlink(st) || (!fs::is_directory(st) && !fs::is_regular_file(st))) return false;
    }
    return true;
}
static bool same_tree(const fs::path& a, const fs::path& b) {
    if (!safe_tree(a) || !safe_tree(b) || !fs::is_directory(a) || !fs::is_directory(b)) return false;
    size_t countA=0, countB=0;
    for (const auto& it : fs::recursive_directory_iterator(a)) {
        ++countA;
        auto to = b / it.path().lexically_relative(a);
        if (it.is_directory() && !fs::is_directory(to)) return false;
        if (it.is_regular_file() && !same_file(it.path(),to)) return false;
    }
    for (const auto& it : fs::recursive_directory_iterator(b)) ++countB;
    return countA == countB;
}
static void copy_tree(const fs::path& src, const fs::path& dest) {
    if (!safe_tree(src)) throw std::runtime_error("Unsafe reparse point or non-regular entry");
    if (fs::exists(dest)) throw std::runtime_error("Destination already exists");
    fs::create_directories(dest);
    for (const auto& it : fs::recursive_directory_iterator(src)) {
        fs::path rel = it.path().lexically_relative(src);
        fs::path to = dest / rel;
        if (it.is_directory()) fs::create_directories(to);
        else { fs::create_directories(to.parent_path()); fs::copy_file(it.path(), to); }
    }
    for (const auto& it : fs::recursive_directory_iterator(src)) {
        fs::path to = dest / it.path().lexically_relative(src);
        if ((it.is_directory() && !fs::is_directory(to)) || (it.is_regular_file() && !same_file(it.path(), to)))
            throw std::runtime_error("Post-copy verification failed");
    }
}
struct Watch { fs::path host, saved; std::wstring name; };
static std::wstring lower(std::wstring s) { for (auto& ch : s) ch = (wchar_t)towlower(ch); return s; }
static std::wstring command_line_arg(const std::wstring& arg) {
    // Exact Windows CommandLineToArgvW escaping; works with spaces, Unicode and trailing slash.
    if (arg.find_first_of(L" \t\"") == std::wstring::npos) return arg;
    std::wstring out = L"\"";
    unsigned slashes=0;
    for (wchar_t c : arg) {
        if (c == L'\\') { ++slashes; continue; }
        if (c == L'"') { out.append(slashes*2 + 1, L'\\'); out += L'"'; slashes=0; continue; }
        out.append(slashes, L'\\'); slashes=0; out += c;
    }
    out.append(slashes*2, L'\\'); out += L'"'; return out;
}
static bool marker_ok(const fs::path& path, const std::wstring& owner) {
    std::wifstream f(path / L".spotube-portable-owner");
    std::wstring read; std::getline(f, read);
    return read == owner;
}
static std::wstring root_id(const fs::path& root) {
    // identity is root-independent: moving the drive/folder must not break recovery.
    // No installed application uses this private marker format.
    return L"SpotubePortable-unofficial-b1";
}
static void capture_one(const Watch& w, const std::wstring& owner, const fs::path& log, bool was_restored) {
    if (!fs::exists(w.host)) return;
    if (!safe_tree(w.host)) { logline(log, L"PRESERVED unsafe host tree: " + w.host.wstring()); return; }
    if (was_restored && !marker_ok(w.host, owner)) {
        logline(log, L"PRESERVED host tree: portable ownership marker missing or changed: " + w.host.wstring()); return;
    }
    if (fs::exists(w.saved)) {
        logline(log, L"PRESERVED host tree: existing recovery data must not be overwritten: " + w.host.wstring()); return;
    }
    try {
        fs::path temp = w.saved.parent_path() / (w.saved.filename().wstring() + L".incomplete");
        if (fs::exists(temp)) { logline(log, L"PRESERVED: unfinished staging exists: " + temp.wstring()); return; }
        copy_tree(w.host, temp);
        fs::rename(temp, w.saved);
        // A new file or concurrent edit after initial copy is ambiguous. Leave BOTH copies.
        if (!same_tree(w.host,w.saved)) {
            logline(log,L"PRESERVED host: post-copy tree changed or no longer matches"); return;
        }
        fs::remove_all(w.host);
        logline(log, L"RECOVERED " + w.name);
    } catch (const std::exception&) {
        logline(log, L"PRESERVED host tree: copy/verify/remove error: " + w.host.wstring());
    }
}
static int main_launcher(const wchar_t* parameters) {
    wchar_t file[32768]; DWORD n = GetModuleFileNameW(nullptr, file, 32768);
    if (!n || n >= 32768) { alert(L"Cannot determine portable executable folder"); return 1; }
    fs::path root = fs::path(std::wstring(file, n)).parent_path();
    fs::path exe = root / L"App" / L"Spotube" / L"spotube.exe";
    if (!fs::is_regular_file(exe)) { alert(L"Missing App\\Spotube\\spotube.exe. Re-extract the complete ZIP."); return 2; }
    fs::path data = root / L"Data";
    fs::create_directories(data / L"Roaming"); fs::create_directories(data / L"Local");
    fs::create_directories(data / L"TraceGuard" / L"Recovered");
    fs::path log = data / L"TraceGuard" / L"launcher.log";
    fs::path active = data / L"TraceGuard" / L"active.txt";
    const std::wstring owner = root_id(root);
    std::wstring hostRoaming = getenvw(L"APPDATA"), hostLocal = getenvw(L"LOCALAPPDATA");
    if (hostRoaming.empty() || hostLocal.empty()) { alert(L"Windows APPDATA and LOCALAPPDATA are unavailable."); return 3; }
    // Conservative watch list: matches product bundle id and display name only.
    // NO shared parent trees, registry keys, generic caches or TEMP are touched.
    std::vector<Watch> watches = {
      {fs::path(hostRoaming)/L"org.spotube.spotube",data/L"TraceGuard"/L"Recovered"/L"Roaming_org.spotube.spotube",L"Roaming/product-id"},
      {fs::path(hostLocal)/L"org.spotube.spotube",data/L"TraceGuard"/L"Recovered"/L"Local_org.spotube.spotube",L"Local/product-id"},
      {fs::path(hostRoaming)/L"Spotube",data/L"TraceGuard"/L"Recovered"/L"Roaming_Spotube",L"Roaming/display-name"},
      {fs::path(hostLocal)/L"Spotube",data/L"TraceGuard"/L"Recovered"/L"Local_Spotube",L"Local/display-name"},
    };
    HANDLE mutex = CreateMutexW(nullptr, TRUE, L"Local\\SpotubePortableUnofficial_2026_Launch");
    if (!mutex || GetLastError() == ERROR_ALREADY_EXISTS) {
        if (mutex) CloseHandle(mutex);
        alert(L"Another Spotube Portable instance may be active. Close it first."); return 4;
    }
    auto unlock = [&](){ ReleaseMutex(mutex); CloseHandle(mutex); };
    bool previous_active = fs::exists(active);
    if (previous_active) logline(log, L"Previous launch may have ended unexpectedly; examining owned recovery paths.");
    // Do not interfere with a normal installed Spotube or any pre-existing host profile.
    for (const auto& w : watches) {
        if (fs::exists(w.host) && !marker_ok(w.host, owner)) {
            logline(log, L"BLOCKED: pre-existing or ambiguous host profile: " + w.host.wstring());
            unlock(); alert(L"A conventional Spotube profile or unowned Spotube folder exists in Windows AppData.\n"
                L"To protect it, this portable launcher did not start. See Data\\TraceGuard\\launcher.log.\n"
                L"Do not delete or move your installed application's data to bypass this check."); return 5;
        }
    }
    // An interrupted run may have a backup plus an owned host directory.
    if (previous_active) {
        for (const auto& w : watches) {
            fs::path backup=w.saved.parent_path()/(w.saved.filename().wstring()+L".during-run-backup");
            if (fs::exists(w.host) && marker_ok(w.host,owner)) {
                capture_one(w,owner,log,true);
                if (!fs::exists(w.host) && fs::exists(backup) && fs::exists(w.saved)) fs::remove_all(backup);
            } else if (!fs::exists(w.host) && fs::exists(backup) && !fs::exists(w.saved)) {
                fs::rename(backup,w.saved);
            }
        }
        for (const auto& w : watches) {
            fs::path backup=w.saved.parent_path()/(w.saved.filename().wstring()+L".during-run-backup");
            if (fs::exists(w.host) || fs::exists(backup)) {
                unlock(); alert(L"Unfinished recovery needs manual review. Host files were preserved; see TraceGuard log."); return 6;
            }
        }
        fs::remove(active);
    }
    // Restore only our own previously recovered app-specific folders; never overwrite host data.
    for (const auto& w : watches) {
        if (!fs::exists(w.saved)) continue;
        try {
            if (!safe_tree(w.saved)) throw std::runtime_error("Unsafe saved directory");
            copy_tree(w.saved, w.host);
            std::wofstream marker(w.host/L".spotube-portable-owner",std::ios::trunc);
            marker << owner << L"\n"; marker.close();
            if (!marker_ok(w.host,owner)) throw std::runtime_error("Marker verify failed");
            // Move recovery copy out of the way only AFTER verify; keep backup on disk for crash recovery.
            fs::path backup = w.saved.parent_path() / (w.saved.filename().wstring()+L".during-run-backup");
            if (fs::exists(backup)) throw std::runtime_error("Old backup exists");
            fs::rename(w.saved, backup);
        } catch (const std::exception&) {
            logline(log,L"BLOCKED: recovery restore failed: " + w.name); unlock();
            alert(L"Recovery restore failed; no application process started. See TraceGuard log."); return 7;
        }
    }
    // In the child only: environment-based paths go straight to Data. No global environment edits.
    SetEnvironmentVariableW(L"APPDATA",(data/L"Roaming").c_str());
    SetEnvironmentVariableW(L"LOCALAPPDATA",(data/L"Local").c_str());
    std::wofstream transaction(active,std::ios::trunc);
    transaction << L"SpotubePortable-unofficial\n"; transaction.close();
    std::wstring cmd = command_line_arg(exe.wstring());
    if (parameters && *parameters) { cmd += L" "; cmd += parameters; }
    STARTUPINFOW si{}; si.cb=sizeof(si); PROCESS_INFORMATION pi{};
    std::vector<wchar_t> mutableCmd(cmd.begin(),cmd.end()); mutableCmd.push_back(L'\0');
    HANDLE job=CreateJobObjectW(nullptr,nullptr);
    if (!job) { logline(log,L"Job object creation failed"); unlock(); return 8; }
    // Job tracks descendants, but never force-kills user processes on launcher close.
    BOOL started=CreateProcessW(exe.c_str(),mutableCmd.data(),nullptr,nullptr,FALSE,
          CREATE_SUSPENDED|CREATE_UNICODE_ENVIRONMENT,nullptr,exe.parent_path().c_str(),&si,&pi);
    if (!started) {
        logline(log,L"CreateProcess failed: " + std::to_wstring(GetLastError()));
        CloseHandle(job); unlock(); alert(L"Spotube failed to start. Recovery journal is retained. See launcher.log."); return 9;
    }
    if (!AssignProcessToJobObject(job,pi.hProcess)) {
        logline(log,L"Cannot track descendant lifecycle; aborting to avoid premature recovery.");
        TerminateProcess(pi.hProcess,1); CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
        CloseHandle(job); unlock(); alert(L"Cannot track Spotube process tree. No cleanup attempted."); return 10;
    }
    ResumeThread(pi.hThread); CloseHandle(pi.hThread);
    WaitForSingleObject(pi.hProcess,INFINITE);
    // Retain job handle while child processes (tray/webview) are active.
    JOBOBJECT_BASIC_ACCOUNTING_INFORMATION info{};
    for (;;) {
        if (!QueryInformationJobObject(job,JobObjectBasicAccountingInformation,&info,sizeof(info),nullptr)) {
            logline(log,L"Cannot verify descendants stopped. Preserving host data, no cleanup.");
            CloseHandle(pi.hProcess); CloseHandle(job); unlock(); return 11;
        }
        if (info.ActiveProcesses==0) break;
        std::this_thread::sleep_for(std::chrono::milliseconds(400));
    }
    DWORD exitCode=0; GetExitCodeProcess(pi.hProcess,&exitCode);
    CloseHandle(pi.hProcess); CloseHandle(job);
    // A previously restored tree has a verified private marker. A first-run newly created
    // tree is attributable only when absent before launch: record conservatively.
    for (const auto& w : watches) {
        fs::path backup=w.saved.parent_path()/(w.saved.filename().wstring()+L".during-run-backup");
        bool restored=fs::exists(backup);
        if (restored && fs::exists(w.saved)) {
            logline(log,L"PRESERVED: recovery collision: " + w.name); continue;
        }
        if (restored) {
            if (!fs::exists(w.host)) { fs::rename(backup,w.saved); continue; }
            // Recovery backup stays in place until the new host tree is copied and verified.
            capture_one(w,owner,log,true);
            if (!fs::exists(w.host) && fs::exists(w.saved)) fs::remove_all(backup);
            else logline(log,L"PRESERVED old backup and host for manual reconciliation: "+w.name);
            continue;
        }
        capture_one(w,owner,log,false);
    }
    // Fail closed when any candidate host folders persist: leave journal for recovery.
    bool dirty=false;
    for (const auto& w:watches) {
        fs::path backup=w.saved.parent_path()/(w.saved.filename().wstring()+L".during-run-backup");
        if(fs::exists(w.host) || fs::exists(backup)) dirty=true;
    }
    if(!dirty) fs::remove(active);
    else logline(log,L"WARNING: host directories retained. Manual review needed before restart.");
    unlock();
    if(dirty) { alert(L"Some Spotube host data could not be safely recovered; files were preserved. See Data\\TraceGuard\\launcher.log."); return 12; }
    return (int)exitCode;
}
int WINAPI wWinMain(HINSTANCE,HINSTANCE,LPWSTR args,int) {
    try { return main_launcher(args); }
    catch (const std::exception&) { alert(L"Launcher encountered a safe-stop exception. Host files were not deliberately removed."); return 99; }
}
