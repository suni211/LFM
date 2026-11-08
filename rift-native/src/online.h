#pragma once
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <winhttp.h>
#include <nlohmann/json.hpp>
#include <stdexcept>
#include <string>

namespace online {
inline const std::wstring host=L"berrple.com",prefix=L"/rift/api/";
inline constexpr INTERNET_PORT port=INTERNET_DEFAULT_HTTPS_PORT;
inline constexpr bool secure=true;
struct Handle {
    HINTERNET value;
    ~Handle() { if (value) WinHttpCloseHandle(value); }
};

inline nlohmann::json Request(const std::wstring& route, const std::string& token,
                              const nlohmann::json& data = nullptr) {
    Handle session{WinHttpOpen(L"Rift Manager", WINHTTP_ACCESS_TYPE_AUTOMATIC_PROXY,
                               WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0)};
    if (!session.value) throw std::runtime_error("서버 연결을 시작할 수 없습니다.");
    WinHttpSetTimeouts(session.value, 8000, 8000, 15000, 20000);
    Handle connection{WinHttpConnect(session.value, host.c_str(), port, 0)};
    if (!connection.value) throw std::runtime_error("서버에 연결할 수 없습니다.");
    const auto path = prefix + route;
    Handle request{WinHttpOpenRequest(connection.value, data.is_null() ? L"GET" : L"POST",
                                      path.c_str(), nullptr, WINHTTP_NO_REFERER,
                                      WINHTTP_DEFAULT_ACCEPT_TYPES, secure?WINHTTP_FLAG_SECURE:0)};
    if (!request.value) throw std::runtime_error("요청을 시작할 수 없습니다.");
    DWORD disabled = WINHTTP_DISABLE_REDIRECTS;
    if (!WinHttpSetOption(request.value, WINHTTP_OPTION_DISABLE_FEATURE, &disabled, sizeof(disabled)))
        throw std::runtime_error("서버 연결 설정에 실패했습니다.");
    DWORD decompression = WINHTTP_DECOMPRESSION_FLAG_GZIP;
    if (!WinHttpSetOption(request.value, WINHTTP_OPTION_DECOMPRESSION, &decompression, sizeof(decompression)))
        throw std::runtime_error("압축 응답 설정에 실패했습니다.");
    std::wstring headers = L"Content-Type: application/json\r\n";
    if (!token.empty()) headers += L"Authorization: Bearer " + std::wstring(token.begin(), token.end()) + L"\r\n";
    auto body = data.is_null() ? std::string{} : data.dump();
    auto length = static_cast<DWORD>(body.size());
    if (!WinHttpSendRequest(request.value, headers.c_str(), static_cast<DWORD>(-1),
                            length ? body.data() : nullptr, length, length, 0) ||
        !WinHttpReceiveResponse(request.value, nullptr))
        throw std::runtime_error("서버에 연결할 수 없습니다.");
    DWORD status = 0, size = sizeof(status);
    if (!WinHttpQueryHeaders(request.value, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
                            WINHTTP_HEADER_NAME_BY_INDEX, &status, &size, WINHTTP_NO_HEADER_INDEX))
        throw std::runtime_error("서버 응답을 확인할 수 없습니다.");
    if (status == 401) throw std::runtime_error("로그인 정보를 확인하거나 다시 로그인하세요.");
    std::string response;
    char buffer[4096];
    DWORD count = 0;
    do {
        if (!WinHttpReadData(request.value, buffer, sizeof(buffer), &count) || response.size() + count > 16777216)
            throw std::runtime_error("서버 응답을 읽을 수 없습니다.");
        response.append(buffer, count);
    } while (count);
    const auto result=nlohmann::json::parse(response,nullptr,false);
    if(result.is_discarded())throw std::runtime_error(status==404?"접속 주소를 찾을 수 없습니다. 최신 실행 파일로 다시 접속하세요.":"서버가 응답을 준비하지 못했습니다. 잠시 후 다시 시도하세요.");
    if (status < 200 || status >= 300) {
        const auto error=result.value("error",std::string{});
        if(error=="endpoint not found")throw std::runtime_error("서버와 앱 버전이 맞지 않습니다. 최신 실행 파일로 다시 접속하세요.");
        if(error=="account name must be 1 to 30 characters")throw std::runtime_error("계정 이름은 1~30자여야 합니다.");
        if(error=="password must be 10 to 128 characters")throw std::runtime_error("비밀번호는 10~128자여야 합니다.");
        if(error=="account name already exists")throw std::runtime_error("이미 사용 중인 계정 이름입니다. 로그인하거나 다른 이름을 입력하세요.");
        if(error=="invalid request")throw std::runtime_error("입력 내용을 확인하세요. 계정 이름은 1~30자, 비밀번호는 10~128자입니다.");
        if(status==404)throw std::runtime_error("해당 구단 또는 인물 정보를 찾을 수 없습니다. 목록을 새로 불러오세요.");
        if(status==403)throw std::runtime_error("이 구단을 관리하는 감독만 할 수 있습니다.");
        if(error=="champion is unavailable or leaves no valid team composition")throw std::runtime_error("이미 선택·금지된 챔피언이거나 포지션 구성이 불가능합니다.");
        if(error=="wait for opponent turn")throw std::runtime_error("상대 팀의 밴픽 차례입니다. 잠시 기다려 주세요.");
        if(error=="champions cannot fill swapped roles")throw std::runtime_error("두 챔피언이 교환할 포지션을 지원하지 않습니다.");
        if(error=="response period expired; automatic draft is running")throw std::runtime_error("응답 시간이 지나 자동 밴픽을 진행하고 있습니다.");
        if(error=="stale draft version" || error=="stale swap version")throw std::runtime_error("밴픽 상태가 변경됐습니다. 최신 화면을 불러오세요.");
        if(status>=500)throw std::runtime_error("서버에서 정보를 처리하지 못했습니다. 잠시 후 다시 불러오세요.");
        if(error=="finalize the five-player lineup before advancing" || error=="five players, one per role, and at most three coaches required")
            throw std::runtime_error("포지션별 선수 1명씩 총 5명을 선발하고 선수단을 확정하세요. 코치는 최대 3명입니다.");
        if(error=="at most three coaches") throw std::runtime_error("코치는 최대 3명까지 선발할 수 있습니다.");
        if(error=="select exactly one player per role") throw std::runtime_error("같은 포지션에서는 한 명만 선발할 수 있습니다.");
        if(error=="initial recruitment already finalized") throw std::runtime_error("이미 초기 선수단을 확정했습니다.");
        if(error=="finish the current series before advancing") throw std::runtime_error("진행 중인 시리즈를 마친 뒤 주차를 진행하세요.");
        if(error=="amateurs and prospects cannot be signed") throw std::runtime_error("일반인과 데뷔 전 유망주는 영입할 수 없습니다. 대화로 유망주를 만든 뒤 프로 데뷔를 시키세요.");
        if(error=="already a pro player") throw std::runtime_error("이미 프로인 선수입니다. 영입으로 접촉하세요.");
        if(error=="player has retired") throw std::runtime_error("은퇴한 선수입니다.");
        if(error=="another club is developing this player") throw std::runtime_error("다른 구단이 키우는 유망주입니다.");
        if(error=="already your prospect") throw std::runtime_error("이미 우리 유망주입니다.");
        if(error=="this player is in another club tryout") throw std::runtime_error("다른 구단 후보로 있는 일반인입니다.");
        if(error=="prospect list is full") throw std::runtime_error("유망주가 너무 많습니다. 데뷔하거나 은퇴한 뒤에 다시 대화하세요.");
        if(error=="talk again later") throw std::runtime_error("같은 선수와는 잠시 뒤에 다시 대화할 수 있습니다.");
        if(error=="not your prospect") throw std::runtime_error("우리 유망주가 아닙니다.");
        if(error=="not ready for pro debut") throw std::runtime_error("솔로랭크가 실버 I 이상이어야 프로 데뷔를 시킬 수 있습니다.");
        if(error=="debut the prospect before the pro roster") throw std::runtime_error("일반인은 바로 선발할 수 없습니다. 대화 후 유망주로 키우고 프로 데뷔를 시키세요.");
        if(error=="operators choose a team") throw std::runtime_error("운영자는 목록에서 팀을 선택해 들어갑니다.");
        if(status==409) throw std::runtime_error("이름이 사용 중이거나 서버 상태가 변경됐습니다. 다시 불러오세요.");
        throw std::runtime_error("서버 요청 실패 (" + std::to_string(status) + ").");
    }
    return result;
}
}
