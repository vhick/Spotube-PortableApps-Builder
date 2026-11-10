// Restricted test application. Runs ONLY inside an isolated TEMP fixture.
// Do not distribute as Spotube or use in a finished release.
#include <windows.h>
#include <filesystem>
#include <fstream>
#include <string>
namespace fs=std::filesystem;
std::wstring env(const wchar_t* key) {
    wchar_t value[32768]{};
    auto n=GetEnvironmentVariableW(key,value,32768);
    if(!n || n>=32768) return L"";
    return value;
}
int wmain() {
    const auto roaming=env(L"APPDATA");
    const auto host=env(L"SPOTUBE_TEST_HOST_LOCAL");
    if(roaming.empty() || host.empty())return 11;
    fs::path target=fs::path(host)/L"Spotube";
    fs::create_directories(target/L"EmptyA"/L"EmptyB");
    fs::create_directories(roaming);
    std::ofstream data(fs::path(roaming)/"portability-test.txt"); data<<"test-data\n";data.close();
    int previous=0;
    if (fs::exists(target/L"session.txt")) { std::ifstream inp(target/L"session.txt"); inp>>previous; }
    std::ofstream count(target/L"session.txt",std::ios::trunc); count<<(previous+1)<<"\n";
    return 0;
}
