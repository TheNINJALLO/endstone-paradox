// SPDX-License-Identifier: GPL-3.0-or-later
#include "paradox/engine.hpp"
#include <algorithm>
#include <cctype>
#include <limits>

namespace paradox {
const std::vector<ModuleSpec> &module_specs() {
    static const std::vector<ModuleSpec> specs = {{"fly", "movement", true},
                                                  {"noclip", "movement", true},
                                                  {"waterwalk", "movement", true},
                                                  {"stephack", "movement", true},
                                                  {"timer", "movement", true},
                                                  {"blink", "movement", true},
                                                  {"killaura", "combat", true},
                                                  {"reach", "combat", true},
                                                  {"autoclicker", "combat", true},
                                                  {"antikb", "combat", true},
                                                  {"criticals", "combat", true},
                                                  {"wallhit", "combat", true},
                                                  {"triggerbot", "combat", true},
                                                  {"vision", "combat", true},
                                                  {"scaffold", "building", true},
                                                  {"xray", "building", true},
                                                  {"gamemode", "policy", true},
                                                  {"namespoof", "validation", true},
                                                  {"selfinfliction", "combat", true},
                                                  {"skinguard", "validation", true},
                                                  {"illegalitems", "inventory", true},
                                                  {"afk", "management", true},
                                                  {"worldborder", "management", true},
                                                  {"lagclear", "management", true},
                                                  {"pvp", "management", true},
                                                  {"ratelimit", "network", false},
                                                  {"packetmonitor", "network", false},
                                                  {"containersee", "inventory", false},
                                                  {"antidupe", "inventory", false},
                                                  {"crashdrop", "inventory", false},
                                                  {"invsync", "inventory", false},
                                                  {"discord", "integration", true},
                                                  {"chatprotection", "chat", true},
                                                  {"antigrief", "building", true},
                                                  {"evidencereplay", "evidence", true},
                                                  {"adaptivecheck", "evidence", false},
                                                  {"botdetection", "evidence", false},
                                                  {"reportsystem", "evidence", false},
                                                  {"fingerprint", "evidence", false},
                                                  {"aimbotmonitor", "combat", true},
                                                  {"anticrash", "network", true},
                                                  {"autototem", "inventory", true},
                                                  {"containerlock", "policy", false},
                                                  {"deathcoords", "management", true},
                                                  {"dimensionlock", "policy", false},
                                                  {"pathingmonitor", "movement", true},
                                                  {"hotbarcheck", "validation", true},
                                                  {"invalidmovementvector", "validation", true},
                                                  {"inventorymovement", "movement", true},
                                                  {"gamemodepolicy", "policy", false},
                                                  {"gravesaver", "management", false},
                                                  {"chunkborders", "management", false},
                                                  {"lockdown", "policy", false},
                                                  {"landclaim", "policy", false}};
    return specs;
}
double angle_delta(double a, double b) {
    return std::abs(std::remainder(a - b, 360.0));
}
std::string normalize_name(std::string_view name) {
    std::string out(name);
    std::transform(out.begin(), out.end(), out.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return out;
}
bool supported_runtime(std::string_view version, int protocol) {
    return protocol == 2193 && (version == "26.51" || version == "1.26.51" || version == "1.26.51.1");
}
void LagGuard::suspend(double now, std::string_view reason, double duration) {
    until_ = std::max(until_, now + duration);
    stable_ = 0;
    reason_ = reason;
    ++epoch_;
}
void LagGuard::reset(double now, double seconds) {
    suspend(now, "transition", seconds);
    last_ = -1;
    last_sample_ = -1;
    last_packet_ = -1;
    tick_ = 0;
    ping_ = 0;
    jitter_ = 0;
}
bool LagGuard::update(double now, const Health &h) {
    if (!std::isfinite(now))
        return false;
    if (last_ >= 0 && (now < last_ || now - last_ > 0.25))
        suspend(now, "server scheduling gap");
    const bool new_sample = last_sample_ < 0 || now - last_sample_ >= 0.025;
    if (new_sample)
        last_sample_ = now;
    last_ = now;
    if (!std::isfinite(h.ping_ms) || h.ping_ms <= 0 || h.ping_ms > 250)
        suspend(now, "latency unknown or high");
    else if (new_sample) {
        const double delta = ping_ > 0 ? std::abs(h.ping_ms - ping_) : 0;
        jitter_ = jitter_ * 0.8 + delta * 0.2;
        ping_ = ping_ > 0 ? ping_ * 0.9 + h.ping_ms * 0.1 : h.ping_ms;
        if (delta > 80 || jitter_ > 35)
            suspend(now, "latency jitter");
    }
    if (!std::isfinite(h.tps) || !std::isfinite(h.tick_ms) || h.tps < 18 || h.tick_ms > 100 || h.tps <= 0)
        suspend(now, "server lag");
    if (!h.loaded)
        suspend(now, "unloaded terrain");
    if (h.exempt || h.transition || h.special_movement)
        suspend(now, "movement exemption");
    if (now >= until_ && new_sample)
        ++stable_;
    return ready(now);
}
bool LagGuard::packet(double now, std::uint64_t tick) {
    if (last_packet_ >= 0) {
        const double gap = now - last_packet_;
        // Duplicates, reordered inputs and catch-up bursts reset timing evidence.
        if (gap < 0.015 || gap > 0.2 || tick <= tick_ || tick - tick_ > 4)
            suspend(now, "input gap, burst or discontinuity");
    }
    last_packet_ = now;
    tick_ = tick;
    return ready(now);
}
bool LagGuard::ready(double now) const {
    return now >= until_ && stable_ >= 20;
}
void Detector::clear_samples() {
    previous_.reset();
    positions_.clear();
    attacks_.clear();
    breaks_.clear();
    places_.clear();
    rigid_since_ = hover_since_ = 0;
    timer_start_ = -1;
    timer_windows_ = reach_hits_ = ore_count_ = break_count_ = 0;
}
void Detector::reset(double now, double duration) {
    lag.reset(now, duration);
    clear_samples();
    epoch_ = lag.epoch();
}
bool Detector::healthy(double now, const Health &h) {
    bool result = lag.update(now, h);
    if (epoch_ != lag.epoch()) {
        clear_samples();
        epoch_ = lag.epoch();
    }
    return result;
}
static void trim(std::deque<double> &q, double now, double window) {
    while (!q.empty() && now - q.front() > window)
        q.pop_front();
    while (q.size() > 512)
        q.pop_front();
}
std::vector<Finding> Detector::move(const Movement &m, const Health &h) {
    std::vector<Finding> out;
    if (!m.pos.finite() || !std::isfinite(m.yaw) || !std::isfinite(m.pitch)) {
        out.push_back({"invalidmovementvector", "Non-finite server movement", Confidence::invalid});
        return out;
    }
    if (!healthy(m.time, h))
        return out;
    if (previous_) {
        double dt = m.time - previous_->time;
        if (dt < 0.025 || dt > 0.25) {
            clear_samples();
            previous_ = m;
            return out;
        }
        const auto &p = *previous_;
        double horizontal = std::hypot(m.pos.x - p.pos.x, m.pos.z - p.pos.z), dy = m.pos.y - p.pos.y;
        // Physics observations are intentionally non-punitive: effects, moving blocks,
        // knockback and server-authorised movement cannot all be inferred from positions.
        if (m.time - last_observation_ >= 10) {
            if (horizontal / dt > 14)
                out.push_back({"fly", "Sustained movement speed review", Confidence::observation, horizontal / dt, 14});
            if (horizontal > 6)
                out.push_back({"blink", "Position discontinuity review", Confidence::observation, horizontal, 6});
            if (m.solid_inside)
                out.push_back({"noclip", "Collision overlap review", Confidence::observation});
            if (dy > 1.6 && p.on_ground && m.on_ground)
                out.push_back({"stephack", "Vertical step review", Confidence::observation, dy, 1.6});
            if (m.liquid_below && !m.in_water && std::abs(dy) < 0.005 && horizontal > 0.1)
                out.push_back({"waterwalk", "Liquid surface movement review", Confidence::observation});
            if (angle_delta(m.yaw, p.yaw) > 150 && horizontal < 0.05)
                out.push_back({"aimbotmonitor", "Large view change; input device is unknown", Confidence::observation});
            if (!out.empty())
                last_observation_ = m.time;
        }
        // Unchanged yaw is normal keyboard/controller movement. No robotic-pathing finding.
        if (!m.on_ground && m.passable_below && std::abs(dy) < 0.002) {
            if (!hover_since_)
                hover_since_ = m.time;
            if (m.time - hover_since_ > 4 && m.time - last_observation_ >= 10) {
                out.push_back({"fly", "Hover review; effects may explain this", Confidence::observation,
                               m.time - hover_since_, 4});
                last_observation_ = m.time;
            }
        } else
            hover_since_ = 0;
    }
    previous_ = m;
    positions_.push_back(m);
    while (positions_.size() > 80)
        positions_.pop_front();
    return out;
}
std::vector<Finding> Detector::attack(const Combat &c, const Health &h) {
    std::vector<Finding> out;
    if (!healthy(c.time, h) || !c.target_healthy || !std::isfinite(c.distance)) {
        reach_hits_ = 0;
        return out;
    }
    attacks_.push_back(c.time);
    trim(attacks_, c.time, 3);
    // A large conservative envelope covers both RTTs plus target movement/reconciliation.
    const double allowance =
        6.0 + std::clamp((h.ping_ms + c.target_ping) / 1000.0, 0.0, 0.5) * std::max(10.0, c.target_speed);
    if (c.standard_melee && c.distance > allowance) {
        if (++reach_hits_ >= 4) {
            out.push_back({"reach", "Repeated melee hits outside latency envelope", Confidence::corroborated,
                           c.distance, allowance});
            reach_hits_ = 0;
        }
    } else
        reach_hits_ = 0;
    if (c.time - last_observation_ < 10)
        return out;
    if (attacks_.size() > 90)
        out.push_back({"autoclicker", "High attack rate review", Confidence::observation, attacks_.size() / 3.0, 30});
    if (!c.unobstructed) {
        out.push_back({"wallhit", "Possible occluded hit", Confidence::observation});
        out.push_back({"vision", "Line of sight review", Confidence::observation});
    }
    if (c.yaw_error > 135)
        out.push_back({"killaura", "Hit behind current view; interpolation may explain this", Confidence::observation,
                       c.yaw_error, 135});
    if (c.self_hit)
        out.push_back({"selfinfliction", "Self-attributed damage review", Confidence::observation});
    if (attacks_.size() >= 12) {
        double sum = 0, sq = 0;
        for (std::size_t i = 1; i < attacks_.size(); ++i) {
            double d = attacks_[i] - attacks_[i - 1];
            sum += d;
            sq += d * d;
        }
        double count = static_cast<double>(attacks_.size() - 1), variance = sq / count - std::pow(sum / count, 2);
        if (variance < 1e-6)
            out.push_back({"triggerbot", "Regular attack cadence review", Confidence::observation, variance, 1e-6});
    }
    if (!out.empty())
        last_observation_ = c.time;
    return out;
}
std::vector<Finding> Detector::input(double now, std::uint64_t tick, Vec3 vector, const Health &h) {
    std::vector<Finding> out;
    if (!vector.finite()) {
        out.push_back({"invalidmovementvector", "Non-finite input vector", Confidence::invalid});
        return out;
    }
    // Each axis is validated; diagonal keyboard input need not be normalised.
    if (std::abs(vector.x) > 1.001 || std::abs(vector.z) > 1.001)
        out.push_back({"invalidmovementvector", "Movement axis exceeds protocol input range", Confidence::invalid,
                       std::max(std::abs(vector.x), std::abs(vector.z)), 1.001});
    healthy(now, h);
    lag.packet(now, tick);
    if (epoch_ != lag.epoch()) {
        clear_samples();
        epoch_ = lag.epoch();
    }
    if (!lag.ready(now))
        return out;
    if (timer_start_ < 0) {
        timer_start_ = now;
        timer_tick_ = tick;
        return out;
    }
    const double elapsed = now - timer_start_;
    if (elapsed >= 5) {
        double rate = static_cast<double>(tick - timer_tick_) / elapsed;
        if (rate > 23 && rate < 100)
            ++timer_windows_;
        else
            timer_windows_ = 0;
        if (timer_windows_ >= 3) {
            out.push_back(
                {"timer", "Client clock accelerated across three healthy windows", Confidence::corroborated, rate, 23});
            timer_windows_ = 0;
        }
        timer_start_ = now;
        timer_tick_ = tick;
    }
    return out;
}
std::vector<Finding> Detector::block(double now, bool place, bool ore, bool unsupported, const Health &h) {
    std::vector<Finding> out;
    if (!healthy(now, h))
        return out;
    auto &q = place ? places_ : breaks_;
    q.push_back(now);
    trim(q, now, 3);
    if (!place) {
        ++break_count_;
        if (ore)
            ++ore_count_;
    }
    if (now - last_observation_ < 10)
        return out;
    if (q.size() > 90)
        out.push_back({"antigrief", "High block action rate; review tool/enchantment context", Confidence::observation,
                       static_cast<double>(q.size()), 90});
    if (place && unsupported)
        out.push_back({"scaffold", "Unsupported placement review", Confidence::observation});
    if (break_count_ >= 100 && static_cast<double>(ore_count_) / break_count_ > 0.5)
        out.push_back({"xray", "Ore ratio review; exposed veins and custom worlds may explain this",
                       Confidence::observation, static_cast<double>(ore_count_) / break_count_, 0.5});
    if (!out.empty())
        last_observation_ = now;
    return out;
}
bool Detector::may_enforce(const Finding &f, double now) const {
    return f.confidence == Confidence::invalid || (f.confidence == Confidence::corroborated && lag.ready(now));
}
Action Enforcement::record(std::string_view player, const Finding &f, double now, bool healthy, std::string_view mode) {
    if (mode == "logonly" || f.confidence == Confidence::observation)
        return Action::observe;
    // Malformed data can be discarded without treating a client/version fault as a ban.
    if (f.confidence == Confidence::invalid)
        return Action::cancel;
    const std::string key = std::string(player) + "/" + f.module;
    if (!healthy) {
        evidence_.erase(key);
        return Action::observe;
    }
    auto &q = evidence_[key];
    trim(q, now, 60);
    if (!q.empty() && now - q.back() < 2)
        return Action::observe;
    q.push_back(now);
    if (mode == "hard" && q.size() >= 6 && now - q.front() >= 15) {
        q.clear();
        return Action::kick;
    }
    if (q.size() >= 3 && now - q.front() >= 4)
        return Action::setback;
    return Action::cancel;
}
void Enforcement::reset(std::string_view player) {
    const std::string prefix = std::string(player) + "/";
    std::erase_if(evidence_, [&](const auto &v) { return v.first.starts_with(prefix); });
}
} // namespace paradox
