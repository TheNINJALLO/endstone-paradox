// SPDX-License-Identifier: GPL-3.0-or-later
#include "paradox/engine.hpp"
#include "paradox/protocol.hpp"
#include "paradox/store.hpp"
#include <bedrock/protocol/chunk.h>
#include <bedrock/protocol/input.h>
#include <bedrock/protocol/inventory.h>
#include <bedrock/protocol/stream.hpp>
#include <filesystem>
#include <iostream>
#include <limits>
#include <random>
#include <sqlite3.h>
using namespace paradox;
namespace bp = bedrock::protocol;
static unsigned checks{};
void check(bool value, const char *message) {
    ++checks;
    if (!value)
        throw std::runtime_error(message);
}
Health healthy() {
    Health h;
    h.ping_ms = 50;
    return h;
}
void warm(Detector &d, double until = 8) {
    for (double t = 0; t < until; t += 0.05)
        d.move({t, {t * 4, 64, 0}, 0, 0, true}, healthy());
}
void test_lag() {
    for (int kind = 0; kind < 9; ++kind) {
        Detector d;
        d.reset(0);
        warm(d);
        Health h = healthy();
        if (kind == 0)
            h.ping_ms = 500;
        if (kind == 1)
            h.tps = 10;
        if (kind == 2)
            h.tick_ms = 200;
        if (kind == 3)
            h.loaded = false;
        if (kind == 4)
            h.transition = true;
        if (kind == 5)
            h.special_movement = true;
        if (kind == 6)
            h.ping_ms = 0;
        if (kind == 7)
            h.ping_ms = std::numeric_limits<double>::quiet_NaN();
        if (kind == 8)
            h.exempt = true;
        auto findings = d.move({8, {300, 70, 0}, 0, 0, false}, h);
        check(findings.empty(), "lag/exemption produced movement finding");
        check(!d.lag.ready(8), "lag did not gate enforcement");
        for (double t = 8.05; t < 12; t += 0.05)
            check(d.move({t, {t * 100, 64, 0}, 0, 0, true}, healthy()).empty(), "recovery leaked samples");
    }
    Detector d;
    d.reset(0);
    warm(d);
    check(d.lag.ready(7.99), "healthy connection did not warm up");
    d.input(8, 160, {0, 0, 1}, healthy());
    d.input(8.001, 161, {0, 0, 1}, healthy());
    check(!d.lag.ready(8.001), "packet burst not gated");
    check(angle_delta(359, 1) == 2, "yaw wrapping");
}
void test_legitimate_movement() {
    Detector d;
    d.reset(0);
    for (unsigned i = 0; i < 2400; ++i) {
        double t = i * .05;
        for (auto &f : d.move({t, {i * .215, 64, 0}, 0, 0, true}, healthy()))
            check(f.module != "pathingmonitor", "straight line flagged as robotic");
    }
    Enforcement engine;
    for (int i = 0; i < 1000; ++i)
        for (const auto &m : module_specs())
            check(engine.record("legit", {std::string(m.name), "heuristic", Confidence::observation}, i, true,
                                "hard") == Action::observe,
                  "heuristics escalated");
}
void test_positive_controls() {
    Detector d;
    d.reset(0);
    bool timer = false;
    for (unsigned i = 0; i < 900; ++i) {
        double t = i / 30.0;
        auto f = d.input(t, i, {0, 0, 1}, healthy());
        for (auto &entry : f)
            timer |= entry.module == "timer";
    }
    check(timer, "accelerated client clock not detected");
    auto invalid = d.input(31, 901, {std::numeric_limits<double>::infinity(), 0, 0}, healthy());
    check(!invalid.empty() && invalid.front().confidence == Confidence::invalid, "nonfinite input accepted");
    auto diagonal = d.input(31.05, 902, {1, 0, 1}, healthy());
    for (auto &f : diagonal)
        check(f.module != "invalidmovementvector", "legitimate diagonal rejected");
    Enforcement e;
    Finding evidence{"reach", "verified", Confidence::corroborated};
    Action result{};
    for (int i = 0; i < 6; ++i)
        result = e.record("cheat", evidence, i * 4, true, "hard");
    check(result == Action::kick, "verified evidence not enforced");
    for (int i = 0; i < 50; ++i)
        check(e.record("lag", evidence, i, false, "hard") == Action::observe, "lag evidence punished");
    e.record("recovery", evidence, 0, true, "hard");
    e.reset("recovery");
    check(e.record("recovery", evidence, 20, true, "hard") == Action::cancel, "reset retained evidence");
}
void test_combat_and_recovery() {
    Detector d;
    d.reset(0);
    warm(d);
    Combat c;
    c.target_healthy = true;
    c.target_ping = 50;
    c.distance = 3.5;
    for (unsigned i = 0; i < 100; ++i) {
        c.time = 8 + i * .05;
        for (auto &f : d.attack(c, healthy()))
            check(f.confidence != Confidence::corroborated, "legitimate melee escalated");
    }
    c.distance = 30;
    c.target_healthy = false;
    for (unsigned i = 0; i < 10; ++i) {
        c.time = 13 + i * .05;
        check(d.attack(c, healthy()).empty(), "lagging target caused reach violation");
    }
    c.target_healthy = true;
    bool reach = false;
    for (unsigned i = 0; i < 10; ++i) {
        c.time = 13.5 + i * .05;
        for (auto &f : d.attack(c, healthy()))
            reach |= f.module == "reach";
    }
    check(reach, "distant repeated melee not detected");
    c.standard_melee = false;
    for (unsigned i = 0; i < 12; ++i) {
        c.time = 14 + i * .05;
        for (const auto &f : d.attack(c, healthy()))
            check(f.module != "reach", "large mob or custom weapon treated as ordinary melee");
    }

    d.reset(14, 10);
    c.time = 14.05;
    check(d.attack(c, healthy()).empty(), "teleport retained reach evidence");
    Detector delayed;
    delayed.reset(0);
    for (unsigned i = 0; i < 1000; ++i) {
        double t = i * .1;
        for (auto &f : delayed.input(t, i, {0, 0, 1}, healthy()))
            check(f.module != "timer", "slow client flagged by timer");
    }
    Detector jitter;
    jitter.reset(0);
    for (unsigned i = 0; i < 1000; ++i) {
        auto h = healthy();
        h.ping_ms = i % 2 ? 230 : 30;
        check(jitter.input(i * .05, i * 2, {0, 0, 1}, h).empty(), "jitter generated timer finding");
    }
    Enforcement e;
    Finding f{"reach", "far", Confidence::corroborated};
    for (int i = 0; i < 2; ++i)
        e.record("a", f, i * 4, true, "hard");
    check(e.record("b", f, 10, true, "hard") == Action::cancel, "players shared evidence");
    f.module = "timer";
    check(e.record("a", f, 10, true, "hard") == Action::cancel, "modules shared evidence");
}
template <class T> std::string encode(const T &packet) {
    std::string buffer;
    bp::BinaryWriter writer(buffer);
    bp::serialize(writer, packet);
    return buffer;
}
void test_protocol() {
    bp::PlayerHotbarPacket_<2193> hotbar;
    hotbar.should_select_slot = true;
    hotbar.selected_slot = 8;
    auto good = inspect_packet(48, encode(hotbar));
    check(good.decoded && !good.malformed, "slot 8 rejected");
    hotbar.selected_slot = 9;
    auto bad = inspect_packet(48, encode(hotbar));
    check(bad.decoded && bad.malformed, "slot 9 accepted");
    hotbar.should_select_slot = false;
    check(!inspect_packet(48, encode(hotbar)).malformed, "unused hotbar slot rejected");
    // Independent wire fixtures from BDS reflection, excluding the packet header.
    check(inspect_packet(48, std::string("\x08\x00\x01", 3)).decoded, "real hotbar field order");
    auto effect = inspect_packet(28, std::string("\x01\x01\x02\x00\x01\x90\x03\x7b\x01", 9), true);
    check(effect.decoded && effect.effect == 1 && effect.effect_duration == 200, "BDS Ambient effect field lost");
    bp::PlayerAuthInputPacket_<2193> input;
    input.client_tick = bp::PlayerInputTick{123};
    input.pos = {1, 64, 2};
    input.move = {1, 1};
    auto decoded = inspect_packet(144, encode(input));
    check(decoded.decoded && decoded.tick == 123 && !decoded.malformed, "protocol 2193 auth input did not round trip");
    check(!inspect_packet(144, "\xff\xff\xff").decoded, "truncated input decoded");
    check(!inspect_packet(175, std::string(300000, 'x')).malformed, "large packet alone treated as cheating");
    bp::SubChunkRequestPacket_<2193> chunks;
    chunks.sub_chunk_pos_offsets.resize(8192);
    auto large = encode(chunks);
    check(large.size() > 16384, "large chunk fixture is too small");
    auto large_result = inspect_packet(175, large);
    check(large_result.decoded && !large_result.malformed, "valid 8192-offset request rejected");
    auto input_wire = encode(input);
    for (std::size_t i = 0; i < input_wire.size(); ++i)
        check(!inspect_packet(144, std::string_view(input_wire).substr(0, i)).decoded, "truncated prefix decoded");
    std::mt19937 random(2193);
    for (unsigned i = 0; i < 3000; ++i) {
        std::string bytes(random() % 256, '\0');
        for (auto &c : bytes)
            c = static_cast<char>(random());
        auto result = inspect_packet(i % 3 == 0 ? 144 : i % 3 == 1 ? 48 : 175, bytes);
        check(!result.input || result.decoded, "fuzz yielded partial input");
    }
    check(supported_runtime("26.51", 2193), "actual Endstone version refused");
    check(supported_runtime("1.26.51.1", 2193), "target refused");
    check(!supported_runtime("1.26.60", 2211), "wrong ABI accepted");
}
void test_migration() {
    auto directory = std::filesystem::temp_directory_path() / "paradox-native-tests";
    std::filesystem::create_directories(directory);
    auto path = directory / "paradox.db";
    std::filesystem::remove(path);
    std::filesystem::remove(path.string() + ".pre-native.bak");
    sqlite3 *legacy{};
    check(sqlite3_open(path.string().c_str(), &legacy) == SQLITE_OK, "legacy db create");
    check(sqlite3_exec(legacy,
                       "CREATE TABLE homes(key TEXT PRIMARY KEY,value TEXT NOT NULL,updated_at REAL DEFAULT "
                       "(julianday('now')));INSERT INTO homes(key,value) "
                       "VALUES('uuid','{\"base\":{\"x\":-1.75,\"y\":64.5,\"z\":2.25}}');CREATE TABLE _meta(key TEXT "
                       "PRIMARY KEY,value TEXT);INSERT INTO _meta VALUES('db_version','2');",
                       nullptr, nullptr, nullptr) == SQLITE_OK,
          "legacy seed");
    sqlite3_close(legacy);
    {
        Store store(path);
        check(store.get("homes", "uuid")["base"]["x"] == -1.75, "home precision lost");
        for (int i = 0; i < 1000; ++i)
            store.set("players", std::to_string(i), {{"clearance", 4}, {"name", "Player"}});
        store.set("bans", "uid", {{"reason", "manual"}});
        store.flush();
        check(std::filesystem::exists(path.string() + ".pre-native.bak"), "backup missing");
    }
    {
        Store store(path);
        check(store.all("players").size() == 1000, "worker lost writes");
        check(store.get("bans", "uid")["reason"] == "manual", "ban did not persist");
        store.erase("bans", "uid");
        store.flush();
    }
    {
        Store store(path);
        check(store.get("bans", "uid").is_null(), "delete did not persist");
    }
    std::filesystem::remove(path);
    std::filesystem::remove(path.string() + ".pre-native.bak");
}
int main() {
    try {
        test_lag();
        test_legitimate_movement();
        test_positive_controls();
        test_combat_and_recovery();
        test_protocol();
        test_migration();
        std::cout << checks << " checks passed\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "FAIL: " << e.what() << '\n';
        return 1;
    }
}
