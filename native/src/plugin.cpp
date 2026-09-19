// SPDX-License-Identifier: GPL-3.0-or-later
// Native Endstone port of Paradox, originally by Visual1mpact.
#include "paradox/abi.hpp"
#include "paradox/engine.hpp"
#include "paradox/protocol.hpp"
#include "paradox/store.hpp"
#include "paradox/web.hpp"
#include <array>
#include <endstone/block/block.h>
#include <endstone/command/console_command_sender.h>
#include <endstone/event/actor/actor_damage_event.h>
#include <endstone/event/actor/actor_explode_event.h>
#include <endstone/event/actor/actor_knockback_event.h>
#include <endstone/event/actor/player_death_event.h>
#include <endstone/event/block/block_break_event.h>
#include <endstone/event/block/block_explode_event.h>
#include <endstone/event/block/block_from_to_event.h>
#include <endstone/event/block/block_piston_extend_event.h>
#include <endstone/event/block/block_piston_retract_event.h>
#include <endstone/event/block/block_place_event.h>
#include <endstone/event/chunk/chunk_load_event.h>
#include <endstone/event/chunk/chunk_unload_event.h>
#include <endstone/event/player/player_chat_event.h>
#include <endstone/event/player/player_command_event.h>
#include <endstone/event/player/player_dimension_change_event.h>
#include <endstone/event/player/player_drop_item_event.h>
#include <endstone/event/player/player_game_mode_change_event.h>
#include <endstone/event/player/player_interact_event.h>
#include <endstone/event/player/player_item_held_event.h>
#include <endstone/event/player/player_join_event.h>
#include <endstone/event/player/player_move_event.h>
#include <endstone/event/player/player_pickup_item_event.h>
#include <endstone/event/player/player_portal_event.h>
#include <endstone/event/player/player_quit_event.h>
#include <endstone/event/player/player_respawn_event.h>
#include <endstone/event/player/player_teleport_event.h>
#include <endstone/event/server/packet_receive_event.h>
#include <endstone/event/server/packet_send_event.h>
#include <endstone/form/action_form.h>
#include <endstone/form/modal_form.h>
#include <endstone/inventory/player_inventory.h>
#include <endstone/level/chunk.h>
#include <endstone/level/dimension.h>
#include <endstone/level/level.h>
#include <endstone/nbt/tag.h>
#include <endstone/player.h>
#include <endstone/plugin/plugin.h>
#include <endstone/plugin/plugin_manager.h>
#include <endstone/scheduler/scheduler.h>
#include <endstone/server.h>
#include <fstream>
#include <iomanip>
#include <random>
#include <set>
#include <sstream>
#include <toml++/toml.hpp>
#include <unordered_set>

namespace paradox {
namespace es = endstone;
double now() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}
double unix_time() {
    return std::chrono::duration<double>(std::chrono::system_clock::now().time_since_epoch()).count();
}
std::string id(const es::Player &p) {
    return p.getUniqueId().str();
}
es::Location eye(es::Player &p) {
    auto l = p.getLocation();
    l.setY(l.getY() + (p.isSneaking() ? 1.27F : 1.62F));
    return l;
}
Vec3 vec(const es::Location &l) {
    return {l.getX(), l.getY(), l.getZ()};
}
Json location_json(const es::Location &l) {
    return {{"x", l.getX()},         {"y", l.getY()},     {"z", l.getZ()},
            {"pitch", l.getPitch()}, {"yaw", l.getYaw()}, {"dimension", l.getDimension().getName()}};
}
std::string chunk_key(const es::Dimension &d, int x, int z) {
    return d.getName() + ":" + std::to_string(x) + ":" + std::to_string(z);
}
std::string block_key(const es::Block &b) {
    return b.getDimension().getName() + ":" + std::to_string(b.getX()) + ":" + std::to_string(b.getY()) + ":" +
           std::to_string(b.getZ());
}
bool air(const std::string &type) {
    return type == "minecraft:air" || type == "minecraft:cave_air" || type == "minecraft:void_air";
}
std::string legacy_block_key(const es::Block &b) {
    return b.getDimension().getName() + ":" + std::to_string(b.getX()) + "," + std::to_string(b.getY()) + "," +
           std::to_string(b.getZ());
}
bool container(const std::string &type) {
    return type.find("chest") != std::string::npos || type.find("barrel") != std::string::npos ||
           type.find("shulker_box") != std::string::npos;
}
std::vector<std::string> split(const std::vector<std::string> &args) {
    std::string joined;
    for (const auto &a : args) {
        if (!joined.empty())
            joined += ' ';
        joined += a;
    }
    std::istringstream in(joined);
    std::vector<std::string> out;
    std::string s;
    while (in >> std::quoted(s)) {
        out.push_back(s);
        if (out.size() > 32)
            throw std::invalid_argument("Too many arguments");
    }
    return out;
}
std::string join(const std::vector<std::string> &a, std::size_t start) {
    std::string s;
    for (; start < a.size(); ++start) {
        if (!s.empty())
            s += ' ';
        s += a[start];
    }
    return s;
}
double number(const std::string &s, double low, double high) {
    std::size_t n{};
    double d = std::stod(s, &n);
    if (n != s.size() || !std::isfinite(d) || d < low || d > high)
        throw std::invalid_argument("Value outside allowed range");
    return d;
}

class ParadoxPlugin : public es::Plugin {
  public:
    void onEnable() override;
    void onDisable() override;
    bool onCommand(es::CommandSender &, const es::Command &, const std::vector<std::string> &) override;

  private:
    struct PlayerState {
        Detector detector;
        std::optional<es::Location> safe;
        double activity{}, impulse_until{}, effect_until{}, last_chat{}, last_command{}, auth_attempt{}, attack_time{},
            inventory_time{}, last_inventory{}, last_packet_window{};
        unsigned packets{};
        std::deque<double> chat_times, command_times;
        double transition_until{}, last_report{};
        bool frozen{}, chunk_borders{}, vanished{};
        unsigned pending_forms{};
        bool inventory_dirty{};
        double combat_until{}, last_pvp_toggle{}, knockback_time{};
        std::optional<Vec3> knockback_origin;
        Json inventory = Json::array();
        Json replay = Json::array();
        std::unordered_map<std::string, double> alerts, exemptions;
        std::string channel, rank, last_message, last_target;
        std::optional<Vec3> previous;
        double speed{};
    };
    std::unique_ptr<Store> db_;
    std::unique_ptr<Web> web_;
    toml::table config_;
    std::unordered_map<std::string, PlayerState> players_;
    std::unordered_map<std::string, std::pair<std::string, double>> tpa_, watchers_;
    std::unordered_set<std::string> chunks_;
    Enforcement enforcement_;
    Json modules_ = Json::object(), recent_ = Json::array(), claims_ = Json::object();
    std::unordered_map<std::string, std::unordered_set<std::string>> identity_lists_;
    void refresh_policies();
    std::string mode_ = "soft";
    bool active_{}, protocol_ok_{}, clean_warning_{};
    unsigned ticks_{};
    double last_tick_{}, last_clean_{}, last_analytics_{}, last_event_error_{};
    std::string fingerprint_salt_;
    std::string global_url_, global_key_;
    double global_next_{}, global_since_{};
    template <class Event>
    void listen(void (ParadoxPlugin::*callback)(Event &), es::EventPriority priority = es::EventPriority::Normal,
                bool ignore_cancelled = false) {
        registerEvent<Event>(
            [this, callback](Event &event) {
                if (!active_ || !getServer().isPrimaryThread())
                    return;
                try {
                    (this->*callback)(event);
                } catch (const std::exception &e) {
                    // A bad integration/configuration sample cannot become a cheating verdict.
                    for (auto &[uid, state] : players_) {
                        state.detector.reset(now());
                        enforcement_.reset(uid);
                    }
                    if (now() - last_event_error_ > 10) {
                        last_event_error_ = now();
                        getLogger().error("Event inspection suspended: {}", e.what());
                    }
                }
            },
            priority, ignore_cancelled);
    }
    template <class T> T setting(std::string_view table, std::string_view key, T fallback) const {
        return config_[table][key].value<T>().value_or(fallback);
    }
    bool enabled(std::string_view name) const {
        auto i = modules_.find(std::string(name));
        return i != modules_.end() && i->value("enabled", false);
    }
    void module(std::string name, bool enabled);
    void tick();
    void initialize(es::Player &);
    void reset(es::Player &, double seconds = 5);
    bool loaded(const es::Location &) const;
    Health health(es::Player &);
    int clearance(es::Player &) const;
    bool allowed(es::Player &, const std::string &table) const;
    void emit(es::Player &, const Finding &, es::ICancellable *event = nullptr);
    void audit(std::string action, es::CommandSender &, Json data);
    Json inventory(es::Player &) const;
    void inspect_inventory(es::Player &);
    void inspect_skin(es::Player &);
    void container_vision(es::Player &);
    bool line_clear(const es::Location &, const es::Location &) const;
    bool protected_environment(es::Block &);
    Json container_lock(es::Block &) const;
    void erase_container_lock(es::Block &);
    void portal_event(es::PlayerPortalEvent &e) {
        teleport_event(e);
    }
    void actor_explode(es::ActorExplodeEvent &e) {
        std::erase_if(e.getBlockList(), [this](auto &b) { return protected_environment(*b); });
    }
    void block_explode(es::BlockExplodeEvent &e) {
        std::erase_if(e.getBlockList(), [this](auto &b) { return protected_environment(*b); });
    }
    void piston(es::BlockPistonEvent &e);
    void piston_extend(es::BlockPistonExtendEvent &e) {
        piston(e);
    }
    void piston_retract(es::BlockPistonRetractEvent &e) {
        piston(e);
    }
    void flow(es::BlockFromToEvent &e) {
        if (protected_environment(e.getToBlock()) && !protected_environment(e.getBlock()))
            e.setCancelled(true);
    }
    void preserve_grave(es::Player &);
    unsigned clear_entities(std::string_view type = "", const es::Location *center = nullptr, double radius = 0);
    bool teleport(es::Player &, const Json &);
    bool protected_block(es::Player &, es::Block &);
    void show_gui(es::Player &);
    void send_form(es::Player &, es::ActionForm);
    bool command(es::CommandSender &, std::string, const std::vector<std::string> &);
    void join_event(es::PlayerJoinEvent &);
    void quit_event(es::PlayerQuitEvent &);
    void move_event(es::PlayerMoveEvent &);
    void teleport_event(es::PlayerTeleportEvent &);
    void respawn_event(es::PlayerRespawnEvent &);
    void dimension_event(es::PlayerDimensionChangeEvent &);
    void gamemode_event(es::PlayerGameModeChangeEvent &);
    void damage_event(es::ActorDamageEvent &);
    void knockback_event(es::ActorKnockbackEvent &);
    void chat_event(es::PlayerChatEvent &);
    void command_event(es::PlayerCommandEvent &);
    void break_event(es::BlockBreakEvent &);
    void place_event(es::BlockPlaceEvent &);
    void interact_event(es::PlayerInteractEvent &);
    void held_event(es::PlayerItemHeldEvent &);
    void death_event(es::PlayerDeathEvent &);
    void drop_event(es::PlayerDropItemEvent &);
    void pickup_event(es::PlayerPickupItemEvent &);
    void chunk_load(es::ChunkLoadEvent &);
    void chunk_unload(es::ChunkUnloadEvent &);
    void receive(es::PacketReceiveEvent &);
    void send(es::PacketSendEvent &);
};

void ParadoxPlugin::onEnable() {
    try {
        const auto data = getDataFolder();
        std::filesystem::create_directories(data);
        const auto config_path = data / "config.toml";
        if (std::filesystem::exists(config_path))
            config_ = toml::parse_file(config_path.string());
        else {
            std::ofstream file(config_path);
            file << "# Paradox native configuration\n[web_ui]\nenabled = true\nhost = \"127.0.0.1\"\nport = "
                    "8080\n\n[global_database]\nenabled = false\napi_url = \"\"\napi_key = "
                    "\"\"\n\n[worldborder]\nradius = 0\nx = 0\nz = 0\n\n[afk]\ntimeout = 600\nkick = "
                    "false\n\n[lagclear]\ninterval = 300\nenabled_removal = false\n";
            file.close();
            config_ = toml::parse_file(config_path.string());
        }
        db_ = std::make_unique<Store>(data / "paradox.db");
        refresh_policies();
        for (const auto &spec : module_specs()) {
            auto old = db_->get("modules", std::string(spec.name));
            bool state = spec.enabled;
            if (auto v = config_["modules"][spec.name]["enabled"].value<bool>())
                state = *v;
            if (old.is_boolean())
                state = old.get<bool>();
            else if (old.is_object())
                state = old.value("enabled", state);
            modules_[spec.name] = {{"enabled", state}, {"kind", spec.kind}};
        }
        mode_ = db_->get("config", "enforcement_mode", "soft").get<std::string>();
        if (mode_ != "soft" && mode_ != "hard" && mode_ != "logonly")
            mode_ = "soft";
        protocol_ok_ = supported_runtime(getServer().getMinecraftVersion(), getServer().getProtocolVersion());
        if (!protocol_ok_)
            getLogger().warning("Packet inspection unavailable for this BDS/protocol. Supported target: 1.26.51.1 / "
                                "2193. Management and API event monitoring remain active.");
        if (auto *level = getServer().getLevel())
            for (auto *dimension : level->getDimensions())
                for (auto &chunk : dimension->getLoadedChunks())
                    chunks_.insert(chunk_key(*dimension, chunk->getX(), chunk->getZ()));
        std::string token;
        const auto token_path = data / "web-token.txt";
        if (std::filesystem::exists(token_path)) {
            std::ifstream file(token_path);
            std::getline(file, token);
        }
        if (token.size() < 32) {
            token = random_token();
            std::ofstream file(token_path, std::ios::trunc);
            file << token << '\n';
            file.close();
            if (!file)
                throw std::runtime_error("Could not save web token");
        }
        fingerprint_salt_ = sha256(token + ":fingerprints");
        web_ = std::make_unique<Web>(
            setting<std::string>("web_ui", "host", "127.0.0.1"),
            setting<bool>("web_ui", "enabled", true) ? setting<int>("web_ui", "port", 8080) : 0, token);
        if (setting<bool>("global_database", "enabled", false)) {
            global_url_ = setting<std::string>("global_database", "api_url", "");
            while (!global_url_.empty() && global_url_.back() == '/')
                global_url_.pop_back();
            global_key_ = setting<std::string>("global_database", "api_key",
                                               db_->get("config", "global_api_key", "").get<std::string>());
            if (global_key_.empty())
                global_key_ = db_->get("config", "global_api_key", "").get<std::string>();
            global_since_ = db_->get("config", "global_last_sync", 0.0).get<double>();
            if (global_url_.empty())
                getLogger().warning("Global database enabled without api_url. Local bans are retained; configure the "
                                    "HTTPS endpoint to resume synchronization.");
        }
        listen(&ParadoxPlugin::join_event);
        listen(&ParadoxPlugin::quit_event);
        listen(&ParadoxPlugin::move_event, es::EventPriority::High, true);
        listen(&ParadoxPlugin::teleport_event, es::EventPriority::High, true);
        listen(&ParadoxPlugin::respawn_event);
        listen(&ParadoxPlugin::portal_event, es::EventPriority::High, true);
        listen(&ParadoxPlugin::actor_explode, es::EventPriority::High, true);
        listen(&ParadoxPlugin::block_explode, es::EventPriority::High, true);
        listen(&ParadoxPlugin::piston_extend, es::EventPriority::High, true);
        listen(&ParadoxPlugin::piston_retract, es::EventPriority::High, true);
        listen(&ParadoxPlugin::flow, es::EventPriority::High, true);
        listen(&ParadoxPlugin::dimension_event);
        listen(&ParadoxPlugin::gamemode_event, es::EventPriority::High, true);
        listen(&ParadoxPlugin::damage_event, es::EventPriority::High, true);
        listen(&ParadoxPlugin::knockback_event, es::EventPriority::Monitor, true);
        listen(&ParadoxPlugin::chat_event, es::EventPriority::High, true);
        listen(&ParadoxPlugin::command_event, es::EventPriority::High, true);
        listen(&ParadoxPlugin::break_event, es::EventPriority::High, true);
        listen(&ParadoxPlugin::place_event, es::EventPriority::High, true);
        listen(&ParadoxPlugin::interact_event, es::EventPriority::High, true);
        listen(&ParadoxPlugin::held_event, es::EventPriority::High, true);
        listen(&ParadoxPlugin::death_event);
        listen(&ParadoxPlugin::drop_event, es::EventPriority::High, true);
        listen(&ParadoxPlugin::pickup_event, es::EventPriority::High, true);
        listen(&ParadoxPlugin::chunk_load, es::EventPriority::Monitor);
        listen(&ParadoxPlugin::chunk_unload, es::EventPriority::Monitor, true);
        listen(&ParadoxPlugin::receive, es::EventPriority::High, true);
        listen(&ParadoxPlugin::send, es::EventPriority::Monitor, true);
        active_ = true;
        last_tick_ = last_clean_ = now();
        for (auto *player : getServer().getOnlinePlayers())
            initialize(*player);
        getServer().getScheduler().runTaskTimer(
            *this,
            [this] {
                try {
                    tick();
                } catch (const std::exception &e) {
                    getLogger().error("Paradox tick: {}", e.what());
                }
            },
            1, 1);
        getLogger().info("Paradox {} native enabled; {} modules. Upstream review: 6.9.1. Web token: web-token.txt in "
                         "plugin data folder.",
                         PARADOX_VERSION, modules_.size());
    } catch (const std::exception &e) {
        getLogger().error("Paradox startup failed: {}", e.what());
        getServer().getPluginManager().disablePlugin(*this);
    }
}
void ParadoxPlugin::onDisable() {
    active_ = false;
    getServer().getScheduler().cancelTasks(*this);
    web_.reset();
    for (auto *p : getServer().getOnlinePlayers())
        if (players_.contains(id(*p)) && players_[id(*p)].pending_forms)
            p->closeForm();
    if (db_) {
        try {
            db_->flush();
        } catch (const std::exception &e) {
            getLogger().error("Database flush failed: {}", e.what());
        }
        db_.reset();
    }
    players_.clear();
    chunks_.clear();
}
void ParadoxPlugin::module(std::string name, bool state) {
    if (!modules_.contains(name))
        throw std::invalid_argument("Unknown module");
    modules_[name]["enabled"] = state;
    db_->set("modules", name, modules_[name]);
    for (auto *p : getServer().getOnlinePlayers())
        reset(*p);
}
int ParadoxPlugin::clearance(es::Player &p) const {
    auto data = db_->get("players", id(p), Json::object());
    return data.is_object() ? std::clamp(data.value("clearance", 1), 1, 4) : 1;
}
void ParadoxPlugin::refresh_policies() {
    claims_ = db_->all("claims");
    for (const std::string table : {"allowlist", "whitelist"}) {
        auto &ids = identity_lists_[table];
        ids.clear();
        const auto rows = db_->all(table);
        for (const auto &[key, row] : rows.items()) {
            if (row == false || row.is_null())
                continue;
            ids.insert(key);
            if (row.is_object())
                for (const std::string field : {"uuid", "xuid"}) {
                    const auto value = row.value(field, "");
                    if (!value.empty())
                        ids.insert(value);
                }
        }
    }
}
bool ParadoxPlugin::allowed(es::Player &p, const std::string &table) const {
    auto found = identity_lists_.find(table);
    return found != identity_lists_.end() &&
           (found->second.contains(id(p)) || (!p.getXuid().empty() && found->second.contains(p.getXuid())));
}
void ParadoxPlugin::initialize(es::Player &p) {
    auto uid = id(p);
    auto &s = players_[uid];
    s.activity = now();
    s.transition_until = s.activity + 8;
    s.detector.reset(s.activity, 8);
    s.safe = p.getLocation();
    auto data = db_->get("players", uid, Json::object());
    if (!data.is_object())
        data = Json::object();
    data["name"] = p.getName();
    data["xuid"] = p.getXuid();
    data["last_seen"] = unix_time();
    if (!data.contains("clearance"))
        data["clearance"] = 1;
    db_->set("players", uid, data);
    s.frozen = db_->get("frozen_players", uid, false).is_object() || db_->get("frozen_players", uid, false) == true;
    s.channel = db_->get("player_data", uid, Json::object()).value("channel", "");
    s.rank = db_->get("ranks", uid, Json::object()).is_string() ? db_->get("ranks", uid).get<std::string>() : "";
    if (!s.rank.empty())
        p.setScoreTag(s.rank);
    inspect_skin(p);
    if (enabled("fingerprint") && !p.getDeviceId().empty())
        db_->set("fingerprints", uid,
                 {{"hash", sha256(fingerprint_salt_ + ":" + p.getDeviceId())},
                  {"platform", p.getDeviceOS()},
                  {"time", unix_time()}});
    for (const auto &key : {uid, p.getXuid(), normalize_name(p.getName()), p.getName()}) {
        if (key.empty())
            continue;
        auto ban = db_->get("bans", key);
        if (ban.is_object() && (ban.value("expires", 0.0) == 0 || ban.value("expires", 0.0) > unix_time())) {
            p.kick("[Paradox] Banned: " + ban.value("reason", "Server ban"));
            return;
        }
    }
    if (!p.getXuid().empty()) {
        auto ban = db_->get("global_bans", p.getXuid());
        if (ban.is_object() && ban.value("player_xuid", "") == p.getXuid() && ban.value("category", "") == "ban") {
            p.kick("[Paradox] Global ban: " + ban.value("reason", "Server network ban"));
            return;
        }
    }
    if (db_->get("config", "whitelist_enabled", false) == true && !allowed(p, "whitelist") && clearance(p) < 4)
        p.kick("[Paradox] This server requires a verified whitelist entry.");
    if (enabled("lockdown") && clearance(p) < db_->get("config", "lockdown_clearance", 4).get<int>())
        p.kick("[Paradox] Server is in lockdown.");
    if (enabled("namespoof"))
        for (auto *other : getServer().getOnlinePlayers())
            if (id(*other) != uid && normalize_name(other->getName()) == normalize_name(p.getName())) {
                db_->set("spoof_log", uid,
                         {{"name", p.getName()}, {"reason", "Duplicate online display name"}, {"time", unix_time()}});
                emit(p, {"namespoof", "Duplicate display name; authenticated identities retained",
                         Confidence::observation});
            }
}
void ParadoxPlugin::reset(es::Player &p, double seconds) {
    auto &s = players_[id(p)];
    s.detector.reset(now(), seconds);
    s.transition_until = now() + seconds;
    s.previous.reset();
    s.safe.reset();
    enforcement_.reset(id(p));
}
bool ParadoxPlugin::loaded(const es::Location &l) const {
    if (!vec(l).finite() || std::abs(l.getX()) > 30000000 || std::abs(l.getZ()) > 30000000)
        return false;
    for (double dx : {-1.0, 1.0})
        for (double dz : {-1.0, 1.0})
            if (!chunks_.contains(chunk_key(l.getDimension(), static_cast<int>(std::floor((l.getX() + dx) / 16)),
                                            static_cast<int>(std::floor((l.getZ() + dz) / 16)))))
                return false;
    return true;
}
Health ParadoxPlugin::health(es::Player &p) {
    auto &s = players_[id(p)];
    Health h;
    h.ping_ms = static_cast<double>(p.getPing().count());
    h.tps = getServer().getCurrentTicksPerSecond();
    h.tick_ms = getServer().getCurrentMillisecondsPerTick();
    h.loaded = loaded(p.getLocation());
    h.exempt = clearance(p) >= 4 || p.hasPermission("paradox.bypass") || allowed(p, "allowlist");
    h.special_movement = p.getAllowFlight() || p.isFlying() || p.isGliding() || p.isInWater() || p.isInLava() ||
                         p.isDead() || p.getGameMode() != es::GameMode::Survival;
    h.transition = now() < s.impulse_until || now() < s.effect_until;
    auto exempt = s.exemptions.find("all");
    if (exempt != s.exemptions.end() && exempt->second > now())
        h.exempt = true;
    return h;
}
void ParadoxPlugin::emit(es::Player &p, const Finding &finding, es::ICancellable *event) {
    if (!active_ || !enabled(finding.module))
        return;
    auto &state = players_[id(p)];
    const double time = now();
    if (state.exemptions.contains(finding.module) && state.exemptions[finding.module] > time)
        return;
    if (clearance(p) >= 4 || allowed(p, "allowlist") || p.hasPermission("paradox.bypass"))
        return;
    bool ready = state.detector.lag.ready(time);
    const auto action = enforcement_.record(id(p), finding, time, ready, mode_);
    if (action == Action::cancel && event)
        event->setCancelled(true);
    if (action == Action::setback) {
        if (event)
            event->setCancelled(true);
        if (state.safe && loaded(*state.safe)) {
            auto safe = *state.safe;
            reset(p);
            p.teleport(safe);
        }
    } else if (action == Action::kick)
        p.kick("[Paradox] Repeated verified " + finding.module + " violations.");
    if (state.alerts.contains(finding.module) && time - state.alerts[finding.module] < 10)
        return;
    state.alerts[finding.module] = time;
    const std::string action_name = action == Action::observe   ? "observe"
                                    : action == Action::cancel  ? "cancel"
                                    : action == Action::setback ? "setback"
                                                                : "kick";
    Json entry = {{"uuid", id(p)},
                  {"name", p.getName()},
                  {"module", finding.module},
                  {"time", unix_time()},
                  {"action", action_name},
                  {"evidence",
                   {{"desc", finding.reason},
                    {"value", finding.value},
                    {"limit", finding.limit},
                    {"ping", p.getPing().count()},
                    {"healthy", ready}}}};
    if (enabled("evidencereplay")) {
        db_->set("replays", id(p), {{"module", finding.module}, {"time", entry["time"]}, {"samples", state.replay}});
        entry["replay_key"] = id(p);
    }
    auto history = db_->get("violations", id(p), Json::array());
    if (!history.is_array())
        history = Json::array();
    history.push_back(entry);
    while (history.size() > 100)
        history.erase(history.begin());
    db_->set("violations", id(p), history);
    recent_.push_back(entry);
    while (recent_.size() > 50)
        recent_.erase(recent_.begin());
    for (auto *staff : getServer().getOnlinePlayers()) {
        auto watch = watchers_.find(id(*staff));
        if (clearance(*staff) >= 4 || staff->hasPermission("paradox.alerts") ||
            (watch != watchers_.end() && watch->second.first == id(p) && watch->second.second > time))
            staff->sendMessage("[Paradox] " + p.getName() + " / " + finding.module + ": " + finding.reason + " (" +
                               action_name + ")");
    }
    if (web_ && enabled("discord") && finding.confidence != Confidence::observation) {
        auto url = setting<std::string>("discord", "webhook_url", "");
        if (!url.empty())
            web_->post(url, {{"content", "[Paradox] " + p.getName() + " / " + finding.module + ": " + action_name},
                             {"allowed_mentions", {{"parse", Json::array()}}}});
    }
    if (web_ && !global_url_.empty() && !global_key_.empty() && finding.confidence == Confidence::corroborated && ready)
        web_->post(global_url_ + "/api/report/batch",
                   {{"reports", Json::array({{{"player_name", p.getName()},
                                              {"player_xuid", p.getXuid()},
                                              {"module", finding.module},
                                              {"severity", 3},
                                              {"evidence", entry["evidence"]}}})}},
                   global_key_);
}
void ParadoxPlugin::audit(std::string action, es::CommandSender &sender, Json data) {
    db_->set("audit", std::to_string(unix_time()) + ":" + random_token().substr(0, 8),
             {{"actor", sender.getName()}, {"action", action}, {"data", data}, {"time", unix_time()}});
}

void ParadoxPlugin::tick() {
    if (!active_)
        return;
    const double time = now(), gap = time - last_tick_;
    last_tick_ = time;
    ++ticks_;
    for (auto *p : getServer().getOnlinePlayers()) {
        auto &s = players_[id(*p)];
        if (gap > 0.15)
            reset(*p);
        const auto epoch = s.detector.lag.epoch();
        s.detector.lag.update(time, health(*p));
        if (s.detector.lag.epoch() != epoch)
            enforcement_.reset(id(*p));
        if (ticks_ % 5 == 0 && enabled("evidencereplay")) {
            auto sample = location_json(p->getLocation());
            sample["time"] = unix_time();
            sample["ping"] = p->getPing().count();
            sample["healthy"] = s.detector.lag.ready(time);
            s.replay.push_back(sample);
            while (s.replay.size() > 80)
                s.replay.erase(s.replay.begin());
        }
        if (s.inventory_dirty) {
            s.inventory_dirty = false;
            inspect_inventory(*p);
        }
        if (ticks_ % 20 != 0)
            continue;
        inspect_inventory(*p);
        if (enabled("containersee"))
            container_vision(*p);
        if (enabled("adaptivecheck"))
            db_->set("baselines", id(*p),
                     {{"ping", p->getPing().count()},
                      {"jitter", s.detector.lag.jitter()},
                      {"tps", getServer().getAverageTicksPerSecond()},
                      {"enforcement_ready", s.detector.lag.ready(time)},
                      {"time", unix_time()}});
        if (s.knockback_origin && time - s.knockback_time >= 0.3) {
            if (time - s.knockback_time < 1 && vec(p->getLocation()).distance(*s.knockback_origin) < 0.05 &&
                p->getPing().count() > 0 && p->getPing().count() < 150 && getServer().getCurrentTicksPerSecond() >= 19)
                emit(*p, {"antikb", "Small response to server knockback; collision/resistance may explain this",
                          Confidence::observation});
            s.knockback_origin.reset();
        }
        if (p->isOnGround() && loaded(p->getLocation()) && s.detector.lag.ready(time))
            s.safe = p->getLocation();
        if (enabled("afk") &&
            time - s.activity >
                db_->get("config", "afk_timeout", setting<double>("afk", "timeout", 600)).get<double>()) {
            p->sendTip("[Paradox] You are AFK");
            if (setting<bool>("afk", "kick", false) && s.detector.lag.ready(time) && clearance(*p) < 4)
                p->kick("[Paradox] AFK timeout");
        }
        if (enabled("chunkborders") && s.chunk_borders) {
            auto l = p->getLocation();
            const int x = static_cast<int>(std::floor(l.getX() / 16)) * 16,
                      z = static_cast<int>(std::floor(l.getZ() / 16)) * 16;
            for (int a = 0; a <= 16; a += 4) {
                p->spawnParticle("minecraft:basic_flame_particle", static_cast<float>(x + a), l.getY() + 0.2F,
                                 static_cast<float>(z));
                p->spawnParticle("minecraft:basic_flame_particle", static_cast<float>(x), l.getY() + 0.2F,
                                 static_cast<float>(z + a));
            }
        }
    }
    if (ticks_ % 20 == 0 && web_) {
        Json online = Json::array();
        for (auto *p : getServer().getOnlinePlayers()) {
            auto &s = players_[id(*p)];
            online.push_back({{"name", p->getName()},
                              {"uuid", id(*p)},
                              {"ping", p->getPing().count()},
                              {"ready", s.detector.lag.ready(time)},
                              {"reason", s.detector.lag.reason()}});
        }
        web_->publish({{"version", PARADOX_VERSION},
                       {"tps", getServer().getAverageTicksPerSecond()},
                       {"players", online},
                       {"modules", modules_},
                       {"evidence", recent_},
                       {"mode", mode_},
                       {"protocol_supported", protocol_ok_}});
        for (auto &line : web_->commands()) {
            std::istringstream in(line);
            std::string name, rest;
            in >> name;
            std::getline(in, rest);
            try {
                command(getServer().getCommandSender(), name, split({rest}));
            } catch (const std::exception &e) {
                getLogger().warning("Web command failed: {}", e.what());
            }
        }
        for (auto &[tag, response] : web_->responses()) {
            if (tag == "register" && response.is_object() && response.value("api_key", "").size() >= 16) {
                global_key_ = response["api_key"].get<std::string>();
                db_->set("config", "global_api_key", global_key_);
                global_next_ = 0;
            } else if (tag == "sync" && response.is_object()) {
                for (const auto &ban : response.value("bans", Json::array()))
                    if (ban.is_object()) {
                        auto xuid = ban.value("player_xuid", "");
                        if (xuid.size() >= 12 && xuid.size() <= 20 &&
                            std::all_of(xuid.begin(), xuid.end(), [](unsigned char c) { return std::isdigit(c); })) {
                            if (ban.value("removed", false) || ban.value("revoked", false))
                                db_->erase("global_bans", xuid);
                            else
                                db_->set(ban.value("category", "") == "ban" ? "global_bans" : "global_flags", xuid,
                                         ban);
                        } else if (!ban.value("player_name", "").empty())
                            db_->set("global_flags", normalize_name(ban["player_name"].get<std::string>()), ban);
                    }
                global_since_ = response.value("server_time", global_since_);
                db_->set("config", "global_last_sync", global_since_);
            }
        }
        if (!global_url_.empty() && time >= global_next_) {
            global_next_ = time + std::max(60.0, setting<double>("global_database", "sync_interval", 300));
            if (global_key_.empty())
                web_->request(
                    "register", global_url_ + "/api/servers/self-register", "",
                    {{"name", setting<std::string>("global_database", "server_name", getServer().getName())}});
            else
                web_->request("sync", global_url_ + "/api/sync?since=" + std::to_string(global_since_), global_key_);
        }
    }
    if (ticks_ % 1200 == 0) {
        std::erase_if(watchers_, [&](auto &i) { return i.second.second < time; });
        std::erase_if(tpa_, [&](auto &i) { return i.second.second < time; });
        if (!db_->error().empty())
            getLogger().error("Paradox persistence is unavailable: {}", db_->error());
    }
    if (ticks_ % 20 == 0 && enabled("lagclear") && setting<bool>("lagclear", "enabled_removal", true)) {
        double interval =
            db_->get("config", "lagclear_interval", setting<double>("lagclear", "interval", 300)).get<double>();
        interval = std::max(60.0, interval);
        if (time - last_clean_ >= interval - 30 && !clean_warning_) {
            getServer().broadcastMessage(
                "[Paradox] Unnamed dropped items, arrows and XP orbs will be cleared in 30 seconds.");
            clean_warning_ = true;
        }
        if (time - last_clean_ >= interval) {
            auto count = clear_entities();
            getServer().broadcastMessage("[Paradox] Cleared " + std::to_string(count) + " dropped entities.");
            last_clean_ = time;
            clean_warning_ = false;
        }
    }
}
unsigned ParadoxPlugin::clear_entities(std::string_view type, const es::Location *center, double radius) {
    auto *level = getServer().getLevel();
    if (!level)
        return 0;
    unsigned count = 0;
    for (auto *actor : level->getActors()) {
        const auto actor_type = actor->getType();
        if (actor_type != "minecraft:item" && actor_type != "minecraft:arrow" && actor_type != "minecraft:xp_orb")
            continue;
        if (!type.empty() && actor_type != type && actor_type != "minecraft:" + std::string(type))
            continue;
        if (!actor->getNameTag().empty() || dynamic_cast<es::Player *>(actor))
            continue;
        if (auto *item = actor->asItem(); item && (item->isUnlimitedLifetime() || item->getPickupDelay() > 0))
            continue;
        if (center && (actor->getDimension().getName() != center->getDimension().getName() ||
                       vec(actor->getLocation()).distance(vec(*center)) > radius))
            continue;
        actor->remove();
        ++count;
    }
    return count;
}
void ParadoxPlugin::inspect_skin(es::Player &p) {
    if (!enabled("skinguard"))
        return;
    const auto skin = p.getSkin();
    const auto &image = skin.getImage();
    // Marketplace/persona geometry and transparency are legitimate. Only report an
    // inconsistent server-decoded image; raw login validation remains BDS's job.
    const auto w = image.getWidth(), h = image.getHeight(), depth = image.getDepth();
    if (w <= 0 || h <= 0 || depth < 1 || depth > 4 ||
        static_cast<std::uint64_t>(w) * h * depth != image.getData().size())
        emit(p, {"skinguard", "Skin image dimensions do not match decoded pixel data", Confidence::observation});
}
Json ParadoxPlugin::inventory(es::Player &p) const {
    Json result = Json::array();
    int slot = 0;
    for (auto &item : p.getInventory().getContents()) {
        if (item) {
            auto meta = item->getItemMeta();
            Json enchants = Json::object();
            for (auto &[enchantment, level] : meta->getEnchants())
                enchants[std::format("{}", enchantment->getId())] = level;
            result.push_back({{"slot", slot},
                              {"type", std::format("{}", item->getType().getId())},
                              {"amount", item->getAmount()},
                              {"name", meta->getDisplayName()},
                              {"lore", meta->getLore()},
                              {"enchants", enchants}});
            if (enabled("invsync") || enabled("antidupe"))
                result.back()["nbt_hash"] = sha256(std::format("{}", es::nbt::Tag(item->getNbt())));
        }
        ++slot;
    }
    return result;
}
void ParadoxPlugin::inspect_inventory(es::Player &p) {
    auto &s = players_[id(p)];
    const auto contents = inventory(p);
    if (contents == s.inventory)
        return;
    if (enabled("invsync") || enabled("antidupe") || enabled("evidencereplay")) {
        db_->set("inventory_snapshots", id(p), {{"items", contents}, {"time", unix_time()}});
        if (enabled("invsync") || enabled("antidupe")) {
            auto delta = Json::diff(s.inventory, contents);
            db_->set("inventory_deltas", id(p),
                     {{"changes", delta}, {"time", unix_time()}, {"healthy", s.detector.lag.ready(now())}});
        }
    }
    if (s.detector.lag.ready(now()) && !s.inventory.empty()) {
        if (enabled("inventorymovement") && s.speed > 0.5 && now() - s.inventory_time < 0.2)
            emit(p, {"inventorymovement",
                     "Inventory changed during movement; knockback, touch input or pickup may explain it",
                     Confidence::observation});
        if (enabled("autototem") && now() - s.last_inventory < 0.15) {
            auto totems = [](const Json &items) {
                int count = 0;
                for (const auto &item : items)
                    if (item.value("type", "") == "minecraft:totem_of_undying")
                        count += item.value("amount", 0);
                return count;
            };
            if (totems(contents) > totems(s.inventory))
                emit(p, {"autototem", "Rapid totem inventory change; pickup or an inventory tool may explain it",
                         Confidence::observation});
        }
    }
    if (enabled("illegalitems"))
        for (auto &item : p.getInventory().getContents())
            if (item && (item->getAmount() < 0 || item->getAmount() > item->getMaxStackSize()))
                emit(p,
                     {"illegalitems", "Server inventory stack exceeds normal item limit; custom plugins may explain it",
                      Confidence::observation, static_cast<double>(item->getAmount()),
                      static_cast<double>(item->getMaxStackSize())});
    s.inventory = contents;
    s.last_inventory = now();
}
bool ParadoxPlugin::teleport(es::Player &p, const Json &data) {
    if (!data.is_object())
        return false;
    auto *level = getServer().getLevel();
    if (!level)
        return false;
    auto *d = level->getDimension(data.value("dimension", "overworld"));
    if (!d)
        return false;
    es::Location to(*d, data.at("x").get<double>(), data.at("y").get<double>(), data.at("z").get<double>(),
                    data.value("pitch", 0.0F), data.value("yaw", 0.0F));
    if (!vec(to).finite() || std::abs(to.getX()) > 30000000 || std::abs(to.getZ()) > 30000000)
        return false;
    reset(p, 10);
    return p.teleport(to);
}
Json ParadoxPlugin::container_lock(es::Block &b) const {
    return db_->get("container_locks", block_key(b), db_->get("chestLockDB", legacy_block_key(b)));
}
void ParadoxPlugin::erase_container_lock(es::Block &b) {
    db_->erase("container_locks", block_key(b));
    db_->erase("chestLockDB", legacy_block_key(b));
}
bool ParadoxPlugin::line_clear(const es::Location &from, const es::Location &to) const {
    if (from.getDimension().getName() != to.getDimension().getName())
        return true;
    const double distance = vec(from).distance(vec(to));
    if (!std::isfinite(distance) || distance > 16)
        return true;
    for (double t = .5; t < distance - .5; t += .5) {
        auto point = from;
        point.setX(from.getX() + (to.getX() - from.getX()) * t / distance);
        point.setY(from.getY() + (to.getY() - from.getY()) * t / distance);
        point.setZ(from.getZ() + (to.getZ() - from.getZ()) * t / distance);
        if (!loaded(point))
            return true;
        auto block = point.getDimension().getBlockAt(point.getBlockX(), point.getBlockY(), point.getBlockZ());
        if (!block)
            return true;
        const auto type = block->getType();
        if (type == "minecraft:stone" || type == "minecraft:bedrock" || type == "minecraft:obsidian")
            return false;
    }
    return true;
}
void ParadoxPlugin::container_vision(es::Player &p) {
    if (clearance(p) < 4 && !p.hasPermission("paradox.invsee"))
        return;
    const auto origin = eye(p);
    const double yaw = origin.getYaw() * std::numbers::pi / 180, pitch = origin.getPitch() * std::numbers::pi / 180;
    const Vec3 direction{-std::sin(yaw) * std::cos(pitch), -std::sin(pitch), std::cos(yaw) * std::cos(pitch)};
    for (auto *other : getServer().getOnlinePlayers()) {
        if (other == &p || other->getDimension().getName() != p.getDimension().getName())
            continue;
        auto l = other->getLocation();
        const Vec3 delta{l.getX() - origin.getX(), l.getY() + 1 - origin.getY(), l.getZ() - origin.getZ()};
        double d = delta.distance({});
        if (d < .1 || d > 10 || (delta.x * direction.x + delta.y * direction.y + delta.z * direction.z) / d < .985 ||
            !line_clear(origin, l))
            continue;
        const auto items = inventory(*other);
        std::string text = other->getName() + ": ";
        const auto page = (ticks_ / 60) % std::max<std::size_t>(1, (items.size() + 5) / 6);
        for (std::size_t i = page * 6; i < std::min(items.size(), page * 6 + 6); ++i)
            text += items[i].value("type", "") + " x" + std::to_string(items[i].value("amount", 0)) + " ";
        p.sendTip(text);
        return;
    }
    for (double distance = .5; distance <= 10; distance += .5) {
        auto l = origin;
        l.setX(l.getX() + direction.x * distance);
        l.setY(l.getY() + direction.y * distance);
        l.setZ(l.getZ() + direction.z * distance);
        if (!loaded(l))
            return;
        auto b = l.getDimension().getBlockAt(l.getBlockX(), l.getBlockY(), l.getBlockZ());
        if (!b)
            return;
        if (air(b->getType()))
            continue;
        if (container(b->getType()))
            p.sendTip(b->getType() + " at " + block_key(*b));
        return;
    }
}
bool ParadoxPlugin::protected_environment(es::Block &b) {
    if (enabled("containerlock") && container_lock(b).is_object())
        return true;
    if (enabled("landclaim"))
        for (auto &[key, c] : claims_.items())
            if (c.value("dimension", "") == b.getDimension().getName() &&
                std::abs(b.getX() - c.value("x", 0)) <= c.value("radius", 16) &&
                std::abs(b.getZ() - c.value("z", 0)) <= c.value("radius", 16))
                return true;
    return false;
}
void ParadoxPlugin::piston(es::BlockPistonEvent &e) {
    if (!enabled("containerlock") && !enabled("landclaim"))
        return;
    // Endstone exposes piston direction but not the slime/honey moved-block list.
    // A bounded conservative envelope protects the 12-block push chain and attached blocks.
    for (int distance = 0; distance <= 13; ++distance) {
        auto centre = e.getBlock().getRelative(e.getDirection(), distance);
        if (!centre)
            continue;
        for (int x = -1; x <= 1; ++x)
            for (int y = -1; y <= 1; ++y)
                for (int z = -1; z <= 1; ++z) {
                    auto b = centre->getRelative(x, y, z);
                    if (b && loaded(b->getLocation()) && protected_environment(*b)) {
                        e.setCancelled(true);
                        return;
                    }
                }
    }
}
bool ParadoxPlugin::protected_block(es::Player &p, es::Block &b) {
    if (clearance(p) >= 4 || p.hasPermission("paradox.bypass"))
        return false;
    if (enabled("containerlock")) {
        // Also retain the Python port's chestLockDB keys during migration.
        auto lock = container_lock(b);
        if (lock.is_object() && lock.value("owner", "") != id(p))
            return true;
        // A locked half of a double chest protects its neighbour too.
        if (b.getType().find("chest") != std::string::npos)
            for (auto [dx, dz] : {std::pair{1, 0}, {-1, 0}, {0, 1}, {0, -1}}) {
                auto other = b.getDimension().getBlockAt(b.getX() + dx, b.getY(), b.getZ() + dz);
                if (!other || other->getType() != b.getType())
                    continue;
                auto l = container_lock(*other);
                if (l.is_object() && l.value("owner", "") != id(p))
                    return true;
            }
    }
    if (enabled("landclaim"))
        for (auto &[key, claim] : claims_.items()) {
            if (claim.value("dimension", "") != b.getDimension().getName() || claim.value("owner", "") == id(p))
                continue;
            auto trusted = claim.value("trusted", Json::array());
            if (std::find(trusted.begin(), trusted.end(), Json(id(p))) != trusted.end())
                continue;
            if (std::abs(b.getX() - claim.value("x", 0)) <= claim.value("radius", 16) &&
                std::abs(b.getZ() - claim.value("z", 0)) <= claim.value("radius", 16))
                return true;
        }
    return false;
}
void ParadoxPlugin::join_event(es::PlayerJoinEvent &e) {
    if (active_)
        initialize(e.getPlayer());
}
void ParadoxPlugin::quit_event(es::PlayerQuitEvent &e) {
    auto uid = id(e.getPlayer());
    players_.erase(uid);
    watchers_.erase(uid);
    tpa_.erase(uid);
    enforcement_.reset(uid);
}
void ParadoxPlugin::move_event(es::PlayerMoveEvent &e) {
    auto &p = e.getPlayer();
    auto &s = players_[id(p)];
    const auto to = e.getTo();
    const double time = now();
    if (s.frozen) {
        e.setCancelled(true);
        return;
    }
    if (vec(to).distance(vec(e.getFrom())) > 0.01)
        s.activity = time;
    if (enabled("worldborder") && clearance(p) < 4) {
        auto border = db_->get("config", "worldborder", Json::object());
        double radius = border.value("radius", setting<double>("worldborder", "radius", 0));
        double x = border.value("center_x", border.value("x", setting<double>("worldborder", "x", 0))),
               z = border.value("center_z", border.value("z", setting<double>("worldborder", "z", 0)));
        double distance = std::hypot(to.getX() - x, to.getZ() - z),
               previous_distance = std::hypot(e.getFrom().getX() - x, e.getFrom().getZ() - z);
        // An admin teleport outside the border must not trap a player; allow movement inward.
        if (border.value("enabled", true) && radius > 0 && distance > radius && distance > previous_distance) {
            e.setCancelled(true);
            p.sendTip("[Paradox] World border");
            reset(p);
            return;
        }
    }
    auto h = health(p);
    h.loaded = h.loaded && loaded(to) && loaded(e.getFrom());
    Movement m{time, vec(to), to.getYaw(), to.getPitch(), p.isOnGround(), p.isInWater()};
    if (h.loaded) {
        auto below = to.getDimension().getBlockAt(to.getBlockX(), to.getBlockY() - 1, to.getBlockZ());
        auto feet = to.getDimension().getBlockAt(to.getBlockX(), to.getBlockY(), to.getBlockZ());
        if (below) {
            m.passable_below = air(below->getType());
            m.liquid_below = below->getType().find("water") != std::string::npos;
        }
        if (feet) {
            auto type = feet->getType();
            m.solid_inside = type == "minecraft:stone" || type == "minecraft:bedrock";
            if (type.find("ladder") != std::string::npos || type.find("vine") != std::string::npos ||
                type.find("scaffolding") != std::string::npos || type.find("web") != std::string::npos)
                h.special_movement = true;
        }
    }
    s.speed = vec(to).distance(vec(e.getFrom())) * 20;
    for (auto &f : s.detector.move(m, h))
        emit(p, f, &e);
}
void ParadoxPlugin::teleport_event(es::PlayerTeleportEvent &e) {
    auto &p = e.getPlayer();
    if (enabled("dimensionlock") && clearance(p) < 4 &&
        e.getFrom().getDimension().getName() != e.getTo().getDimension().getName()) {
        e.setCancelled(true);
        p.sendMessage("[Paradox] Dimension travel is locked.");
    }
    reset(p, 10);
}
void ParadoxPlugin::respawn_event(es::PlayerRespawnEvent &e) {
    reset(e.getPlayer(), 10);
}
void ParadoxPlugin::dimension_event(es::PlayerDimensionChangeEvent &e) {
    reset(e.getPlayer(), 10);
}
void ParadoxPlugin::gamemode_event(es::PlayerGameModeChangeEvent &e) {
    auto &p = e.getPlayer();
    reset(p);
    // Server-authorised gamemode changes are legitimate unless an explicit policy is configured.
    static const std::array<std::string_view, 4> modes = {"survival", "creative", "adventure", "spectator"};
    int mode = static_cast<int>(e.getNewGameMode());
    bool permitted = mode >= 0 && mode < 4 && setting<bool>("gamemodepolicy", modes[mode], true);
    if (auto legacy_mode = config_["gamemodepolicy"]["mode"].value<int>())
        permitted = mode == *legacy_mode;
    if (enabled("gamemodepolicy") && clearance(p) < 4 && !permitted) {
        e.setCancelled(true);
        p.sendMessage("[Paradox] That game mode is disabled by server policy.");
    }
}
void ParadoxPlugin::damage_event(es::ActorDamageEvent &e) {
    auto *victim = dynamic_cast<es::Player *>(&e.getActor());
    auto *attacker = dynamic_cast<es::Player *>(e.getDamageSource().getDamagingActor());
    const bool target_ready =
        !victim || (players_[id(*victim)].transition_until <= now() && players_[id(*victim)].detector.lag.ready(now()));
    if (victim) {
        auto &s = players_[id(*victim)];
        s.impulse_until = now() + 4;
        reset(*victim, 4);
    }
    auto *source_player = dynamic_cast<es::Player *>(e.getDamageSource().getActor());
    if (!attacker)
        attacker = source_player;
    if (!attacker)
        return;
    auto &s = players_[id(*attacker)];
    s.activity = now();
    if (victim && enabled("pvp")) {
        auto disabled = [&](es::Player &p) {
            auto data = db_->get("pvp_data", id(p), true);
            return data == false || (data.is_object() && !data.value("enabled", true));
        };
        if (db_->get("config", "global_pvp", true) == false || disabled(*victim) || disabled(*attacker)) {
            e.setCancelled(true);
            return;
        }
        s.combat_until = now() + 15;
        players_[id(*victim)].combat_until = now() + 15;
    }
    if (e.getDamageSource().isIndirect() || e.getDamageSource().getType() != "entity_attack")
        return;
    auto location = e.getActor().getLocation();
    auto h = health(*attacker);
    Combat c;
    c.time = now();
    c.distance = vec(attacker->getLocation()).distance(vec(location));
    c.target_ping = victim ? victim->getPing().count() : 0;
    c.target_speed = victim ? players_[id(*victim)].speed : 0;
    // Damage resets the victim's movement state, so assess their transport directly here.
    c.target_healthy = target_ready && loaded(location) &&
                       (!victim || (victim->getPing().count() > 0 && victim->getPing().count() <= 250));
    c.unobstructed = line_clear(eye(*attacker), location);
    // Non-player hitboxes and extended/custom weapons have no reliable reach
    // envelope through this API. Never apply ordinary player-melee limits to them.
    auto held = attacker->getInventory().getItemInMainHand();
    const auto held_type = held ? std::string(held->getType().getId()) : "minecraft:air";
    static const std::set<std::string> ordinary_melee = {
        "minecraft:air",          "minecraft:wooden_sword",  "minecraft:stone_sword",     "minecraft:iron_sword",
        "minecraft:golden_sword", "minecraft:diamond_sword", "minecraft:netherite_sword", "minecraft:wooden_axe",
        "minecraft:stone_axe",    "minecraft:iron_axe",      "minecraft:golden_axe",      "minecraft:diamond_axe",
        "minecraft:netherite_axe"};
    c.standard_melee = victim && ordinary_melee.contains(held_type);
    c.self_hit = victim == attacker;
    c.falling = attacker->getVelocity().getY() < 0;
    c.same_target = s.last_target == std::to_string(e.getActor().getRuntimeId());
    auto a = attacker->getLocation();
    double target_yaw = std::atan2(-(location.getX() - a.getX()), location.getZ() - a.getZ()) * 180 / std::numbers::pi;
    c.yaw_error = angle_delta(a.getYaw(), target_yaw);
    for (auto &f : s.detector.attack(c, h))
        emit(*attacker, f, &e);
    if (enabled("criticals") && !attacker->isOnGround() && std::abs(attacker->getVelocity().getY()) < 0.001 &&
        s.detector.lag.ready(now()))
        emit(*attacker, {"criticals", "Airborne attack with little vertical motion; apex/effects may explain this",
                         Confidence::observation});
    s.attack_time = now();
    s.last_target = std::to_string(e.getActor().getRuntimeId());
}
void ParadoxPlugin::knockback_event(es::ActorKnockbackEvent &e) {
    if (auto *p = dynamic_cast<es::Player *>(&e.getActor())) {
        auto &s = players_[id(*p)];
        s.knockback_origin = vec(p->getLocation());
        s.knockback_time = now();
        s.impulse_until = now() + 5;
        reset(*p, 5);
    }
}
void ParadoxPlugin::chat_event(es::PlayerChatEvent &e) {
    auto &p = e.getPlayer();
    auto &s = players_[id(p)];
    const double time = now();
    s.activity = time;
    auto legacy_mutes = db_->get("config", "muted_players", Json::object());
    auto mute = db_->get("mutes", id(p), legacy_mutes.is_object() ? legacy_mutes.value(id(p), Json()) : Json());
    if (mute.is_number() && (mute.get<double>() == 0 || mute.get<double>() > unix_time())) {
        e.setCancelled(true);
        p.sendMessage("[Paradox] You are muted.");
        return;
    }
    if (enabled("chatprotection") && clearance(p) < 4) {
        s.chat_times.push_back(time);
        while (!s.chat_times.empty() && time - s.chat_times.front() > 1)
            s.chat_times.pop_front();
        bool duplicate = e.getMessage() == s.last_message && time - s.last_chat < 3;
        if ((s.chat_times.size() > 5 || duplicate) && s.detector.lag.ready(time)) {
            e.setCancelled(true);
            p.sendMessage("[Paradox] Please slow down in chat.");
        }
        if (e.getMessage().size() > 1024) {
            e.setCancelled(true);
            return;
        }
    }
    s.last_chat = time;
    s.last_message = e.getMessage();
    if (!s.channel.empty() && !e.isCancelled()) {
        e.setCancelled(true);
        for (auto *recipient : getServer().getOnlinePlayers())
            if (players_[id(*recipient)].channel == s.channel)
                recipient->sendMessage("[" + s.channel + "] " + p.getName() + ": " + e.getMessage());
    }
}
void ParadoxPlugin::command_event(es::PlayerCommandEvent &e) {
    auto &p = e.getPlayer();
    auto &s = players_[id(p)];
    auto time = now();
    s.activity = time;
    s.command_times.push_back(time);
    while (!s.command_times.empty() && time - s.command_times.front() > 1)
        s.command_times.pop_front();
    s.last_command = time;
    if (enabled("chatprotection") && s.command_times.size() > 10 && s.detector.lag.ready(time) && clearance(p) < 4)
        e.setCancelled(true);
}
void ParadoxPlugin::break_event(es::BlockBreakEvent &e) {
    auto &p = e.getPlayer();
    if (protected_block(p, e.getBlock())) {
        e.setCancelled(true);
        p.sendMessage("[Paradox] This area/container is protected.");
        return;
    }
    auto type = e.getBlock().getType();
    for (auto &f :
         players_[id(p)].detector.block(now(), false, type.find("ore") != std::string::npos, false, health(p)))
        emit(p, f, &e);
    if (enabled("botdetection") && db_->get("honeypots", block_key(e.getBlock())).is_object())
        emit(p, {"botdetection", "Configured honeypot interacted with; review required", Confidence::observation});
    if (!e.isCancelled())
        erase_container_lock(e.getBlock());
}
void ParadoxPlugin::place_event(es::BlockPlaceEvent &e) {
    auto &p = e.getPlayer();
    if (protected_block(p, e.getBlock())) {
        e.setCancelled(true);
        return;
    }
    auto h = health(p);
    bool unsupported = h.loaded && loaded(e.getBlock().getLocation());
    if (unsupported)
        for (auto delta : {std::array{1, 0, 0}, std::array{-1, 0, 0}, std::array{0, 1, 0}, std::array{0, -1, 0},
                           std::array{0, 0, 1}, std::array{0, 0, -1}}) {
            auto b = e.getBlock().getRelative(delta[0], delta[1], delta[2]);
            if (!b || !air(b->getType())) {
                unsupported = false;
                break;
            }
        }
    for (auto &f : players_[id(p)].detector.block(now(), true, false, unsupported, h))
        emit(p, f, &e);
}
void ParadoxPlugin::interact_event(es::PlayerInteractEvent &e) {
    auto &p = e.getPlayer();
    players_[id(p)].activity = now();
    if (e.getItem() && e.getItem()->getItemMeta()->getDisplayName() == "Paradox Menu" &&
        (e.getAction() == es::PlayerInteractEvent::Action::RightClickAir ||
         e.getAction() == es::PlayerInteractEvent::Action::RightClickBlock)) {
        e.setCancelled(true);
        show_gui(p);
        return;
    }
    auto *block = e.getBlock();
    if (!block)
        return;
    if (protected_block(p, *block)) {
        e.setCancelled(true);
        p.sendMessage("[Paradox] This container is locked.");
        return;
    }
    if (enabled("containerlock") && container(block->getType()) && p.isSneaking() && e.getItem() &&
        std::string(e.getItem()->getType().getId()) == "minecraft:stick") {
        const auto key = block_key(*block);
        auto old = container_lock(*block);
        if (old.is_object()) {
            erase_container_lock(*block);
            p.sendMessage("[Paradox] Container unlocked.");
        } else {
            db_->set("container_locks", key, {{"owner", id(p)}, {"name", p.getName()}});
            p.sendMessage("[Paradox] Container locked.");
        }
        e.setCancelled(true);
    }
}
void ParadoxPlugin::held_event(es::PlayerItemHeldEvent &e) {
    if (e.getNewSlot() < 0 || e.getNewSlot() > 8)
        emit(e.getPlayer(),
             {"hotbarcheck", "Invalid hotbar slot", Confidence::invalid, static_cast<double>(e.getNewSlot()), 8}, &e);
}
void ParadoxPlugin::death_event(es::PlayerDeathEvent &e) {
    auto &p = e.getPlayer();
    auto l = p.getLocation();
    db_->set("death_coordinates", id(p), location_json(l));
    if (enabled("deathcoords"))
        p.sendMessage(std::format("[Paradox] Death: {:.2f}, {:.2f}, {:.2f} ({})", l.getX(), l.getY(), l.getZ(),
                                  l.getDimension().getName()));
    if (enabled("gravesaver"))
        preserve_grave(p);
    reset(p, 10);
}
void ParadoxPlugin::preserve_grave(es::Player &p) {
    const auto l = p.getLocation();
    const auto uid = id(p), name = p.getName();
    const auto actor_id = p.getId();
    // Keep the original dropped ItemStacks in the world: no NBT reconstruction,
    // replacing terrain, copying inventory or deleting drops before a chest write.
    getServer().getScheduler().runTaskLater(
        *this,
        [this, l, uid, name, actor_id] {
            if (!active_ || !enabled("gravesaver") || !loaded(l))
                return;
            unsigned count = 0;
            for (auto *actor : l.getDimension().getActors())
                if (auto *item = actor->asItem();
                    item && item->getThrower() == actor_id && vec(item->getLocation()).distance(vec(l)) <= 4) {
                    if (!item->addScoreboardTag("paradox_grave:" + uid))
                        continue;
                    item->setUnlimitedLifetime(true);
                    item->setNameTag("Grave: " + name);
                    ++count;
                }
            if (count)
                db_->set("graves", uid, {{"location", location_json(l)}, {"items", count}, {"time", unix_time()}});
        },
        1);
}
void ParadoxPlugin::drop_event(es::PlayerDropItemEvent &e) {
    if (e.getItem().getAmount() < 0)
        emit(e.getPlayer(), {"crashdrop", "Negative item amount", Confidence::invalid}, &e);
    players_[id(e.getPlayer())].inventory_time = now();
    players_[id(e.getPlayer())].inventory_dirty = true;
}
void ParadoxPlugin::pickup_event(es::PlayerPickupItemEvent &e) {
    auto &p = e.getPlayer();
    auto &item = e.getItem();
    for (const auto &tag : item.getScoreboardTags())
        if (tag.starts_with("paradox_grave:") && tag.substr(14) != id(p) && clearance(p) < 4) {
            e.setCancelled(true);
            return;
        }
    players_[id(p)].inventory_time = now();
    players_[id(p)].inventory_dirty = true;
}
void ParadoxPlugin::chunk_load(es::ChunkLoadEvent &e) {
    auto &c = e.getChunk();
    chunks_.insert(chunk_key(c.getDimension(), c.getX(), c.getZ()));
}
void ParadoxPlugin::chunk_unload(es::ChunkUnloadEvent &e) {
    auto &c = e.getChunk();
    chunks_.erase(chunk_key(c.getDimension(), c.getX(), c.getZ()));
}
void ParadoxPlugin::receive(es::PacketReceiveEvent &e) {
    if (!active_ || !protocol_ok_ || !getServer().isPrimaryThread())
        return;
    auto *p = e.getPlayer();
    if (!p)
        return;
    auto &s = players_[id(*p)];
    const double time = now();
    auto packet = inspect_packet(e.getPacketId(), e.getPayload());
    if (!packet.reason.empty() && !packet.decoded && !packet.malformed) {
        s.detector.reset(time);
        enforcement_.reset(id(*p));
        return;
    }
    if (packet.malformed)
        emit(*p, {e.getPacketId() == 48 ? "hotbarcheck" : "anticrash", packet.reason, Confidence::invalid}, &e);
    if (packet.malformed) {
        s.detector.reset(time);
        enforcement_.reset(id(*p));
        return;
    }
    if (packet.transition)
        reset(*p, 5);
    if (packet.input)
        for (auto &f : s.detector.input(time, packet.tick, packet.movement, health(*p)))
            emit(*p, f, &e);
    if (packet.inventory) {
        s.inventory_time = time;
        s.inventory_dirty = true;
    }
    ++s.packets;
    if (time - s.last_packet_window >= 5) {
        if (s.packets > 5000 && s.detector.lag.ready(time)) {
            emit(*p, {"packetmonitor", "High network traffic review", Confidence::observation,
                      static_cast<double>(s.packets), 5000});
            emit(*p, {"ratelimit", "Traffic burst review; BDS transport limits remain authoritative",
                      Confidence::observation, static_cast<double>(s.packets), 5000});
        }
        s.packets = 0;
        s.last_packet_window = time;
    }
}
void ParadoxPlugin::send(es::PacketSendEvent &e) {
    if (!active_ || !protocol_ok_ || !getServer().isPrimaryThread())
        return;
    auto *p = e.getPlayer();
    if (!p)
        return;
    if (e.getPacketId() != 28 && e.getPacketId() != 19 && e.getPacketId() != 40)
        return;
    auto packet = inspect_packet(e.getPacketId(), e.getPayload(), true);
    if (packet.decoded && packet.actor == p->getRuntimeId()) {
        if (packet.transition)
            reset(*p, 5);
        if (packet.effect >= 0) {
            auto &s = players_[id(*p)];
            s.effect_until = std::max(s.effect_until, now() + std::max(5.0, packet.effect_duration / 20.0 + 3));
            reset(*p, 5);
        }
    }
}

// Commands and form callbacks are implemented below; all run on the server thread.
bool ParadoxPlugin::onCommand(es::CommandSender &sender, const es::Command &cmd, const std::vector<std::string> &args) {
    if (!active_) {
        sender.sendErrorMessage("Paradox is unavailable; check the server log.");
        return true;
    }
    try {
        return command(sender, cmd.getName(), split(args));
    } catch (const std::exception &e) {
        sender.sendErrorMessage(e.what());
        return true;
    }
}
void ParadoxPlugin::send_form(es::Player &p, es::ActionForm form) {
    auto done = [this](es::Player *player) {
        if (!player)
            return;
        auto found = players_.find(id(*player));
        if (found != players_.end() && found->second.pending_forms > 0)
            --found->second.pending_forms;
    };
    form.setOnClose(done).setOnSubmit([done](es::Player *player, int) { done(player); });
    ++players_[id(p)].pending_forms;
    p.sendForm(std::move(form));
}
void ParadoxPlugin::show_gui(es::Player &p) {
    es::ActionForm form;
    form.setTitle("Paradox").setContent("Protection, evidence and server controls");
    form.addButton("Module settings", std::nullopt, [this](es::Player *player) {
        if (!active_ || !player || (clearance(*player) < 4 && !player->hasPermission("paradox.settings")))
            return;
        es::ActionForm list;
        list.setTitle("Modules");
        for (auto &[name, data] : modules_.items())
            list.addButton(name + ": " + (data.value("enabled", false) ? "on" : "off"), std::nullopt,
                           [this, name](es::Player *p) {
                               if (active_ && p && (clearance(*p) >= 4 || p->hasPermission("paradox.settings"))) {
                                   module(name, !enabled(name));
                                   p->sendMessage("[Paradox] " + name + " updated.");
                               }
                           });
        send_form(*player, std::move(list));
    });
    form.addButton("Recent evidence", std::nullopt, [this](es::Player *player) {
        if (active_ && player && (clearance(*player) >= 3 || player->hasPermission("paradox.case"))) {
            es::ActionForm f;
            f.setTitle("Evidence").setContent(recent_.dump(2));
            send_form(*player, std::move(f));
        }
    });
    form.addButton("My homes", std::nullopt, [this](es::Player *player) {
        if (active_ && player)
            command(*player, "ac-home", {"list"});
    });
    form.addButton("Connection health", std::nullopt, [this](es::Player *player) {
        if (active_ && player)
            command(*player, "ac-ping", {});
    });
    send_form(p, std::move(form));
}

bool ParadoxPlugin::command(es::CommandSender &sender, std::string name, const std::vector<std::string> &a) {
    auto *player = dynamic_cast<es::Player *>(&sender);
    auto need = [&](int level, const std::string &permission) {
        if (player && clearance(*player) < level && !player->hasPermission(permission))
            throw std::invalid_argument("You do not have permission for this action.");
    };
    auto arg = [&](std::size_t n) -> std::string {
        if (n >= a.size())
            throw std::invalid_argument("Missing command argument");
        return a[n];
    };
    auto require_player = [&]() -> es::Player & {
        if (!player)
            throw std::invalid_argument("This command requires a player.");
        return *player;
    };
    auto target = [&](std::size_t index) -> es::Player & {
        auto *p = getServer().getPlayer(arg(index));
        if (!p)
            throw std::invalid_argument("Player is not online.");
        return *p;
    };
    auto say = [&](std::string message) {
        sender.sendMessage(db_->get("config", "prefix", "[Paradox]").get<std::string>() + " " + message);
    };
    if (name.starts_with("ac-"))
        name.erase(0, 3);
    static const std::set<std::string> utility_permissions = {
        "home",  "tpa",  "tpr", "pvp",      "pvptoggle",    "channels", "gui",      "guiitem",
        "about", "ping", "tps", "waypoint", "chunkborders", "report",   "landclaim"};
    if (player && utility_permissions.contains(name) && !player->hasPermission("paradox." + name))
        throw std::invalid_argument("You do not have permission for this command.");
    if (player && clearance(*player) < 4 && db_->get("disabled_commands", "ac-" + name, false) == true)
        throw std::invalid_argument("That command is disabled.");
    if (name == "pvptoggle")
        name = "pvp";
    if (name == "gui") {
        show_gui(require_player());
        return true;
    }
    if (name == "guiitem") {
        auto &p = require_player();
        es::ItemStack item(es::ItemTypeId("minecraft:compass"), 1);
        auto meta = item.getItemMeta();
        meta->setDisplayName("Paradox Menu");
        meta->setLore(std::vector<std::string>{"Open your Paradox controls"});
        item.setItemMeta(meta.get());
        if (!p.getInventory().addItem(item).empty())
            throw std::invalid_argument("Your inventory is full.");
        say("Use the Paradox Menu compass to open controls.");
        return true;
    }
    if (name == "about" || name == "paradox-info") {
        say("Paradox " + std::string(PARADOX_VERSION) + " native | Endstone 0.11.11 | upstream review 6.9.1");
        return true;
    }
    if (name == "ping") {
        auto &p = a.empty() ? require_player() : target(0);
        auto &s = players_[id(p)];
        say(p.getName() + ": " + std::to_string(p.getPing().count()) + " ms; " +
            (s.detector.lag.ready(now()) ? "checks active" : std::string(s.detector.lag.reason())));
        return true;
    }
    if (name == "tps") {
        say(std::format("{:.2f} TPS / {:.2f} ms per tick", getServer().getAverageTicksPerSecond(),
                        getServer().getAverageMillisecondsPerTick()));
        return true;
    }
    if (name == "modules" || name == "modstate") {
        need(3, "paradox.modules");
        if (!a.empty()) {
            need(4, "paradox.settings");
            if (arg(1) != "on" && arg(1) != "off")
                throw std::invalid_argument("Use on or off");
            if (a[0] == "all") {
                bool state = arg(1) == "on";
                for (const auto &m : module_specs())
                    module(std::string(m.name), state);
            } else
                module(a[0], arg(1) == "on");
        }
        for (auto &[key, value] : modules_.items())
            say(key + ": " + (value.value("enabled", false) ? "on" : "off"));
        return true;
    }
    if (name == "mode") {
        need(4, "paradox.settings");
        if (!a.empty()) {
            if (a[0] != "soft" && a[0] != "hard" && a[0] != "logonly")
                throw std::invalid_argument("Use soft, hard or logonly");
            mode_ = a[0];
            db_->set("config", "enforcement_mode", mode_);
            for (auto *p : getServer().getOnlinePlayers())
                reset(*p);
        }
        say("Enforcement: " + mode_);
        return true;
    }
    if (name == "setclearance") {
        need(4, "paradox.opsec");
        auto &p = target(0);
        int level = static_cast<int>(number(arg(1), 1, 4));
        auto data = db_->get("players", id(p), Json::object());
        data["clearance"] = level;
        db_->set("players", id(p), data);
        reset(p);
        audit(name, sender, {{"target", id(p)}, {"level", level}});
        say("Clearance updated.");
        return true;
    }
    if (name == "op") {
        auto &p = require_player();
        auto &s = players_[id(p)];
        if (now() - s.auth_attempt < 5)
            throw std::invalid_argument("Wait before trying again.");
        s.auth_attempt = now();
        auto hash = db_->get("config", "op_password_hash", "").get<std::string>();
        if (hash.empty() || !constant_equal(hash, sha256(join(a, 0))))
            throw std::invalid_argument("Authentication failed. The console can use ac-setclearance.");
        auto data = db_->get("players", id(p), Json::object());
        data["clearance"] = 4;
        db_->set("players", id(p), data);
        reset(p);
        say("Clearance granted.");
        return true;
    }
    if (name == "deop") {
        auto &p = a.empty() ? require_player() : target(0);
        if (player != &p)
            need(4, "paradox.deop");
        auto data = db_->get("players", id(p), Json::object());
        data["clearance"] = 1;
        db_->set("players", id(p), data);
        reset(p);
        say("Clearance removed.");
        return true;
    }
    if (name == "opsec" || name == "whois") {
        need(3, "paradox.opsec");
        if (a.empty())
            say(db_->all("players").dump(2));
        else {
            auto &p = target(0);
            say(db_->get("players", id(p)).dump(2));
        }
        return true;
    }
    if (name == "ban" || name == "kick" || name == "freeze" || name == "punish") {
        need(3, "paradox." + name);
        auto &p = target(0);
        auto action = name == "punish" ? arg(1) : name;
        auto reason = join(a, name == "punish" ? 2 : 1);
        if (reason.empty())
            reason = "Server moderation";
        if (player && clearance(p) >= clearance(*player) && !player->hasPermission("paradox.settings"))
            throw std::invalid_argument("Cannot moderate a player with equal or higher clearance.");
        if (action == "ban" || action == "tempban") {
            db_->set("bans", id(p),
                     {{"name", p.getName()},
                      {"xuid", p.getXuid()},
                      {"reason", reason},
                      {"time", unix_time()},
                      {"expires", action == "tempban" ? unix_time() + 3600 : 0}});
            db_->flush();
            p.kick("[Paradox] " + reason);
        } else if (action == "kick")
            p.kick("[Paradox] " + reason);
        else if (action == "freeze") {
            auto &s = players_[id(p)];
            s.frozen = !s.frozen;
            db_->set("frozen_players", id(p), s.frozen);
            reset(p);
        } else if (action == "mute")
            db_->set("mutes", id(p), unix_time() + 600);
        else if (action == "warn")
            p.sendMessage("[Paradox] " + reason);
        else
            throw std::invalid_argument("Use warn, mute, kick, ban, tempban or freeze.");
        audit(action, sender, {{"target", id(p)}, {"reason", reason}});
        say("Moderation action completed.");
        return true;
    }
    if (name == "unban") {
        need(3, "paradox.unban");
        auto who = normalize_name(join(a, 0));
        if (who.empty())
            throw std::invalid_argument("Supply a name or UUID");
        for (auto &[key, row] : db_->all("bans").items())
            if (normalize_name(key) == who || (row.is_object() && normalize_name(row.value("name", "")) == who))
                db_->erase("bans", key);
        audit(name, sender, who);
        say("Matching bans removed.");
        return true;
    }
    if (name == "allowlist" || name == "whitelist") {
        need(4, "paradox." + name);
        std::string action = a.empty() ? "list" : a[0];
        if (action == "list") {
            say(db_->all(name).dump(2));
            return true;
        }
        if (name == "whitelist" && (action == "on" || action == "off")) {
            db_->set("config", "whitelist_enabled", action == "on");
            say("Whitelist updated.");
            return true;
        }
        std::string who = join(a, 1), key;
        Json record;
        for (auto &[uid, data] : db_->all("players").items())
            if (uid == who || normalize_name(data.value("name", "")) == normalize_name(who)) {
                key = uid;
                record = data;
                break;
            }
        if (action == "remove") {
            for (auto &[uid, data] : db_->all(name).items())
                if (uid == who || uid == key ||
                    (data.is_object() && normalize_name(data.value("name", "")) == normalize_name(who)))
                    db_->erase(name, uid);
        } else if (action == "add") {
            if (key.empty())
                throw std::invalid_argument("No authenticated player history. Add a player who has joined before; "
                                            "offline players are supported.");
            record["uuid"] = key;
            db_->set(name, key, record);
        } else
            throw std::invalid_argument("Use add, remove, list, on or off.");
        audit(name, sender, {{"operation", action}, {"target", who}});
        refresh_policies();
        say("List updated.");
        return true;
    }
    if (name == "case" || name == "history" ||
        (name == "evidencereplay" && !a.empty() && a[0] != "on" && a[0] != "off")) {
        need(3, "paradox.case");
        auto who = arg(0);
        std::string uid = who;
        if (auto *p = getServer().getPlayer(who))
            uid = id(*p);
        else
            for (auto &[key, data] : db_->all("players").items())
                if (normalize_name(data.value("name", "")) == normalize_name(who))
                    uid = key;
        say((name == "evidencereplay" ? db_->get("replays", uid, Json::object())
                                      : db_->get("violations", uid, Json::array()))
                .dump(2));
        return true;
    }
    if (name == "watch" || name == "exempt") {
        need(3, "paradox." + name);
        auto &p = target(0);
        if (name == "watch")
            watchers_[id(require_player())] = {id(p), now() + (a.size() > 1 ? number(a[1], 1, 3600) : 300)};
        else {
            auto module_name = arg(1);
            if (module_name != "all" && !modules_.contains(module_name))
                throw std::invalid_argument("Unknown module");
            players_[id(p)].exemptions[module_name] = now() + (a.size() > 2 ? number(a[2], 1, 3600) : 300);
            reset(p);
        }
        say("Updated.");
        return true;
    }
    if (name == "home" || name == "waypoint") {
        auto &p = require_player();
        std::string table = name == "home" ? "homes" : "waypoints", uid = id(p);
        auto homes = db_->get(table, uid, Json::object());
        if (!homes.is_object())
            homes = Json::object();
        std::string action = a.empty() ? (name == "home" ? "default" : "list") : a[0],
                    label = a.size() > 1 ? a[1] : "default";
        if (action == "set") {
            if (label.size() > 48 || (homes.size() >= 20 && !homes.contains(label)))
                throw std::invalid_argument("Limit: 20 locations, 48 characters per name.");
            homes[label] = location_json(p.getLocation());
            db_->set(table, uid, homes);
            say("Saved " + label + ".");
        } else if (action == "help") {
            say("Use set, delete, list or tp followed by a location name.");
        } else if (action == "delete" || action == "del" || action == "remove") {
            homes.erase(label);
            db_->set(table, uid, homes);
            say("Deleted " + label + ".");
        } else if (action == "list")
            say(homes.dump(2));
        else {
            label = action == "tp" ? label : action;
            if (!homes.contains(label) || !teleport(p, homes[label]))
                throw std::invalid_argument("Location unavailable.");
        }
        return true;
    }
    if (name == "tpr") {
        auto &p = require_player();
        if (players_[id(p)].combat_until > now())
            throw std::invalid_argument("Wait until combat ends before teleporting.");
        const double radius = a.empty() ? 500 : number(a[0], 16, 10000);
        const auto origin = p.getLocation();
        std::mt19937 random(std::random_device{}());
        std::uniform_real_distribution<double> range(-radius, radius);
        for (int attempt = 0; attempt < 64; ++attempt) {
            auto to = origin;
            to.setX(origin.getX() + range(random));
            to.setZ(origin.getZ() + range(random));
            if (!loaded(to))
                continue;
            int y = to.getDimension().getHighestBlockYAt(to.getBlockX(), to.getBlockZ());
            auto support = to.getDimension().getBlockAt(to.getBlockX(), y, to.getBlockZ());
            if (!support)
                continue;
            const auto type = support->getType();
            if (type != "minecraft:grass_block" && type != "minecraft:grass" && type != "minecraft:stone" &&
                type != "minecraft:sand" && type != "minecraft:dirt")
                continue;
            auto feet = to.getDimension().getBlockAt(to.getBlockX(), y + 1, to.getBlockZ()),
                 head = to.getDimension().getBlockAt(to.getBlockX(), y + 2, to.getBlockZ());
            if (!feet || !head || !air(feet->getType()) || !air(head->getType()))
                continue;
            to.setY(y + 1.0);
            to.setX(to.getBlockX() + 0.5);
            to.setZ(to.getBlockZ() + 0.5);
            if (teleport(p, location_json(to))) {
                say("Teleported to a safe loaded location.");
                return true;
            }
        }
        throw std::invalid_argument(
            "No safe loaded destination in that radius. Try a smaller radius or explore more terrain.");
    }
    if (name == "vanish") {
        need(3, "paradox.vanish");
        auto &p = require_player();
        auto &s = players_[id(p)];
        s.vanished = !s.vanished;
        std::ostringstream quoted;
        quoted << std::quoted(p.getName());
        bool result =
            getServer().dispatchCommand(getServer().getCommandSender(), "effect " + quoted.str() + " invisibility " +
                                                                            (s.vanished ? "1000000 0 true" : "0"));
        if (!result) {
            s.vanished = !s.vanished;
            throw std::runtime_error("Server could not apply invisibility.");
        }
        p.setNameTagVisible(!s.vanished);
        db_->set("vanished_players", id(p), s.vanished);
        say(s.vanished ? "Invisible; name tag hidden." : "Visibility restored.");
        return true;
    }
    if (name == "despawn") {
        need(3, "paradox.despawn");
        std::string type = a.empty() ? "" : a[0];
        if (!type.empty() && type != "item" && type != "arrow" && type != "xp_orb")
            throw std::invalid_argument("Supported cleanup targets: item, arrow, xp_orb.");
        std::optional<es::Location> center;
        if (player)
            center = player->getLocation();
        double radius = a.size() > 1 ? number(a[1], 1, 1000) : 100;
        auto count = clear_entities(type, center ? &*center : nullptr, radius);
        audit(name, sender, {{"count", count}});
        say("Removed " + std::to_string(count) + " unnamed dropped entities.");
        return true;
    }
    if (name == "landclaim") {
        auto &p = require_player();
        const auto action = a.empty() ? "list" : a[0];
        const auto uid = id(p);
        auto l = p.getLocation();
        if (action == "list" || action == "online") {
            for (auto &[key, c] : claims_.items())
                if (c.value("owner", "") == uid || clearance(p) >= 3)
                    say(key + ": " + c.dump());
            return true;
        }
        auto label = a.size() > 1 ? a[1] : "default";
        if (label.empty() || label.size() > 32)
            throw std::invalid_argument("Claim name limit: 32 characters.");
        const auto key = uid + ":" + label;
        if (action == "create") {
            if (!enabled("landclaim"))
                throw std::invalid_argument("Land claims are disabled by the server administrator.");
            unsigned owned = 0;
            for (auto &[key, c] : claims_.items())
                if (c.value("owner", "") == uid)
                    ++owned;
            if (owned >= 5 && !claims_.contains(key))
                throw std::invalid_argument("Limit: five claims per player.");
            int radius = a.size() > 2 ? static_cast<int>(number(a[2], 4, 128)) : 16;
            for (auto &[other, c] : claims_.items())
                if (other != key && c.value("dimension", "") == l.getDimension().getName() &&
                    std::abs(l.getBlockX() - c.value("x", 0)) <= radius + c.value("radius", 16) + 4 &&
                    std::abs(l.getBlockZ() - c.value("z", 0)) <= radius + c.value("radius", 16) + 4)
                    throw std::invalid_argument("Claim overlaps an existing claim or its four-block buffer.");
            db_->set("claims", key,
                     {{"owner", uid},
                      {"name", label},
                      {"dimension", l.getDimension().getName()},
                      {"x", l.getBlockX()},
                      {"z", l.getBlockZ()},
                      {"radius", radius},
                      {"trusted", Json::array()}});
            refresh_policies();
            say("Claim created.");
            return true;
        }
        if (action == "delete") {
            db_->erase("claims", key);
            refresh_policies();
            say("Claim removed.");
            return true;
        }
        if (action == "trust" || action == "untrust") {
            auto c = db_->get("claims", key);
            if (!c.is_object())
                throw std::invalid_argument("Unknown claim.");
            auto &who = target(2);
            auto trusted = c.value("trusted", Json::array());
            auto found = std::find(trusted.begin(), trusted.end(), Json(id(who)));
            if (action == "trust" && found == trusted.end())
                trusted.push_back(id(who));
            if (action == "untrust" && found != trusted.end())
                trusted.erase(found);
            c["trusted"] = trusted;
            db_->set("claims", key, c);
            refresh_policies();
            say("Claim trust updated.");
            return true;
        }
        throw std::invalid_argument("Use create, delete, list, trust or untrust.");
    }
    if (name == "tpa") {
        auto &p = require_player();
        if (arg(0) == "accept") {
            auto it = tpa_.find(id(p));
            if (it == tpa_.end() || it->second.second < now())
                throw std::invalid_argument("No pending request.");
            es::Player *requester = nullptr;
            for (auto *candidate : getServer().getOnlinePlayers())
                if (id(*candidate) == it->second.first)
                    requester = candidate;
            if (!requester)
                throw std::invalid_argument("Requester left the server.");
            auto where = location_json(p.getLocation());
            tpa_.erase(it);
            teleport(*requester, where);
        } else if (a[0] == "deny")
            tpa_.erase(id(p));
        else {
            auto &to = target(0);
            tpa_[id(to)] = {id(p), now() + 60};
            to.sendMessage("[Paradox] " + p.getName() + " requests teleport. Use /ac-tpa accept or deny.");
        }
        return true;
    }
    if (name == "invsee" || name == "inventory-editor" || name == "invclone") {
        need(3, "paradox.invsee");
        auto &p = target(0);
        if (name == "invclone") {
            need(4, "paradox.settings");
            require_player().getInventory().setContents(p.getInventory().getContents());
            audit(name, sender, id(p));
        } else if (name == "inventory-editor" && a.size() > 2) {
            need(4, "paradox.settings");
            auto slot = static_cast<int>(number(a[1], 0, p.getInventory().getSize() - 1));
            if (a[2] == "clear")
                p.getInventory().clear(slot);
            else {
                es::ItemStack item(es::ItemTypeId(a[2]), a.size() > 3 ? static_cast<int>(number(a[3], 1, 64)) : 1);
                p.getInventory().setItem(slot, item);
            }
            audit(name, sender, {{"target", id(p)}, {"slot", slot}});
        } else
            say(inventory(p).dump(2));
        return true;
    }
    if (name == "channels") {
        auto &p = require_player();
        auto &s = players_[id(p)];
        auto action = a.empty() ? "list" : a[0];
        if (action == "list") {
            say(db_->all("channels").dump(2));
            return true;
        }
        if (action == "leave")
            s.channel = "";
        else if (action == "create") {
            auto label = arg(1);
            if (label.size() > 32)
                throw std::invalid_argument("Channel name too long");
            db_->set("channels", label, {{"owner", id(p)}});
            s.channel = label;
        } else if (action == "join") {
            auto label = arg(1);
            if (db_->get("channels", label).is_null())
                throw std::invalid_argument("Unknown channel");
            s.channel = label;
        } else
            throw std::invalid_argument("Use create, join, leave or list");
        auto data = db_->get("player_data", id(p), Json::object());
        data["channel"] = s.channel;
        db_->set("player_data", id(p), data);
        say("Channel updated.");
        return true;
    }
    if (name == "rank") {
        need(3, "paradox.rank");
        auto &p = target(0);
        auto rank = join(a, 1);
        players_[id(p)].rank = rank;
        db_->set("ranks", id(p), rank);
        p.setScoreTag(rank);
        say("Rank updated.");
        return true;
    }
    if (name == "pvp") {
        if (!enabled("pvp"))
            throw std::invalid_argument("PvP management is disabled.");
        if (!a.empty() && a[0] == "global") {
            need(4, "paradox.settings");
            auto state = db_->get("config", "global_pvp", true) != false;
            db_->set("config", "global_pvp", !state);
            say(state ? "Global PvP disabled." : "Global PvP enabled.");
            return true;
        }
        auto &p = require_player();
        auto &s = players_[id(p)];
        auto data = db_->get("pvp_data", id(p), true);
        bool state = data.is_object() ? data.value("enabled", true) : data != false;
        if (!a.empty() && (a[0] == "status" || a[0] == "info")) {
            say(std::string("Personal PvP: ") + (state ? "on" : "off") +
                "; global: " + (db_->get("config", "global_pvp", true) == true ? "on" : "off"));
            return true;
        }
        if (!a.empty() && a[0] != "on" && a[0] != "off")
            throw std::invalid_argument("Use on, off, status or global.");
        if (s.combat_until > now())
            throw std::invalid_argument("PvP cannot be changed during combat.");
        if (now() - s.last_pvp_toggle < 10)
            throw std::invalid_argument("Wait ten seconds between PvP changes.");
        state = a.empty() ? !state : a[0] == "on";
        db_->set("pvp_data", id(p), state);
        s.last_pvp_toggle = now();
        say(std::string("PvP ") + (state ? "enabled" : "disabled"));
        return true;
    }
    if (name == "chunkborders") {
        auto &p = require_player();
        if (!enabled("chunkborders"))
            throw std::invalid_argument("Chunk border display is disabled by the server administrator.");
        auto &s = players_[id(p)];
        s.chunk_borders = !s.chunk_borders;
        say("Chunk borders toggled.");
        return true;
    }
    if (name == "transfer") {
        need(3, "paradox.transfer");
        auto &p = target(0);
        p.transfer(arg(1), a.size() > 2 ? static_cast<int>(number(a[2], 1, 65535)) : 19132);
        return true;
    }
    if (name == "switch-game-mode" || name == "switchgamemode") {
        need(4, "paradox.settings");
        auto &p = a.size() > 1 ? target(1) : require_player();
        auto gm = static_cast<es::GameMode>(static_cast<int>(number(arg(0), 0, 3)));
        reset(p);
        p.setGameMode(gm);
        return true;
    }
    if (name == "broadcast") {
        need(3, "paradox.broadcast");
        getServer().broadcastMessage(join(a, 0));
        return true;
    }
    if (name == "report") {
        auto &p = require_player();
        if (!enabled("reportsystem"))
            throw std::invalid_argument("Player reports are disabled.");
        auto &s = players_[id(p)];
        if (now() - s.last_report < 30)
            throw std::invalid_argument("Wait thirty seconds between reports.");
        s.last_report = now();
        auto &who = target(0);
        auto reason = join(a, 1);
        if (reason.empty())
            throw std::invalid_argument("Supply a reason");
        db_->set("reports", random_token(),
                 {{"reporter", id(p)}, {"target", id(who)}, {"reason", reason}, {"time", unix_time()}});
        say("Report recorded for review.");
        return true;
    }
    if (name == "command") {
        need(4, "paradox.command");
        if (arg(0) != "enable" && arg(0) != "disable")
            throw std::invalid_argument("Use enable or disable.");
        auto which = arg(1);
        if (!which.starts_with("ac-"))
            which = "ac-" + which;
        db_->set("disabled_commands", which, arg(0) == "disable");
        say("Command policy updated.");
        return true;
    }
    if (name == "prefix") {
        need(4, "paradox.prefix");
        db_->set("config", "prefix", join(a, 0));
        say("Prefix saved.");
        return true;
    }
    if (name == "debug-db") {
        need(4, "paradox.opsec");
        db_->flush();
        say(db_->error().empty() ? "SQLite cache and write queue healthy." : db_->error());
        return true;
    }
    if (name == "spooflog") {
        need(3, "paradox.spooflog");
        say(db_->all("spoof_log").dump(2));
        return true;
    }
    if ((name == "afk" || name == "lagclear") && !a.empty() && a[0] != "on" && a[0] != "off") {
        need(4, "paradox.settings");
        db_->set("config", name == "afk" ? "afk_timeout" : "lagclear_interval", number(a[0], 60, 86400));
        module(name, true);
        say("Interval saved.");
        return true;
    }
    if (name == "environment") {
        need(4, "paradox.settings");
        auto kind = arg(0), value = arg(1);
        static const std::set<std::string> times = {"sunrise", "day", "noon", "sunset", "night", "midnight"},
                                           weather = {"clear", "rain", "thunder"};
        if ((kind == "time" && times.contains(value)) || (kind == "weather" && weather.contains(value))) {
            if (!getServer().dispatchCommand(getServer().getCommandSender(),
                                             kind + (kind == "time" ? " set " : " ") + value))
                throw std::runtime_error("Server rejected environment command.");
            return true;
        }
        throw std::invalid_argument("Use time sunrise/day/noon/sunset/night/midnight or weather clear/rain/thunder.");
    }
    if (name == "worldborder" && !a.empty() && a[0] != "on" && a[0] != "off") {
        need(4, "paradox.settings");
        db_->set("config", "worldborder",
                 {{"radius", number(a[0], 0, 30000000)},
                  {"x", a.size() > 1 ? number(a[1], -30000000, 30000000) : 0},
                  {"z", a.size() > 2 ? number(a[2], -30000000, 30000000) : 0}});
        module(name, true);
        say("World border updated.");
        return true;
    }
    if (name == "lockdown") {
        need(4, "paradox.lockdown");
        bool state = a.empty() ? !enabled(name) : a[0] != "off";
        module(name, state);
        if (a.size() > 1 && a[1] == "kick")
            for (auto *p : getServer().getOnlinePlayers())
                if (clearance(*p) < 4)
                    p->kick("[Paradox] Server lockdown");
        say(state ? "Lockdown enabled; existing players retained unless kick was requested." : "Lockdown disabled.");
        return true;
    }
    if (modules_.contains(name)) {
        need(4, "paradox.settings");
        bool state = a.empty() ? !enabled(name) : a[0] == "on";
        if (!a.empty() && a[0] != "on" && a[0] != "off")
            throw std::invalid_argument("Use on or off");
        module(name, state);
        say(name + (state ? " enabled." : " disabled."));
        return true;
    }
    throw std::invalid_argument("Unknown Paradox command.");
}
} // namespace paradox

ENDSTONE_PLUGIN("paradox", PARADOX_VERSION, paradox::ParadoxPlugin) {
    description = "Native Paradox protection, moderation and administration";
    authors = {"TheNINJALLO", "Visual1mpact"};
    website = "https://github.com/TheNINJALLO/endstone-paradox";
    for (const auto &spec : paradox::module_specs()) {
        auto name = "ac-" + std::string(spec.name);
        command(name).description("Configure " + std::string(spec.name));
        command(name).usages("/" + name + " [args: message]");
        command(name).permissions("paradox.use");
    }
    const std::vector<std::string> admin = {"op",           "deop",
                                            "ban",          "unban",
                                            "kick",         "freeze",
                                            "vanish",       "lockdown",
                                            "punish",       "allowlist",
                                            "whitelist",    "opsec",
                                            "despawn",      "modules",
                                            "spooflog",     "command",
                                            "prefix",       "invsee",
                                            "rank",         "debug-db",
                                            "case",         "mode",
                                            "watch",        "exempt",
                                            "setclearance", "modstate",
                                            "whois",        "history",
                                            "transfer",     "inventory-editor",
                                            "invclone",     "switch-game-mode",
                                            "broadcast",    "environment"};
    const std::vector<std::string> utility = {"home",     "tpa",      "tpr",          "pvp",    "pvptoggle",
                                              "channels", "gui",      "guiitem",      "about",  "ping",
                                              "tps",      "waypoint", "chunkborders", "report", "landclaim"};
    for (const auto &name : admin) {
        auto cmd = "ac-" + name;
        command(cmd).description("Paradox " + name);
        command(cmd).usages("/" + cmd + " [args: message]");
        command(cmd).permissions("paradox.use");
        permission("paradox." + name).default_(endstone::PermissionDefault::Operator);
    }
    for (const auto &name : utility) {
        auto cmd = "ac-" + name;
        command(cmd).description("Paradox " + name);
        command(cmd).usages("/" + cmd + " [args: message]");
        command(cmd).permissions("paradox." + name);
        permission("paradox." + name).default_(endstone::PermissionDefault::True);
    }
    permission("paradox.use").default_(endstone::PermissionDefault::True);
    permission("paradox.settings").default_(endstone::PermissionDefault::Operator);
    permission("paradox.alerts").default_(endstone::PermissionDefault::Operator);
    permission("paradox.bypass").default_(endstone::PermissionDefault::False);
}
