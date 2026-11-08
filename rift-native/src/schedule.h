#pragma once
#include <algorithm>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace schedule {
struct Match { int week; std::string home, away, competition; };
inline bool valid(const std::vector<Match>& matches) {
    std::set<std::pair<int, std::string>> occupied;
    for (const auto& m : matches) {
        if (m.week < 1 || m.week > 104 || m.home.empty() || m.away.empty() || m.home == m.away ||
            !occupied.insert({m.week,m.home}).second || !occupied.insert({m.week,m.away}).second) return false;
    }
    return true;
}
// Circle method; empty slots are byes. Existing fixtures are respected across competitions.
inline std::vector<Match> round_robin(std::vector<std::string> teams, const std::vector<int>& weeks,
                                       const std::vector<Match>& existing, const std::string& competition, bool twice) {
    std::set<std::string> unique(teams.begin(), teams.end());
    if (teams.size() < 2 || unique.size() != teams.size() || unique.count("") || !valid(existing))
        throw std::invalid_argument("invalid teams or existing fixtures");
    if (teams.size() % 2) teams.push_back("");
    const int rounds = static_cast<int>(teams.size()) - 1;
    auto result = existing;
    size_t next = 0;
    for (int leg=0; leg<(twice ? 2 : 1); ++leg) {
        for (int round=0; round<rounds; ++round) {
            std::vector<Match> batch;
            for (size_t i=0; i<teams.size()/2; ++i) {
                auto a=teams[i], b=teams[teams.size()-1-i];
                if (a.empty() || b.empty()) continue;
                if ((round + static_cast<int>(i) + leg) % 2) std::swap(a,b);
                batch.push_back({0,a,b,competition});
            }
            bool placed=false;
            while (next < weeks.size()) {
                int week=weeks[next++];
                auto trial=result;
                for (auto m:batch) { m.week=week; trial.push_back(m); }
                if (valid(trial)) { result=std::move(trial); placed=true; break; }
            }
            if (!placed) throw std::runtime_error("not enough conflict-free weeks");
            std::rotate(teams.begin()+1, teams.end()-1, teams.end());
        }
    }
    return result;
}
}
