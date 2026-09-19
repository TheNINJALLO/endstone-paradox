// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <cmath>
#include <cstdint>
#include <deque>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace paradox {
struct Vec3 {
    double x{}, y{}, z{};
    bool finite() const {
        return std::isfinite(x) && std::isfinite(y) && std::isfinite(z);
    }
    double distance(const Vec3 &v) const {
        return std::hypot(x - v.x, y - v.y, z - v.z);
    }
};
enum class Confidence { observation, corroborated, invalid };
struct Finding {
    std::string module, reason;
    Confidence confidence{Confidence::observation};
    double value{}, limit{};
};
struct Health {
    double ping_ms{}, tps{20}, tick_ms{50};
    bool loaded{true}, exempt{}, transition{}, special_movement{};
};
// Time is always monotonic seconds supplied by the caller; never wall time or packet count.
class LagGuard {
  public:
    void reset(double now, double seconds = 5);
    bool update(double now, const Health &health);
    bool packet(double now, std::uint64_t tick);
    bool ready(double now) const;
    std::uint64_t epoch() const {
        return epoch_;
    }
    double jitter() const {
        return jitter_;
    }
    std::string_view reason() const {
        return reason_;
    }

  private:
    double until_{}, last_{-1}, last_sample_{-1}, last_packet_{-1}, ping_{}, jitter_{};
    std::uint64_t tick_{}, epoch_{};
    unsigned stable_{};
    std::string reason_ = "join warmup";
    void suspend(double now, std::string_view reason, double duration = 5);
};
struct Movement {
    double time{};
    Vec3 pos;
    double yaw{}, pitch{};
    bool on_ground{}, in_water{}, solid_inside{}, liquid_below{}, passable_below{true};
};
struct Combat {
    double time{}, distance{}, target_ping{}, target_speed{}, yaw_error{};
    bool target_healthy{}, unobstructed{true}, same_target{}, falling{}, self_hit{};
    bool standard_melee{true};
};
struct ModuleSpec {
    std::string_view name, kind;
    bool enabled;
};
const std::vector<ModuleSpec> &module_specs();

class Detector {
  public:
    LagGuard lag;
    void reset(double now, double duration = 5);
    std::vector<Finding> move(const Movement &, const Health &);
    std::vector<Finding> attack(const Combat &, const Health &);
    std::vector<Finding> input(double now, std::uint64_t tick, Vec3 move_vector, const Health &);
    std::vector<Finding> block(double now, bool place, bool ore, bool unsupported, const Health &);
    // A repeatable observation does not become proof merely by being repeated.
    bool may_enforce(const Finding &, double now) const;

  private:
    std::uint64_t epoch_{};
    std::optional<Movement> previous_;
    std::deque<Movement> positions_;
    std::deque<double> attacks_, breaks_, places_;
    double rigid_since_{}, hover_since_{}, timer_start_{-1}, last_observation_{-100};
    std::uint64_t timer_tick_{};
    unsigned timer_windows_{}, reach_hits_{}, ore_count_{}, break_count_{};
    void clear_samples();
    bool healthy(double now, const Health &);
};

enum class Action { observe, cancel, setback, kick };
class Enforcement {
  public:
    Action record(std::string_view player, const Finding &, double now, bool healthy, std::string_view mode);
    void reset(std::string_view player);

  private:
    // Independent evidence per detector: correlated movement checks never stack into a ban.
    std::unordered_map<std::string, std::deque<double>> evidence_;
};
double angle_delta(double a, double b);
std::string normalize_name(std::string_view name);
bool supported_runtime(std::string_view version, int protocol);
} // namespace paradox
