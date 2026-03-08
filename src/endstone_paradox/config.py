# config.py - Configuration loader for Paradox AntiCheat
# Uses TOML format for config file. Python 3.11+ has tomllib built in.

import uuid
from pathlib import Path
from typing import Any, Dict

# TOML reading: Python 3.11+ has tomllib, older versions need tomli
try:
    import tomllib  # Python 3.11+
    HAS_TOML_READ = True
except ImportError:
    try:
        import tomli as tomllib  # pip install tomli
        HAS_TOML_READ = True
    except ImportError:
        HAS_TOML_READ = False


DEFAULT_CONFIG = {
    "web_ui": {
        "enabled": True,
        "port": 8080,
        "host": "0.0.0.0",
        "secret_key": "",  # auto-generated
    },
    "database": {
        "mode": "internal",  # "internal" or "external"
        "external": {
            "type": "mysql",  # "mysql" or "postgresql"
            "host": "localhost",
            "port": 3306,
            "name": "paradox",
            "user": "paradox",
            "password": "",
        },
    },
    "global_database": {
        "enabled": True,
        "api_url": "",               # Auto-resolved if empty (official endpoint)
        "api_key": "",               # Auto-populated on first connect
        "server_name": "",           # Auto-set to hostname if empty
        "sync_interval": 300,
        # Intelligence Network
        "share_fingerprints": True,  # Push fingerprint hashes to the network
        "share_telemetry": True,     # Push violation/behavioral stats
        "auto_tune": False,          # Auto-apply crowd-sourced thresholds
    },
    "modules": {
        # Movement Detection
        "fly": {"enabled": True, "sensitivity": 5},
        "noclip": {"enabled": True, "sensitivity": 5},
        "waterwalk": {"enabled": True, "sensitivity": 5},
        "stephack": {"enabled": True, "sensitivity": 5},
        "timer": {"enabled": True, "sensitivity": 5},
        "blink": {"enabled": True, "sensitivity": 5},
        # Combat Detection
        "killaura": {"enabled": True, "sensitivity": 5},
        "reach": {"enabled": True, "sensitivity": 5},
        "autoclicker": {"enabled": True, "sensitivity": 5},
        "antikb": {"enabled": True, "sensitivity": 5},
        "criticals": {"enabled": True, "sensitivity": 5},
        "wallhit": {"enabled": True, "sensitivity": 5},
        "triggerbot": {"enabled": True, "sensitivity": 5},
        "vision": {"enabled": True, "sensitivity": 5},
        # Mining / Building
        "scaffold": {"enabled": True, "sensitivity": 5},
        "xray": {"enabled": True, "sensitivity": 5},
        # Player Validation
        "gamemode": {"enabled": True, "sensitivity": 5},
        "namespoof": {"enabled": True, "sensitivity": 5},
        "selfinfliction": {"enabled": True, "sensitivity": 5},
        "skinguard": {"enabled": True, "sensitivity": 5},
        "illegalitems": {"enabled": True, "sensitivity": 5},
        # Server Management
        "afk": {"enabled": True, "sensitivity": 5},
        "worldborder": {"enabled": True, "sensitivity": 5},
        "lagclear": {"enabled": True, "sensitivity": 5},
        "pvp": {"enabled": True, "sensitivity": 5},
        # Advanced (off by default — need tuning)
        "ratelimit": {"enabled": False, "sensitivity": 5},
        "packetmonitor": {"enabled": False, "sensitivity": 5},
        "containersee": {"enabled": False, "sensitivity": 5},
        "antidupe": {"enabled": False, "sensitivity": 5},
        "crashdrop": {"enabled": False, "sensitivity": 5},
        "invsync": {"enabled": False, "sensitivity": 5},
        # Tier 2
        "discord": {"enabled": True, "sensitivity": 5},
        "chatprotection": {"enabled": True, "sensitivity": 5},
        "antigrief": {"enabled": True, "sensitivity": 5},
        "evidencereplay": {"enabled": True, "sensitivity": 5},
        # Tier 3 (off by default — need per-server tuning)
        "adaptivecheck": {"enabled": False, "sensitivity": 5},
        "botdetection": {"enabled": False, "sensitivity": 5},
        "reportsystem": {"enabled": False, "sensitivity": 5},
        "fingerprint": {"enabled": False, "sensitivity": 5},
    },
    "discord": {
        "webhook_url": "",
        "min_severity": 3,
        "send_bans": True,
        "send_kicks": True,
        "footer_text": "Paradox AntiCheat",
    },
    "chatprotection": {
        "anti_spam": True,
        "anti_ads": True,
        "anti_swear": True,
        "caps_limit": True,
        "caps_threshold": 70,
        "cmd_throttle": True,
        "max_cmds_per_sec": 3,
    },
    "antigrief": {
        "break_limit": 45,
        "break_window": 3,
        "place_limit": 40,
        "place_window": 3,
        "log_explosions": True,
    },
}


def _toml_dumps(data: dict, indent: int = 0) -> str:
    """Serialize a dict to TOML format."""
    lines = []
    tables = []    # nested tables go after simple keys

    for key, value in data.items():
        if isinstance(value, dict):
            tables.append((key, value))
        elif isinstance(value, bool):
            lines.append(f"{key} = {'true' if value else 'false'}")
        elif isinstance(value, int):
            lines.append(f"{key} = {value}")
        elif isinstance(value, str):
            lines.append(f'{key} = "{value}"')
        else:
            lines.append(f'{key} = "{value}"')

    result = "\n".join(lines)

    for table_key, table_val in tables:
        result += f"\n\n[{table_key}]\n"
        # Handle nested tables (one level deep)
        sub_tables = []
        for k, v in table_val.items():
            if isinstance(v, dict):
                sub_tables.append((k, v))
            elif isinstance(v, bool):
                result += f"{k} = {'true' if v else 'false'}\n"
            elif isinstance(v, int):
                result += f"{k} = {v}\n"
            elif isinstance(v, str):
                result += f'{k} = "{v}"\n'
            else:
                result += f'{k} = "{v}"\n'

        for sub_key, sub_val in sub_tables:
            result += f"\n[{table_key}.{sub_key}]\n"
            for k, v in sub_val.items():
                if isinstance(v, bool):
                    result += f"{k} = {'true' if v else 'false'}\n"
                elif isinstance(v, int):
                    result += f"{k} = {v}\n"
                elif isinstance(v, str):
                    result += f'{k} = "{v}"\n'
                else:
                    result += f'{k} = "{v}"\n'

    return result.strip() + "\n"


def _simple_toml_parse(raw: str) -> dict:
    """Minimal TOML parser for when tomllib is not available."""
    config = {}
    current_section = None

    for line in raw.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Table header: [section] or [section.subsection]
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped[1:-1].strip()
            # Ensure nested path exists
            parts = current_section.split(".")
            d = config
            for p in parts:
                if p not in d:
                    d[p] = {}
                d = d[p]
            continue

        if "=" in stripped:
            key, val = stripped.split("=", 1)
            key = key.strip()
            val = val.strip()

            # Strip inline comments
            if " #" in val:
                val = val[:val.index(" #")].strip()

            # Parse value types
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.lower() == "true":
                val = True
            elif val.lower() == "false":
                val = False
            elif val.isdigit():
                val = int(val)

            # Set value in the right section
            if current_section:
                parts = current_section.split(".")
                d = config
                for p in parts:
                    d = d.setdefault(p, {})
                d[key] = val
            else:
                config[key] = val

    return config


class ParadoxConfig:
    """Loads and manages config.toml for Paradox AntiCheat."""

    def __init__(self, data_folder: Path, logger=None):
        self._path = data_folder / "config.toml"
        self._logger = logger
        self._config = {}
        self._load()

    def _load(self):
        """Load config from file, creating defaults if needed."""
        if self._path.exists():
            try:
                raw = self._path.read_bytes()
                if HAS_TOML_READ:
                    self._config = tomllib.loads(raw.decode("utf-8"))
                else:
                    self._config = _simple_toml_parse(raw.decode("utf-8"))
            except Exception as e:
                if self._logger:
                    self._logger.error(f"Failed to load config: {e}")
                self._config = {}

        # Merge defaults for any missing keys
        self._config = self._deep_merge(DEFAULT_CONFIG, self._config)

        # Auto-generate secret key if empty
        if not self._config["web_ui"]["secret_key"]:
            self._config["web_ui"]["secret_key"] = str(uuid.uuid4())

        self._save()

    def _save(self):
        """Write config back to file."""
        try:
            content = _toml_dumps(self._config)
            self._path.write_text(content, encoding="utf-8")
        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to save config: {e}")

    def get(self, *keys, default=None) -> Any:
        """Get a nested config value. e.g. config.get('web_ui', 'port')"""
        d = self._config
        for k in keys:
            if isinstance(d, dict):
                d = d.get(k)
            else:
                return default
            if d is None:
                return default
        return d

    def set(self, *keys_and_value):
        """Set a nested config value. Last arg is the value."""
        if len(keys_and_value) < 2:
            return
        keys = keys_and_value[:-1]
        value = keys_and_value[-1]

        d = self._config
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value
        self._save()

    @property
    def raw(self) -> Dict:
        return self._config

    def reload(self):
        """Reload config from disk."""
        self._load()

    @staticmethod
    def _deep_merge(defaults: dict, overrides: dict) -> dict:
        """Deep merge overrides into defaults."""
        result = dict(defaults)
        for k, v in overrides.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = ParadoxConfig._deep_merge(result[k], v)
            else:
                result[k] = v
        return result
