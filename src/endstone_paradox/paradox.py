# paradox.py - Main entry point for Paradox AntiCheat
# Ported from Visual1mpact's original JS version to Endstone/Python

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
    PlayerTeleportEvent,
    PlayerDeathEvent,
    PlayerInteractEvent,
)

from endstone_paradox.database import ParadoxDatabase
from endstone_paradox.security import SecurityManager, SecurityClearance
from endstone_paradox.config import ParadoxConfig
from endstone_paradox.core.violation_engine import ViolationEngine, EnforcementMode


class ParadoxPlugin(Plugin):
    api_version = "0.11"

    commands = {
        # --- Moderation ---
        "ac-op": {"description": "Authenticate with password to gain security clearance", "usages": ["/ac-op [password: message]"], "permissions": ["paradox.op"]},
        "ac-deop": {"description": "Revoke your or another player's security clearance", "usages": ["/ac-deop [player: player]"], "permissions": ["paradox.deop"]},
        "ac-ban": {"description": "Ban a player with an optional reason", "usages": ["/ac-ban <player: player> [reason: message]"], "permissions": ["paradox.ban"]},
        "ac-unban": {"description": "Unban a player by name", "usages": ["/ac-unban <name: message>"], "permissions": ["paradox.unban"]},
        "ac-kick": {"description": "Kick a player from the server with an optional reason", "usages": ["/ac-kick <player: player> [reason: message]"], "permissions": ["paradox.kick"]},
        "ac-freeze": {"description": "Freeze or unfreeze a player in place", "usages": ["/ac-freeze <player: player>"], "permissions": ["paradox.freeze"]},
        "ac-vanish": {"description": "Toggle invisibility - hide from all players", "usages": ["/ac-vanish"], "permissions": ["paradox.vanish"]},
        "ac-lockdown": {"description": "Toggle server lockdown, or set lockdown level (1=L4 only, 2=L4+L3)", "usages": ["/ac-lockdown [level: int]"], "permissions": ["paradox.lockdown"]},
        "ac-punish": {"description": "Punish a player (warn/mute/kick/ban)", "usages": ["/ac-punish <player: player> [action: message]"], "permissions": ["paradox.punish"]},
        "ac-tpa": {"description": "Send a teleport request to another player", "usages": ["/ac-tpa <player: player>"], "permissions": ["paradox.tpa"]},
        "ac-allowlist": {"description": "Manage allow list: add/remove/list players", "usages": ["/ac-allowlist [args: message]"], "permissions": ["paradox.allowlist"]},
        "ac-whitelist": {"description": "Manage whitelist: add/remove/list players", "usages": ["/ac-whitelist [args: message]"], "permissions": ["paradox.whitelist"]},
        "ac-opsec": {"description": "View security dashboard with admin clearance levels", "usages": ["/ac-opsec"], "permissions": ["paradox.opsec"]},
        "ac-despawn": {"description": "Despawn entities by type within radius", "usages": ["/ac-despawn [args: message]"], "permissions": ["paradox.despawn"]},
        "ac-modules": {"description": "View all detection modules and their on/off status", "usages": ["/ac-modules"], "permissions": ["paradox.modules"]},
        "ac-spooflog": {"description": "View log of detected name spoofing attempts", "usages": ["/ac-spooflog"], "permissions": ["paradox.spooflog"]},
        "ac-command": {"description": "Enable or disable a Paradox command", "usages": ["/ac-command [args: message]"], "permissions": ["paradox.command"]},
        "ac-prefix": {"description": "Change the Paradox chat prefix display", "usages": ["/ac-prefix [prefix: message]"], "permissions": ["paradox.prefix"]},
        # --- Detection toggles ---
        "ac-fly": {"description": "Toggle fly/hover hack detection on or off", "usages": ["/ac-fly"], "permissions": ["paradox.settings"]},
        "ac-killaura": {"description": "Toggle kill aura detection on or off", "usages": ["/ac-killaura"], "permissions": ["paradox.settings"]},
        "ac-reach": {"description": "Toggle reach hack detection on or off", "usages": ["/ac-reach"], "permissions": ["paradox.settings"]},
        "ac-autoclicker": {"description": "Toggle autoclicker detection, optionally set max CPS", "usages": ["/ac-autoclicker [maxcps: int]"], "permissions": ["paradox.settings"]},
        "ac-scaffold": {"description": "Toggle scaffold/fast-bridge detection on or off", "usages": ["/ac-scaffold"], "permissions": ["paradox.settings"]},
        "ac-xray": {"description": "Toggle X-ray mining detection on or off", "usages": ["/ac-xray"], "permissions": ["paradox.settings"]},
        "ac-gamemode": {"description": "Toggle illegal gamemode change detection on or off", "usages": ["/ac-gamemode"], "permissions": ["paradox.settings"]},
        "ac-afk": {"description": "Toggle AFK detection, optionally set timeout in seconds", "usages": ["/ac-afk [timeout: int]"], "permissions": ["paradox.settings"]},
        "ac-vision": {"description": "Toggle aimbot/snap detection on or off", "usages": ["/ac-vision"], "permissions": ["paradox.settings"]},
        "ac-worldborder": {"description": "Set world border radius and center position", "usages": ["/ac-worldborder [args: message]"], "permissions": ["paradox.settings"]},
        "ac-lagclear": {"description": "Toggle periodic entity clearing, optionally set interval", "usages": ["/ac-lagclear [interval: int]"], "permissions": ["paradox.settings"]},
        "ac-ratelimit": {"description": "Toggle packet rate limiting on or off", "usages": ["/ac-ratelimit"], "permissions": ["paradox.settings"]},
        "ac-namespoof": {"description": "Toggle name spoofing detection on or off", "usages": ["/ac-namespoof"], "permissions": ["paradox.settings"]},
        "ac-packetmonitor": {"description": "Toggle packet spam monitoring on or off", "usages": ["/ac-packetmonitor"], "permissions": ["paradox.settings"]},
        "ac-containersee": {"description": "Toggle container vision for admins (see contents by looking)", "usages": ["/ac-containersee"], "permissions": ["paradox.settings"]},
        "ac-skinguard": {"description": "Toggle skin validation (blocks 4D/tiny/invisible skins)", "usages": ["/ac-skinguard"], "permissions": ["paradox.settings"]},
        "ac-noclip": {"description": "Toggle noclip hack detection on or off", "usages": ["/ac-noclip"], "permissions": ["paradox.settings"]},
        "ac-waterwalk": {"description": "Toggle water-walk hack detection on or off", "usages": ["/ac-waterwalk"], "permissions": ["paradox.settings"]},
        "ac-stephack": {"description": "Toggle step-hack detection on or off", "usages": ["/ac-stephack"], "permissions": ["paradox.settings"]},
        "ac-timer": {"description": "Toggle timer hack detection on or off", "usages": ["/ac-timer"], "permissions": ["paradox.settings"]},
        "ac-blink": {"description": "Toggle blink/teleport hack detection on or off", "usages": ["/ac-blink"], "permissions": ["paradox.settings"]},
        "ac-antikb": {"description": "Toggle anti-knockback detection on or off", "usages": ["/ac-antikb"], "permissions": ["paradox.settings"]},
        "ac-criticals": {"description": "Toggle criticals hack detection on or off", "usages": ["/ac-criticals"], "permissions": ["paradox.settings"]},
        "ac-wallhit": {"description": "Toggle wall-hit detection on or off", "usages": ["/ac-wallhit"], "permissions": ["paradox.settings"]},
        "ac-triggerbot": {"description": "Toggle triggerbot detection on or off", "usages": ["/ac-triggerbot"], "permissions": ["paradox.settings"]},
        "ac-illegalitems": {"description": "Toggle illegal item detection on or off", "usages": ["/ac-illegalitems"], "permissions": ["paradox.settings"]},
        "ac-selfinfliction": {"description": "Toggle self-infliction detection on or off", "usages": ["/ac-selfinfliction"], "permissions": ["paradox.settings"]},
        "ac-pvptoggle": {"description": "Toggle PvP module on or off", "usages": ["/ac-pvptoggle"], "permissions": ["paradox.settings"]},
        "ac-antidupe": {"description": "Toggle anti-dupe detection on or off", "usages": ["/ac-antidupe"], "permissions": ["paradox.settings"]},
        "ac-crashdrop": {"description": "Toggle crash-drop prevention on or off", "usages": ["/ac-crashdrop"], "permissions": ["paradox.settings"]},
        "ac-invsync": {"description": "Toggle inventory sync module on or off", "usages": ["/ac-invsync"], "permissions": ["paradox.settings"]},
        "ac-discord": {"description": "Toggle Discord webhook integration on or off", "usages": ["/ac-discord"], "permissions": ["paradox.settings"]},
        "ac-chatprotection": {"description": "Toggle chat protection (spam/ads/swear filter) on or off", "usages": ["/ac-chatprotection"], "permissions": ["paradox.settings"]},
        "ac-antigrief": {"description": "Toggle anti-grief (nuke/rapid place detection) on or off", "usages": ["/ac-antigrief"], "permissions": ["paradox.settings"]},
        "ac-evidencereplay": {"description": "Toggle evidence replay system on or off", "usages": ["/ac-evidencereplay"], "permissions": ["paradox.settings"]},
        # --- Tier 3 toggles ---
        "ac-adaptivecheck": {"description": "Toggle adaptive check frequency on or off", "usages": ["/ac-adaptivecheck"], "permissions": ["paradox.settings"]},
        "ac-botdetection": {"description": "Toggle bot detection on or off", "usages": ["/ac-botdetection"], "permissions": ["paradox.settings"]},
        "ac-reportsystem": {"description": "Toggle player report system on or off", "usages": ["/ac-reportsystem"], "permissions": ["paradox.settings"]},
        "ac-fingerprint": {"description": "Toggle session fingerprinting on or off", "usages": ["/ac-fingerprint"], "permissions": ["paradox.settings"]},
        # --- Utility ---
        "ac-home": {"description": "Manage homes: set/delete/list or teleport by name", "usages": ["/ac-home [args: message]"], "permissions": ["paradox.home"]},
        "ac-tpr": {"description": "Teleport to a random location, optionally set radius", "usages": ["/ac-tpr [radius: int]"], "permissions": ["paradox.tpr"]},
        "ac-invsee": {"description": "View another player's inventory contents", "usages": ["/ac-invsee <player: player>"], "permissions": ["paradox.invsee"]},
        "ac-pvp": {"description": "Toggle PvP: use alone or with global/status/help", "usages": ["/ac-pvp [args: message]"], "permissions": ["paradox.pvp"]},
        "ac-channels": {"description": "Private chat: create/join/leave/list/send channels", "usages": ["/ac-channels [args: message]"], "permissions": ["paradox.channels"]},
        "ac-rank": {"description": "Set or view a player's display rank", "usages": ["/ac-rank <player: player> [rank: message]"], "permissions": ["paradox.rank"]},
        "ac-debug-db": {"description": "Inspect or modify the Paradox database directly", "usages": ["/ac-debug-db [args: message]"], "permissions": ["paradox.debugdb"]},
        "ac-gui": {"description": "Open the Paradox admin GUI menu", "usages": ["/ac-gui"], "permissions": ["paradox.gui"]},
        "ac-report": {"description": "Report a player for suspicious behavior", "usages": ["/ac-report <player: player> [reason: message]"], "permissions": ["paradox.report"]},
        "ac-about": {"description": "View Paradox AntiCheat version and info", "usages": ["/ac-about"], "permissions": ["paradox.about"]},
        # --- Violation Engine ---
        "ac-case": {"description": "View violation evidence for a player", "usages": ["/ac-case <player: player> [count: int]"], "permissions": ["paradox.case"]},
        "ac-watch": {"description": "Stream violations for a player in real-time", "usages": ["/ac-watch <player: player> [minutes: int]"], "permissions": ["paradox.watch"]},
        "ac-mode": {"description": "Set enforcement mode: logonly, soft, or hard", "usages": ["/ac-mode <mode: message>"], "permissions": ["paradox.mode"]},
        "ac-exempt": {"description": "Temporarily exempt a player from a module", "usages": ["/ac-exempt <player: player> [args: message]"], "permissions": ["paradox.exempt"]},
    }

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
        "paradox.report": {"description": "Use /ac-report command", "default": True},
        "paradox.case": {"description": "Use /ac-case command", "default": "op"},
        "paradox.watch": {"description": "Use /ac-watch command", "default": "op"},
        "paradox.mode": {"description": "Use /ac-mode command", "default": "op"},
        "paradox.exempt": {"description": "Use /ac-exempt command", "default": "op"},
    }

    def __init__(self):
        super().__init__()
        self.db: ParadoxDatabase = None
        self.security: SecurityManager = None
        self.paradox_config: ParadoxConfig = None
        self._web_server = None

        self._modules = {}        # loaded module instances
        self._module_tasks = {}

        self._player_jump_flags = {}   # uuid -> recently jumped?
        self._frozen_players = set()
        self._vanished_players = set()
        self._lockdown_active = False
        self._lockdown_level = 1       # 1 = L4 only, 2 = L4+L3

        self._command_handlers = {}

        # Violation engine (initialized in on_enable)
        self.violation_engine: ViolationEngine = None

        # Player baseline (initialized in on_enable)
        self.player_baseline = None

        # Analytics collector (initialized in on_enable)
        self.analytics_collector = None

        # Global API client (initialized in on_enable)
        self._global_api = None

    # -------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------

    def on_enable(self):
        # startup banner
        self.logger.info("")
        self.logger.info("§2════════════════════════════════════════════════════════")
        self.logger.info("")
        self.logger.info("  §f§l ██████   █████  ██████   █████  ██████   ██████  ██   ██")
        self.logger.info("  §f§l ██   ██ ██   ██ ██   ██ ██   ██ ██   ██ ██    ██  ██ ██")
        self.logger.info("  §f§l ██████  ███████ ██████  ███████ ██   ██ ██    ██   ███")
        self.logger.info("  §f§l ██      ██   ██ ██   ██ ██   ██ ██   ██ ██    ██  ██ ██")
        self.logger.info("  §f§l ██      ██   ██ ██   ██ ██   ██ ██████   ██████  ██   ██")
        self.logger.info("")
        self.logger.info("  §7AntiCheat §ev1.9.0")
        self.logger.info("  §7Designed by §fVisual1mpact")
        self.logger.info("  §7Ported to Endstone by §a§lTheN1NJ4LL0")
        self.logger.info("")
        self.logger.info("§2════════════════════════════════════════════════════════")
        self.logger.info("")

        data_folder = Path(self.data_folder)
        self.paradox_config = ParadoxConfig(data_folder, self.logger)
        self.db = ParadoxDatabase(data_folder, self.logger)
        self.security = SecurityManager(self.db)

        self._lockdown_active = self.db.get("config", "lockdown", False)
        self._lockdown_level = self.db.get("config", "lockdown_level", 1)

        # restore frozen/vanished from last session
        frozen = self.db.get_all("frozen_players")
        self._frozen_players = set(frozen.keys())
        vanished = self.db.get_all("vanished_players")
        self._vanished_players = set(vanished.keys())

        self._register_command_handlers()
        self.register_events(self)
        self._init_modules()

        # Init violation engine
        self.violation_engine = ViolationEngine(self)

        # Init player baseline
        from endstone_paradox.core.player_baseline import PlayerBaseline
        self.player_baseline = PlayerBaseline(self.db, self.logger)

        # Init analytics collector
        from endstone_paradox.core.analytics_collector import AnalyticsCollector
        self.analytics_collector = AnalyticsCollector(self.db, self.logger)

        # Hook Discord, Evidence Replay, and Analytics into the violation engine
        self._hook_violation_engine()

        # Periodic flush task (every 30s = 600 ticks)
        def _flush_violations():
            if self.violation_engine:
                self.violation_engine.maybe_flush()
            if self.player_baseline:
                self.player_baseline.flush()
            if self.analytics_collector:
                self.analytics_collector.flush()
            self.server.scheduler.run_task(self, _flush_violations, delay=600)
        self.server.scheduler.run_task(self, _flush_violations, delay=600)

        # Start web UI
        if self.paradox_config.get("web_ui", "enabled", default=True):
            try:
                from endstone_paradox.web.server import ParadoxWebServer
                self._web_server = ParadoxWebServer(
                    self.db.db_path, self.paradox_config, self.logger
                )
                self._web_server.start()
            except Exception as e:
                self.logger.warning(f"§2[§7Paradox§2]§e Web UI failed to start: {e}")

        # Start Global Ban API client
        if self.paradox_config.get("global_database", "enabled", default=False):
            try:
                from endstone_paradox.global_api import GlobalAPIClient
                self._global_api = GlobalAPIClient(self)
                self._global_api.start()
            except Exception as e:
                self.logger.warning(f"§2[§7Paradox§2]§e Global API client failed to start: {e}")

        self.logger.info("§2[§7Paradox§2]§a Loaded successfully!")
        self.logger.info(f"§2[§7Paradox§2]§7 Database: {self.db._db_path}")
        self.logger.info(f"§2[§7Paradox§2]§7 Modules loaded: {len(self._modules)}")

    def on_disable(self):
        self.logger.info("§2[§7Paradox§2]§r Shutting down Paradox AntiCheat...")

        # Stop web server
        if self._web_server:
            try:
                self._web_server.stop()
            except Exception:
                pass
            self._web_server = None

        for name, module in self._modules.items():
            try:
                module.stop()
            except Exception as e:
                self.logger.error(f"Error stopping module {name}: {e}")

        if self.db:
            # Final flush of violation evidence and analytics
            if self.violation_engine:
                self.violation_engine.flush()
            if self.analytics_collector:
                self.analytics_collector.flush()
            self.db.close()

        # Stop global API client
        if self._global_api:
            try:
                self._global_api.stop()
            except Exception:
                pass
            self._global_api = None

        self.logger.info("§2[§7Paradox§2]§c Paradox AntiCheat disabled.")

    # -------------------------------------------------------------------
    # Module init
    # -------------------------------------------------------------------

    def _init_modules(self):
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
        from endstone_paradox.modules.containersee import ContainerSeeModule
        from endstone_paradox.modules.antidupe import AntiDupeModule
        from endstone_paradox.modules.crashdrop import CrashDropModule
        from endstone_paradox.modules.invsync import InvSyncModule
        from endstone_paradox.modules.skinguard import SkinGuardModule
        from endstone_paradox.modules.noclip import NoClipModule
        from endstone_paradox.modules.waterwalk import WaterWalkModule
        from endstone_paradox.modules.stephack import StepHackModule
        from endstone_paradox.modules.timer import TimerModule
        from endstone_paradox.modules.blink import BlinkModule
        from endstone_paradox.modules.antikb import AntiKBModule
        from endstone_paradox.modules.criticals import CriticalsModule
        from endstone_paradox.modules.wallhit import WallHitModule
        from endstone_paradox.modules.triggerbot import TriggerBotModule
        from endstone_paradox.modules.illegal_items import IllegalItemsModule
        from endstone_paradox.modules.discord_webhook import DiscordWebhookModule
        from endstone_paradox.modules.chat_protection import ChatProtectionModule
        from endstone_paradox.modules.antigrief import AntiGriefModule
        from endstone_paradox.modules.evidence_replay import EvidenceReplayModule
        # Tier 3
        from endstone_paradox.modules.adaptive_check import AdaptiveCheckModule
        from endstone_paradox.modules.bot_detection import BotDetectionModule
        from endstone_paradox.modules.report_system import ReportSystemModule
        from endstone_paradox.modules.session_fingerprint import SessionFingerprintModule
        
        # Ported V6 Modules
        from endstone_paradox.modules.aimbot_monitor import AimbotMonitorModule
        from endstone_paradox.modules.anticrash import AntiCrashModule
        from endstone_paradox.modules.autototem import AutoTotemModule
        from endstone_paradox.modules.container_lock import ContainerLockModule
        from endstone_paradox.modules.death_coords import DeathCoordsModule
        from endstone_paradox.modules.dimension_lock import DimensionLockModule
        from endstone_paradox.modules.pathing_monitor import PathingMonitorModule

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
            "containersee": ContainerSeeModule,
            "antidupe": AntiDupeModule,
            "crashdrop": CrashDropModule,
            "invsync": InvSyncModule,
            "skinguard": SkinGuardModule,
            "noclip": NoClipModule,
            "waterwalk": WaterWalkModule,
            "stephack": StepHackModule,
            "timer": TimerModule,
            "blink": BlinkModule,
            "antikb": AntiKBModule,
            "criticals": CriticalsModule,
            "wallhit": WallHitModule,
            "triggerbot": TriggerBotModule,
            "illegalitems": IllegalItemsModule,
            "discord": DiscordWebhookModule,
            "chatprotection": ChatProtectionModule,
            "antigrief": AntiGriefModule,
            "evidencereplay": EvidenceReplayModule,
            # Tier 3
            "adaptivecheck": AdaptiveCheckModule,
            "botdetection": BotDetectionModule,
            "reportsystem": ReportSystemModule,
            "fingerprint": SessionFingerprintModule,
            "aimbotmonitor": AimbotMonitorModule,
            "anticrash": AntiCrashModule,
            "autototem": AutoTotemModule,
            "containerlock": ContainerLockModule,
            "deathcoords": DeathCoordsModule,
            "dimensionlock": DimensionLockModule,
            "pathingmonitor": PathingMonitorModule,
        }

        # these are off by default since they need tuning per-server
        default_off = {"ratelimit", "packetmonitor", "containersee", "antidupe", "crashdrop", "invsync",
                        "discord", "chatprotection", "antigrief", "evidencereplay",
                        "adaptivecheck", "botdetection", "reportsystem", "fingerprint",
                        "containerlock", "dimensionlock"}

        for name, cls in module_classes.items():
            try:
                module = cls(self)
                self._modules[name] = module
                default_state = name not in default_off
                enabled = self.db.get("modules", name, default_state)
                if enabled:
                    module.start()
                    self.logger.info(f"  §2[§7Paradox§2]§a Module '{name}' started")
                else:
                    self.logger.info(f"  §2[§7Paradox§2]§7 Module '{name}' disabled")
            except Exception as e:
                self.logger.error(f"  §2[§7Paradox§2]§c Failed to init module '{name}': {e}")

        # Hook Discord + Evidence Replay into the violation engine
        if hasattr(self, 'violation_engine') and self.violation_engine:
            self._hook_violation_engine()

    def get_module(self, name: str):
        return self._modules.get(name)

    def is_module_enabled(self, name: str) -> bool:
        module = self._modules.get(name)
        return module is not None and module.running

    def toggle_module(self, name: str) -> bool:
        """Toggle a module on/off, returns the new state."""
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

    # -------------------------------------------------------------------
    # Command routing
    # -------------------------------------------------------------------

    def _register_command_handlers(self):
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

        from endstone_paradox.commands.violation.case_cmd import handle_case
        from endstone_paradox.commands.violation.watch_cmd import handle_watch
        from endstone_paradox.commands.violation.mode_cmd import handle_mode
        from endstone_paradox.commands.violation.exempt_cmd import handle_exempt

        # moderation
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

        # all detection toggles share one handler
        # We create a closure that captures cmd so handle_toggle gets cmd_name
        for cmd in [
            "ac-fly", "ac-killaura", "ac-reach", "ac-autoclicker",
            "ac-scaffold", "ac-xray", "ac-gamemode", "ac-afk",
            "ac-vision", "ac-worldborder", "ac-lagclear", "ac-ratelimit",
            "ac-namespoof", "ac-packetmonitor", "ac-containersee",
            # Tier 1
            "ac-skinguard", "ac-noclip", "ac-waterwalk", "ac-stephack",
            "ac-timer", "ac-blink", "ac-antikb", "ac-criticals",
            "ac-wallhit", "ac-triggerbot", "ac-illegalitems",
            "ac-selfinfliction", "ac-pvptoggle", "ac-antidupe", "ac-crashdrop", "ac-invsync",
            # Tier 2
            "ac-discord", "ac-chatprotection", "ac-antigrief", "ac-evidencereplay",
            # Tier 3
            "ac-adaptivecheck", "ac-botdetection", "ac-reportsystem", "ac-fingerprint",
            # New V6 Modules
            "ac-aimbotmonitor", "ac-anticrash", "ac-autototem", "ac-containerlock",
            "ac-deathcoords", "ac-dimensionlock", "ac-pathingmonitor",
        ]:
            self._command_handlers[cmd] = handle_toggle

        # utility
        self._command_handlers["ac-home"] = handle_home
        self._command_handlers["ac-tpr"] = handle_tpr
        self._command_handlers["ac-invsee"] = handle_invsee
        self._command_handlers["ac-pvp"] = handle_pvp
        self._command_handlers["ac-channels"] = handle_channels
        self._command_handlers["ac-rank"] = handle_rank
        self._command_handlers["ac-debug-db"] = handle_debug_db
        self._command_handlers["ac-gui"] = handle_gui
        self._command_handlers["ac-about"] = handle_about

        # Tier 3 - report command
        from endstone_paradox.commands.utility.report_cmd import handle_report
        self._command_handlers["ac-report"] = handle_report

        # violation engine
        self._command_handlers["ac-case"] = handle_case
        self._command_handlers["ac-watch"] = handle_watch
        self._command_handlers["ac-mode"] = handle_mode
        self._command_handlers["ac-exempt"] = handle_exempt

    def on_command(self, sender, command, args) -> bool:
        from endstone import Player
        cmd_name = command.name

        handler = self._command_handlers.get(cmd_name)
        if handler is None:
            sender.send_message("§2[§7Paradox§2]§c Unknown command.")
            return False

        # disabled?
        if self.db.has("disabled_commands", cmd_name):
            sender.send_message("§2[§7Paradox§2]§c This command is currently disabled.")
            return False

        is_player = isinstance(sender, Player)

        if is_player:
            # clearance check (ac-op always accessible for obvious reasons)
            if cmd_name != "ac-op":
                required = self._get_required_clearance(cmd_name)
                if not self.security.has_clearance(sender, required):
                    sender.send_message("§2[§7Paradox§2]§c Insufficient security clearance.")
                    return False

            # lockdown: restrict commands based on lockdown level
            if self._lockdown_active and cmd_name != "ac-lockdown":
                from endstone_paradox.commands.moderation.lockdown_cmd import _player_meets_lockdown
                if not _player_meets_lockdown(self, sender):
                    sender.send_message("§2[§7Paradox§2]§c Server is in lockdown mode.")
                    return False

        try:
            try:
                return handler(self, sender, args, cmd_name=cmd_name)
            except TypeError:
                return handler(self, sender, args)
        except Exception as e:
            self.logger.error(f"Error executing {cmd_name}: {e}")
            sender.send_message(f"§2[§7Paradox§2]§c Error: {e}")
            return False

    def _get_required_clearance(self, cmd_name: str) -> SecurityClearance:
        # public (L1) - everyone can use these
        public_commands = {
            "ac-op", "ac-tpa", "ac-home", "ac-tpr", "ac-pvp", "ac-channels",
            "ac-about", "ac-report",
        }
        level2_commands = set()  # placeholder for future expansion
        # L3 - moderator tools
        level3_commands = {
            "ac-kick", "ac-freeze", "ac-vanish", "ac-despawn",
            "ac-invsee", "ac-spooflog", "ac-rank", "ac-case", "ac-watch",
        }
        # everything else -> L4

        if cmd_name in public_commands:
            return SecurityClearance.LEVEL_1
        elif cmd_name in level2_commands:
            return SecurityClearance.LEVEL_2
        elif cmd_name in level3_commands:
            return SecurityClearance.LEVEL_3
        else:
            return SecurityClearance.LEVEL_4

    # -------------------------------------------------------------------
    # Event handlers
    # -------------------------------------------------------------------

    @event_handler
    def on_player_join(self, event: PlayerJoinEvent):
        player = event.player
        uuid_str = str(player.unique_id)

        # global API ban check (synced entries from Global Ban API)
        if self._global_api:
            if not self._global_api.check_player_on_join(player):
                return

        # global ban list check (hardcoded from original Paradox AntiCheat)
        from endstone_paradox.globalban import is_globally_banned
        if is_globally_banned(player.name):
            player.kick("§cYou are globally banned from Paradox AntiCheat!")
            self.logger.info(f"Globally banned player {player.name} attempted to join - kicked.")
            return

        # ban check
        ban_data = self.db.get("bans", uuid_str)
        if ban_data is None:
            ban_data = self.db.get("bans", player.name.lower())  # also try by name
        if ban_data:
            reason = ban_data.get("reason", "Banned by Paradox AntiCheat") if isinstance(ban_data, dict) else "Banned by Paradox AntiCheat"
            player.kick(f"§c{reason}")
            return

        # allowlist = anticheat exemption (for bots, etc.)
        if self.db.count("allowlist") > 0:
            allowed = (self.db.has("allowlist", uuid_str) or
                       self.db.has("allowlist", player.name.lower()) or
                       self.db.has("allowlist", player.name))
            if allowed and self.violation_engine:
                self.violation_engine.add_exemption(uuid_str, "all", 86400 * 365)

        if self._lockdown_active:
            from endstone_paradox.commands.moderation.lockdown_cmd import _player_meets_lockdown
            if not _player_meets_lockdown(self, player):
                player.kick("§cServer is currently in lockdown mode.")
                return

        # update player record
        player_data = self.db.get("players", uuid_str, {})
        if not isinstance(player_data, dict):
            player_data = {}
        player_data["name"] = player.name
        player_data["last_join"] = __import__("time").time()
        self.db.set("players", uuid_str, player_data)

        # skin validation (before module notifications)
        skinguard = self._modules.get("skinguard")
        if skinguard and skinguard.running:
            if not skinguard.check_player(player):
                return  # kicked for invalid skin

        # load player baseline from DB
        if self.player_baseline:
            self.player_baseline.load(uuid_str)

        # notify modules about the join (e.g. invsync)
        for module in self._modules.values():
            try:
                module.on_player_join(player)
            except Exception:
                pass

        # ping L4 admins about the join
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
        player = event.player
        for module in self._modules.values():
            try:
                module.on_player_leave(player)
            except Exception:
                pass
        if self.violation_engine:
            self.violation_engine.on_player_leave(player)
        if self.player_baseline:
            self.player_baseline.on_player_leave(str(player.unique_id))
        self._player_jump_flags.pop(str(player.unique_id), None)

    @event_handler
    def on_player_jump(self, event: PlayerJumpEvent):
        player = event.player
        uuid_str = str(player.unique_id)
        self._player_jump_flags[uuid_str] = True

        # clear after ~1 second
        def clear_jump():
            self._player_jump_flags.pop(uuid_str, None)
        self.server.scheduler.run_task(self, clear_jump, delay=20)

    @event_handler
    def on_player_move(self, event: PlayerMoveEvent):
        player = event.player
        uuid_str = str(player.unique_id)

        if uuid_str in self._frozen_players:
            event.is_cancelled = True
            return

        module = self._modules.get("pathingmonitor")
        if module and module.running:
            try:
                module.on_player_move(event)
            except Exception as e:
                self.logger.error(f"PathingMonitor error: {e}")

    @event_handler
    def on_actor_damage(self, event: ActorDamageEvent):
        for module_name in ("killaura", "reach", "autoclicker", "pvp", "selfinfliction", "vision", "antikb", "criticals", "wallhit", "triggerbot", "botdetection", "aimbotmonitor"):
            module = self._modules.get(module_name)
            if module and module.running:
                try:
                    module.on_damage(event)
                except Exception as e:
                    self.logger.error(f"Module {module_name} damage handler error: {e}")

    @event_handler
    def on_block_break(self, event: BlockBreakEvent):
        module = self._modules.get("xray")
        if module and module.running:
            try:
                module.on_block_break(event)
            except Exception as e:
                self.logger.error(f"XRay module block break error: {e}")

    @event_handler
    def on_block_place(self, event: BlockPlaceEvent):
        for module_name in ("scaffold", "antidupe", "containerlock"):
            module = self._modules.get(module_name)
            if module and module.running:
                try:
                    module.on_block_place(event)
                except Exception as e:
                    self.logger.error(f"{module_name} module block place error: {e}")

    @event_handler
    def on_player_interact(self, event: PlayerInteractEvent):
        module = self._modules.get("containerlock")
        if module and module.running:
            try:
                module.on_player_interact(event)
            except Exception as e:
                self.logger.error(f"ContainerLock module error: {e}")

    @event_handler
    def on_player_death(self, event: PlayerDeathEvent):
        module = self._modules.get("deathcoords")
        if module and module.running:
            try:
                module.on_player_death(event)
            except Exception as e:
                self.logger.error(f"DeathCoords module error: {e}")

    @event_handler
    def on_player_teleport(self, event: PlayerTeleportEvent):
        module = self._modules.get("dimensionlock")
        if module and module.running:
            try:
                module.on_player_teleport(event)
            except Exception as e:
                self.logger.error(f"DimensionLock module error: {e}")

    @event_handler
    def on_gamemode_change(self, event: PlayerGameModeChangeEvent):
        module = self._modules.get("gamemode")
        if module and module.running:
            try:
                module.on_gamemode_change(event)
            except Exception as e:
                self.logger.error(f"GameMode module error: {e}")

    @event_handler
    def on_packet_receive(self, event: PacketReceiveEvent):
        for module_name in ("ratelimit", "packetmonitor", "antidupe", "autoclicker", "timer", "anticrash"):
            module = self._modules.get(module_name)
            if module and module.running:
                try:
                    module.on_packet(event)
                except Exception as e:
                    self.logger.error(f"Module {module_name} packet handler error: {e}")

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------

    def is_player_jumping(self, player) -> bool:
        return self._player_jump_flags.get(str(player.unique_id), False)

    def is_player_climbing(self, player) -> bool:
        """Check block at player pos for climbable blocks (ladders, vines, etc)."""
        try:
            loc = player.location
            block = player.dimension.get_block(int(loc.x), int(loc.y), int(loc.z))
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
        return str(player.unique_id) in self._frozen_players

    def send_to_level4(self, message: str):
        """Broadcast a message to all L4 admins."""
        for player in self.server.online_players:
            if self.security.is_level4(player):
                player.send_message(message)

    # -------------------------------------------------------------------
    # Tier 2 Event Handlers
    # -------------------------------------------------------------------

    @event_handler
    def on_player_chat(self, event: PlayerChatEvent):
        """Route chat events to chat protection module."""
        module = self._modules.get("chatprotection")
        if module and module.running:
            try:
                blocked = module.on_player_chat(event)
                if blocked:
                    event.cancelled = True
            except Exception as e:
                self.logger.error(f"ChatProtection error: {e}")

    @event_handler
    def on_block_break(self, event: BlockBreakEvent):
        """Route block break events to anti-grief module."""
        # Evidence replay: record action
        replay = self._modules.get("evidencereplay")
        if replay and replay.running:
            try:
                uuid_str = str(event.player.unique_id)
                block_type = str(event.block.type) if event.block else ""
                replay.record_action(uuid_str, "breaking", block_type)
            except Exception:
                pass

        module = self._modules.get("antigrief")
        if module and module.running:
            try:
                module.on_block_break(event)
            except Exception as e:
                self.logger.error(f"AntiGrief break error: {e}")

    @event_handler
    def on_block_place(self, event: BlockPlaceEvent):
        """Route block place events to anti-grief and scaffold modules."""
        # Evidence replay: record action
        replay = self._modules.get("evidencereplay")
        if replay and replay.running:
            try:
                uuid_str = str(event.player.unique_id)
                block_type = str(event.block.type) if event.block else ""
                replay.record_action(uuid_str, "placing", block_type)
            except Exception:
                pass

        module = self._modules.get("antigrief")
        if module and module.running:
            try:
                module.on_block_place(event)
            except Exception as e:
                self.logger.error(f"AntiGrief place error: {e}")

    def _hook_violation_engine(self):
        """Hook Discord and Evidence Replay into the violation engine."""
        engine = self.violation_engine
        original_emit = engine.emit_violation

        def hooked_emit(player, module, severity, evidence, action_hint=None):
            original_emit(player, module, severity, evidence, action_hint)

            # Forward to Discord webhook
            discord = self._modules.get("discord")
            if discord and discord.running:
                try:
                    # Resolve the action the engine would take
                    name = player.name if hasattr(player, 'name') else "?"
                    uuid_str = str(player.unique_id) if hasattr(player, 'unique_id') else ""
                    discord.on_violation(name, uuid_str, module, severity,
                                        evidence, action_hint or "warn")
                except Exception:
                    pass

            # Forward to Evidence Replay
            replay = self._modules.get("evidencereplay")
            if replay and replay.running:
                try:
                    replay.on_violation(player, module, severity, evidence)
                except Exception:
                    pass

            # Forward to Analytics Collector (Tier 3)
            if self.analytics_collector:
                try:
                    uuid_str = str(player.unique_id) if hasattr(player, 'unique_id') else ""
                    self.analytics_collector.record_violation(
                        module, severity, action_hint or "warn", uuid_str
                    )
                except Exception:
                    pass

        engine.emit_violation = hooked_emit
