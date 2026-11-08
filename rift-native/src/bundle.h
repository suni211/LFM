#pragma once
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
#include <windows.h>

namespace bundle {
inline constexpr std::uint64_t kMagic = 0x31474B5054464952ull;

inline std::uint16_t Read16(const unsigned char* data) {
    return static_cast<std::uint16_t>(data[0] | (data[1] << 8));
}
inline std::uint32_t Read32(const unsigned char* data) {
    return static_cast<std::uint32_t>(data[0] | (data[1] << 8) | (data[2] << 16) | (data[3] << 24));
}

inline bool SafePath(const std::string& name, std::filesystem::path& relative) {
    if (name.empty() || name.back() == '/') return false;
    std::filesystem::path path;
    std::string part;
    for (char character : name) {
        if (character == '/' || character == '\\') {
            if (part.empty() || part == "." || part == "..") return false;
            path /= part;
            part.clear();
        } else part.push_back(character);
    }
    if (part.empty() || part == "." || part == "..") return false;
    relative = path / part;
    return true;
}

inline bool ExtractStored(const std::vector<unsigned char>& zip, const std::filesystem::path& root) {
    std::uint64_t offset = 0;
    while (offset + 30 <= zip.size()) {
        const auto* header = zip.data() + offset;
        const auto signature = Read32(header);
        if (signature == 0x02014b50) return true;
        if (signature != 0x04034b50) return false;
        const auto method = Read16(header + 8);
        const auto compressed = Read32(header + 18);
        const auto name_length = Read16(header + 26);
        const auto extra_length = Read16(header + 28);
        const auto data_at = offset + 30 + name_length + extra_length;
        if (method != 0 || data_at + compressed > zip.size()) return false;
        const std::string name(reinterpret_cast<const char*>(header + 30), name_length);
        offset = data_at + compressed;
        if (!name.empty() && name.back() == '/') continue;
        std::filesystem::path relative;
        if (!SafePath(name, relative)) return false;
        const auto destination = root / relative;
        std::filesystem::create_directories(destination.parent_path());
        std::ofstream output(destination, std::ios::binary | std::ios::trunc);
        if (!output) return false;
        output.write(reinterpret_cast<const char*>(zip.data() + data_at), compressed);
    }
    return true;
}

inline bool Prepare() {
    wchar_t executable[MAX_PATH];
    if (!GetModuleFileNameW(nullptr, executable, MAX_PATH)) return false;
    std::ifstream input(std::filesystem::path(executable), std::ios::binary | std::ios::ate);
    if (!input) return false;
    const auto size = static_cast<std::uint64_t>(input.tellg());
    if (size < 16) return false;
    input.seekg(static_cast<std::streamoff>(size - 16));
    std::uint64_t packed = 0, magic = 0;
    input.read(reinterpret_cast<char*>(&packed), 8);
    input.read(reinterpret_cast<char*>(&magic), 8);
    if (!input || magic != kMagic || packed < 30 || packed + 16 > size) return false;
    wchar_t local[MAX_PATH];
    const auto local_length = GetEnvironmentVariableW(L"LOCALAPPDATA", local, MAX_PATH);
    const std::filesystem::path root = (local_length > 0 && local_length < MAX_PATH
        ? std::filesystem::path(local) : std::filesystem::temp_directory_path()) / L"RiftManager" / L"package";
    std::filesystem::create_directories(root);
    const auto stamp_path = root / L"stamp.txt";
    std::ifstream stamp(stamp_path);
    std::uint64_t current = 0;
    if (stamp) stamp >> current;
    if (current == packed && std::filesystem::exists(root / "assets" / "main.rml")) {
        std::filesystem::current_path(root);
        return true;
    }
    input.seekg(static_cast<std::streamoff>(size - 16 - packed));
    std::vector<unsigned char> zip(static_cast<size_t>(packed));
    input.read(reinterpret_cast<char*>(zip.data()), static_cast<std::streamsize>(packed));
    if (!input || !ExtractStored(zip, root)) return false;
    std::ofstream written(stamp_path, std::ios::trunc);
    written << packed;
    std::filesystem::current_path(root);
    return std::filesystem::exists(root / "assets" / "main.rml");
}
}
