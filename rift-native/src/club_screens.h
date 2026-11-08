// Screen builders included inside Application; all values come from the online club.
int calendar_week=0;
Json competition_state;
static std::string Money(const Json& value) {
    std::string result=std::to_string(value.get<long long>());
    const int first=result[0]=='-'?1:0;
    for(int i=static_cast<int>(result.size())-3;i>first;i-=3)result.insert(i,",");
    return result+"원";
}
std::string ScheduleBody(bool fetch) {
    if(fetch)cached_fixtures=online::Request(L"fixtures?id="+std::to_wstring(career.at("id").get<int>()),online_token).at("fixtures");
    if(!calendar_week)calendar_week=career.at("week").get<int>();
    const int begin=((calendar_week-1)/13)*13+1;
    std::string body="<div class='page-toolbar'><button id='cal-prev'>이전 구간</button><h2>"+career.at("season").dump()+"시즌 · "+std::to_string(begin)+"~"+std::to_string(begin+12)+"주</h2><button id='cal-next'>다음 구간</button><button id='cal-today'>이번 주</button><button id='fixture-refresh'>새로고침</button></div><div class='schedule-grid'>";
    for(int week=begin;week<begin+13;++week) {
        int count=0;
        for(const auto& game:cached_fixtures)if(game.at("season")==career.at("season") && game.at("week")==week)++count;
        body+="<button class='week-cell "+std::string(week==calendar_week?"selected":"")+"' id='cal-week-"+std::to_string(week)+"'><h2>"+std::to_string(week)+"주</h2><small>"+(count?std::to_string(count)+"경기":"경기 없음")+"</small>"+(week==career.at("week").get<int>()?"<p>이번 주</p>":"")+"</button>";
    }
    body+="</div><div class='fm-panel'><h2>"+std::to_string(calendar_week)+"주 일정</h2>";
    bool any=false;
    for(const auto& game:cached_fixtures)if(game.at("season")==career.at("season") && game.at("week")==calendar_week) {
        any=true;const auto state=game.at("state").get<std::string>();
        body+="<div class='schedule-event'><span>"+Escape(game.at("competition").get<std::string>())+" · BO"+game.at("best_of").dump()+"</span><h2>"+Escape(career.at("club").get<std::string>())+" vs "+Escape(game.at("opponent").get<std::string>())+"</h2><p>"+std::string(state=="queued"?"진행 중":state=="finished"?"종료":state=="failed"?"진행 확인 필요":"예정")+"</p><button id='match-open-"+game.at("id").dump()+"'>"+(state=="finished"?"결과 · 다시보기":state=="queued"?"경기 화면 열기":"경기 일정 보기")+"</button></div>";
    }
    if(!any)body+="<p>이 주에 등록된 경기가 없습니다.</p>";
    return body+"</div>";
}
std::string CompetitionBody() {
    competition_state=online::Request(L"competitions?id="+std::to_wstring(career.at("id").get<int>()),online_token);
    std::string body="<div class='fm-panel'><h2>"+Escape(competition_state.at("league").get<std::string>())+" · "+competition_state.at("season").dump()+"시즌</h2><div class='data-row table-heading'><span class='cell-small'>순위</span><span class='cell-name'>구단</span><span>경기</span><span>승</span><span>패</span><span>세트 승</span><span>세트 패</span></div>";
    const auto& table=competition_state.at("standings");
    for(size_t i=0;i<table.size();++i) {
        const auto& row=table[i];
        body+="<div class='data-row "+std::string(row.at("team")==career.at("club")?"own-row":"")+"'><span class='cell-small'>"+(row.at("rank").is_null()?"—":row.at("rank").dump())+"</span><button class='cell-name' id='comp-team-"+std::to_string(i)+"'>"+Logo(competition_state.at("league").get<std::string>(),row.at("team").get<std::string>())+Escape(row.at("team").get<std::string>())+"</button>";
        for(const auto* field:{"played","wins","losses","sets_won","sets_lost"})body+="<span>"+row.at(field).dump()+"</span>";
        body+="</div>";
    }
    body+="</div><div class='fm-panel'><h2>대회별 경기 방식</h2>";
    for(const auto& rule:competition_state.at("rules"))body+="<div class='data-row'><span class='cell-name'>"+Escape(rule.at("competition").get<std::string>())+"</span><span class='cell-name'>"+Escape(rule.at("stage").get<std::string>())+"</span><span>BO"+rule.at("best_of").dump()+"</span></div>";
    return body+"</div>";
}
