// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include "engine.hpp"
#include <string_view>
namespace paradox {
struct PacketResult {
    bool decoded{}, malformed{}, input{}, inventory{}, transition{};
    std::uint64_t tick{};
    Vec3 movement, position;
    int hotbar{-1}, effect{-1}, effect_duration{};
    std::uint64_t actor{};
    std::string reason;
};
PacketResult inspect_packet(int id, std::string_view payload, bool outgoing = false);
} // namespace paradox
