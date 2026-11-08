#pragma once
#include "client_version.h"
#include "online.h"
#include <bcrypt.h>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <vector>

namespace client_update {
enum class Result { Current, Available, Restart, Failed };
struct Status {
    Result result;
    std::string message;
    std::string file;
    std::string sha256;
    std::string notes;
    std::string version_name;
};

inline std::wstring Widen(const std::string& text) {
    if (text.empty()) return {};
    const int count = MultiByteToWideChar(CP_UTF8, 0, text.data(), static_cast<int>(text.size()), nullptr, 0);
    std::wstring out(count > 0 ? count : 0, L'\0');
    if (count > 0) MultiByteToWideChar(CP_UTF8, 0, text.data(), static_cast<int>(text.size()), out.data(), count);
    return out;
}

inline std::string Hex(const unsigned char* data, size_t size) {
    std::string out(size * 2, '0');
    for (size_t i = 0; i < size; ++i) {
        static const char digits[] = "0123456789abcdef";
        out[i * 2] = digits[data[i] >> 4];
        out[i * 2 + 1] = digits[data[i] & 15];
    }
    return out;
}

inline std::string FileSha256(const std::filesystem::path& path) {
    BCRYPT_ALG_HANDLE algorithm = nullptr;
    BCRYPT_HASH_HANDLE hash = nullptr;
    if (BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0) != 0)
        throw std::runtime_error("업데이트 파일 검증을 시작하지 못했습니다.");
    DWORD length = 0, written = 0;
    if (BCryptGetProperty(algorithm, BCRYPT_HASH_LENGTH, reinterpret_cast<PUCHAR>(&length), sizeof(length), &written, 0) != 0 ||
        BCryptCreateHash(algorithm, &hash, nullptr, 0, nullptr, 0, 0) != 0) {
        BCryptCloseAlgorithmProvider(algorithm, 0);
        throw std::runtime_error("업데이트 파일 검증을 시작하지 못했습니다.");
    }
    std::ifstream input(path, std::ios::binary);
    std::vector<char> buffer(65536);
    while (input) {
        input.read(buffer.data(), static_cast<std::streamsize>(buffer.size()));
        if (input.gcount() > 0 && BCryptHashData(hash, reinterpret_cast<PUCHAR>(buffer.data()), static_cast<ULONG>(input.gcount()), 0) != 0) {
            BCryptDestroyHash(hash);
            BCryptCloseAlgorithmProvider(algorithm, 0);
            throw std::runtime_error("업데이트 파일 검증에 실패했습니다.");
        }
    }
    std::vector<unsigned char> digest(length);
    const auto finish = BCryptFinishHash(hash, digest.data(), length, 0);
    BCryptDestroyHash(hash);
    BCryptCloseAlgorithmProvider(algorithm, 0);
    if (finish != 0) throw std::runtime_error("업데이트 파일 검증에 실패했습니다.");
    return Hex(digest.data(), digest.size());
}

inline std::string GetText(const std::wstring& route, int max_bytes) {
    online::Handle session{WinHttpOpen(L"Rift Manager", WINHTTP_ACCESS_TYPE_AUTOMATIC_PROXY,
                                        WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0)};
    if (!session.value) throw std::runtime_error("업데이트 서버에 연결할 수 없습니다.");
    WinHttpSetTimeouts(session.value, 4000, 4000, 8000, 8000);
    online::Handle connection{WinHttpConnect(session.value, online::host.c_str(), online::port, 0)};
    if (!connection.value) throw std::runtime_error("업데이트 서버에 연결할 수 없습니다.");
    const auto path = online::prefix + route;
    online::Handle request{WinHttpOpenRequest(connection.value, L"GET", path.c_str(), nullptr, WINHTTP_NO_REFERER,
                                               WINHTTP_DEFAULT_ACCEPT_TYPES, online::secure ? WINHTTP_FLAG_SECURE : 0)};
    if (!request.value) throw std::runtime_error("업데이트 요청을 시작하지 못했습니다.");
    DWORD disabled = WINHTTP_DISABLE_REDIRECTS;
    if (!WinHttpSetOption(request.value, WINHTTP_OPTION_DISABLE_FEATURE, &disabled, sizeof(disabled)) ||
        !WinHttpSendRequest(request.value, WINHTTP_NO_ADDITIONAL_HEADERS, 0, WINHTTP_NO_REQUEST_DATA, 0, 0, 0) ||
        !WinHttpReceiveResponse(request.value, nullptr))
        throw std::runtime_error("업데이트 서버에 연결할 수 없습니다.");
    DWORD status = 0, size = sizeof(status);
    if (!WinHttpQueryHeaders(request.value, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
                             WINHTTP_HEADER_NAME_BY_INDEX, &status, &size, WINHTTP_NO_HEADER_INDEX) || status != 200)
        throw std::runtime_error("업데이트 정보를 찾지 못했습니다.");
    std::string body;
    char buffer[4096];
    DWORD count = 0;
    do {
        if (!WinHttpReadData(request.value, buffer, sizeof(buffer), &count) || body.size() + count > static_cast<size_t>(max_bytes))
            throw std::runtime_error("업데이트 정보가 올바르지 않습니다.");
        body.append(buffer, count);
    } while (count);
    return body;
}

inline void DownloadFile(const std::wstring& route, const std::filesystem::path& destination, const std::string& expected, std::uint64_t max_bytes) {
    online::Handle session{WinHttpOpen(L"Rift Manager", WINHTTP_ACCESS_TYPE_AUTOMATIC_PROXY,
                                        WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0)};
    if (!session.value) throw std::runtime_error("업데이트 서버에 연결할 수 없습니다.");
    WinHttpSetTimeouts(session.value, 8000, 8000, 20000, 60000);
    online::Handle connection{WinHttpConnect(session.value, online::host.c_str(), online::port, 0)};
    if (!connection.value) throw std::runtime_error("업데이트 서버에 연결할 수 없습니다.");
    const auto path = online::prefix + route;
    online::Handle request{WinHttpOpenRequest(connection.value, L"GET", path.c_str(), nullptr, WINHTTP_NO_REFERER,
                                               WINHTTP_DEFAULT_ACCEPT_TYPES, online::secure ? WINHTTP_FLAG_SECURE : 0)};
    if (!request.value) throw std::runtime_error("업데이트 요청을 시작하지 못했습니다.");
    DWORD disabled = WINHTTP_DISABLE_REDIRECTS;
    if (!WinHttpSetOption(request.value, WINHTTP_OPTION_DISABLE_FEATURE, &disabled, sizeof(disabled)) ||
        !WinHttpSendRequest(request.value, WINHTTP_NO_ADDITIONAL_HEADERS, 0, WINHTTP_NO_REQUEST_DATA, 0, 0, 0) ||
        !WinHttpReceiveResponse(request.value, nullptr))
        throw std::runtime_error("업데이트 서버에 연결할 수 없습니다.");
    DWORD status = 0, size = sizeof(status);
    if (!WinHttpQueryHeaders(request.value, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
                             WINHTTP_HEADER_NAME_BY_INDEX, &status, &size, WINHTTP_NO_HEADER_INDEX) || status != 200)
        throw std::runtime_error("업데이트 파일을 찾지 못했습니다.");
    const auto partial = destination;
    std::ofstream output(partial, std::ios::binary | std::ios::trunc);
    if (!output) throw std::runtime_error("업데이트 파일을 저장할 수 없습니다.");
    char buffer[65536];
    DWORD count = 0;
    std::uint64_t total = 0;
    do {
        if (!WinHttpReadData(request.value, buffer, sizeof(buffer), &count))
            throw std::runtime_error("업데이트 파일을 받지 못했습니다.");
        total += count;
        if (total > max_bytes) throw std::runtime_error("업데이트 파일이 너무 큽니다.");
        if (count) output.write(buffer, count);
    } while (count);
    output.close();
    const auto actual = FileSha256(partial);
    if (actual != expected) {
        std::error_code ignored;
        std::filesystem::remove(partial, ignored);
        throw std::runtime_error("업데이트 파일 검증에 실패했습니다.");
    }
}

inline bool LaunchReplacement(const std::filesystem::path& current, const std::filesystem::path& staged) {
    wchar_t system[MAX_PATH];
    if (!GetSystemDirectoryW(system, MAX_PATH)) return false;
    const std::wstring powershell = std::wstring(system) + L"\\WindowsPowerShell\\v1.0\\powershell.exe";
    std::wstring command = L"\"" + powershell + L"\" -NoProfile -ExecutionPolicy Bypass -Command \"Start-Sleep -Seconds 2; "
        L"Move-Item -LiteralPath '" + staged.wstring() + L"' -Destination '" + current.wstring() + L"' -Force; "
        L"Start-Process -LiteralPath '" + current.wstring() + L"'\"";
    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    PROCESS_INFORMATION process{};
    if (!CreateProcessW(nullptr, command.data(), nullptr, nullptr, FALSE,
                        CREATE_NO_WINDOW | DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                        nullptr, current.parent_path().c_str(), &startup, &process))
        return false;
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    return true;
}

inline Status Probe() {
    try {
        const auto manifest = nlohmann::json::parse(GetText(L"updates/windows/latest.json", 16384));
        const int version = manifest.at("version").get<int>();
        if (version <= RIFT_CLIENT_VERSION) return {Result::Current, "최신 버전입니다."};
        Status found{Result::Available, "", manifest.at("file").get<std::string>(), manifest.at("sha256").get<std::string>(),
                     manifest.value("notes", std::string{}), manifest.value("versionName", std::to_string(version))};
        const std::string prefix = "RiftManagerNative-";
        const bool named = found.file.size() > prefix.size() + 4 && found.file.compare(0, prefix.size(), prefix) == 0 &&
            found.file.compare(found.file.size() - 4, 4, ".exe") == 0;
        bool digits = named;
        for (size_t index = prefix.size(); digits && index + 4 < found.file.size(); ++index)
            digits = found.file[index] >= '0' && found.file[index] <= '9';
        for (char& c : found.sha256) if (c >= 'A' && c <= 'F') c = static_cast<char>(c - 'A' + 'a');
        if (!digits || found.sha256.size() != 64 || found.sha256.find_first_not_of("0123456789abcdef") != std::string::npos)
            return {Result::Failed, "업데이트 정보가 올바르지 않습니다."};
        return found;
    } catch (const std::exception& error) {
        return {Result::Failed, error.what()};
    }
}

inline Status Apply(const Status& found) {
    try {
        const auto question = L"새 버전 " + Widen(found.version_name) + L"이 있습니다.\n" + Widen(found.notes) + L"\n지금 받고 다시 시작할까요?";
        if (MessageBoxW(nullptr, question.c_str(), L"RIFT MANAGER", MB_YESNO | MB_ICONINFORMATION) != IDYES)
            return {Result::Current, "업데이트를 보류했습니다."};
        wchar_t executable[MAX_PATH];
        if (!GetModuleFileNameW(nullptr, executable, MAX_PATH))
            return {Result::Failed, "실행 파일 위치를 찾지 못했습니다."};
        const std::filesystem::path current = executable;
        const auto staged = current.parent_path() / L"RiftManagerNative.update.exe";
        DownloadFile(L"updates/windows/" + Widen(found.file), staged, found.sha256, 80ull * 1024 * 1024);
        if (!LaunchReplacement(current, staged))
            return {Result::Failed, "새 버전을 받았지만 다시 시작하지 못했습니다."};
        return {Result::Restart, "새 버전으로 다시 시작합니다."};
    } catch (const std::exception& error) {
        return {Result::Failed, error.what()};
    }
}
}
