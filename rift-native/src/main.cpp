#include "online.h"
#include "update.h"
#include "bundle.h"
#include <RmlUi/Core.h>
#include <RmlUi/Core/Elements/ElementFormControl.h>
#include <RmlUi_Backend.h>
#include <SDL3/SDL.h>
#include <SDL3/SDL_main.h>
#include <SDL3_image/SDL_image.h>
#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <set>
#include <string>
#include <algorithm>
#include <map>
#include <ctime>
#include <cmath>
#include <future>
#include <chrono>
using Json = nlohmann::json;
namespace fs = std::filesystem;

static std::string Escape(const std::string& text) {
    std::string output;
    for (char c : text) {
        switch (c) {
        case '&': output += "&amp;"; break;
        case '<': output += "&lt;"; break;
        case '>': output += "&gt;"; break;
        case '"': output += "&quot;"; break;
        case '\'': output += "&#39;"; break;
        default: output += c;
        }
    }
    return output;
}
static size_t Utf8Count(const std::string& text) {
    size_t characters=0;
    for(unsigned char c:text) if((c&0xc0)!=0x80) ++characters;
    return characters;
}
static std::string CleanName(std::string text, size_t limit) {
    const auto first = text.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return "";
    text = text.substr(first, text.find_last_not_of(" \t\r\n") - first + 1);
    size_t characters = 0;
    for (unsigned char c : text) {
        if (c < 32 || c == 127) return "";
        if ((c & 0xc0) != 0x80) ++characters;
    }
    return characters <= limit && text.size() <= limit * 4 ? text : "";
}
static std::string Lower(std::string text) {
    for(char& c:text)if(c>='A' && c<='Z')c=static_cast<char>(c-'A'+'a');
    return text;
}
static std::string ChampionName(const std::string& key) {
    static const Json names=[] {std::ifstream file("assets/champion-names-ko.json");Json data=Json::object();if(file)file>>data;return data;}();
    return names.value(key,key);
}
static std::string JText(const Json& node, const char* key, const std::string& fallback = {}) {
    if (!node.is_object() || !node.contains(key)) return fallback;
    const auto& value = node.at(key);
    if (value.is_string()) return value.get<std::string>();
    if (value.is_number_integer()) return std::to_string(value.get<long long>());
    return fallback;
}
static std::string PersonName(const Json& person) {
    const auto korean = person.value("display_name_ko",std::string{});
    if (!korean.empty()) return korean;
    const auto real = person.value("real_name",std::string{});
    return real.empty() ? "본명 확인 중" : real;
}
static std::string UrlEncode(const std::string& input) {
    const char* hex="0123456789ABCDEF";
    std::string out;
    for (unsigned char c:input) { out+='%'; out+=hex[c>>4]; out+=hex[c&15]; }
    return out;
}
static bool ValidCareer(const Json& data) {
    if (!data.is_object() || !data.contains("manager") || !data["manager"].is_string() ||
        !data.contains("club") || !data["club"].is_string() ||
        !data.contains("week") || !data["week"].is_number_integer() ||
        !data.contains("season") || !data["season"].is_number_integer()) return false;
    return !CleanName(data["manager"], 30).empty() && !CleanName(data["club"], 40).empty() &&
        data["week"] >= 1 && data["week"] <= 104 && data["season"] >= 1 && data["season"] <= 10000;
}
static const std::pair<const char*,const char*> Navigation[] = {
 {"overview","대시보드"},{"news","뉴스 사이트"},{"mail","우편함"},{"tactics","전술"},{"training","훈련"},
 {"staff","스탭"},{"first","1군"},{"academy","2군 · 3군"},{"calendar","달력"},{"relations","선수간 관계"},
 {"medical","의료 센터"},{"people","선수 데이터베이스"},{"transfers","이적 활동"},{"shortlist","영입 명단"},
 {"transfer-budget","영입 예산"},{"staff-search","스탭 검색"},{"staff-transfers","스탭 이적 활동"},
 {"finance","재정"},{"competition","대회"},{"data","데이터 허브"},{"vision","구단 비전"},
 {"profile","내 프로필"},{"admin","운영자"},{"community","커뮤니티"},{"solo","솔로랭크"}
};
class Application : public Rml::EventListener {
public:
    Rml::ElementDocument* document = nullptr;
    Json people, career;
    fs::path save_path, session_path;
    int page = 0;
    std::string selected_person;
    std::string load_notice, online_token, online_manager;
    Json online_careers, local_career;
    bool online_active = false, online_operator = false, restarting = false, update_started = false;
    std::future<client_update::Status> update_probe;
    void PollUpdate() {
        if (restarting) return;
        if (!update_started) {
            update_started = true;
            update_probe = std::async(std::launch::async, [] { return client_update::Probe(); });
            return;
        }
        if (!update_probe.valid() || update_probe.wait_for(std::chrono::milliseconds(0)) != std::future_status::ready) return;
        const auto found = update_probe.get();
        if (found.result != client_update::Result::Available) return;
        const auto status = client_update::Apply(found);
        if (status.result == client_update::Result::Restart) restarting = true;
        else if (auto* info = document->GetElementById("lobby-info")) info->SetInnerRML(Escape(status.message));
    }
    std::future<Json> search_future;
    std::string search_pending,search_requested,search_token;
    Uint64 search_due=0;
    Json search_items=Json::array();
    void PollSearch() {
        if(search_future.valid() && search_future.wait_for(std::chrono::milliseconds(0))==std::future_status::ready) {
            try {
                const auto result=search_future.get();
                if(search_token==online_token && search_requested==search_pending && !search_pending.empty()) {
                    search_items=result.at("results");std::string body;
                    for(size_t i=0;i<search_items.size();++i) {const auto& item=search_items[i];
                        const auto kind=item.at("kind").get<std::string>();
                        body+="<button id='global-result-"+std::to_string(i)+"'>"+std::string(kind=="player"?"선수":kind=="staff"?"스태프":kind=="team"?"구단":kind=="owner"?"구단주":"감독")+" · "+Escape(item.at("label").get<std::string>())+"<br/><small>"+Escape(item.at("subtitle").get<std::string>())+"</small></button>";
                    }
                    if(body.empty())body="<p>연관 검색 결과가 없습니다.</p>";
                    document->GetElementById("global-results")->SetInnerRML(body);Display("global-results",true);
                    for(size_t i=0;i<search_items.size();++i) document->GetElementById("global-result-"+std::to_string(i))->AddEventListener("click",this);
                }
            }catch(const std::exception&) {Display("global-results",false);}
        }
        if(!search_future.valid() && !online_token.empty() && !search_pending.empty() && search_requested!=search_pending && SDL_GetTicks()>=search_due) {
            search_requested=search_pending;search_token=online_token;
            const auto query=search_requested,token=search_token;
            search_future=std::async(std::launch::async,[query,token] {const auto route="search?query="+UrlEncode(query);return online::Request(std::wstring(route.begin(),route.end()),token);});
        }
    }
    void LoadOnlineList() {
        online_careers = online::Request(L"careers", online_token).at("careers");
        online_operator = online::Request(L"world", online_token).value("operator", false);
        std::string options;
        for (const auto& item : online_careers)
            options += "<option value='" + item.at("id").dump() + "'>" +
                       Escape(JText(item, "name")) + " · " +
                       item.at("week").dump() + "주차</option>";
        document->GetElementById("online-list")->SetInnerRML(options);
        const auto clubs=online::Request(L"clubs",online_token).at("clubs");
        options.clear();
        for(const auto& club:clubs) {
            if(!online_operator && club.value("claimed",false)) continue;
            const auto kind=JText(club, "kind", "ai");
            const auto owner=JText(club, "owner");
            std::string label=JText(club, "league")+" / "+JText(club, "team");
            if(online_operator) label+=" · "+std::string(kind=="user"?"유저 구경":"AI 관리")+(owner.empty()?"":" · "+owner);
            options+="<option value='"+JText(club, "team_key")+"'>"+Escape(label)+"</option>";
        }
        document->GetElementById("online-team")->SetInnerRML(options);
        Display("online-user-start", !online_operator);
        document->GetElementById("online-team-label")->SetInnerRML(online_operator?"팀 선택":"부임 가능한 실제 구단");
        document->GetElementById("online-takeover")->SetInnerRML(online_operator?"선택한 팀 열기":"실제 구단 감독 부임");
        Display("online-auth", false);
        Display("online-careers", true);
    }
    void PersistSession() {
        if (online_token.empty()) return;
        std::ofstream out(session_path, std::ios::binary);
        out << Json{{"name", online_manager},{"token", online_token}}.dump();
    }
    void ForgetSession() {
        online_token.clear();
        online_manager.clear();
        std::error_code ignored;
        fs::remove(session_path, ignored);
    }
    void TryAutoLogin() {
        std::ifstream in(session_path, std::ios::binary);
        if (!in) return;
        const auto saved = Json::parse(in, nullptr, false);
        const auto token = JText(saved, "token");
        if (token.empty()) return;
        online_token = token;
        online_manager = JText(saved, "name");
        try {
            LoadOnlineList();
            Display("online-panel", true);
            if (auto* info = document->GetElementById("lobby-info"))
                info->SetInnerRML(online_manager.empty() ? "자동으로 로그인했습니다." : Escape(online_manager) + " 계정으로 자동 로그인했습니다.");
        } catch (const std::exception&) {
            ForgetSession();
            Display("online-auth", true);
            Display("online-careers", false);
            Display("online-panel", false);
        }
    }
    Json highlight;
    std::map<int,Json> replay_units;
    std::size_t replay_frame = 0;
    Uint64 replay_started = 0;
    void PlayHighlight(const std::string& fixture, const std::string& index) {
        auto route = L"highlight?id=" + std::wstring(fixture.begin(),fixture.end()) +
                     L"&clip=" + std::wstring(index.begin(),index.end());
        auto recording = online::Request(route,online_token);
        if (recording.at("version") != 1 || recording.at("frames").empty())
            throw std::runtime_error("하이라이트 파일을 열 수 없습니다.");
        calendar_key.clear();
        highlight = std::move(recording);
        replay_units.clear();
        for (const auto& unit : highlight.at("units")) replay_units.emplace(unit.at("id").get<int>(),unit);
        auto* body = document->GetElementById("page-body");
        body->SetInnerRML("<button id='replay-back'>경기 화면으로</button><button id='replay-restart'>다시 보기</button>"
            "<h2 id='replay-caption'></h2><div style='position:relative;width:512px;height:512px;background:#081317'>"
            "<img src='replay-map.png' style='width:512px;height:512px'/><div id='replay-markers'></div></div>");
        for (const auto* id : {"replay-back","replay-restart"})
            document->GetElementById(id)->AddEventListener("click",this);
        replay_frame = 0;
        replay_started = SDL_GetTicks();
    }
    void UpdateHighlight() {
        auto* markers = document->GetElementById("replay-markers");
        if (!markers || highlight.is_null()) return;
        const auto& clip = highlight.at("clip");
        const auto& frames = highlight.at("frames");
        const double time = std::min(clip.at("end").get<double>(),clip.at("start").get<double>() +
                                    (SDL_GetTicks()-replay_started)/1000.0);
        auto next = replay_frame;
        while (next+1 < frames.size() && frames[next+1][0].get<double>() <= time) ++next;
        if (next == replay_frame && markers->GetNumChildren() != 0) return;
        replay_frame = next;
        std::string points;
        for (const auto& point : frames[replay_frame][1]) {
            auto it = replay_units.find(point[0].get<int>());
            if (it == replay_units.end()) continue;
            const auto& unit = it->second;
            const auto type = unit.at("kind").get<std::string>();
            const int team = unit.at("team");
            const char* color = team==0 ? "#6ab9ff" : team==1 ? "#ff697e" : "#e6c47c";
            const int radius = type=="champion" ? 7 : type=="minion" ? 2 : 4;
            auto x = std::clamp(static_cast<int>(point[1].get<double>())-radius,0,512-radius*2);
            auto y = std::clamp(static_cast<int>(point[2].get<double>())-radius,0,512-radius*2);
            points += "<div style='position:absolute;left:"+std::to_string(x)+"px;top:"+std::to_string(y)+
                      "px;width:"+std::to_string(radius*2)+"px;height:"+std::to_string(radius*2)+
                      "px;border-radius:"+std::to_string(radius)+"px;background:"+color+"'></div>";
        }
        markers->SetInnerRML(points);
        document->GetElementById("replay-caption")->SetInnerRML(Escape(clip.at("label").get<std::string>()) +
            " · " + std::to_string(static_cast<int>(time)/60) + "분 " + std::to_string(static_cast<int>(time)%60) + "초");
    }
    std::future<Json> fixture_poll;
    Json cached_fixtures;
    int active_match=0,swap_first=-1;
    std::string draft_query,draft_selection;
    Json match_game;
    std::string calendar_key;
    Json club_assets=Json::object();
    std::string Face(const Json& person, int size=44) {
        std::string path=person.value("photo",std::string{});
        if(path.rfind("portraits/",0)!=0) {
            const auto id=person.value("id",std::string{});
            if(id.empty()) return "";
            path="portraits/"+id+".png";
        }
        if(!fs::exists(fs::path("assets")/fs::u8path(path))) return "";
        return "<img class='face' src='"+Escape(path)+"' style='width:"+std::to_string(size)+"px;height:"+std::to_string(size)+"px;'/>";
    }
    std::string Logo(const std::string& league, const std::string& team, int size=28) {
        if(!club_assets.is_object()) return "";
        const auto key=league+"\n"+team;
        if(!club_assets.contains(key)) return "";
        const auto path=club_assets.at(key).value("logo",std::string{});
        if(path.empty() || !fs::exists(fs::path("assets")/fs::u8path(path))) return "";
        return "<img class='logo' src='"+Escape(path)+"' style='width:"+std::to_string(size)+"px;height:"+std::to_string(size)+"px;'/>";
    }
    #include "club_screens.h"
    Uint64 next_fixture_poll = 0, calendar_generation = 0;
    void PollFixtures() {
        if (fixture_poll.valid() && fixture_poll.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            try {
                auto response = fixture_poll.get();
                if (!calendar_key.empty() && calendar_key == response.at("key").get<std::string>() &&
                    response.at("generation") == calendar_generation && response.at("fixtures") != cached_fixtures) {
                    cached_fixtures = std::move(response.at("fixtures"));
                    if(active_match)OpenMatch(active_match,false);else OpenPage("calendar",false);
                }
            } catch (const std::exception&) { /* The manual refresh still reports connection errors. */ }
        }
        if (calendar_key.empty()) return;
        bool poll = false;
        for (const auto& game : cached_fixtures) {
            const auto series = game.value("series",Json{});
            if (game.at("state") != "queued" || series.is_null()) continue;
            const auto phase = series.at("phase");
            if (phase == "choice" || phase == "draft" || phase == "ready" || phase=="draft_pending" || phase=="swap") poll = true;
            if(phase=="choice" && !series.value("response_until",Json{}).is_null()) {
                const int left=std::max(0,static_cast<int>(std::ceil(series.at("response_until").get<double>()-std::time(nullptr))));
                if(auto* timer=document->GetElementById("response-timer-"+game.at("id").dump()))timer->SetInnerRML(std::to_string(left)+"초 · 미응답 시 자동 진행");
            }
            if(phase=="swap") {
                const auto left=std::max(0,static_cast<int>(std::ceil(series.at("swap_until").get<double>()-std::time(nullptr))));
                if(auto* timer=document->GetElementById("swap-timer-"+game.at("id").dump()))timer->SetInnerRML(std::to_string(left)+"초 남음");
            }
            if (phase == "feedback") {
                const auto left = std::max(0,static_cast<int>(std::ceil(series.at("feedback_until").get<double>()-std::time(nullptr))));
                if (auto* timer = document->GetElementById("feedback-timer-"+game.at("id").dump())) {
                    const auto remaining = std::to_string(left)+"초 남음";
                    if (timer->GetInnerRML() != remaining) timer->SetInnerRML(remaining);
                }
                if (left == 0) poll = true;
            }
        }
        if (!poll || fixture_poll.valid() || SDL_GetTicks()<next_fixture_poll) return;
        next_fixture_poll = SDL_GetTicks()+2500;
        auto token = online_token;
        auto key = calendar_key;
        fixture_poll = std::async(std::launch::async,[token,key,generation=calendar_generation] {
            const auto id = key.substr(key.find(':')+1);
            return Json{{"key",key},{"generation",generation},{"fixtures",online::Request(L"fixtures?id="+std::wstring(id.begin(),id.end()),token).at("fixtures")}};
        });
    }
    std::string SeriesControls(const Json& game) {
        const auto state = game.value("series",Json{});
        if (state.is_null()) return "";
        const auto id = game.at("id").dump();
        const auto phase = state.at("phase").get<std::string>();
        const int best_of=state.value("best_of",3);
        std::string text = "<p>"+std::to_string(best_of)+"판 "+std::to_string(best_of/2+1)+"선승 · " + state.at("score")[0].dump() + " : " + state.at("score")[1].dump() + "</p>";
        text+="<div class='card'><h2>피어리스 · 이전 세트 사용 금지</h2>";
        for(const auto& champion:state.value("fearless_bans",Json::array()))text+="<span>"+Escape(ChampionName(champion.get<std::string>()))+"　</span>";
        text+="</div>";
        if(state.value("autoplay",false))text+="<p>3분 미응답 · 남은 시리즈 자동 진행 중</p>";
        if (phase == "choice") {
            text+="<p id='response-timer-"+id+"'>3분 내에 선택하세요. 미응답 시 남은 경기를 자동으로 처리합니다.</p>";
            const auto choice = state.at("choice");
            if (!choice.is_null()) {
                const auto value = choice.value("value","");
                text += "<p>상대 선택 · " + std::string(value=="first"?"선픽":value=="second"?"후픽":value=="blue"?"블루":"레드") + "</p>";
            }
            if (career.value("role","") == "admin") {
                const auto add = [&](const char* category, const char* value, const char* label) {
                    text += "<button id='draft-"+id+"-"+category+"-"+value+"'>"+label+"</button>";
                };
                if (choice.is_null() || choice.at("category") != "priority") { add("priority","first","선픽"); add("priority","second","후픽"); }
                if (choice.is_null() || choice.at("category") != "side") { add("side","blue","블루"); add("side","red","레드"); }
            }
        } else if(phase=="draft_pending") text+="<p>밴픽 준비 중 · 잠시 기다려 주세요.</p>";
        else if(phase=="draft") {
            const int first=state.at("first"),other=1-first;
            const int turns[]={first,other,first,other,first,other,first,other,other,first,first,other,other,first,other,first,other,first,first,other};
            const int step=static_cast<int>(state.at("draft").size());const bool own=turns[step]==0;
            const bool ban=step<6 || (step>=12 && step<16);
            text+="<h2>"+std::string(own?"우리 팀":"상대 팀")+" · "+(ban?"밴":"픽")+" "+std::to_string(step+1)+" / 20</h2><div class='columns'>";
            for(int side=0;side<2;++side) {
                const int team=side==state.at("blue").get<int>()?0:1;
                text+="<div class='card'><h2>"+std::string(side==0?"BLUE":"RED")+(team==0?" · 우리 팀":" · 상대 팀")+"</h2>";
                for(const auto& name:state.at("draft_picks").at(team))text+="<img style='width:100px;height:170px;margin:3px;' src='loading/"+Escape(name.get<std::string>())+".jpg'/>";
                text+="</div>";
            }
            text+="</div><input id='manual-query' type='text' maxlength='40' value='"+Escape(draft_query)+"'/><button id='manual-search'>챔피언 검색</button>";
            if(own) {
                std::ifstream champion_file("assets/champion-index.json");Json roster;champion_file>>roster;
                std::set<std::string> blocked;
                for(const auto& value:state.value("fearless_bans",Json::array()))blocked.insert(value.get<std::string>());
                for(const auto& action:state.at("draft"))blocked.insert(action.at("champion").get<std::string>());
                text+="<div style='height:310px;overflow-y:auto;'>";
                for(const auto& name:roster) {
                    const auto champion=name.get<std::string>();
                    if(blocked.count(champion) || (!draft_query.empty() && Lower(champion+" "+ChampionName(champion)).find(Lower(draft_query))==std::string::npos))continue;
                    text+="<button id='manual-champ-"+Escape(champion)+"' style='width:112px;height:98px;'><img style='width:54px;height:54px;' src='champions/"+Escape(champion)+".png'/><br/>"+Escape(ChampionName(champion))+"</button>";
                }
                text+="</div>";
                if(!draft_selection.empty())text+="<p>선택 · "+Escape(ChampionName(draft_selection))+"</p><button id='manual-confirm'>"+(ban?std::string("밴 확정"):std::string("픽 확정"))+"</button>";
            } else text+="<p>상대 팀이 챔피언을 선택하고 있습니다.</p>";
            text+="<button id='manual-auto'>남은 밴픽 자동</button>";
        }
        else if(phase=="swap") {
            const auto remaining=std::max(0,static_cast<int>(std::ceil(state.at("swap_until").get<double>()-std::time(nullptr))));
            text+="<h2>밴픽 완료 · 30초 챔피언 스왑</h2><p id='swap-timer-"+id+"'>"+std::to_string(remaining)+"초 남음</p>";
            const char* roles[]={"TOP","JUNGLE","MID","ADC","SUPPORT"};
            text+="<div class='columns'>";
            for(int side=0;side<2;++side) {
                const bool own=side==state.at("blue").get<int>();
                text+="<div class='card'><h2>"+std::string(side==0?"BLUE":"RED")+(own?" · 우리 팀":" · 상대 팀")+"</h2>";
                const auto& roster=state.at("roster").at(side);
                for(int i=0;i<5;++i) {
                    if(own && remaining && career.value("role","")=="admin")text+="<button style='display:block;width:94%;text-align:left;' id='swapcard-"+id+"-"+std::to_string(i)+"'>"+std::string(swap_first==i?"[선택] ":"")+roles[i]+" · "+Escape(ChampionName(roster[i].get<std::string>()))+"</button>";
                    else text+="<div class='row'>"+std::string(roles[i])+" · "+Escape(ChampionName(roster[i].get<std::string>()))+"</div>";
                }
                text+="</div>";
            }
            text+="</div><p>우리 팀 카드 두 개를 선택하면 챔피언을 교환합니다. 30초 후 최종 배치로 경기를 시작합니다.</p>";
        } else if (phase == "feedback") {
            const auto remaining = std::max(0,static_cast<int>(std::ceil(state.at("feedback_until").get<double>()-std::time(nullptr))));
            text += "<p>세트 피드백 · <span id='feedback-timer-"+id+"'>"+std::to_string(remaining)+"초 남음</span></p>";
            if (remaining && career.value("role","") == "admin")
                text += "<input type='text' maxlength='300' id='feedback-note-"+id+"'/><button id='feedback-"+id+"'>피드백 저장</button>";
        }
        if (phase == "ready" || phase=="swap") {
            text += "<p>" + std::string(state.at("blue")==0?"우리 블루":"우리 레드") + " · " +
                    (state.at("first")==0?"선픽":"후픽") + "</p>";
            const auto draft = state.value("draft",Json::array());
            if (!draft.empty()) {
                text += "<p>밴픽 · ";
                for (const auto& action : draft)
                    text += std::string(action.at("team")==0?"우리 ":"상대 ") +
                            (action.at("action")=="ban"?"밴 ":"픽 ") +
                            Escape(ChampionName(action.at("champion").get<std::string>()))+"　";
                text += "</p>";
            }
        }
        std::size_t clipIndex = 0;
        for (const auto& set : state.at("sets")) {
            for (const auto& clip : set.at("highlights"))
                text += "<button id='highlight-"+id+"-"+std::to_string(clipIndex++)+"'>"+
                        Escape(clip.at("label").get<std::string>())+"</button>";
        }
        return text;
    }
    std::string OnlineFixtures(bool fetch) {
        const auto route = L"fixtures?id=" + std::to_wstring(career.at("id").get<int>());
        if (fetch) { ++calendar_generation; cached_fixtures = online::Request(route,online_token).at("fixtures"); }
        const auto& fixtures = cached_fixtures;
        std::string rows = std::string("<h2>경기 일정</h2>")+"<button id='fixture-refresh'>새로고침</button>";
        if (fixtures.empty()) rows += "<p>예정된 연습 경기가 없습니다.</p>";
        for (const auto& game : fixtures) {
            const auto state = game.at("state").get<std::string>();
            rows += "<div class='row'>시즌 " + game.at("season").dump() + " · " +
                game.at("week").dump() + "주 · " + Escape(game.at("opponent").get<std::string>()) + " · ";
            if (state == "finished")
                rows += game.at("result").at("winner") == 0 ? "승리" : "패배";
            else if (state == "queued") rows += "경기 계산 대기 / 진행 중";
            else if (state == "failed") rows += "경기 계산 실패";
            else rows += "예정";
            rows+="<button id='match-open-"+game.at("id").dump()+"'>"+std::string(state=="queued"?"경기 진행":state=="finished"?"결과 · 다시보기":"일정 상세")+"</button>";
            if (state == "finished" && game.value("series",Json{}).is_null()) {
                const auto clips = game.at("result").value("highlights",Json::array());
                for (std::size_t i=0;i<clips.size();++i)
                    rows += "<button id='highlight-"+game.at("id").dump()+"-"+std::to_string(i)+"'>"+
                            Escape(clips[i].at("label").get<std::string>())+"</button>";
            }
            rows += "</div>";
        }
        return rows;
    }
    void OpenMatch(int fixture,bool fetch=true) {
        if(fetch)cached_fixtures=online::Request(L"fixtures?id="+std::to_wstring(career.at("id").get<int>()),online_token).at("fixtures");
        Json game;
        for(const auto& item:cached_fixtures)if(item.at("id")==fixture){game=item;break;}
        if(game.is_null()){Notice("경기를 찾을 수 없습니다.");return;}
        Home(false);Display("overview-page",false);Display("directory",false);Display("page-pane",true);
        active_match=fixture;match_game=game;calendar_key=online_token+":"+career.at("id").dump();++calendar_generation;
        Highlight("match");
        document->GetElementById("page-title")->SetInnerRML("경기 진행");
        document->GetElementById("page-subtitle")->SetInnerRML(Escape(career.at("club").get<std::string>())+" vs "+Escape(game.at("opponent").get<std::string>()));
        std::string body="<div class='card'><h1>"+Escape(career.at("club").get<std::string>())+" vs "+Escape(game.at("opponent").get<std::string>())+"</h1><button id='match-open-"+std::to_string(fixture)+"'>새로고침</button>";
        body+=SeriesControls(game);
        if(game.value("series",Json{}).is_null())body+="<p>"+std::string(game.at("state")=="scheduled"?"예정된 경기입니다. 경기 주차가 되면 진행할 수 있습니다.":game.at("state")=="failed"?"경기 처리에 실패했습니다.":"경기 결과를 불러오는 중입니다.")+"</p>";
        body+="</div>";
        document->GetElementById("page-body")->SetInnerRML(body);
        Rml::ElementList buttons;document->GetElementById("page-body")->GetElementsByTagName(buttons,"button");
        for(auto* button:buttons)button->AddEventListener("click",this);
    }
    void OpenCurrentMatch() {
        cached_fixtures=online::Request(L"fixtures?id="+std::to_wstring(career.at("id").get<int>()),online_token).at("fixtures");
        for(const auto& game:cached_fixtures)if(game.at("state")=="queued"){OpenMatch(game.at("id").get<int>(),false);return;}
        for(const auto& game:cached_fixtures)if(game.at("state")=="scheduled"){OpenMatch(game.at("id").get<int>(),false);return;}
        if(!cached_fixtures.empty()){OpenMatch(cached_fixtures.back().at("id").get<int>(),false);return;}
        Home(false);Display("overview-page",false);Display("page-pane",true);Highlight("match");
        document->GetElementById("page-title")->SetInnerRML("경기 진행");
        document->GetElementById("page-subtitle")->SetInnerRML("");
        document->GetElementById("page-body")->SetInnerRML("<div class='card'><h2>진행할 경기가 없습니다.</h2><p>달력에서 다음 경기 일정을 확인하세요.</p></div>");
    }
    void OpenOnline(const Json& item) {
        local_career = career;
        career = {{"manager",item.value("manager",online_manager)},{"club",item.at("name")},{"week",item.at("week")},
                  {"season",item.at("season")},{"id",item.at("id")},{"version",item.at("version")},{"role",item.at("role")}};
        career["club_profile"]=item.value("club_profile",Json::object());
        career["league_operator"]=item.value("league_operator",false);
        news_competition=JText(career["club_profile"], "league", "LCK CL");
        forum_league=news_competition;
        const auto settings = item.value("settings",Json::object());
        for (const auto& [key,value] : settings.items())
            career[key] = value;
        online_active = true;
        online_roster=online::Request(L"recruitment?id="+std::to_wstring(career.at("id").get<int>()),online_token).at("roster");
        Home();
        Notice(item.value("role","")=="viewer"?"유저 팀을 구경합니다.":"온라인 리그에 연결됐습니다.");
    }
    Application() {
        std::ifstream database("assets/people.json");
        people=Json::parse(database).at("people");
        std::ifstream logos("assets/club-assets.json");
        if(logos) logos>>club_assets;
        char* directory=SDL_GetPrefPath("RiftManager","Native");
        if(!directory)throw std::runtime_error(SDL_GetError());
        save_path=fs::u8path(directory)/"ui-cache.json";
        session_path=fs::u8path(directory)/"session.json";
        SDL_free(directory);
    }
    void Notice(const std::string& text) {
        document->GetElementById("notice")->SetInnerRML(Escape(text));
    }
    std::string Value(const char* id) {
        auto* input = dynamic_cast<Rml::ElementFormControl*>(document->GetElementById(id));
        return input ? input->GetValue() : "";
    }
    void Display(const char* id, bool visible) {
        document->GetElementById(id)->SetProperty("display", visible ? "block" : "none");
    }
    void ShowLobby() {
        search_pending.clear();search_requested.clear();Display("global-results",false);
        calendar_key.clear();
        if (online_active) { career = nullptr; online_active = false; }
        Display("online-panel",false);
        Display("app-main",false);Display("app-header",false);Display("lobby",true);
        document->GetElementById("resume-title")->SetInnerRML(career.is_null()?"새로운 시즌을 시작하세요":Escape(career.value("club","")));
        document->GetElementById("resume-description")->SetInnerRML(career.is_null()?"저장된 구단이 없습니다.":Escape(career.value("manager",""))+" / "+std::to_string(career.value("week",1))+"주차");
    }
    void ShowShell() { Display("lobby",false);Display("app-main",true);Display("app-header",true); }
    void Home(bool fetch_dashboard=true) {
        if(fetch_dashboard)active_match=0;
        if(!online_active || career.is_null()) { ShowLobby(); return; }
        calendar_key.clear();
        highlight = nullptr;
        ShowShell();
        Display("directory", false);
        Display("page-pane", false);
        Display("overview-page", true);
        Highlight("overview");
        Display("setup", career.is_null());
        Display("career", !career.is_null());
        Display("legacy-overview",!online_active);Display("online-dashboard",online_active);
        if(online_active && fetch_dashboard) {
            dashboard_state=online::Request(L"dashboard?id="+std::to_wstring(career.at("id").get<int>()),online_token);
            document->GetElementById("online-dashboard")->SetInnerRML(DashboardBody(dashboard_state));
            BindDashboard();
        }
        if (!career.is_null()) {
            document->GetElementById("club-title")->SetInnerRML(Escape(career.at("club").get<std::string>()));
            const int week = career.at("week");
            const std::string phase = week <= 10 ? "스토브" : week <= 20 ? "시즌 초 대회" : week <= 46 ? "국내 정규리그" : week <= 58 ? "국내 플레이오프" : week <= 88 ? "국제대회" : week <= 92 ? "승강전" : week <= 100 ? "이동 및 휴식" : "결산";
            document->GetElementById("career-state")->SetInnerRML(
                Escape(career.at("manager").get<std::string>()) + " / " + std::to_string(career.at("season").get<int>()) +
                "시즌 " + std::to_string(week) + "주 / " + phase +
                (career.value("role","")=="viewer"?" / 구경":""));
            document->GetElementById("week-plan")->SetInnerRML(phase + " / " + std::to_string(week) + "주차");
            document->GetElementById("club-info")->SetInnerRML(
                "감독 " + Escape(career.at("manager").get<std::string>()));
            document->GetElementById("advance")->SetInnerRML(online_active?(career.value("league_operator",false)?"온라인 리그 턴 진행":"준비 완료 · 진행 투표"):"검증용 주차 진행");
            const auto next_match=dashboard_state.value("next_fixture",Json{});
            const bool match_due=!next_match.is_null() && next_match.value("state","")=="queued";
            document->GetElementById("league-advance")->SetInnerRML(match_due?"경기 진행":career.value("league_operator",false)?"리그 턴 진행":"준비 완료");
            std::string roster;
            int registered = 0;
            for (const auto& person : (online_active?online_roster:people)) {
                if (person.value("team", "") != career.at("club")) continue;
                roster += "<div class='row person' id='person-"+person.value("id","")+"'>" + Escape(PersonName(person)) + " / " +
                          Escape(person.value("raw_role", "")) + " / 계약 " + Escape(person.value("contract_end", "")) + "</div>";
                ++registered;
            }
            if (!registered) roster = "<p>선수단을 구성하세요.</p>";
            document->GetElementById("roster")->SetInnerRML(roster);
            BindPeople("roster");
            document->GetElementById("calendar")->SetInnerRML(
                "<div class='row'>1~10주 · 스토브</div><div class='row'>11~20주 · 시즌 초 대회</div>"
                "<div class='row'>21~46주 · 국내 정규리그</div><div class='row'>47~58주 · 국내 플레이오프</div>"
                "<div class='row'>59~88주 · 국제대회</div><div class='row'>89~92주 · 승강전</div>"
                "<div class='row'>93~100주 · 이동 및 휴식</div><div class='row'>101~104주 · 결산</div>"
                "<p>시즌 구성 초안 · 실제 대회별 경기 일정은 아직 연결되지 않았습니다.</p>");

        }
    }
    void Save() {
        if(!online_active)throw std::runtime_error("온라인 리그에서 구단을 선택하세요.");
    }
    void Database() {
        if (career.is_null()) { Notice("구단 설정을 먼저 완료하세요."); return; }
        Home(false); Display("overview-page", false); Display("directory", true); Highlight("people");
        Json matches=Json::array();
        int total=0;
        if(online_active) {
            const auto query="people?id="+career.at("id").dump()+"&page="+std::to_string(std::max(0,page))+"&query="+UrlEncode(people_query);
            const auto result=online::Request(std::wstring(query.begin(),query.end()),online_token);
            matches=result.at("people"); total=result.at("total");
        } else {
            for(const auto& person:people) {
                const auto text=PersonName(person)+" "+person.value("nickname","")+" "+person.value("team","");
                if(people_query.empty() || text.find(people_query)!=std::string::npos) matches.push_back(person);
            }
            total=static_cast<int>(matches.size());
        }
        const int last_page=std::max(0,(total-1)/150);
        if(online_active && page>last_page) { page=last_page; Database(); return; }
        page = std::clamp(page, 0, last_page);
        std::string rows;
        const int first=online_active?0:page*150;
        for (int i = first; i < std::min(static_cast<int>(matches.size()), first+150); ++i) {
            const auto& person = matches[i];
            rows += "<div class='row person' id='person-"+person.value("id","")+"'>" + Face(person) + Escape(PersonName(person)) + " / " + Escape(person.value("team", "")) +
                " / " + Escape(person.value("league", "")) + " / 계약 " + Escape(person.value("contract_end", "")) +
                (person.value("contract_estimated", false) ? " (게임용 추정)" : "") + "</div>";
        }
        document->GetElementById("rows")->SetInnerRML(rows);
        BindPeople("rows");
        document->GetElementById("page-label")->SetInnerRML(std::to_string(total) + "명 / " + std::to_string(page + 1) + "페이지");
    }
    void Highlight(const std::string& key) {
        const std::pair<const char*,const char*> groups[]={
            {"club","|overview|mail|news|vision|profile|community|"},
            {"squad","|first|academy|staff|relations|medical|people|solo|"},
            {"preparation","|tactics|training|"},{"recruitment","|transfers|shortlist|transfer-budget|staff-search|staff-transfers|"},
            {"competition","|calendar|competition|data|match|"},{"operations","|finance|admin|"}};
        for(const auto& group:groups)if(auto* element=document->GetElementById(std::string("nav-select-")+group.first))
            element->SetClass("active",std::string(group.second).find("|"+key+"|")!=std::string::npos);
        for (const auto& entry : Navigation) {
            if (auto* element = document->GetElementById(std::string("nav-")+entry.first))
                element->SetClass("active", key == entry.first);
        }
    }
    void OpenPage(const std::string& key, bool fetch_calendar=true) {
        active_match=0;
        if(key=="match"){OpenCurrentMatch();return;}
        if(key=="community") { CommunityBoard();return; }
        if (career.is_null()) { Notice("구단 설정을 먼저 완료하세요."); return; }
        if (key=="overview") { Home(); return; }
        if (key=="people") { Database(); return; }
        Home(false); Display("overview-page",false); Display("page-pane",true); Highlight(key);
        std::string title;
        for (const auto& entry : Navigation) if (key==entry.first) title=entry.second;
        document->GetElementById("page-title")->SetInnerRML(title);
        document->GetElementById("page-subtitle")->SetInnerRML(Escape(career.at("club").get<std::string>())+" / "+title);
        std::string body;
        if (key=="news") {
            if (!online_active) body="<p>뉴스와 팔로우는 온라인 커리어에서 이용할 수 있습니다.</p>";
            else body=NewsBody();
        } else if (key=="solo" && online_active) {
            body=SoloBody();
        } else if (key=="calendar") {
            body=ScheduleBody(fetch_calendar);
            if (online_active) calendar_key = online_token+":"+career.at("id").dump();
        } else if (key=="admin" && online_active) {
            const auto rules=online::Request(L"competition-rules?id="+std::to_wstring(career.at("id").get<int>()),online_token).at("rules");
            body="<h2>대회 단계별 시리즈 규칙</h2><p>이미 예약된 경기의 규칙은 유지됩니다. 운영자 변경은 게임용 규칙으로 기록됩니다.</p>";
            for(const auto& rule:rules)
                body+="<div class='row'>"+Escape(rule.at("competition").get<std::string>())+" / "+Escape(rule.at("stage").get<std::string>())+
                    " · BO"+rule.at("best_of").dump()+"<p>출처 · "+Escape(rule.at("source").get<std::string>())+"</p></div>";
            if(career.value("league_operator",false))
                body+="<label>대회</label><input id='rule-competition' type='text' maxlength='120'/><label>단계</label>"
                    "<input id='rule-stage' type='text' maxlength='80'/><select id='rule-format'><option value='3'>BO3</option>"
                    "<option value='5'>BO5</option></select><button id='rule-save'>규칙 저장</button>";
        } else if (online_active && (key=="transfers" || key=="staff-transfers")) {
            body=TransferBody(key=="staff-transfers");
        } else if (online_active && IsManagementPage(key)) {
            body=ManagementBody(key);
        } else if (key=="profile") {
            body="<div class='row'>감독 "+Escape(career.at("manager").get<std::string>())+"</div>"
                 "<div class='row'>계약 · 연봉 · 감독 능력치는 아직 이전되지 않았습니다.</div>";
        } else if (key=="staff-search" && online_active) {
            const auto query="people?id="+career.at("id").dump()+"&kind=staff&query="+UrlEncode(staff_query);
            const auto result=online::Request(std::wstring(query.begin(),query.end()),online_token);
            body="<p>단장 1 · 수석 코치 1 · 코치 2 · 커뮤니티 3 · 데이터분석 3 · 팀 닥터 5</p><input id='staff-query' type='text' maxlength='120' value='"+Escape(staff_query)+"'/><button id='staff-search-go'>스태프 검색</button><button id='staff-generate'>전문 스태프 후보 모집</button>";
            for(const auto& p:result.at("people")) body+="<div class='row person' id='person-"+p.at("id").get<std::string>()+"'>"+Escape(PersonName(p))+" · "+Escape(p.value("staff_role_name",p.value("raw_role","")))+" / "+Escape(p.value("team",""))+"</div>";
        } else if ((key=="first" || key=="staff") && online_active) {
            recruitment_page=key;
            const auto state=online::Request(L"recruitment?id="+std::to_wstring(career.at("id").get<int>()),online_token);
            const bool complete=state.value("complete",false);
            const bool takeover=state.value("mode",std::string{})=="takeover";
            body=takeover?"<p>실제 구단의 GCD 등록 명단입니다. 원본 역할 미분류 인물의 포지션 지정은 게임 내 감독 설정으로 보존됩니다.</p>":complete?"<p>프로 데뷔를 마친 선발과 스태프입니다. 일반인은 대화로 유망주가 된 뒤에만 데뷔합니다.</p>":"<p>일반인은 바로 선발되지 않습니다. 대화가 통하면 유망주가 되고, 솔로랭크 실버 I 이후에 프로 데뷔를 시킵니다. 코치 선발은 그대로입니다.</p>";
            if(key=="staff") {
                for(const auto& pos:state.at("staff_limits")) body+="<span>"+Escape(pos.at("name").get<std::string>())+" "+pos.at("count").dump()+"/"+pos.at("limit").dump()+"　</span>";
                if(career.value("role","")=="admin") {
                    body+="<p><button id='staff-generate'>전문 스태프 후보 모집</button></p><select id='staff-position-person'>";
                    for(const auto& p:state.at("staff")) body+="<option value='"+p.at("id").get<std::string>()+"'>"+Escape(PersonName(p))+"</option>";
                    body+="</select><select id='staff-position-role'>";
                    for(const auto& pos:state.at("staff_limits")) body+="<option value='"+pos.at("role").get<std::string>()+"'>"+Escape(pos.at("name").get<std::string>())+"</option>";
                    body+="</select><button id='staff-position-save'>스태프 직책 지정</button>";
                }
            }
            if((takeover || complete) && career.value("role","")=="admin") {
                body+="<select id='club-person'>";
                for(const auto& person:state.at("people")) body+="<option value='"+person.at("id").get<std::string>()+"'>"+Escape(PersonName(person))+" · "+Escape(person.value("nickname",""))+"</option>";
                body+="</select><select id='club-role'><option value='TOP'>탑</option><option value='JUNGLE'>정글</option><option value='MID'>미드</option><option value='ADC'>원딜</option><option value='SUPPORT'>서폿</option><option value='COACH'>코치</option></select>"
                    "<select id='club-squad'><option value='first'>1군 선발</option><option value='reserve'>후보</option><option value='academy'>2군 · 유소년</option><option value='staff'>스탭</option></select><button id='club-assign'>등록 인물 포지션 · 선수단 저장</button>";
            }
            if(state.at("people").empty() && career.value("role","")=="admin") body+="<button id='recruit-start'>초기 후보 모집</button>";
            for(const auto& person:state.at("people")) {
                const bool coach=person.value("kind","")!="player",selected=person.value("assignment","")!="candidate";
                if(takeover) { if(key=="staff" && person.value("assignment","")!="staff") continue; }
                else if(coach!=(key=="staff") || (complete && !selected)) continue;
                const auto pid=person.at("id").get<std::string>();
                const auto solo=person.value("solo",Json::object());
                const auto path=solo.value("path",std::string{});
                body+="<div class='row person' id='person-"+pid+"'>"+Face(person)+Escape(PersonName(person))+" · "+Escape(person.value("nickname",""))+" / "+
                    Escape(person.value("role",std::string{}))+" · "+Escape(solo.value("path_name",person.value("assignment",std::string{})))+
                    (solo.contains("label")?" · "+Escape(solo.at("label").get<std::string>()):"")+
                    (solo.contains("personality")?" · "+Escape(solo.at("personality").get<std::string>()):"")+"</div>";
                if(!takeover && !complete && career.value("role","")=="admin" && coach) body+="<button id='recruit-"+std::string(selected?"drop-":"pick-")+pid+"'>"+(selected?"선택 해제":"선발")+"</button>";
                if(!takeover && career.value("role","")=="admin" && !coach && path=="amateur") body+="<button id='recruit-talk-"+pid+"'>대화</button>";
                if(career.value("role","")=="admin" && !coach && path=="prospect") body+="<button id='recruit-debut-"+pid+"'>프로 데뷔</button>";
            }
            if(!complete && career.value("role","")=="admin") body+="<button id='recruit-finalize'>5명 선수단 확정</button>";
        } else if (key=="first" || key=="staff" || key=="staff-search") {
            for (const auto& person : people) {
                const bool coach=person.value("kind","")=="coach";
                if (key!="staff-search" && person.value("team","")!=career.at("club")) continue;
                if ((key=="staff" || key=="staff-search") && !coach) continue;
                if (key=="first" && person.value("kind","")!="player") continue;
                body+="<div class='row person' id='person-"+person.value("id","")+"'>"+Face(person)+Escape(PersonName(person))+" / "+Escape(person.value("team",""))+
                      " / "+Escape(person.value("raw_role",""))+" / 계약 "+Escape(person.value("contract_end",""))+"</div>";
            }
            if (body.empty()) body="<p>확인된 등록 명단이 없습니다. 원본에서 역할이 없는 인물은 선수 DB에서 볼 수 있습니다.</p>";
        } else if (key=="competition" && online_active) {
            body=CompetitionBody();
        } else if (key=="data" && online_active) {
            const auto query="analytics?id="+career.at("id").dump()+"&season="+career.at("season").dump();
            const auto stats=online::Request(std::wstring(query.begin(),query.end()),online_token);
            body="<p>게임 내 실제 계산된 경기 기록 · "+stats.at("series").dump()+"시리즈 / "+stats.at("sets").dump()+"세트</p><h2>선수 기록</h2>";
            for(const auto& p:stats.at("players")) body+="<div class='row person' id='person-"+p.at("id").get<std::string>()+"'>"+Escape(p.at("name").get<std::string>())+
                " · "+p.at("games").dump()+"경기 · 승률 "+p.at("win_rate").dump()+"% · KDA "+p.at("kda").dump()+" · CS "+p.at("cs").dump()+" · 누적 피해량 "+p.at("damage").dump()+"</div>";
            body+="<h2>챔피언 출전 · 밴</h2>";
            for(const auto& c:stats.at("champions")) body+="<div class='row'>"+Escape(c.at("champion").get<std::string>())+" · "+c.at("games").dump()+"회 출전 / "+c.at("bans").dump()+"회 밴 · 승률 "+(c.at("win_rate").is_null()?"기록 없음":c.at("win_rate").dump()+"%")+"</div>";
            if(stats.at("series")==0) body+="<p>완료된 경기가 없습니다. 시리즈가 종료되면 집계됩니다.</p>";
        } else if (key=="competition" || key=="data") {
            std::map<std::string,int> leagues;
            for (const auto& person:people) ++leagues[person.value("league","")];
            body="<p>GCD 등록 인원 / 경기 순위와 승률은 아직 연결되지 않았습니다.</p>";
            for (const auto& league:leagues)
                body+="<div class='row'>"+Escape(league.first)+" / "+std::to_string(league.second)+"명</div>";
        } else if (key=="shortlist" && online_active) {
            const auto items=online::Request(L"shortlist?id="+std::to_wstring(career.at("id").get<int>()),online_token).at("people");
            body="<p>내 계정의 영입 검토 명단 · 프로필에서 추가할 수 있습니다.</p>";
            for(const auto& person:items)
                body+="<div class='row person' id='person-"+person.at("id").get<std::string>()+"'>"+Escape(PersonName(person))+" / "+
                    Escape(person.value("team",""))+"</div><button id='shortlist-remove-"+person.at("id").get<std::string>()+"'>명단에서 제외</button>";
            if(items.empty()) body+="<p>영입 검토 명단이 비어 있습니다.</p>";
        } else if (key=="mail" && online_active) {
            const auto messages=online::Request(L"inbox?id="+std::to_wstring(career.at("id").get<int>()),online_token).at("messages");
            for(const auto& mail:messages)
                body+="<div class='card'><small>"+std::string(mail.at("read").get<int>()?"읽음":"새 우편")+" · "+mail.at("season").dump()+"시즌 "+mail.at("week").dump()+
                    "주</small><h2>"+Escape(mail.at("subject").get<std::string>())+"</h2><p>"+Escape(mail.at("body").get<std::string>())+
                    "</p><button id='mail-read-"+mail.at("id").dump()+"'>읽음 표시</button></div>";
            if(messages.empty()) body="<p>도착한 우편이 없습니다.</p>";
        } else if (key=="mail") {
            body="<div class='row'>구단 커리어가 시작됐습니다.</div><div class='row'>현재 "+
                 std::to_string(career.at("week").get<int>())+"주차입니다.</div>";
        } else if (key=="tactics" || key=="training") {
            body=key=="tactics"?"<p>선택한 전술은 이 구단의 경기에 반영됩니다.</p>":"<p>선택한 훈련은 다음 주차의 성장과 피로에 반영됩니다.</p>";
            const char* tactics[]={"균형","오브젝트 중심","한타 중심","사이드 압박"};
            const char* training[]={"기본기","라인 관리","시야와 합류","휴식"};
            for(int index=0;index<4;++index)
                body+="<button id='choice-"+std::to_string(index)+"'>"+
                       std::string(key=="tactics"?tactics[index]:training[index])+"</button>";
            body+="<p>현재 설정 · "+Escape(career.value(key,std::string("미설정")))+"</p>";
        } else {
            body="<p>이 화면의 상세 기능은 아직 연결되지 않았습니다.</p>";
        }
        document->GetElementById("page-body")->SetInnerRML(body);
        BindPeople("page-body");
        if(key=="competition") {
            Rml::ElementList buttons;document->GetElementById("page-body")->GetElementsByTagName(buttons,"button");
            for(auto* button:buttons)button->AddEventListener("click",this);
        }
        if(online_active && (key=="transfers" || key=="staff-transfers")) {
            Rml::ElementList buttons;document->GetElementById("page-body")->GetElementsByTagName(buttons,"button");
            for(auto* button:buttons) if(button->GetId().rfind("deal-",0)==0) button->AddEventListener("click",this);
        }
        if(online_active && IsManagementPage(key)) {
            Rml::ElementList buttons;document->GetElementById("page-body")->GetElementsByTagName(buttons,"button");
            for(auto* button:buttons) if(button->GetId().rfind("mg-",0)==0) button->AddEventListener("click",this);
        }
        if ((key=="mail" || key=="shortlist" || key=="first" || key=="staff" || key=="staff-search" || key=="solo") && online_active) {
            Rml::ElementList buttons;
            document->GetElementById("page-body")->GetElementsByTagName(buttons,"button");
            for(auto* button:buttons) button->AddEventListener("click",this);
        }
        if (key=="news" && online_active) {
            Rml::ElementList buttons;
            document->GetElementById("page-body")->GetElementsByTagName(buttons,"button");
            for (auto* button:buttons) button->AddEventListener("click",this);
        }
        if (key=="calendar" && online_active) {
            Rml::ElementList buttons;
            document->GetElementById("page-body")->GetElementsByTagName(buttons,"button");
            for (auto* button : buttons)
                if (button->GetId().rfind("cal-",0)==0 || button->GetId().rfind("match-open-",0)==0 || button->GetId().rfind("highlight-",0)==0 || button->GetId().rfind("draft-",0)==0 ||
                    button->GetId().rfind("feedback-",0)==0 || button->GetId().rfind("swap-",0)==0 || button->GetId()=="fixture-refresh")
                    button->AddEventListener("click",this);
        }
        if (auto* create = document->GetElementById("league-create")) create->AddEventListener("click",this);
        if (auto* save = document->GetElementById("rule-save")) save->AddEventListener("click",this);
        if (auto* add = document->GetElementById("fixture-add")) add->AddEventListener("click", this);
        if (key=="tactics" || key=="training") {
            active_setting=key;
            for(int index=0;index<4;++index)
                document->GetElementById("choice-"+std::to_string(index))->AddEventListener("click",this);
        }
    }
    void BindPeople(const char* container) {
        Rml::ElementList rows;
        document->GetElementById(container)->GetElementsByTagName(rows,"div");
        for (auto* row:rows)
            if (row->GetId().rfind("person-",0)==0) row->AddEventListener("click",this);
    }
    std::string active_setting;
    Json dashboard_state;
    std::string CashChart(const Json& points) {
        if(points.empty())return "";
        long long low=points[0].at("cash"),high=low;
        for(const auto& p:points){const auto value=p.at("cash").get<long long>();low=std::min(low,value);high=std::max(high,value);}
        if(high==low){low-=1;high+=1;}
        std::string path;
        for(size_t i=0;i<points.size();++i) {
            const double x=10+280.0*i/std::max<size_t>(1,points.size()-1);
            const double y=125-110.0*(points[i].at("cash").get<long long>()-low)/(high-low);
            path+=std::to_string(x)+","+std::to_string(y)+" ";
        }
        const auto file=save_path.parent_path()/("cash-chart-"+std::to_string(SDL_GetTicksNS())+".svg");
        std::ofstream out(file,std::ios::binary);
        out<<"<svg xmlns='http://www.w3.org/2000/svg' width='300' height='140' viewBox='0 0 300 140'><rect width='300' height='140' fill='#14151f'/><path d='M10 15H290M10 70H290M10 125H290' stroke='#393148'/><polyline points='"<<path<<"' fill='none' stroke='#ed65df' stroke-width='3'/></svg>";
        out.close();const auto utf=file.generic_u8string();return std::string(utf.begin(),utf.end());
    }
    std::string DashboardBody(const Json& d) {
        std::string body="<div class='fm-dashboard'><div class='fm-column' style='width:24%'><div class='fm-panel fm-inbox'><h2>우편함</h2>";
        for(const auto& mail:d.at("inbox")) body+="<button id='dash-mail-"+mail.at("id").dump()+"' class='"+std::string(mail.at("read").get<int>()?"":"unread")+"'><small>"+mail.at("season").dump()+"시즌 "+mail.at("week").dump()+"주 · "+(mail.at("read").get<int>()?"읽음":"새 우편")+"</small><br/>"+Escape(mail.at("subject").get<std::string>())+"</button>";
        if(d.at("inbox").empty())body+="<p>도착한 우편이 없습니다.</p>";
        body+="<button id='dash-go-mail'>우편함 전체 보기</button></div></div><div class='fm-column' style='width:28%'><div class='fm-panel'><h2>뉴스</h2>";
        for(const auto& item:d.at("news"))body+="<div class='fm-news-item'><small>"+Escape(item.value("label",std::string("게임 내 가상 기사")))+" · "+item.at("week").dump()+"주</small><p>"+Escape(item.at("headline").get<std::string>())+"</p></div>";
        if(d.at("news").empty())body+="<p>새 구단 뉴스가 없습니다.</p>";
        body+="<button id='dash-go-news'>뉴스 전체 보기</button></div><div class='fm-panel'><h2>다음 경기 일정</h2>";
        const auto next=d.at("next_fixture");
        if(next.is_object())body+="<button id='dash-opponent'>"+Escape(next.at("opponent").get<std::string>())+"</button><p>"+next.at("season").dump()+"시즌 "+next.at("week").dump()+"주 · BO"+next.at("best_of").dump()+"</p><small>"+Escape(next.at("competition").get<std::string>())+" / "+Escape(next.at("stage").get<std::string>())+"</small>";
        else body+="<p>예정된 경기가 없습니다.</p>";
        body+="<button id='dash-go-calendar'>달력 · 경기 일정</button></div></div><div class='fm-column' style='width:28%'><div class='fm-panel'><h2>"+Escape(d.at("league").get<std::string>())+" 순위</h2><div class='fm-table-row'><span class='position'>순위</span><span class='team-name'>구단</span><span class='record'>경기</span><span class='record'>승</span><span class='record'>패</span></div>";
        const auto& table=d.at("standings");
        for(size_t i=0;i<table.size();++i){const auto& r=table[i];if(i>=14 && r.at("team")!=d.at("club"))continue;
            body+="<div class='fm-table-row "+std::string(r.at("team")==d.at("club")?"self":"")+"'><span class='position'>"+(r.at("rank").is_null()?"-":r.at("rank").dump())+"</span><button class='team-name' id='dash-team-"+std::to_string(i)+"'>"+Logo(d.at("league").get<std::string>(),r.at("team").get<std::string>())+Escape(r.at("team").get<std::string>())+"</button><span class='record'>"+r.at("played").dump()+"</span><span class='record'>"+r.at("wins").dump()+"</span><span class='record'>"+r.at("losses").dump()+"</span></div>";
        }
        body+="<button id='dash-go-competition'>리그 전체 보기</button></div><div class='fm-panel'><h2>선발 5명 성적 · 평점 1.0~9.9</h2>";
        for(const auto& p:d.at("lineup")){const auto& person=p.at("person");body+="<div class='fm-player'><div class='player-line person' id='person-"+person.at("id").get<std::string>()+"'>"+Face(person)+Escape(PersonName(person))+"<br/><small>"+Escape(person.value("role",""))+" · "+p.at("games").dump()+"경기 · "+p.at("kills").dump()+" / "+p.at("deaths").dump()+" / "+p.at("assists").dump()+"</small></div><span class='fm-rating'>"+(p.at("rating").is_null()?"-":p.at("rating").dump())+"</span></div>";}
        if(d.at("lineup").empty())body+="<p>먼저 온라인 선수단을 확정하세요.</p>";
        body+="<button id='dash-go-first'>선수단 관리</button></div></div><div class='fm-column' style='width:20%'><div class='fm-panel'><h2>다음 상대 · 최근 5경기</h2>";
        if(next.is_object())body+="<p>"+Escape(next.at("opponent").get<std::string>())+"</p>";
        for(const auto& game:d.at("opponent_form"))body+="<span class='fm-form "+std::string(game.at("won").get<bool>()?"win":"loss")+"'>"+(game.at("won").get<bool>()?"승":"패")+"</span>";
        if(d.at("opponent_form").empty())body+="<p>완료된 상대 경기 기록이 없습니다.</p>";
        else for(const auto& game:d.at("opponent_form"))body+="<p><small>"+Escape(game.at("opponent").get<std::string>())+" · "+game.at("score").dump()+"</small></p>";
        body+="</div><div class='fm-panel'><h2>영입 금액 · 예산</h2><div class='fm-money'>"+d.at("transfer_budget").dump()+"원</div><p>시즌 지출 "+d.at("transfer_spent").dump()+"원</p><button id='dash-go-transfer-budget'>예산 관리</button></div><div class='fm-panel'><h2>현금 추이</h2><div class='fm-money'>"+d.at("cash").dump()+"원</div><img class='fm-chart' src='"+Escape(CashChart(d.at("cash_history")))+"'/><small>회계 원장의 실제 잔액 추이</small><button id='dash-go-finance'>재정 상세</button></div></div></div>";
        return body;
    }
    void BindDashboard() {
        Rml::ElementList buttons;document->GetElementById("online-dashboard")->GetElementsByTagName(buttons,"button");for(auto* button:buttons)button->AddEventListener("click",this);
        BindPeople("online-dashboard");
    }
    std::string staff_query;
    std::string forum_category="all",forum_query;
    std::string forum_league="LCK";
    int forum_page=0;
    Json forum_post;
    int forum_user=0;
    bool forum_operator=false,forum_edit=false;
    void ForumShell() {
        calendar_key.clear();active_match=0;highlight=nullptr;
        if(online_token.empty()) throw std::runtime_error("커뮤니티를 이용하려면 온라인 계정에 로그인하세요.");
        ShowShell();Display("setup",false);Display("career",true);Display("overview-page",false);Display("directory",false);Display("page-pane",true);Highlight("community");
        document->GetElementById("club-title")->SetInnerRML("R/M 커뮤니티");
        document->GetElementById("career-state")->SetInnerRML("리그별 AI 팬 커뮤니티 · 감독 · 선수 · 팀 평가");
        document->GetElementById("page-title")->SetInnerRML("");document->GetElementById("page-subtitle")->SetInnerRML("");
    }
    void BindForum() {
        Rml::ElementList buttons;document->GetElementById("page-body")->GetElementsByTagName(buttons,"button");
        for(auto* button:buttons) button->AddEventListener("click",this);
    }
    static std::string ForumAuthor(const Json& author) {
        return "<span class='board-author'><img src='community-rank-"+author.at("level").dump()+".svg'/><span class='board-name'>"+Escape(author.at("name").get<std::string>())+"</span></span>";
    }
    static std::string ForumText(const std::string& input) {
        const auto escaped=Escape(input);std::string out;
        for(char c:escaped) { if(c=='\n') out+="<br/>";else if(c!='\r') out+=c; }return out;
    }
    void CommunityBoard() {
        ForumShell();
        Json data;
        {
            const auto route="community?league="+UrlEncode(forum_league)+"&category="+forum_category+"&page="+std::to_string(forum_page)+"&query="+UrlEncode(forum_query);
            data=online::Request(std::wstring(route.begin(),route.end()),online_token);
        }
        forum_page=data.at("page");
        std::string body="<div class='community'><h2>"+Escape(forum_league)+" 팬 커뮤니티</h2><p class='board-muted'>게임 속 AI 팬들의 글·닉네임·댓글·조회·추천입니다.</p><select id='forum-league'>";
        for(const auto& league:data.value("leagues",Json::array({forum_league}))) body+="<option value='"+Escape(league.get<std::string>())+"'>"+Escape(league.get<std::string>())+"</option>";
        body+="</select><button id='forum-league-go'>리그 게시판 이동</button><div class='board-tabs'>";
        const char* cats[]={"all","popular","general","manager","player","team","tactics","transfer","notice"};
        const char* labels[]={"전체","인기","잡담","감독평가","선수평가","팀평가","전술/밴픽","이적","공지"};
        for(int i=0;i<9;++i) body+="<button id='forum-cat-"+std::string(cats[i])+"'>"+labels[i]+"</button>";
        body+="</div><div class='board-row board-heading'><span class='board-category'>탭</span><span class='board-title'>제목</span><span class='board-author'><span>글쓴이</span></span><span class='board-date'>날짜</span><span class='board-count'>조회</span><span class='board-count'>추천</span></div>";
        for(const auto& p:data.at("posts")) body+="<div class='board-row "+std::string(p.value("pinned",false)?"notice":"")+"'><span class='board-category'>"+Escape(p.at("category_name").get<std::string>())+"</span><button class='board-title' id='forum-open-"+p.at("id").dump()+"'>"+Escape(p.at("title").get<std::string>())+"  "+p.at("comments").dump()+"</button>"+ForumAuthor(p.at("author"))+"<span class='board-date'>"+Escape(p.at("display_time").get<std::string>())+"</span><span class='board-count'>"+p.at("views").dump()+"</span><span class='board-count'>"+p.at("up").dump()+"</span></div>";
        if(data.at("posts").empty()) body+="<p>등록된 게시글이 없습니다.</p>";
        body+="<p class='board-muted'>"+data.at("total").dump()+"개 글 · "+std::to_string(forum_page+1)+"페이지</p><button id='forum-prev'>이전</button><button id='forum-next'>다음</button><input id='forum-query' type='text' maxlength='100' value='"+Escape(forum_query)+"'/><button id='forum-search'>평가 · 글 검색</button></div>";
        document->GetElementById("page-body")->SetInnerRML(body);BindForum();
        static_cast<Rml::ElementFormControl*>(document->GetElementById("forum-league"))->SetValue(forum_league);
    }
    void CommunityPost(int post_id) {
        ForumShell();Json data;
        data=online::Request(L"community-post?post="+std::to_wstring(post_id),online_token);
        forum_post=data.at("post");forum_user=data.at("user_id");forum_operator=data.value("operator",false);
        const auto& p=forum_post;
        std::string body="<div class='community'><button id='forum-list'>목록</button><span class='board-muted'>"+Escape(p.at("category_name").get<std::string>())+"</span><div class='board-meta'><h2>"+Escape(p.at("title").get<std::string>())+"</h2><span class='board-muted'>"+Escape(p.at("full_time").get<std::string>())+"</span></div><div class='board-meta'>"+ForumAuthor(p.at("author"))+"<span class='board-muted'>조회 "+p.at("views").dump()+"　추천 "+p.at("up").dump()+"　댓글 "+p.at("comments").dump()+"</span></div><div class='board-body'>"+ForumText(p.at("body").get<std::string>())+"</div><div class='board-votes'><button class='upvote' id='forum-up'>추천 "+p.at("up").dump()+"</button><span> "+p.at("score").dump()+" </span><button class='downvote' id='forum-down'>비추천 "+p.at("down").dump()+"</button><button id='forum-unvote'>추천 취소</button></div>";
        body=body.substr(0,body.find("<div class='board-votes'>"))+"<div class='board-votes'><span class='upvote'>AI 팬 추천 "+p.at("up").dump()+"</span>　"+p.at("score").dump()+"　<span class='downvote'>비추천 "+p.at("down").dump()+"</span></div><p class='board-muted'>게임 내 AI 팬 반응 · "+Escape(p.value("game_time",std::string("게임 내 게시글")))+"</p>";
        body+="<h2>댓글 "+p.at("comments").dump()+"</h2>";
        for(const auto& comment:p.at("comments_list")) body+="<div class='board-comment'>"+ForumAuthor(comment.at("author"))+"<span class='board-muted'>"+Escape(comment.at("full_time").get<std::string>())+"</span><p>"+ForumText(comment.at("body").get<std::string>())+"</p></div>";
        body+="<button id='forum-list'>목록으로</button></div>";
        document->GetElementById("page-body")->SetInnerRML(body);BindForum();
    }
    void CommunityCompose(bool editing) {
        forum_edit=editing;ForumShell();
        std::string body="<div class='community'><h2>"+std::string(editing?"게시글 수정":"게시글 작성")+"</h2><select id='forum-compose-category'>";
        const char* cats[]={"general","question","issue","media","season","event","notice"};const char* names[]={"자유","질문","버그/이슈","미디어","시즌결산","이벤트","공지 · 운영자"};
        for(int i=0;i<7;++i) body+="<option value='"+std::string(cats[i])+"'>"+names[i]+"</option>";
        body+="</select><label>제목</label><input id='forum-compose-title' type='text' maxlength='100' value='"+Escape(editing?forum_post.at("title").get<std::string>():"")+"'/><label>본문</label><textarea id='forum-compose-body' maxlength='20000'>"+Escape(editing?forum_post.at("body").get<std::string>():"")+"</textarea><button id='forum-compose-save'>게시글 저장</button><button id='forum-list'>목록으로</button></div>";
        document->GetElementById("page-body")->SetInnerRML(body);BindForum();
        if(editing) static_cast<Rml::ElementFormControl*>(document->GetElementById("forum-compose-category"))->SetValue(forum_post.at("category").get<std::string>());
    }
    std::string transfer_person;
    std::string TransferBody(bool staff) {
        const auto id=std::to_wstring(career.at("id").get<int>());
        const auto offers=online::Request(L"transfer-offers?id="+id,online_token).at("offers");
        const auto events=online::Request(L"transfer-activity?id="+id+(staff?L"&kind=coach":L""),online_token).at("events");
        std::string body="<p>온라인 리그 전체 이적 · 게임 내 협상과 계약입니다. 인물 프로필에서 에이전트에게 접촉할 수 있습니다.</p><h2>우리 구단 협상</h2>";
        for(const auto& offer:offers) {
            const auto& person=offer.at("person");if(staff && person.value("kind","")=="player") continue;
            const auto oid=offer.at("id").dump(),phase=offer.at("state").get<std::string>();
            body+="<div class='card'><div class='row person' id='person-"+person.at("id").get<std::string>()+"'>"+Escape(PersonName(person))+" / "+Escape(person.value("team",""))+"</div><p>상태 · "+Escape(phase)+" / "+offer.at("years").dump()+"시즌 / 연봉 "+std::to_string(std::max(offer.at("annual_salary").get<long long>(),offer.at("asking_salary").get<long long>()))+"원 / 이적료 "+std::to_string(std::max(offer.at("fee").get<long long>(),offer.at("asking_fee").get<long long>()))+"원</p>";
            if(career.value("role","")=="admin") {
                if(offer.at("direction")=="incoming" && (phase=="quoted" || phase=="ready")) body+="<button id='deal-accept-"+oid+"'>위 조건 동의 · 영입 진행</button>";
                if(offer.at("direction")=="outgoing" && phase=="seller_pending") body+="<button id='deal-approve-"+oid+"'>이적 허용</button><button id='deal-decline-"+oid+"'>이적 거절</button><input id='deal-fee-"+oid+"' type='text' maxlength='13'/><button id='deal-counter-"+oid+"'>이적료 역제안</button>";
                if(offer.at("direction")=="incoming" && phase!="completed" && phase!="cancelled" && phase!="declined") body+="<button id='deal-cancel-"+oid+"'>협상 철회</button>";
            }
            body+="</div>";
        }
        body+="<h2>온라인 리그 이적 활동</h2>";
        for(const auto& e:events) body+="<div class='row person' id='person-"+e.at("person_id").get<std::string>()+"'>"+e.at("season").dump()+"시즌 "+e.at("week").dump()+"주 · "+Escape(e.at("buyer_name").get<std::string>())+" 영입 · 게임 이적료 "+e.at("fee").dump()+"원</div>";
        if(events.empty()) body+="<p>아직 확정된 이적이 없습니다.</p>";
        return body;
    }
    void OfferScreen() {
        transfer_person=profile_person;
        Home(false);Display("overview-page",false);Display("page-pane",true);Highlight("transfers");
        document->GetElementById("page-title")->SetInnerRML("에이전트 접촉 · 게임 내 영입 협상");
        document->GetElementById("page-body")->SetInnerRML("<p>0원을 제안하면 요구 조건을 먼저 확인합니다. 조건에 동의한 뒤 구단 동의와 예산 검사를 거쳐 체결됩니다.</p><label>제안 연봉 (원)</label><input id='deal-salary' type='text' maxlength='12' value='0'/><label>제안 이적료 (원)</label><input id='deal-fee' type='text' maxlength='13' value='0'/><select id='deal-years'><option value='1'>1시즌</option><option value='2'>2시즌</option><option value='3'>3시즌</option></select><select id='deal-pitch'><option value='development'>성장 계획 제시</option><option value='starting'>출전 기회 논의</option><option value='salary'>보수 중심 협상</option></select><button id='deal-submit'>조건 제시 · 요구 확인</button>");
        document->GetElementById("deal-submit")->AddEventListener("click",this);
    }
    Json management_state;
    std::string management_page;
    bool IsManagementPage(const std::string& key) {
        return key=="finance" || key=="transfer-budget" || key=="medical" || key=="relations" || key=="vision" || key=="profile" || key=="training" || key=="academy";
    }
    std::string ManagementBody(const std::string& key) {
        management_page=key;
        management_state=online::Request(L"management?id="+std::to_wstring(career.at("id").get<int>()),online_token);
        const auto& state=management_state;const bool admin=career.value("role","")=="admin";
        std::string body="<p>온라인 구단 상태 · 금액과 효과는 게임용 추정입니다.</p>";
        const auto& contracts=state.at("contracts");
        const auto person_row=[&](const Json& p) { return "<div class='row person' id='person-"+p.at("id").get<std::string>()+"'>"+Face(p)+Escape(PersonName(p))+" · "+Escape(p.value("nickname",""))+" / "+Escape(p.value("role",std::string{}))+"</div>"; };
        if(key=="finance" || key=="transfer-budget") {
            body+="<h2>잔액 "+state.at("cash").dump()+"원</h2><p>이적 예산 "+state.at("transfer_budget").dump()+"원 / 연봉 예산 "+state.at("wage_budget").dump()+"원</p><p>계약 연봉 합계 "+state.at("annual_payroll").dump()+"원 · 104턴 분할 지급</p>";
            if(admin) body+="<label>이적 예산 (원)</label><input id='mg-transfer' type='text' maxlength='13' value='"+state.at("transfer_budget").dump()+"'/><label>연봉 예산 (원)</label><input id='mg-wages' type='text' maxlength='13' value='"+state.at("wage_budget").dump()+"'/><button id='mg-budget'>예산 저장</button>";
            body+="<h2>계약</h2>";
            for(const auto& contract:contracts) {
                body+=person_row(contract.at("person"))+"<p>게임용 연봉 "+contract.at("annual_salary").dump()+"원 / 남은 계약 "+contract.at("remaining_turns").dump()+"턴 · "+(contract.at("active").get<bool>()?"계약 중":"만료")+"</p>";
            }
            if(admin && !contracts.empty()) {
                body+="<label>계약 갱신 대상</label><select id='mg-person'>";
                for(size_t i=0;i<contracts.size();++i) body+="<option value='"+std::to_string(i)+"'>"+Escape(PersonName(contracts[i].at("person")))+"</option>";
                body+="</select><label>제안 연봉 (원, 현재 연봉 이상)</label><input id='mg-salary' type='text' maxlength='12'/><select id='mg-years'><option value='1'>현재부터 1시즌</option><option value='2'>현재부터 2시즌</option><option value='3'>현재부터 3시즌</option></select><button id='mg-renew'>계약 갱신 제안</button>";
            }
            body+="<h2>회계 원장</h2>";
            for(const auto& row:state.at("ledger")) body+="<div class='row'>"+row.at("season").dump()+"시즌 "+row.at("week").dump()+"주 · "+Escape(row.at("description").get<std::string>())+" · "+row.at("amount").dump()+"원</div>";
        } else if(key=="medical" || key=="training") {
            if(key=="training") {
                body+="<p>훈련은 다음 온라인 턴에 성장·피로를 반영합니다. 휴식은 피로를 줄이고 성장을 멈춥니다.</p>";
                const char* choices[]={"기본기","라인 관리","시야와 합류","휴식"};
                for(int i=0;i<4;++i) body+="<button id='choice-"+std::to_string(i)+"'>"+std::string(choices[i])+"</button>";
                body+="<p>현재 훈련 · "+Escape(career.value("training",std::string("기본기")))+"</p>";
            }
            for(size_t i=0;i<contracts.size();++i) {
                const auto& c=contracts[i];if(!c.at("active").get<bool>()) continue;
                body+=person_row(c.at("person"))+"<p>피로 "+c.at("fatigue").dump()+" / 사기 "+c.at("morale").dump()+" / 부상 회복 "+c.at("injury_turns").dump()+"턴 / 회복 계획 "+Escape(c.at("treatment").get<std::string>())+"</p>";
                if(key=="training") for(const auto& [attribute,progress]:c.at("growth").items()) body+="<span>"+Escape(attribute)+" 성장 "+progress.dump()+"/100 · </span>";
                if(key=="medical" && admin) for(const auto& mode:{"normal","rest","rehab"})
                    body+="<button id='mg-treat-"+std::to_string(i)+"-"+mode+"'>"+std::string(std::string(mode)=="normal"?"일반 회복":std::string(mode)=="rest"?"개인 휴식":"재활 · 부상당 25만원")+"</button>";
            }
        } else if(key=="relations") {
            const auto name=[&](const std::string& id) { for(const auto& c:contracts) if(c.at("person").at("id")==id) return PersonName(c.at("person"));return id; };
            const auto& relations=state.at("relationships");
            for(size_t i=0;i<relations.size();++i) {
                const auto& r=relations[i];body+="<div class='row'>"+Escape(name(r.at("first")))+" / "+Escape(name(r.at("second")))+" · 신뢰 "+r.at("trust").dump()+" / 100</div>";
                if(admin) for(const auto& approach:{"listen","roles","demand"})
                    body+="<button id='mg-mediate-"+std::to_string(i)+"-"+approach+"'>"+std::string(std::string(approach)=="listen"?"양쪽 의견 듣기":std::string(approach)=="roles"?"역할 정리":"강하게 요구")+"</button>";
            }
        } else if(key=="vision") {
            body+="<h2>구단주 신임 "+state.at("board").dump()+" / 팬 지지 "+state.at("fans").dump()+"</h2><p>현재 비전 · "+Escape(state.at("manager").at("vision").get<std::string>())+"</p><p>적자가 이어지면 구단주 신임이 낮아집니다.</p>";
            if(admin) body+="<button id='mg-vision-development'>선수 성장</button><button id='mg-vision-promotion'>승격 도전</button><button id='mg-vision-stability'>재정 안정</button>";
        } else if(key=="profile") {
            const auto& manager=state.at("manager");body+="<label>감독 이름</label><input id='mg-manager-name' type='text' maxlength='30' value='"+Escape(manager.at("name").get<std::string>())+"'/><p>능력치 1~20 · 합계 60</p>";
            for(int i=0;i<6;++i) { const char* attrs[]={"전술","훈련","협상","동기부여","선수관리","스카우팅"};body+="<label>"+std::string(attrs[i])+"</label><input id='mg-stat-"+std::to_string(i)+"' type='text' maxlength='2' value='"+manager.at("stats").at(attrs[i]).dump()+"'/>"; }
            if(admin) body+="<button id='mg-manager'>감독 프로필 저장</button>";
        } else if(key=="academy") {
            for(const auto& c:contracts) if(c.at("person").value("assignment","")=="academy" || c.at("person").value("assignment","")=="reserve") {
                body+=person_row(c.at("person"));
                const auto path=c.at("person").value("solo",Json::object()).value("path",std::string{});
                if(admin && path=="prospect") body+="<button id='recruit-debut-"+c.at("person").at("id").get<std::string>()+"'>프로 데뷔</button>";
            }
            if(body.find("person-")==std::string::npos) body+="<p>등록된 2군·유소년 또는 후보 선수가 없습니다.</p>";
        }
        return body;
    }
    std::string people_query;
    std::string solo_role;
    std::string profile_person,profile_team;
    std::string recruitment_page="first";
    Json online_roster=Json::array();
    Json profile_evaluation=nullptr;
    std::string news_scope="home", news_competition="LCK CL";
    Json news_follows=Json::array();
    Json fixture_rules=Json::array();
    std::string NewsBody() {
        const auto cid=career.at("id").dump();
        news_follows=online::Request(L"follows?id="+std::wstring(cid.begin(),cid.end()),online_token).at("follows");
        std::string query="news?id="+cid+"&scope="+news_scope+"&competition=";
        const char* hex="0123456789ABCDEF";
        for (unsigned char c:news_competition) { query+='%'; query+=hex[c>>4]; query+=hex[c&15]; }
        auto items=online::Request(std::wstring(query.begin(),query.end()),online_token).at("news");
        std::string body="<button id='news-home'>내 팀 · 팔로우</button><button id='news-league'>리그</button>"
            "<button id='news-following'>팔로우만</button><p>현재 필터 · "+Escape(news_scope)+"</p>"
            "<label>리그 이름</label><input id='news-competition' type='text' maxlength='120' value='"+Escape(news_competition)+"'/>"
            "<button id='news-filter'>리그 뉴스 보기</button><h2>팔로우 관리</h2>"
            "<select id='news-kind'><option value='team'>구단</option><option value='player'>선수 ID</option>"
            "<option value='competition'>대회</option></select><input id='news-entity' type='text' maxlength='120'/>"
            "<button id='news-add'>팔로우 저장</button><p>선수는 DB의 고유 ID로 구분합니다.</p>";
        for (size_t i=0;i<news_follows.size();++i)
            body+="<div class='row'>"+Escape(news_follows[i].at("kind").get<std::string>())+" · "+
                Escape(news_follows[i].at("entity").get<std::string>())+" <button id='news-remove-"+std::to_string(i)+"'>해제</button></div>";
        if (items.empty()) body+="<p>이 필터에 해당하는 기사가 없습니다.</p>";
        for (const auto& item:items)
            body+="<div class='card'><small>"+Escape(item.value("label",std::string("게임 내 가상 기사")))+" · "+item.at("season").dump()+"시즌 "+item.at("week").dump()+
                "주 · "+Escape(item.at("competition").get<std::string>())+"</small><h2>"+
                Escape(item.at("headline").get<std::string>())+"</h2><p>"+Escape(item.at("body").get<std::string>())+"</p></div>";
        return body;
    }
    void Profile(const std::string& id) {
        const auto found=std::find_if(people.begin(),people.end(),[&](const Json& person){return person.value("id","")==id;});
        if(found==people.end() && !online_active) return;
        Json person=found==people.end()?Json::object():*found;
        if(online_active) {
            const auto query="person?id="+career.at("id").dump()+"&person="+UrlEncode(id);
            person=online::Request(std::wstring(query.begin(),query.end()),online_token).at("person");
        }
        profile_person=id; profile_team=person.value("team","");
        profile_evaluation=person.value("game_evaluation",Json{});
        Home(false);Highlight("people");Display("overview-page",false);Display("page-pane",true);
        document->GetElementById("page-title")->SetInnerRML(Escape(PersonName(person)));
        document->GetElementById("page-subtitle")->SetInnerRML(Escape(person.value("team",""))+" · "+Escape(person.value("league","")));
        std::string body="<button id='profile-back'>선수 목록으로</button><button id='profile-team'>"+Escape(profile_team)+" 구단</button>";
        if(online_active) body+="<button id='profile-follow'>인물 뉴스 팔로우</button><button id='profile-shortlist'>영입 명단에 추가</button>";
        if(online_active && career.value("role","")=="admin" && person.contains("solo")) {
            const auto path=person.at("solo").value("path",std::string{});
            if(path=="amateur") body+="<button id='profile-talk'>일반인과 대화</button>";
            if(path=="prospect") body+="<button id='profile-debut'>프로 데뷔</button>";
        }
        const auto solo_path=person.contains("solo")?person.at("solo").value("path",std::string{}):std::string{};
        if(online_active && career.value("role","")=="admin" && solo_path!="amateur" && solo_path!="prospect" && solo_path!="retired" && (person.value("team","")!=career.value("club","") || person.value("assignment","")=="candidate")) body+="<button id='deal-start'>에이전트 접촉 · 영입 협상</button>";
        if(online_active && career.value("league_operator",false)) body+="<button id='profile-evaluate'>게임용 평가 수정</button>";
        body+="<div class='profile-columns'>"
                         "<div class='card profile-id'><h2>선수 정보</h2><p>"+Escape(PersonName(person))+"</p><p>"+
                         "닉네임 "+Escape(person.value("nickname",""))+"</p><p>등록 역할 "+Escape(person.value("raw_role","미분류"))+
                         (person.contains("solo")?"</p><p>"+Escape(person.at("solo").at("label").get<std::string>())+" · "+Escape(person.at("solo").at("path_name").get<std::string>())+" · 성격 "+Escape(person.at("solo").at("personality").get<std::string>()):"")+
                         "</p><p>계약 만료 "+Escape(person.value("contract_end",""))+"</p><small>"+
                         (person.value("contract_estimated",false)?"게임용 1년 계약 추정":"라이엇 GCD 확인")+
                         "</small><p>국적 "+Escape(person.value("nationality_name_ko","확인 중"))+"</p>"+
                         (Face(person,200).empty() ? "<p>공식 사진 미확인</p>" : Face(person,200))+
                         "</div><div class='card profile-stats'><h2>능력치</h2>"
                         "<p><small>운영자 게임용 평가 · 원본 경기 평가와 구분</small></p><div class='profile-table'>";
        if(profile_evaluation.is_object()) {
            for(const auto& [attribute,value]:profile_evaluation.at("ratings").items())
                body+="<div class='row'>"+Escape(attribute)+" · "+value.dump()+" / 100</div>";
            body+="<p>2026 폼 · "+profile_evaluation.at("form").dump()+" / 100</p><p>평가 근거 · "+Escape(profile_evaluation.at("note").get<std::string>())+"</p>";
        } else body+="<p>능력치와 2026 폼 평가 미등록</p>";
        body+="</div></div><div class='card profile-summary'><h2>챔피언 숙련도</h2><p>시즌 출전과 밴 기록은 데이터 허브에 모입니다.</p></div></div>";
        document->GetElementById("page-body")->SetInnerRML(body);
        document->GetElementById("profile-back")->AddEventListener("click",this);
        document->GetElementById("profile-team")->AddEventListener("click",this);
        if(auto* follow=document->GetElementById("profile-follow")) follow->AddEventListener("click",this);
        if(auto* shortlist=document->GetElementById("profile-shortlist")) shortlist->AddEventListener("click",this);
        if(auto* offer=document->GetElementById("deal-start")) offer->AddEventListener("click",this);
        if(auto* evaluate=document->GetElementById("profile-evaluate")) evaluate->AddEventListener("click",this);
        if(auto* talk=document->GetElementById("profile-talk")) talk->AddEventListener("click",this);
        if(auto* debut=document->GetElementById("profile-debut")) debut->AddEventListener("click",this);
    }
    std::string SoloBody() {
        std::wstring query=L"solo-ladder?id="+std::to_wstring(career.at("id").get<int>());
        if(!solo_role.empty()) {
            const std::wstring role(solo_role.begin(),solo_role.end());
            query+=L"&role="+role;
        }
        const auto data=online::Request(query,online_token);
        const bool admin=career.value("role","")=="admin";
        std::string body="<p>솔로랭크 순위입니다. 프로는 영입할 수 있습니다. 일반인은 영입되지 않고, 대화가 통하면 유망주가 됩니다. 성과가 없으면 빨리 은퇴하고, 독하게 버티는 성격은 더 오래 남습니다. 실버 I이 되면 프로 데뷔를 시킬 수 있습니다.</p>";
        const char* roles[]={"all","TOP","JUNGLE","MID","ADC","SUPPORT"};
        const char* labels[]={"전체","탑","정글","미드","원딜","서폿"};
        for(int i=0;i<6;++i) body+="<button id='solo-role-"+std::string(roles[i])+"'>"+labels[i]+"</button>";
        body+="<h2>우리 일반인 · 유망주</h2>";
        if(data.at("mine").empty()) body+="<p>우리 구단이 대화 중인 일반인이나 유망주가 없습니다.</p>";
        for(const auto& player:data.at("mine")) {
            const auto id=player.at("id").get<std::string>();
            const auto path=player.at("path").get<std::string>();
            body+="<div class='row person' id='person-"+id+"'>"+Escape(player.at("real_name").get<std::string>())+" · "+Escape(player.at("nickname").get<std::string>())+
                " / "+Escape(player.at("role").get<std::string>())+" · "+Escape(player.at("path_name").get<std::string>())+" · "+Escape(player.at("label").get<std::string>())+
                " · "+Escape(player.at("personality").get<std::string>())+"</div>";
            if(admin && path=="amateur") body+="<button id='solo-talk-"+id+"'>대화</button>";
            if(admin && path=="prospect") body+="<button id='solo-debut-"+id+"'>프로 데뷔</button>";
        }
        body+="<h2>순위</h2>";
        for(const auto& player:data.at("rows")) {
            const auto id=player.at("id").get<std::string>();
            body+="<div class='row person' id='person-"+id+"'>"+player.at("rank").dump()+"위 "+Escape(player.at("real_name").get<std::string>())+" · "+
                Escape(player.at("nickname").get<std::string>())+" / "+Escape(player.at("role").get<std::string>())+" · "+Escape(player.at("label").get<std::string>())+
                " · "+Escape(player.at("path_name").get<std::string>())+" · "+Escape(player.at("personality").get<std::string>())+
                (player.at("club").get<std::string>().empty()?"":" · "+Escape(player.at("club").get<std::string>()))+"</div>";
            if(admin && player.at("path")=="amateur") body+="<button id='solo-talk-"+id+"'>대화</button>";
        }
        return body;
    }
    void Team(const std::string& name) {
        Home(false); Display("overview-page",false);Display("page-pane",true);
        std::string body;
        Json roster=people;
        if(online_active) {
            const auto query="people?id="+career.at("id").dump()+"&team="+UrlEncode(name);
            roster=online::Request(std::wstring(query.begin(),query.end()),online_token).at("people");
        }
        std::string league;
        for(const auto& person:roster) if(person.value("team","")==name) { league=person.value("league",""); break; }
        document->GetElementById("page-title")->SetInnerRML(Logo(league,name)+Escape(name));
        document->GetElementById("page-subtitle")->SetInnerRML("등록 선수 · 스태프 · 미분류 인물");
        for(const auto& person:roster) if(person.value("team","")==name)
            body+="<div class='row person' id='person-"+person.value("id","")+"'>"+Face(person)+Logo(person.value("league",""),person.value("team",""))+Escape(PersonName(person))+" · "+
                Escape(person.value("nickname",""))+" / "+Escape(person.value("raw_role",""))+" / 계약 "+Escape(person.value("contract_end",""))+"</div>";
        document->GetElementById("page-body")->SetInnerRML(body.empty()?"<p>확인된 등록 인물이 없습니다.</p>":body);
        BindPeople("page-body");
    }
    void SearchEntity(const std::string& kind,int id) {
        const auto query="entity?kind="+kind+"&entity="+std::to_string(id);
        const auto entity=online::Request(std::wstring(query.begin(),query.end()),online_token);
        ForumShell();document->GetElementById("club-title")->SetInnerRML("통합 검색");document->GetElementById("career-state")->SetInnerRML(kind=="owner"?"구단주 정보":"온라인 리그 감독 정보");
        std::string body="<h2>"+Escape(entity.at("name").get<std::string>())+"</h2>";
        if(kind=="owner") body+="<p>기업 · "+Escape(entity.at("company").get<std::string>())+"</p>";
        else {body+="<p>구단 · "+Escape(entity.at("club").get<std::string>())+"</p>";for(const auto& [attr,value]:entity.at("stats").items())body+="<div class='row'>"+Escape(attr)+" · "+value.dump()+" / 20</div>";}
        body+="<small>출처 · "+Escape(entity.at("source").get<std::string>())+"</small>";
        document->GetElementById("page-body")->SetInnerRML(body);
    }
    void EditEvaluation() {
        std::string body="<p>원본 자료와 별도로 저장되는 운영자 게임용 평가입니다.</p>";
        const char* attributes[]={"라인전","교전","운영","시야","협동","멘탈"};
        for(int i=0;i<6;++i) body+="<label>"+std::string(attributes[i])+" (1~100)</label><input id='rating-"+std::to_string(i)+"' type='text' maxlength='3' value='"+
            (profile_evaluation.is_object()?profile_evaluation.at("ratings").at(attributes[i]).dump():"")+"'/>";
        body+="<label>2026 폼 (1~100)</label><input id='rating-form' type='text' maxlength='3'/><label>평가 근거</label>"
            "<input id='rating-note' type='text' maxlength='1000'/><button id='rating-save'>평가 저장</button>";
        document->GetElementById("page-body")->SetInnerRML(body);
        document->GetElementById("rating-save")->AddEventListener("click",this);
    }
    void Bind() {
        const char* actions[] = {"quit", "home", "database", "create", "advance", "league-advance", "previous", "next", "people-search", "new-mode", "existing-mode", "resume", "lobby-new", "lobby-load", "lobby-online", "online-login", "online-register", "online-update", "online-open", "online-create", "online-takeover", "online-refresh", "online-logout", "online-community", "lobby-quit", "lobby-home"};
        for (const char* id : actions) {
            auto* element=document->GetElementById(id);
            if(!element) throw std::runtime_error(std::string("Missing control: ")+id);
            element->AddEventListener("click", this);
        }
        for(const auto* group:{"club","squad","preparation","recruitment","competition","operations"})
            document->GetElementById(std::string("nav-select-")+group)->AddEventListener("change",this);
        document->GetElementById("global-search")->AddEventListener("change",this);
        document->GetElementById("global-search")->SetAttribute("placeholder","선수 · 스태프 · 구단 · 구단주 검색");
        std::set<std::string> teams;
        for (const auto& person : people) {
            const auto team = JText(person, "team");
            if (!team.empty()) teams.insert(team);
        }
        std::string options;
        for (const auto& team : teams) options += "<option value='" + Escape(team) + "'>" + Escape(team) + "</option>";
        document->GetElementById("team")->SetInnerRML(options);
        SetMode(false);
        if (!load_notice.empty()) Notice(load_notice);
        ShowLobby();
        TryAutoLogin();
    }
    void SetMode(bool takeover) {
        auto* mode = dynamic_cast<Rml::ElementFormControl*>(document->GetElementById("mode"));
        mode->SetValue(takeover ? "takeover" : "create");
        Display("new-club", !takeover);
        Display("existing-club", takeover);
        document->GetElementById("new-mode")->SetClass("selected", !takeover);
        document->GetElementById("existing-mode")->SetClass("selected", takeover);
    }
    void ProcessEvent(Rml::Event& event) override {
        try {
            const auto id = event.GetCurrentElement()->GetId();
            if(id.rfind("cal-",0)==0) {
                if(id=="cal-prev")calendar_week=std::max(1,calendar_week-13);
                else if(id=="cal-next")calendar_week=std::min(104,calendar_week+13);
                else if(id=="cal-today")calendar_week=career.at("week").get<int>();
                else if(id.rfind("cal-week-",0)==0)calendar_week=std::stoi(id.substr(9));
                OpenPage("calendar",false);return;
            }
            if(id.rfind("comp-team-",0)==0){Team(competition_state.at("standings").at(std::stoul(id.substr(10))).at("team").get<std::string>());return;}
            if(id.rfind("nav-select-",0)==0) {
                const auto key=Value(id.c_str());
                dynamic_cast<Rml::ElementFormControl*>(event.GetCurrentElement())->SetValue("");
                if(!key.empty())OpenPage(key);
                return;
            }
            if(id.rfind("match-open-",0)==0){OpenMatch(std::stoi(id.substr(11)));return;}
            if(id.rfind("manual-",0)==0) {
                if(id=="manual-search")draft_query=CleanName(Value("manual-query"),40);
                else if(id.rfind("manual-champ-",0)==0)draft_selection=id.substr(13);
                else if(id=="manual-confirm" || id=="manual-auto") {
                    Json body={{"id",active_match},{"version",match_game.at("series").at("draft_version")}};
                    if(id=="manual-confirm")body["champion"]=draft_selection;
                    online::Request(id=="manual-confirm"?L"draft-action":L"draft-auto",online_token,body);draft_selection.clear();
                    OpenMatch(active_match);return;
                }
                OpenMatch(active_match,false);return;
            }
            if(id.rfind("swapcard-",0)==0) {
                const auto separator=id.find('-',9);const int fixture=std::stoi(id.substr(9,separator-9)),role=std::stoi(id.substr(separator+1));
                if(swap_first<0){swap_first=role;OpenMatch(fixture,false);return;}
                const char* roles[]={"TOP","JUNGLE","MID","ADC","SUPPORT"};
                const int first=swap_first;swap_first=-1;
                if(first!=role)online::Request(L"draft-swap",online_token,{{"id",fixture},{"version",match_game.at("series").at("swap_version")},{"first",roles[first]},{"second",roles[role]}});
                OpenMatch(fixture);return;
            }
            if(id=="global-search") {
                search_pending=CleanName(Value("global-search"),120);search_due=SDL_GetTicks()+180;
                if(search_pending.empty()){search_requested.clear();Display("global-results",false);}
                return;
            }
            if(id.rfind("global-result-",0)==0) {
                const auto item=search_items.at(std::stoul(id.substr(14)));Display("global-results",false);
                const auto kind=item.at("kind").get<std::string>();
                if(kind=="manager" || kind=="owner") SearchEntity(kind,item.at("id").get<int>());
                else {
                    if(!online_active || career.is_null())throw std::runtime_error("온라인 구단을 먼저 선택하세요.");
                    if(kind=="team")Team(item.at("team").get<std::string>());else Profile(item.at("id").get<std::string>());
                }
                return;
            }
            if((id=="create" || id=="new-mode" || id=="existing-mode" || id=="lobby-new" || id=="lobby-load" || id=="resume"))
                throw std::runtime_error("온라인 리그에서 실제 구단 부임 또는 새 구단 창단을 선택하세요.");
            if (id=="lobby-home") ShowLobby();
            else if (id=="lobby-quit") Backend::RequestExit();
            else if(id=="online-community") CommunityBoard();
            else if (id=="lobby-online") {
                Display("online-panel", true);
                Display("online-auth", online_token.empty());
                Display("online-careers", !online_token.empty());
                if (!online_token.empty()) LoadOnlineList();
            } else if (id=="online-update") {
                const auto found = client_update::Probe();
                const auto status = found.result == client_update::Result::Available ? client_update::Apply(found) : found;
                if (status.result == client_update::Result::Restart) restarting = true;
                else if (auto* info = document->GetElementById("lobby-info")) info->SetInnerRML(Escape(status.message));
            } else if (id=="online-login" || id=="online-register") {
                auto name = CleanName(Value("online-name"), 30);
                auto password = Value("online-password");
                const auto password_length=Utf8Count(password);
                if (name.empty() || password_length < 10 || password_length > 128)
                    throw std::runtime_error("계정 이름은 1~30자, 비밀번호는 10~128자여야 합니다.");
                auto result = online::Request(id=="online-login" ? L"login" : L"register", "",
                                              {{"name",name},{"password",password}});
                static_cast<Rml::ElementFormControl*>(document->GetElementById("online-password"))->SetValue("");
                online_token = result.at("token").is_string() ? result.at("token").get<std::string>() : std::string{};
                if (online_token.empty()) throw std::runtime_error("로그인 응답에 세션이 없습니다.");
                online_manager = name;
                LoadOnlineList();
                PersistSession();
            } else if (id=="online-refresh") {
                LoadOnlineList();
            } else if (id=="online-logout") {
                ForgetSession();
                Display("online-auth",true);
                Display("online-careers",false);
            } else if (id=="online-takeover") {
                const auto selected=Value("online-team");
                if(selected.empty()) throw std::runtime_error(online_operator?"열 팀을 선택하세요.":"부임할 실제 구단을 선택하세요.");
                const auto created=online::Request(L"careers",online_token,online_operator?Json{{"mode","enter"},{"team_key",selected}}:Json{{"mode","takeover"},{"team_key",selected}});
                LoadOnlineList();
                for(const auto& item:online_careers) if(item.at("id")==created.at("id")) { OpenOnline(item); break; }
            } else if (id=="online-create") {
                auto name = CleanName(Value("online-club"),40);
                if (name.empty()) throw std::runtime_error("구단 이름을 입력하세요.");
                auto created = online::Request(L"careers",online_token,{{"name",name},{"mode","create"}});
                LoadOnlineList();
                for (const auto& item : online_careers)
                    if (item.at("id") == created.at("id")) { OpenOnline(item); break; }
            } else if (id=="online-open") {
                auto selected = Value("online-list");
                for (const auto& item : online_careers)
                    if (item.at("id").dump() == selected) { OpenOnline(item); break; }
            }
            else if (id=="resume" || id=="lobby-load") {
                if(career.is_null()) document->GetElementById("lobby-info")->SetInnerRML("불러올 커리어가 없습니다. 새 게임을 시작하세요.");
                else Home();
            }
            else if (id=="lobby-new") {
                if(!career.is_null() && fs::exists(save_path)) {
                    const auto archive=save_path.parent_path()/("career-archive-"+std::to_string(SDL_GetTicksNS())+".json");
                    fs::copy_file(save_path,archive);
                }
                career=nullptr;
                Home();
                Notice("감독과 구단을 설정하세요.");
            }
            else if(id.rfind("dash-go-",0)==0) OpenPage(id.substr(8));
            else if(id.rfind("dash-mail-",0)==0)OpenPage("mail");
            else if(id=="dash-opponent" && online_active)Team(dashboard_state.at("next_fixture").at("opponent").get<std::string>());
            else if(id.rfind("dash-team-",0)==0 && online_active)Team(dashboard_state.at("standings").at(std::stoul(id.substr(10))).at("team").get<std::string>());
            else if(id=="staff-search-go" && online_active) {staff_query=CleanName(Value("staff-query"),120);OpenPage("staff-search");}
            else if(id=="staff-generate" && online_active) {online::Request(L"staff-candidates",online_token,{{"id",career.at("id")}});OpenPage("staff-search");Notice("단장·커뮤니티·분석·의료 전문 후보를 모집했습니다.");}
            else if(id=="staff-position-save" && online_active) {
                online::Request(L"staff-role",online_token,{{"id",career.at("id")},{"person",Value("staff-position-person")},{"staff_role",Value("staff-position-role")}});OpenPage("staff");
            }
            else if(id.rfind("forum-",0)==0) {
                if(id=="forum-list") CommunityBoard();
                else if(id=="forum-league-go") {forum_league=Value("forum-league");forum_category="all";forum_page=0;CommunityBoard();}
                else if(id=="forum-write") CommunityCompose(false);
                else if(id=="forum-edit") CommunityCompose(true);
                else if(id.rfind("forum-cat-",0)==0) { forum_category=id.substr(10);forum_page=0;CommunityBoard(); }
                else if(id=="forum-search") { forum_query=CleanName(Value("forum-query"),100);forum_page=0;CommunityBoard(); }
                else if(id=="forum-prev" || id=="forum-next") { forum_page=std::max(0,forum_page+(id=="forum-next"?1:-1));CommunityBoard(); }
                else if(id.rfind("forum-open-",0)==0) CommunityPost(std::stoi(id.substr(11)));
                else if(id=="forum-compose-save") {
                    Json data={{"title",Value("forum-compose-title")},{"body",Value("forum-compose-body")},{"category",Value("forum-compose-category")}};
                    if(forum_edit) data.update({{"post",forum_post.at("id")},{"version",forum_post.at("version")}});
                    const auto result=online::Request(forum_edit?L"community-edit":L"community-create",online_token,data);
                    CommunityPost(result.at("post").get<int>());
                } else {
                    Json data={{"post",forum_post.at("id")}};std::wstring route;
                    if(id=="forum-up" || id=="forum-down" || id=="forum-unvote") {route=L"community-vote";data["value"]=id=="forum-up"?1:id=="forum-down"?-1:0;}
                    else if(id=="forum-comment-save") {route=L"community-comment";data["body"]=Value("forum-comment");}
                    else if(id=="forum-report") {route=L"community-report";data["reason"]=Value("forum-report-reason");}
                    else if(id=="forum-delete") {route=L"community-delete";data["version"]=forum_post.at("version");}
                    else throw std::runtime_error("지원되지 않는 게시판 조작입니다.");
                    online::Request(route,online_token,data);
                    if(id=="forum-delete") CommunityBoard();else CommunityPost(forum_post.at("id").get<int>());
                    if(id=="forum-report") Notice("게시글 신고를 접수했습니다.");
                }
            }
            else if(id=="deal-start" && online_active) OfferScreen();
            else if(id.rfind("deal-",0)==0 && online_active) {
                Json data={{"id",career.at("id")}};
                const auto amount=[&](const std::string& field) -> long long { const auto raw=Value(field.c_str());if(raw.empty() || raw.find_first_not_of("0123456789")!=std::string::npos) throw std::runtime_error("제안 금액을 숫자로 입력하세요.");return std::stoll(raw); };
                if(id=="deal-submit") {
                    data.update({{"person",transfer_person},{"annual_salary",amount("deal-salary")},{"fee",amount("deal-fee")},{"years",amount("deal-years")},{"pitch",Value("deal-pitch")}});
                    online::Request(L"transfer-offer",online_token,data);
                } else {
                    const auto split=id.find('-',5);
                    const auto choice=id.substr(5,split-5),oid=id.substr(split+1);
                    data.update({{"offer",std::stoi(oid)},{"choice",choice}});
                    if(choice=="counter") data["counter_fee"]=amount("deal-fee-"+oid);
                    online::Request(L"transfer-response",online_token,data);
                }
                OpenPage("transfers");Notice("온라인 이적 협상 상태를 저장했습니다.");
            }
            else if(id.rfind("mg-",0)==0 && online_active) {
                Json data={{"id",career.at("id")}};
                const auto number=[&](const std::string& control) -> long long {
                    const auto raw=Value(control.c_str());
                    if(raw.empty() || raw.find_first_not_of("0123456789")!=std::string::npos) throw std::runtime_error("금액과 능력치는 숫자로 입력하세요.");
                    return std::stoll(raw);
                };
                if(id=="mg-budget") data.update({{"action","budget"},{"transfer_budget",number("mg-transfer")},{"wage_budget",number("mg-wages")}});
                else if(id=="mg-renew") {
                    const auto& c=management_state.at("contracts").at(std::stoul(Value("mg-person")));
                    data.update({{"action","renew"},{"person",c.at("person").at("id")},{"annual_salary",number("mg-salary")},{"years",number("mg-years")}});
                } else if(id.rfind("mg-treat-",0)==0) {
                    const auto split=id.find('-',9);const auto index=std::stoul(id.substr(9,split-9));
                    data.update({{"action","treatment"},{"person",management_state.at("contracts").at(index).at("person").at("id")},{"treatment",id.substr(split+1)}});
                } else if(id.rfind("mg-mediate-",0)==0) {
                    const auto split=id.find('-',11);const auto& r=management_state.at("relationships").at(std::stoul(id.substr(11,split-11)));
                    data.update({{"action","mediate"},{"first",r.at("first")},{"second",r.at("second")},{"approach",id.substr(split+1)}});
                } else if(id.rfind("mg-vision-",0)==0) data.update({{"action","vision"},{"vision",id.substr(10)}});
                else if(id=="mg-manager") {
                    Json stats=Json::object();const char* attrs[]={"전술","훈련","협상","동기부여","선수관리","스카우팅"};
                    for(int i=0;i<6;++i) stats[attrs[i]]=number("mg-stat-"+std::to_string(i));
                    data.update({{"action","manager"},{"name",CleanName(Value("mg-manager-name"),30)},{"stats",stats}});
                } else throw std::runtime_error("지원되지 않는 구단 조작입니다.");
                const auto result=online::Request(L"management",online_token,data);
                career["manager"]=result.at("manager").at("name");
                const auto key=management_page;OpenPage(key);Notice("온라인 구단 상태를 저장했습니다.");
            }
            else if (id.rfind("news-",0)==0 && online_active) {
                if (id=="news-add") {
                    const auto entity=CleanName(Value("news-entity"),120);
                    if (entity.empty()) throw std::runtime_error("팔로우할 대상을 입력하세요.");
                    online::Request(L"follows",online_token,{{"id",career.at("id")},{"kind",Value("news-kind")},{"entity",entity},{"enabled",true}});
                } else if (id.rfind("news-remove-",0)==0) {
                    const auto& item=news_follows.at(std::stoul(id.substr(12)));
                    online::Request(L"follows",online_token,{{"id",career.at("id")},{"kind",item.at("kind")},{"entity",item.at("entity")},{"enabled",false}});
                } else if (id=="news-filter") {
                    news_competition=CleanName(Value("news-competition"),120); news_scope="league";
                } else news_scope=id.substr(5);
                OpenPage("news");
            }
            else if (id=="fixture-refresh" && online_active) OpenPage("calendar");
            else if(id.rfind("swap-",0)==0 && online_active) {
                const auto split=id.find('-',5);
                const auto fixture=id.substr(5,split-5);
                online::Request(L"draft-swap",online_token,{{"id",std::stoi(fixture)},{"version",std::stoi(id.substr(split+1))},
                    {"first",Value(("swap-a-"+fixture).c_str())},{"second",Value(("swap-b-"+fixture).c_str())}});
                OpenMatch(std::stoi(fixture));Notice("최종 챔피언 배치를 저장했습니다.");
            }
            else if (id.rfind("draft-",0)==0 && online_active) {
                const auto separator = id.find('-',6);
                const auto second = id.find('-',separator+1);
                online::Request(L"draft-choice",online_token,{{"id",std::stoi(id.substr(6,separator-6))},
                    {"category",id.substr(separator+1,second-separator-1)},{"value",id.substr(second+1)},{"manual",true}});
                OpenMatch(std::stoi(id.substr(6,separator-6)));
            } else if (id.rfind("feedback-",0)==0 && online_active) {
                auto fixture = id.substr(9);
                auto note = CleanName(Value(("feedback-note-"+fixture).c_str()),300);
                if (note.empty()) throw std::runtime_error("피드백을 입력하세요.");
                online::Request(L"set-feedback",online_token,{{"id",std::stoi(fixture)},{"note",note}});
                OpenMatch(std::stoi(fixture));
                Notice("세트 피드백을 저장했습니다.");
            }
            else if (id.rfind("highlight-",0)==0 && online_active) {
                const auto separator = id.find('-',10);
                if (separator != std::string::npos) PlayHighlight(id.substr(10,separator-10),id.substr(separator+1));
            } else if (id=="replay-back") {
                highlight = nullptr;
                if(active_match)OpenMatch(active_match);else OpenCurrentMatch();
            } else if (id=="replay-restart") {
                replay_started = SDL_GetTicks();
                replay_frame = 0;
                document->GetElementById("replay-markers")->SetInnerRML("");
            }
            else if (id=="league-create" && online_active) {
                Json opponents=Json::array();
                const auto names=Value("league-opponents");
                std::size_t start=0;
                do {
                    const auto end=names.find(',',start);
                    auto name=CleanName(names.substr(start,end==std::string::npos ? end : end-start),40);
                    if (name.empty()) throw std::runtime_error("구단 이름을 확인하세요.");
                    opponents.push_back(name);
                    if (end==std::string::npos) break;
                    start=end+1;
                } while (true);
                if (opponents.size()<3 || opponents.size()>15) throw std::runtime_error("상대 구단을 3~15개 입력하세요.");
                const int week=career.at("week"), season=career.at("season");
                online::Request(L"league",online_token,{{"id",career.at("id")},{"season",season+(week==104)},
                    {"week",week==104?1:week+1},{"opponents",opponents}});
                OpenPage("competition");
                Notice("리그 일정을 생성했습니다.");
            }
            else if (id=="rule-save" && online_active) {
                const auto competition=CleanName(Value("rule-competition"),120),stage=CleanName(Value("rule-stage"),80);
                if(competition.empty() || stage.empty()) throw std::runtime_error("대회와 단계를 입력하세요.");
                online::Request(L"competition-rules",online_token,{{"id",career.at("id")},{"competition",competition},
                    {"stage",stage},{"best_of",std::stoi(Value("rule-format"))}});
                OpenPage("admin"); Notice("대회 규칙을 저장했습니다.");
            }
            else if (id=="fixture-add" && online_active) {
                const auto opponent = CleanName(Value("fixture-opponent"),40);
                if (opponent.empty()) throw std::runtime_error("연습 경기 상대 이름을 입력하세요.");
                const auto week = career.at("week").get<int>();
                const auto season = career.at("season").get<int>();
                const auto& rule=fixture_rules.at(std::stoul(Value("fixture-rule")));
                online::Request(L"fixtures",online_token,{{"id",career.at("id")},{"season",season+(week==104)},
                                {"week",week==104?1:week+1},{"opponent",opponent},
                                {"competition",rule.at("competition")},{"stage",rule.at("stage")}});
                OpenPage("calendar");
                Notice("다음 주 연습 경기를 예약했습니다.");
            }
            else if(id=="club-assign" && online_active) {
                const auto result=online::Request(L"club-lineup",online_token,{{"id",career.at("id")},{"person",Value("club-person")},
                    {"role",Value("club-role")},{"assignment",Value("club-squad")}});
                online_roster=result.at("roster");OpenPage(recruitment_page); Notice("온라인 구단의 선수단 배치를 저장했습니다.");
            }
            else if(id.rfind("recruit-",0)==0 && online_active) {
                Json payload={{"id",career.at("id")}};
                std::wstring route;
                if(id=="recruit-start") route=L"recruitment-start";
                else if(id=="recruit-finalize") route=L"recruitment-finalize";
                else if(id.rfind("recruit-talk-",0)==0) { route=L"solo-talk"; payload["person"]=id.substr(13); }
                else if(id.rfind("recruit-debut-",0)==0) { route=L"solo-debut"; payload["person"]=id.substr(14); }
                else {
                    route=L"recruitment-select"; payload["person"]=id.substr(13); payload["enabled"]=id.rfind("recruit-pick-",0)==0;
                }
                const auto result=online::Request(route,online_token,payload);
                if(route==L"solo-talk" || route==L"solo-debut") { OpenPage(route==L"solo-debut" && management_page=="academy" ? "academy" : recruitment_page); Notice(route==L"solo-talk"?(result.value("accepted",false)?"유망주가 되기로 했습니다.":"이번 대화는 거절당했습니다."):"프로 데뷔를 마쳤습니다."); return; }
                online_roster=result.at("roster");
                OpenPage(recruitment_page); Notice("초기 선수단 선택을 저장했습니다.");
            }
            else if((id=="profile-talk" || id=="profile-debut") && online_active) {
                const auto result=online::Request(id=="profile-talk"?L"solo-talk":L"solo-debut",online_token,{{"id",career.at("id")},{"person",profile_person}});
                Profile(profile_person);
                Notice(id=="profile-debut"?"프로 데뷔를 마쳤습니다.":(result.value("accepted",false)?"유망주가 되기로 했습니다.":"이번 대화는 거절당했습니다."));
            }
            else if(id.rfind("solo-role-",0)==0 && online_active) {
                solo_role=id.substr(10)=="all"?"":id.substr(10);
                OpenPage("solo");
            }
            else if(id.rfind("solo-talk-",0)==0 && online_active) {
                const auto result=online::Request(L"solo-talk",online_token,{{"id",career.at("id")},{"person",id.substr(10)}});
                OpenPage("solo");
                Notice(result.value("accepted",false)?"유망주가 되기로 했습니다.":"이번 대화는 거절당했습니다.");
            }
            else if(id.rfind("solo-debut-",0)==0 && online_active) {
                online::Request(L"solo-debut",online_token,{{"id",career.at("id")},{"person",id.substr(11)}});
                OpenPage("solo");
                Notice("프로 데뷔를 마쳤습니다.");
            }
            else if(id=="profile-shortlist" && online_active) {
                online::Request(L"shortlist",online_token,{{"id",career.at("id")},{"person",profile_person},{"enabled",true}});
                Notice("영입 검토 명단에 추가했습니다.");
            }
            else if(id.rfind("shortlist-remove-",0)==0 && online_active) {
                online::Request(L"shortlist",online_token,{{"id",career.at("id")},{"person",id.substr(17)},{"enabled",false}});
                OpenPage("shortlist");
            }
            else if(id.rfind("mail-read-",0)==0 && online_active) {
                online::Request(L"read-mail",online_token,{{"id",career.at("id")},{"mail",std::stoi(id.substr(10))}});
                OpenPage("mail");
            }
            else if (id=="profile-team") { const auto team=profile_team; Team(team); }
            else if (id=="profile-follow" && online_active) {
                online::Request(L"follows",online_token,{{"id",career.at("id")},{"kind","player"},{"entity",profile_person},{"enabled",true}});
                Notice("인물 뉴스 팔로우를 저장했습니다. 뉴스에서 해제할 수 있습니다.");
            }
            else if(id=="profile-evaluate") EditEvaluation();
            else if(id=="rating-save" && online_active) {
                Json ratings=Json::object();
                const char* attributes[]={"라인전","교전","운영","시야","협동","멘탈"};
                const auto parse=[&](const std::string& control) {
                    const auto raw=Value(control.c_str());
                    if(raw.empty() || raw.find_first_not_of("0123456789")!=std::string::npos) throw std::runtime_error("평가 값은 1~100으로 입력하세요.");
                    const int number=std::stoi(raw);
                    if(number<1 || number>100) throw std::runtime_error("평가 값은 1~100으로 입력하세요.");
                    return number;
                };
                for(int i=0;i<6;++i) ratings[attributes[i]]=parse("rating-"+std::to_string(i));
                const auto note=CleanName(Value("rating-note"),1000);
                if(note.empty()) throw std::runtime_error("평가 근거를 입력하세요.");
                online::Request(L"person-evaluation",online_token,{{"id",career.at("id")},{"person",profile_person},
                    {"ratings",ratings},{"form",parse("rating-form")},{"note",note}});
                const auto person=profile_person; Profile(person); Notice("게임용 평가를 저장했습니다.");
            }
            else if (id=="profile-back") Database();
            else if (id.rfind("person-",0)==0) Profile(id.substr(7));
            else if (id.rfind("nav-",0)==0) OpenPage(id.substr(4));
            else if (id.rfind("choice-",0)==0 && !career.is_null()) {
                const int index=std::stoi(id.substr(7));
                const char* tactics[]={"균형","오브젝트 중심","한타 중심","사이드 압박"};
                const char* training[]={"기본기","라인 관리","시야와 합류","휴식"};
                if (index>=0 && index<4 && (active_setting=="tactics" || active_setting=="training")) {
                    const auto* value = active_setting=="tactics"?tactics[index]:training[index];
                    if (online_active)
                        online::Request(L"settings",online_token,{{"id",career.at("id")},{"key",active_setting},{"value",value}});
                    career[active_setting]=value;
                    Save(); OpenPage(active_setting); Notice("설정을 저장했습니다.");
                }
            }
            else if (id == "quit") Backend::RequestExit();
            else if (id == "home") Home();
            else if (id == "database" || id == "personnel") Database();
            else if (id == "overview") Home();
            else if (id == "squad") { Home(); document->GetElementById("roster")->ScrollIntoView(); }
            else if (id == "schedule") { Home(); document->GetElementById("calendar")->ScrollIntoView(); }
            else if (id == "budget") Notice("재정 거래와 예산은 아직 연결되지 않았습니다.");
            else if (id == "new-mode") SetMode(false);
            else if (id == "existing-mode") SetMode(true);
            else if (id=="people-search") { people_query=CleanName(Value("people-query"),120); page=0; Database(); }
            else if (id == "next") { ++page; Database(); }
            else if (id == "previous") { --page; Database(); }
            else if (id == "create") {
                const std::string manager = CleanName(Value("manager"), 30);
                const bool takeover = Value("mode") == "takeover";
                const std::string club = CleanName(Value(takeover ? "team" : "club"), 40);
                if (takeover && std::none_of(people.begin(), people.end(), [&](const Json& person) {
                    return person.value("team", "") == club;
                })) { Notice("목록에서 부임할 구단을 선택하세요."); return; }
                if (manager.empty() || club.empty()) { Notice("감독 이름과 구단을 입력하세요."); return; }
                career = Json{{"manager", manager}, {"club", club}, {"week", 1}, {"season", 1}};
                Save(); Home(); Notice("커리어를 시작했습니다.");
            } else if ((id == "advance" || id=="league-advance") && !career.is_null()) {
                if (online_active) {
                    cached_fixtures=online::Request(L"fixtures?id="+std::to_wstring(career.at("id").get<int>()),online_token).at("fixtures");
                    for(const auto& game:cached_fixtures)if(game.at("state")=="queued"){OpenMatch(game.at("id").get<int>(),false);return;}
                    auto result = online::Request(L"advance",online_token,{{"id",career.at("id")},{"version",career.at("version")}});
                    for (const char* key : {"week","season","version"}) career[key] = result.at(key);
                    Home();
                    Notice(result.at("advanced").get<bool>() ? "서버에서 다음 주로 진행했습니다." : "진행 투표를 저장했습니다.");
                    return;
                }
                int week = career.at("week"), season = career.at("season");
                if (week == 104) {
                    if (season >= 10000) { Notice("더 이상 시즌을 진행할 수 없습니다."); return; }
                    week = 1; ++season;
                } else ++week;
                career["week"] = week; career["season"] = season;
                Save(); Home(); Notice("주차 진행 완료. 경기 일정은 아직 연결되지 않았습니다.");
            }
        } catch (const std::exception& error) { Notice(error.what()); document->GetElementById("lobby-info")->SetInnerRML(Escape(error.what())); }
    }
};
static bool KeyDown(Rml::Context*, Rml::Input::KeyIdentifier key, int, float, bool priority) {
    if (priority && key == Rml::Input::KI_F11) {
        if (SDL_Window* window = SDL_GetKeyboardFocus())
            SDL_SetWindowFullscreen(window, !(SDL_GetWindowFlags(window) & SDL_WINDOW_FULLSCREEN));
        return false;
    }
    return true;
}
int main(int argc,char** argv) {
    if (!bundle::Prepare()) {
        const char* base=SDL_GetBasePath();
        if(base)fs::current_path(fs::u8path(base));
    }
    if(!Backend::Initialize("RIFT MANAGER",1920,1080,true))return 1;
    Rml::SetSystemInterface(Backend::GetSystemInterface());
    Rml::SetRenderInterface(Backend::GetRenderInterface());
    if(!Rml::Initialise()){Backend::Shutdown();return 2;}
    int result=0;
    {
        try {
            Rml::LoadFontFace("assets/SUITE-Regular.ttf");
            Rml::LoadFontFace("assets/SUITE-SemiBold.ttf");
            Rml::LoadFontFace("assets/SUITE-Bold.ttf");
            auto* context=Rml::CreateContext("main",Rml::Vector2i(1920,1080));
            if(!context)throw std::runtime_error("UI context failed");
            Application application;
            application.document=context->LoadDocument("assets/main.rml");
            if(!application.document)throw std::runtime_error("UI document failed");
            application.Bind();application.document->Show();
            if(auto* window=SDL_GetKeyboardFocus()) {
                if(auto* icon=IMG_Load("assets/rm-logo.png")){SDL_SetWindowIcon(window,icon);SDL_DestroySurface(icon);}
                SDL_SetWindowFullscreen(window,true);
            }
            application.PollUpdate();
            while(Backend::ProcessEvents(context,KeyDown) && !application.restarting) {
                application.PollUpdate();application.PollFixtures();application.PollSearch();application.UpdateHighlight();
                context->Update();Backend::BeginFrame();context->Render();Backend::PresentFrame();SDL_Delay(16);
            }
        }catch(const std::exception& error){SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR,"R/M",error.what(),nullptr);std::cerr<<error.what()<<'\n';result=3;}
    }
    Rml::Shutdown();Backend::Shutdown();return result;
}
