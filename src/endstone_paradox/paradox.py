"""
Paradox AntiCheat - Main Plugin Entry Point

Core plugin class that initializes all systems, registers events,
starts detection modules, and routes /ac-* commands.
"""

from pathlib import Path

from endstone.plugin import Plugin
from endstone.event import event_handler, EventPriority
from endstone.event import (
    PlayerJoinEvent,
    PlayerQuitEvent,
    PlayerJumpEvent,
    PlayerMoveEvent,
    PlayerChatEvent,
    PlayerGameModeChangeEvent,
    ActorDamageEvent,
    BlockBreakEvent,
    BlockPlaceEvent,
    PacketReceiveEvent,
)

from endstone_paradox.database import ParadoxDatabase
from endstone_paradox.security import SecurityManager, SecurityClearance


class ParadoxPlugin(Plugin):
    """Main Paradox AntiCheat plugin class."""

    api_version = "0.11"

    # ─── Command Definitions ────────────────────────────────────
    commands = {
        # Moderation
        "ac-op": {"description": "Grant security clearance with password", "usages": ["/ac-op <password: str>"], "permissions": ["paradox.op"]},
        "ac-deop": {"description": "Revoke security clearance", "usages": ["/ac-deop [player: player]"], "permissions": ["paradox.deop"]},
        "ac-ban": {"description": "Ban a player", "usages": ["/ac-ban <player: player> [reason: str]"], "permissions": ["paradox.ban"]},
        "ac-unban": {"description": "Unban a player", "usages": ["/ac-unban <name: str>"], "permissions": ["paradox.unban"]},
        "ac-kick": {"description": "Kick a player", "usages": ["/ac-kick <player: player> [reason: str]"], "permissions": ["paradox.kick"]},
        "ac-freeze": {"description": "Freeze/unfreeze a player", "usages": ["/ac-freeze <player: player>"], "permissions": ["paradox.freeze"]},
        "ac-vanish": {"description": "Toggle admin invisibility", "usages": ["/ac-vanish"], "permissions": ["paradox.vanish"]},
        "ac-lockdown": {"description": "Toggle server lockdown mode", "usages": ["/ac-lockdown"], "permissions": ["paradox.lockdown"]},
        "ac-punish": {"description": "Punish a player", "usages": ["/ac-punish <player: player> <action: str>"], "permissions": ["paradox.punish"]},
        "ac-tpa": {"description": "Send teleport request", "usages": ["/ac-tpa <player: player>"], "permissions": ["paradox.tpa"]},
        "ac-allowlist": {"description": "Manage allow list", "usages": ["/ac-allowlist <action: str> [player: str]"], "permissions": ["paradox.allowlist"]},
        "ac-whitelist": {"description": "Manage whitelist", "usages": ["/ac-whitelist <action: str> [player: str]"], "permissions": ["paradox.whitelist"]},
        "ac-opsec": {"description": "Security dashboard", "usages": ["/ac-opsec"], "permissions": ["paradox.opsec"]},
        "ac-despawn": {"description": "Remove entities", "usages": ["/ac-despawn [type: str] [radius: int]"], "permissions": ["paradox.despawn"]},
        "ac-modules": {"description": "Module status dashboard", "usages": ["/ac-modules"], "permissions": ["paradox.modules"]},
        "ac-spooflog": {"description": "View namespoof logs", "usages": ["/ac-spooflog"], "permissions": ["paradox.spooflog"]},
        "ac-command": {"description": "Enable/disable commands", "usages": ["/ac-command <action: str> <command: str>"], "permissions": ["paradox.command"]},
        "ac-prefix": {"description": "Change command prefix display", "usages": ["/ac-prefix [prefix: str]"], "permissions": ["paradox.prefix"]},
        # Settings
        "ac-fly": {"description": "Toggle fly detection", "usages": ["/ac-fly"], "permissions": ["paradox.settings"]},
        "ac-killaura": {"description": "Toggle killaura detection", "usages": ["/ac-killaura"], "permissions": ["paradox.settings"]},
        "ac-reach": {"description": "Toggle reach detection", "usages": ["/ac-reach"], "permissions": ["paradox.settings"]},
        "ac-autoclicker": {"description": "Toggle autoclicker detection", "usages": ["/ac-autoclicker [maxcps: int]"], "permissions": ["paradox.settings"]},
        "ac-scaffold": {"description": "Toggle scaffold detection", "usages": ["/ac-scaffold"], "permissions": ["paradox.settings"]},
        "ac-xray": {"description": "Toggle xray detection", "usages": ["/ac-xray"], "permissions": ["paradox.settings"]},
        "ac-gamemode": {"description": "Toggle gamemode detection", "usages": ["/ac-gamemode"], "permissions": ["paradox.settings"]},
        "ac-afk": {"description": "Toggle/configure AFK detection", "usages": ["/ac-afk [timeout: int]"], "permissions": ["paradox.settings"]},
        "ac-vision": {"description": "Toggle vision detection", "usages": ["/ac-vision"], "permissions": ["paradox.settings"]},
        "ac-worldborder": {"description": "Configure world border", "usages": ["/ac-worldborder [radius: int] [x: int] [z: int]"], "permissions": ["paradox.settings"]},
        "ac-lagclear": {"description": "Toggle/configure lag clear", "usages": ["/ac-lagclear [interval: int]"], "permissions": ["paradox.settings"]},
        "ac-ratelimit": {"description": "Toggle rate limiting", "usages": ["/ac-ratelimit"], "permissions": ["paradox.settings"]},
        "ac-namespoof": {"description": "Toggle namespoof detection", "usages": ["/ac-namespoof"], "permissions": ["paradox.settings"]},
        "ac-packetmonitor": {"description": "Toggle packet monitor", "usages": ["/ac-packetmonitor"], "permissions": ["paradox.settings"]},
        # Utility
        "ac-home": {"description": "Set/teleport to home locations", "usages": ["/ac-home [action: str] [name: str]"], "permissions": ["paradox.home"]},
        "ac-tpr": {"description": "Random teleport", "usages": ["/ac-tpr [radius: int]"], "permissions": ["paradox.tpr"]},
        "ac-invsee": {"description": "View player inventory", "usages": ["/ac-invsee <player: player>"], "permissions": ["paradox.invsee"]},
        "ac-pvp": {"description": "Toggle PvP", "usages": ["/ac-pvp"], "permissions": ["paradox.pvp"]},
        "ac-channels": {"description": "Private chat channels", "usages": ["/ac-channels <action: str> [name: str] [message: str]"], "permissions": ["paradox.channels"]},
        "ac-rank": {"description": "Player rank management", "usages": ["/ac-rank <player: player> [rank: str]"], "permissions": ["paradox.rank"]},
        "ac-debug-db": {"description": "Inspect/modify SQLite database", "usages": ["/ac-debug-db [table: str] [key: str] [value: str]"], "permissions": ["paradox.debugdb"]},
        "ac-gui": {"description": "Open Paradox GUI menu", "usages": ["/ac-gui"], "permissions": ["paradox.gui"]},
        "ac-about": {"description": "About Paradox AntiCheat", "usages": ["/ac-about"], "permissions": ["paradox.about"]},
    }

    # ─── Permission Definitions ─────────────────────────────────
    permissions = {
        "paradox.op": {"description": "Use /ac-op command", "default": True},
        "paradox.deop": {"description": "Use /ac-deop command", "default": "op"},
        "paradox.ban": {"description": "Use /ac-ban command", "default": "op"},
        "paradox.unban": {"description": "Use /ac-unban command", "default": "op"},
        "paradox.kick": {"description": "Use /ac-kick command", "default": "op"},
        "paradox.freeze": {"description": "Use /ac-freeze command", "default": "op"},
        "paradox.vanish": {"description": "Use /ac-vanish command", "default": "op"},
        "paradox.lockdown": {"description": "Use /ac-lockdown command", "default": "op"},
        "paradox.punish": {"description": "Use /ac-punish command", "default": "op"},
        "paradox.tpa": {"description": "Use /ac-tpa command", "default": True},
        "paradox.allowlist": {"description": "Use /ac-allowlist command", "default": "op"},
        "paradox.whitelist": {"description": "Use /ac-whitelist command", "default": "op"},
        "paradox.opsec": {"description": "Use /ac-opsec command", "default": "op"},
        "paradox.despawn": {"description": "Use /ac-despawn command", "default": "op"},
        "paradox.modules": {"description": "Use /ac-modules command", "default": "op"},
        "paradox.spooflog": {"description": "Use /ac-spooflog command", "default": "op"},
        "paradox.command": {"description": "Use /ac-command command", "default": "op"},
        "paradox.prefix": {"description": "Use /ac-prefix command", "default": "op"},
        "paradox.settings": {"description": "Use settings commands", "default": "op"},
        "paradox.home": {"description": "Use /ac-home command", "default": True},
        "paradox.tpr": {"description": "Use /ac-tpr command", "default": True},
        "paradox.invsee": {"description": "Use /ac-invsee command", "default": "op"},
        "paradox.pvp": {"description": "Use /ac-pvp command", "default": True},
        "paradox.channels": {"description": "Use /ac-channels command", "default": True},
        "paradox.rank": {"description": "Use /ac-rank command", "default": "op"},
        "paradox.debugdb": {"description": "Use /ac-debug-db command", "default": "op"},
        "paradox.gui": {"description": "Use /ac-gui command", "default": "op"},
        "paradox.about": {"description": "Use /ac-about command", "default": True},
    }

    def __init__(self):
        super().__init__()
        self.db: ParadoxDatabase = None
        self.security: SecurityManager = None

        # Module instances (lazy-loaded in on_enable)
        self._modules = {}
        self._module_tasks = {}

        # Per-player state tracking
        self._player_jump_flags = {}   # UUID -> bool (recently jumped)
        self._frozen_players = set()   # Set of frozen player UUIDs
        self._vanished_players = set() # Set of vanished player UUIDs
        self._lockdown_active = False

        # Command handlers mapping
        self._command_handlers = {}

    # ─── Lifecycle ──────────────────────────────────────────────

    def on_enable(self):
        """Called when the plugin is enabled."""
        # Print startup banner
        self.logger.info("")
        self.logger.info("§2════════════════════════════════════════════════════════")
        self.logger.info("")
        self.logger.info("  §f§l ██████   █████  ██████   █████  ██████   ██████  ██   ██")
        self.logger.info("  §f§l ██   ██ ██   ██ ██   ██ ██   ██ ██   ██ ██    ██  ██ ██")
        self.logger.info("  §f§l ██████  ███████ ██████  ███████ ██   ██ ██    ██   ███")
        self.logger.info("  §f§l ██      ██   ██ ██   ██ ██   ██ ██   ██ ██    ██  ██ ██")
        self.logger.info("  §f§l ██      ██   ██ ██   ██ ██   ██ ██████   ██████  ██   ██")
        self.logger.info("")
        self.logger.info("  §7AntiCheat §ev1.0.0")
        self.logger.info("  §7Designed by §fVisual1mpact")
        self.logger.info("  §7Ported to Endstone by §a§lTheN1NJ4LL0")
        self.logger.info("")
        self.logger.info("§2════════════════════════════════════════════════════════")
        self.logger.info("")

        # Initialize database
        data_folder = Path(self.data_folder)
        self.db = ParadoxDatabase(data_folder, self.logger)

        # Initialize security system
        self.security = SecurityManager(self.db)

        # Load lockdown state
        self._lockdown_active = self.db.get("config", "lockdown", False)

        # Load frozen/vanished players
        frozen = self.db.get_all("frozen_players")
        self._frozen_players = set(frozen.keys())
        vanished = self.db.get_all("vanished_players")
        self._vanished_players = set(vanished.keys())

        # Register command handlers
        self._register_command_handlers()

        # Register event listeners
        self.register_events(self)

        # Initialize and start all enabled modules
        self._init_modules()

        self.logger.info("§2[§7Paradox§2]§a Loaded successfully!")
        self.logger.info(f"§2[§7Paradox§2]§7 Database: {self.db._db_path}")
        self.logger.info(f"§2[§7Paradox§2]§7 Modules loaded: {len(self._modules)}")

    def on_disable(self):
        """Called when the plugin is disabled."""
        self.logger.info("§2[§7Paradox§2]§r Shutting down Paradox AntiCheat...")

        # Stop all modules
        for name, module in self._modules.items():
            try:
                module.stop()
            except Exception as e:
                self.logger.error(f"Error stopping module {name}: {e}")

        # Close database
        if self.db:
            self.db.close()

        self.logger.info("§2[§7Paradox§2]§c Paradox AntiCheat disabled.")

    # ─── Module Management ──────────────────────────────────────

    def _init_modules(self):
        """Initialize and start all detection modules."""
        from endstone_paradox.modules.fly import FlyModule
        from endstone_paradox.modules.killaura import KillAuraModule
        from endstone_paradox.modules.reach import ReachModule
        from endstone_paradox.modules.autoclicker import AutoClickerModule
        from endstone_paradox.modules.scaffold import ScaffoldModule
        from endstone_paradox.modules.xray import XrayModule
        from endstone_paradox.modules.gamemode import GameModeModule
        from endstone_paradox.modules.namespoof import NameSpoofModule
        from endstone_paradox.modules.afk import AFKModule
        from endstone_paradox.modules.world_border import WorldBorderModule
        from endstone_paradox.modules.lag_clear import LagClearModule
        from endstone_paradox.modules.vision import VisionModule
        from endstone_paradox.modules.self_infliction import SelfInflictionModule
        from endstone_paradox.modules.rate_limit import RateLimitModule
        from endstone_paradox.modules.packet_monitor import PacketMonitorModule
        from endstone_paradox.modules.pvp_manager import PvPManagerModule

        module_classes = {
            "fly": FlyModule,
            "killaura": KillAuraModule,
            "reach": ReachModule,
            "autoclicker": AutoClickerModule,
            "scaffold": ScaffoldModule,
            "xray": XrayModule,
            "gamemode": GameModeModule,
            "namespoof": NameSpoofModule,
            "afk": AFKModule,
            "worldborder": WorldBorderModule,
            "lagclear": LagClearModule,
            "vision": VisionModule,
            "selfinfliction": SelfInflictionModule,
            "ratelimit": RateLimitModule,
            "packetmonitor": PacketMonitorModule,
            "pvp": PvPManagerModule,
        }

        # Modules that are OFF by default (need server-specific calibration)
        default_off = {
            "fly", "killaura", "reach", "autoclicker", "scaffold",
            "xray", "vision", "selfinfliction", "ratelimit", "packetmonitor",
        }

        for name, cls in module_classes.items():
            try:
                module = cls(self)
                self._modules[name] = module
                # Check DB first; if no DB entry, use default based on module type
                default_state = name not in default_off
                enabled = self.db.get("modules", name, default_state)
                if enabled:
                    module.start()
                    self.logger.info(f"  §2[§7Paradox§2]§a Module '{name}' started")
                else:
                    self.logger.info(f"  §2[§7Paradox§2]§7 Module '{name}' disabled")
            except Exception as e:
                self.logger.error(f"  §2[§7Paradox§2]§c Failed to init module '{name}': {e}")

    def get_module(self, name: str):
        """Get a module instance by name."""
        return self._modules.get(name)

    def is_module_enabled(self, name: str) -> bool:
        """Check if a module is enabled."""
        module = self._modules.get(name)
        return module is not None and module.running

    def toggle_module(self, name: str) -> bool:
        """Toggle a module on/off. Returns the new state."""
        module = self._modules.get(name)
        if module is None:
            return False
        if module.running:
            module.stop()
            self.db.set("modules", name, False)
            return False
        else:
            module.start()
            self.db.set("modules", name, True)
            return True

    # ─── Command Routing ────────────────────────────────────────

    def _register_command_handlers(self):
        """Register all command handler functions."""
        from endstone_paradox.commands.moderation.op_cmd import handle_op
        from endstone_paradox.commands.moderation.deop_cmd import handle_deop
        from endstone_paradox.commands.moderation.ban_cmd import handle_ban
        from endstone_paradox.commands.moderation.unban_cmd import handle_unban
        from endstone_paradox.commands.moderation.kick_cmd import handle_kick
        from endstone_paradox.commands.moderation.freeze_cmd import handle_freeze
        from endstone_paradox.commands.moderation.vanish_cmd import handle_vanish
        from endstone_paradox.commands.moderation.lockdown_cmd import handle_lockdown
        from endstone_paradox.commands.moderation.punish_cmd import handle_punish
        from endstone_paradox.commands.moderation.tpa_cmd import handle_tpa
        from endstone_paradox.commands.moderation.allowlist_cmd import handle_allowlist
        from endstone_paradox.commands.moderation.whitelist_cmd import handle_whitelist
        from endstone_paradox.commands.moderation.opsec_cmd import handle_opsec
        from endstone_paradox.commands.moderation.despawn_cmd import handle_despawn
        from endstone_paradox.commands.moderation.modules_cmd import handle_modules
        from endstone_paradox.commands.moderation.spooflog_cmd import handle_spooflog
        from endstone_paradox.commands.moderation.command_cmd import handle_command
        from endstone_paradox.commands.moderation.prefix_cmd import handle_prefix

        from endstone_paradox.commands.settings.toggle_cmds import handle_toggle

        from endstone_paradox.commands.utility.home_cmd import handle_home
        from endstone_paradox.commands.utility.tpr_cmd import handle_tpr
        from endstone_paradox.commands.utility.invsee_cmd import handle_invsee
        from endstone_paradox.commands.utility.pvp_cmd import handle_pvp
        from endstone_paradox.commands.utility.channels_cmd import handle_channels
        from endstone_paradox.commands.utility.rank_cmd import handle_rank
        from endstone_paradox.commands.utility.debug_db_cmd import handle_debug_db
        from endstone_paradox.commands.utility.gui_cmd import handle_gui
        from endstone_paradox.commands.utility.about_cmd import handle_about

        # Moderation commands
        self._command_handlers["ac-op"] = handle_op
        self._command_handlers["ac-deop"] = handle_deop
        self._command_handlers["ac-ban"] = handle_ban
        self._command_handlers["ac-unban"] = handle_unban
        self._command_handlers["ac-kick"] = handle_kick
        self._command_handlers["ac-freeze"] = handle_freeze
        self._command_handlers["ac-vanish"] = handle_vanish
        self._command_handlers["ac-lockdown"] = handle_lockdown
        self._command_handlers["ac-punish"] = handle_punish
        self._command_handlers["ac-tpa"] = handle_tpa
        self._command_handlers["ac-allowlist"] = handle_allowlist
        self._command_handlers["ac-whitelist"] = handle_whitelist
        self._command_handlers["ac-opsec"] = handle_opsec
        self._command_handlers["ac-despawn"] = handle_despawn
        self._command_handlers["ac-modules"] = handle_modules
        self._command_handlers["ac-spooflog"] = handle_spooflog
        self._command_handlers["ac-command"] = handle_command
        self._command_handlers["ac-prefix"] = handle_prefix

        # Settings toggle commands - all use the same handler
        toggle_commands = [
            "ac-fly", "ac-killaura", "ac-reach", "ac-autoclicker",
            "ac-scaffold", "ac-xray", "ac-gamemode", "ac-afk",
            "ac-vision", "ac-worldborder", "ac-lagclear", "ac-ratelimit",
            "ac-namespoof", "ac-packetmonitor",
        ]
        for cmd in toggle_commands:
            self._command_handlers[cmd] = handle_toggle

        # Utility commands
        self._command_handlers["ac-home"] = handle_home
        self._command_handlers["ac-tpr"] = handle_tpr
        self._command_handlers["ac-invsee"] = handle_invsee
        self._command_handlers["ac-pvp"] = handle_pvp
        self._command_handlers["ac-channels"] = handle_channels
        self._command_handlers["ac-rank"] = handle_rank
        self._command_handlers["ac-debug-db"] = handle_debug_db
        self._command_handlers["ac-gui"] = handle_gui
        self._command_handlers["ac-about"] = handle_about

    def on_command(self, sender, command, args) -> bool:
        """Route all /ac-* commands to their handlers."""
        from endstone import Player
        cmd_name = command.name

        handler = self._command_handlers.get(cmd_name)
        if handler is None:
            sender.send_message("§2[§7Paradox§2]§c Unknown command.")
            return False

        # Check if command is disabled
        if self.db.has("disabled_commands", cmd_name):
            sender.send_message("§2[§7Paradox§2]§c This command is currently disabled.")
            return False

        # Console sender always has full access (not a Player, no unique_id)
        is_player = isinstance(sender, Player)

        if is_player:
            # Security clearance check (ac-op is always accessible)
            if cmd_name != "ac-op":
                required = self._get_required_clearance(cmd_name)
                if not self.security.has_clearance(sender, required):
                    sender.send_message("§2[§7Paradox§2]§c Insufficient security clearance.")
                    return False

            # Lockdown check - only Level 4 can use commands during lockdown
            if self._lockdown_active and cmd_name != "ac-lockdown":
                if not self.security.is_level4(sender):
                    sender.send_message("§2[§7Paradox§2]§c Server is in lockdown mode.")
                    return False

        try:
            return handler(self, sender, args)
        except Exception as e:
            self.logger.error(f"Error executing {cmd_name}: {e}")
            sender.send_message(f"§2[§7Paradox§2]§c Error: {e}")
            return False

    def _get_required_clearance(self, cmd_name: str) -> SecurityClearance:
        """Get the required security clearance for a command."""
        # Commands accessible to all players (Level 1)
        public_commands = {
            "ac-op", "ac-tpa", "ac-home", "ac-tpr", "ac-pvp", "ac-channels",
            "ac-about",
        }
        # Commands requiring Level 2
        level2_commands = set()
        # Commands requiring Level 3
        level3_commands = {
            "ac-kick", "ac-freeze", "ac-vanish", "ac-despawn",
            "ac-invsee", "ac-spooflog", "ac-rank",
        }
        # Everything else requires Level 4
        if cmd_name in public_commands:
            return SecurityClearance.LEVEL_1
        elif cmd_name in level2_commands:
            return SecurityClearance.LEVEL_2
        elif cmd_name in level3_commands:
            return SecurityClearance.LEVEL_3
        else:
            return SecurityClearance.LEVEL_4

    # ─── Event Handlers ─────────────────────────────────────────

    @event_handler
    def on_player_join(self, event: PlayerJoinEvent):
        """Handle player joins: ban check, welcome, module notifications."""
        player = event.player
        uuid_str = str(player.unique_id)

        # Ban check
        ban_data = self.db.get("bans", uuid_str)
        if ban_data is None:
            # Also check by name
            ban_data = self.db.get("bans", player.name.lower())
        if ban_data:
            reason = ban_data.get("reason", "Banned by Paradox AntiCheat") if isinstance(ban_data, dict) else "Banned by Paradox AntiCheat"
            player.kick(f"§c{reason}")
            return

        # Allowlist check
        if self.db.count("allowlist") > 0:
            if not self.db.has("allowlist", uuid_str) and not self.db.has("allowlist", player.name.lower()):
                player.kick("§cYou are not on the allow list.")
                return

        # Lockdown check
        if self._lockdown_active and not self.security.is_level4(player):
            player.kick("§cServer is currently in lockdown mode.")
            return

        # Store/update player data
        player_data = self.db.get("players", uuid_str, {})
        if not isinstance(player_data, dict):
            player_data = {}
        player_data["name"] = player.name
        player_data["last_join"] = __import__("time").time()
        self.db.set("players", uuid_str, player_data)

        # Notify Level 4 players about this join
        if self.security.get_level4_players():
            for online_player in self.server.online_players:
                if self.security.is_level4(online_player):
                    clearance = self.security.get_clearance(player)
                    online_player.send_message(
                        f"§2[§7Paradox§2]§7 {player.name} joined "
                        f"(Clearance: {clearance.name})"
                    )

    @event_handler
    def on_player_quit(self, event: PlayerQuitEvent):
        """Handle player disconnects: cleanup state."""
        player = event.player
        uuid_str = str(player.unique_id)

        # Clean up jump flags
        self._player_jump_flags.pop(uuid_str, None)

        # Notify modules
        for module in self._modules.values():
            try:
                module.on_player_leave(player)
            except Exception:
                pass

    @event_handler
    def on_player_jump(self, event: PlayerJumpEvent):
        """Track player jumps for fly detection."""
        player = event.player
        uuid_str = str(player.unique_id)
        self._player_jump_flags[uuid_str] = True

        # Auto-clear after 1 second (20 ticks)
        def clear_jump():
            self._player_jump_flags.pop(uuid_str, None)

        self.server.scheduler.run_task(self, clear_jump, delay=20)

    @event_handler
    def on_player_move(self, event: PlayerMoveEvent):
        """Handle player movement for fly/speed detection and freeze."""
        player = event.player
        uuid_str = str(player.unique_id)

        # Freeze enforcement
        if uuid_str in self._frozen_players:
            event.is_cancelled = True
            return

    @event_handler
    def on_actor_damage(self, event: ActorDamageEvent):
        """Route damage events to combat-related modules."""
        for module_name in ("killaura", "reach", "autoclicker", "pvp", "selfinfliction"):
            module = self._modules.get(module_name)
            if module and module.running:
                try:
                    module.on_damage(event)
                except Exception as e:
                    self.logger.error(f"Module {module_name} damage handler error: {e}")

    @event_handler
    def on_block_break(self, event: BlockBreakEvent):
        """Route block break events to xray module."""
        module = self._modules.get("xray")
        if module and module.running:
            try:
                module.on_block_break(event)
            except Exception as e:
                self.logger.error(f"XRay module block break error: {e}")

    @event_handler
    def on_block_place(self, event: BlockPlaceEvent):
        """Route block place events to scaffold module."""
        module = self._modules.get("scaffold")
        if module and module.running:
            try:
                module.on_block_place(event)
            except Exception as e:
                self.logger.error(f"Scaffold module block place error: {e}")

    @event_handler
    def on_gamemode_change(self, event: PlayerGameModeChangeEvent):
        """Route gamemode change events."""
        module = self._modules.get("gamemode")
        if module and module.running:
            try:
                module.on_gamemode_change(event)
            except Exception as e:
                self.logger.error(f"GameMode module error: {e}")

    @event_handler
    def on_packet_receive(self, event: PacketReceiveEvent):
        """Route incoming packets to packet-related modules."""
        for module_name in ("ratelimit", "packetmonitor"):
            module = self._modules.get(module_name)
            if module and module.running:
                try:
                    module.on_packet(event)
                except Exception as e:
                    self.logger.error(f"Module {module_name} packet handler error: {e}")

    # ─── Utility Methods ────────────────────────────────────────

    def is_player_jumping(self, player) -> bool:
        """Check if a player recently jumped (via PlayerJumpEvent tracking)."""
        return self._player_jump_flags.get(str(player.unique_id), False)

    def is_player_climbing(self, player) -> bool:
        """
        Infer if a player is climbing by checking the block at their position.

        Climbable blocks: ladder, vine, twisting_vines, weeping_vines,
        cave_vines, scaffolding.
        """
        try:
            loc = player.location
            block = player.dimension.get_block(
                int(loc.x), int(loc.y), int(loc.z)
            )
            if block:
                block_type = str(block.type).lower()
                climbable = {"ladder", "vine", "twisting_vines", "weeping_vines",
                             "cave_vines", "cave_vines_body_with_berries",
                             "cave_vines_head_with_berries", "scaffolding"}
                return any(c in block_type for c in climbable)
        except Exception:
            pass
        return False

    def is_player_frozen(self, player) -> bool:
        """Check if a player is frozen."""
        return str(player.unique_id) in self._frozen_players

    def send_to_level4(self, message: str):
        """Send a message to all Level 4 security clearance players."""
        for player in self.server.online_players:
            if self.security.is_level4(player):
                player.send_message(message)
