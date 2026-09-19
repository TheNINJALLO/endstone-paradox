// SPDX-License-Identifier: GPL-3.0-or-later
#include "paradox/protocol.hpp"
#include <algorithm>
#include <bedrock/protocol/chunk.h>
#include <bedrock/protocol/effect.h>
#include <bedrock/protocol/input.h>
#include <bedrock/protocol/inventory.h>
#include <bedrock/protocol/movement.h>
#include <bedrock/protocol/stream.hpp>
namespace paradox {
namespace bp = bedrock::protocol;
PacketResult inspect_packet(int id, std::string_view payload, bool outgoing) {
    PacketResult r;
    // Large legitimate payloads are left to the server; size alone is never a ban.
    // Our decoder has a bounded inspection budget, including nested allocations.
    if (payload.size() > 262144) {
        r.reason = "Inspection size budget exceeded";
        return r;
    }
    bp::BinaryReader stream(payload);
    try {
        if (!outgoing && id == 144) {
            auto packet = bp::deserialize<bp::PlayerAuthInputPacket_<2193>>(stream);
            if (!packet || stream.getUnreadLength() != 0) {
                r.malformed = true;
                r.reason = "Malformed protocol 2193 input";
                return r;
            }
            r.decoded = true;
            r.input = true;
            r.tick = packet->client_tick;
            r.movement = {packet->move.x, 0, packet->move.y};
            r.position = {packet->pos.x, packet->pos.y, packet->pos.z};
            using Flag = bp::PlayerAuthInputPacket_<2193>::InputData;
            for (auto flag : packet->input_data) {
                if (flag == Flag::HandledTeleport || flag == Flag::IsInClientPredictedVehicle ||
                    flag == Flag::StartGliding || flag == Flag::StartSpinAttack)
                    r.transition = true;
            }
            r.inventory = packet->item_stack_request.has_value();
            if (!r.position.finite() || !r.movement.finite() || !std::isfinite(packet->rot.x) ||
                !std::isfinite(packet->rot.y)) {
                r.malformed = true;
                r.reason = "Non-finite movement fields";
            }
        } else if (!outgoing && id == 48) {
            auto packet = bp::deserialize<bp::PlayerHotbarPacket_<2193>>(stream);
            if (!packet || stream.getUnreadLength() != 0) {
                r.malformed = true;
                r.reason = "Malformed protocol 2193 hotbar selection";
                return r;
            }
            r.decoded = true;
            r.hotbar = static_cast<int>(packet->selected_slot);
            if (packet->should_select_slot && packet->selected_slot > 8) {
                r.malformed = true;
                r.reason = "Selected hotbar slot outside 0..8";
            }
        } else if (!outgoing && id == 175) {
            auto packet = bp::deserialize<bp::SubChunkRequestPacket_<2193>>(stream);
            if (!packet || stream.getUnreadLength() != 0) {
                r.malformed = true;
                r.reason = "Malformed protocol 2193 subchunk request";
                return r;
            }
            r.decoded = true;
        } else if (outgoing && id == 40) {
            auto packet = bp::deserialize<bp::SetActorMotionPacket>(stream);
            if (!packet || stream.getUnreadLength() != 0)
                return r;
            r.decoded = true;
            r.transition = true;
            r.actor = packet->runtime_id;
        } else if (outgoing && id == 19) {
            auto packet = bp::deserialize<bp::MovePlayerPacket_<2193>>(stream);
            if (!packet || stream.getUnreadLength() != 0)
                return r;
            r.decoded = true;
            r.transition = packet->teleport_data.has_value();
            r.actor = packet->player_id;
        } else if (outgoing && id == 28) {
            auto packet = bp::deserialize<bp::MobEffectPacket_<2193>>(stream);
            if (!packet || stream.getUnreadLength() != 0)
                return r;
            r.decoded = true;
            r.effect = static_cast<int>(packet->effect_id);
            r.effect_duration =
                packet->event_id == bp::MobEffectPacket_<2193>::Event::Remove ? 0 : packet->effect_duration_ticks;
            r.actor = packet->runtime_id;
        } else if (!outgoing && (id == 147 || id == 30))
            r.inventory = true;
    } catch (const std::exception &) {
        r.reason = "Packet inspection budget or schema failure";
    }
    return r;
}
} // namespace paradox
