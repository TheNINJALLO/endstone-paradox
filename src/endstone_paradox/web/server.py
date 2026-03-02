# web/server.py - Flask web server for Paradox AntiCheat
# Runs in a daemon thread, shares the same paradox.db.

import json
import sqlite3
import threading
import logging
from pathlib import Path
from functools import wraps

try:
    from flask import (
        Flask, render_template_string, request, redirect,
        url_for, session, jsonify, flash
    )
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False


# Full list of all modules with their default enabled state
ALL_MODULES = {
    "fly": True, "killaura": True, "reach": True, "autoclicker": True,
    "scaffold": True, "xray": True, "gamemode": True, "namespoof": True,
    "afk": True, "worldborder": True, "lagclear": True, "vision": True,
    "selfinfliction": True, "pvp": True, "ratelimit": False,
    "packetmonitor": False, "containersee": False,
}


class ParadoxWebServer:
    """Flask-based web companion for Paradox AntiCheat."""

    def __init__(self, db_path: Path, config, logger=None):
        self._db_path = db_path
        self._config = config
        self._logger = logger
        self._thread = None
        self._app = None

    def start(self):
        if not HAS_FLASK:
            if self._logger:
                self._logger.warning(
                    "§2[§7Paradox§2]§e Flask not installed — web UI disabled. "
                    "Install with: pip install flask"
                )
            return

        port = self._config.get("web_ui", "port", default=8080)
        host = self._config.get("web_ui", "host", default="0.0.0.0")
        secret = self._config.get("web_ui", "secret_key", default="paradox")

        self._app = Flask(__name__)
        self._app.secret_key = secret

        # Suppress Flask request logging
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.WARNING)

        # Store refs on app for route access
        self._app.config["PARADOX_DB_PATH"] = str(self._db_path)
        self._app.config["PARADOX_CONFIG"] = self._config
        self._app.config["PARADOX_SECRET"] = secret

        _register_routes(self._app)

        self._thread = threading.Thread(
            target=self._run_server,
            args=(host, port),
            daemon=True,
            name="ParadoxWebUI",
        )
        self._thread.start()

        if self._logger:
            self._logger.info(
                f"§2[§7Paradox§2]§a Web UI started on http://{host}:{port}"
            )

    def _run_server(self, host, port):
        try:
            self._app.run(host=host, port=port, debug=False, use_reloader=False)
        except Exception as e:
            if self._logger:
                self._logger.error(f"§2[§7Paradox§2]§c Web UI error: {e}")

    def stop(self):
        # Flask in a thread can't be gracefully stopped easily,
        # but since it's a daemon thread it dies with the process
        self._app = None
        self._thread = None


# ══════════════════════════════════════════════════════════
#  DATABASE HELPER
# ══════════════════════════════════════════════════════════

def _get_db():
    """Get a read/write SQLite connection for the web UI."""
    from flask import g, current_app
    if "db" not in g:
        db_path = current_app.config["PARADOX_DB_PATH"]
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


def _db_get_all(table):
    """Get all key-value pairs from a table."""
    db = _get_db()
    try:
        rows = db.execute(f"SELECT key, value, updated_at FROM [{table}]").fetchall()
        result = []
        for r in rows:
            try:
                val = json.loads(r["value"])
            except Exception:
                val = r["value"]
            result.append({"key": r["key"], "value": val, "updated_at": r["updated_at"]})
        return result
    except Exception:
        return []


def _db_get(table, key, default=None):
    db = _get_db()
    try:
        row = db.execute(f"SELECT value FROM [{table}] WHERE key = ?", (key,)).fetchone()
        if row:
            return json.loads(row["value"])
        return default
    except Exception:
        return default


def _db_set(table, key, value):
    db = _get_db()
    db.execute(
        f"""INSERT OR REPLACE INTO [{table}] (key, value, updated_at)
            VALUES (?, ?, julianday('now'))""",
        (key, json.dumps(value)),
    )
    db.commit()


def _db_delete(table, key):
    db = _get_db()
    db.execute(f"DELETE FROM [{table}] WHERE key = ?", (key,))
    db.commit()


def _db_count(table):
    db = _get_db()
    try:
        return db.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
    except Exception:
        return 0


def _db_tables():
    db = _get_db()
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name != '_meta'"
    ).fetchall()
    return [r[0] for r in rows]


# ══════════════════════════════════════════════════════════
#  AUTH DECORATOR
# ══════════════════════════════════════════════════════════

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ══════════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════════

def _register_routes(app):

    @app.teardown_appcontext
    def close_db(exception):
        from flask import g
        db = g.pop("db", None)
        if db is not None:
            db.close()

    # ── Login ──

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            key = request.form.get("secret_key", "")
            if key == app.config["PARADOX_SECRET"]:
                session["authenticated"] = True
                return redirect(url_for("dashboard"))
            else:
                return render_template_string(LOGIN_HTML, error="Invalid secret key")
        return render_template_string(LOGIN_HTML, error=None)

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    # ── Dashboard ──

    @app.route("/")
    @login_required
    def dashboard():
        from endstone_paradox.globalban import GLOBAL_BAN_LIST
        stats = {
            "modules": len(ALL_MODULES),
            "bans": _db_count("bans") + len(GLOBAL_BAN_LIST),
            "server_bans": _db_count("bans"),
            "global_bans": len(GLOBAL_BAN_LIST),
            "players": _db_count("players"),
            "frozen": _db_count("frozen_players"),
            "vanished": _db_count("vanished_players"),
            "allowlist": _db_count("allowlist"),
            "whitelist": _db_count("whitelist"),
            "lockdown": _db_get("config", "lockdown", False),
            "lockdown_level": _db_get("config", "lockdown_level", 1),
        }
        # Build full module list
        mod_list = []
        for name, default_on in ALL_MODULES.items():
            enabled = _db_get("modules", name, default_on)
            mod_list.append({"key": name, "value": enabled})
        # High-risk players: anyone with warnings in player_data
        high_risk = []
        all_player_data = _db_get_all("player_data")
        for pd in all_player_data:
            if isinstance(pd["value"], dict) and pd["value"].get("warnings", 0) > 0:
                high_risk.append(pd)
        # Also add banned players as high-risk
        ban_list = _db_get_all("bans")
        return render_template_string(DASHBOARD_HTML, stats=stats, modules=mod_list, high_risk=high_risk, bans=ban_list)

    # ── Modules ──

    @app.route("/modules")
    @login_required
    def modules():
        # Build complete module list from hardcoded names + DB overrides
        mod_list = []
        for name, default_on in ALL_MODULES.items():
            enabled = _db_get("modules", name, default_on)
            sens = _db_get("modules", f"{name}_sensitivity", 5)
            mod_list.append({"key": name, "value": enabled, "sensitivity": sens})
        return render_template_string(MODULES_HTML, modules=mod_list)

    @app.route("/modules/<name>/toggle", methods=["POST"])
    @login_required
    def toggle_module(name):
        current = _db_get("modules", name, True)
        _db_set("modules", name, not current)
        return redirect(url_for("modules"))

    @app.route("/modules/<name>/sensitivity", methods=["POST"])
    @login_required
    def set_sensitivity(name):
        val = int(request.form.get("sensitivity", 5))
        val = max(1, min(10, val))
        _db_set("modules", f"{name}_sensitivity", val)
        return redirect(url_for("modules"))

    # ── Bans ──

    @app.route("/bans")
    @login_required
    def bans():
        ban_list = _db_get_all("bans")
        from endstone_paradox.globalban import GLOBAL_BAN_LIST
        return render_template_string(BANS_HTML, bans=ban_list, global_bans=sorted(GLOBAL_BAN_LIST))

    @app.route("/bans/add", methods=["POST"])
    @login_required
    def add_ban():
        name = request.form.get("player_name", "").strip()
        reason = request.form.get("reason", "Banned via Web UI")
        if name:
            import time
            _db_set("bans", name, {
                "reason": reason,
                "banned_by": "WebUI",
                "timestamp": time.time(),
            })
        return redirect(url_for("bans"))

    @app.route("/bans/remove", methods=["POST"])
    @login_required
    def remove_ban():
        name = request.form.get("player_name", "").strip()
        if name:
            _db_delete("bans", name)
        return redirect(url_for("bans"))

    # ── Players & Warnings ──

    @app.route("/players")
    @login_required
    def players():
        player_list = _db_get_all("players")
        player_data = _db_get_all("player_data")
        ranks = _db_get_all("ranks")
        frozen = _db_get_all("frozen_players")
        vanished = _db_get_all("vanished_players")
        return render_template_string(
            PLAYERS_HTML,
            players=player_list,
            player_data=player_data,
            ranks=ranks,
            frozen=frozen,
            vanished=vanished,
        )

    # ── Logs ──

    @app.route("/logs")
    @login_required
    def logs():
        spoof_log = _db_get_all("spoof_log")
        return render_template_string(LOGS_HTML, spoof_log=spoof_log)

    # ── Config ──

    @app.route("/config", methods=["GET", "POST"])
    @login_required
    def config_page():
        if request.method == "POST":
            for key in ["lockdown", "lockdown_level"]:
                val = request.form.get(key)
                if val is not None:
                    if val.lower() in ("true", "1", "on"):
                        _db_set("config", key, True)
                    elif val.lower() in ("false", "0", "off"):
                        _db_set("config", key, False)
                    elif val.isdigit():
                        _db_set("config", key, int(val))
                    else:
                        _db_set("config", key, val)
            return redirect(url_for("config_page"))
        all_config = _db_get_all("config")
        paradox_config = app.config["PARADOX_CONFIG"].raw
        return render_template_string(CONFIG_HTML, db_config=all_config, file_config=paradox_config)

    # ── Lists (Allow/White) ──

    @app.route("/lists")
    @login_required
    def lists():
        allow = _db_get_all("allowlist")
        white = _db_get_all("whitelist")
        return render_template_string(LISTS_HTML, allowlist=allow, whitelist=white)

    @app.route("/lists/<list_type>/add", methods=["POST"])
    @login_required
    def add_to_list(list_type):
        table = "allowlist" if list_type == "allow" else "whitelist"
        name = request.form.get("player_name", "").strip()
        if name:
            _db_set(table, name, True)
        return redirect(url_for("lists"))

    @app.route("/lists/<list_type>/remove", methods=["POST"])
    @login_required
    def remove_from_list(list_type):
        table = "allowlist" if list_type == "allow" else "whitelist"
        name = request.form.get("player_name", "").strip()
        if name:
            _db_delete(table, name)
        return redirect(url_for("lists"))

    # ── Global DB (future placeholder) ──

    @app.route("/global")
    @login_required
    def global_db():
        cfg = app.config["PARADOX_CONFIG"]
        global_cfg = cfg.get("global_database", default={})
        return render_template_string(GLOBAL_HTML, config=global_cfg)

    # ── API Stats ──

    @app.route("/api/stats")
    @login_required
    def api_stats():
        return jsonify({
            "modules": len(ALL_MODULES),
            "bans": _db_count("bans"),
            "players": _db_count("players"),
            "frozen": _db_count("frozen_players"),
            "vanished": _db_count("vanished_players"),
            "lockdown": _db_get("config", "lockdown", False),
        })

    # ── Player Permissions ──

    @app.route("/permissions")
    @login_required
    def permissions():
        player_list = _db_get_all("players")
        return render_template_string(PERMISSIONS_HTML, players=player_list)

    @app.route("/permissions/set", methods=["POST"])
    @login_required
    def set_permission():
        uuid_str = request.form.get("uuid", "").strip()
        level = int(request.form.get("level", 1))
        level = max(1, min(4, level))
        if uuid_str:
            data = _db_get("players", uuid_str, {})
            if not isinstance(data, dict):
                data = {}
            data["clearance"] = level
            _db_set("players", uuid_str, data)
        return redirect(url_for("permissions"))


# ══════════════════════════════════════════════════════════
#  HTML TEMPLATES
# ══════════════════════════════════════════════════════════

# ── Shared base styles ──

BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Inter', sans-serif;
    background: #0a0e17;
    color: #e0e0e0;
    min-height: 100vh;
}

.layout {
    display: flex;
    min-height: 100vh;
}

/* Sidebar */
.sidebar {
    width: 240px;
    background: linear-gradient(180deg, #0f1520 0%, #0a0e17 100%);
    border-right: 1px solid rgba(34, 197, 94, 0.15);
    padding: 24px 0;
    position: fixed;
    height: 100vh;
    overflow-y: auto;
    z-index: 100;
}

.sidebar-brand {
    padding: 0 20px 24px;
    border-bottom: 1px solid rgba(34, 197, 94, 0.1);
    margin-bottom: 16px;
}

.sidebar-brand h1 {
    font-size: 18px;
    font-weight: 700;
    background: linear-gradient(135deg, #22c55e, #10b981, #059669);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -.5px;
}

.sidebar-brand span {
    font-size: 11px;
    color: #6b7280;
    display: block;
    margin-top: 4px;
}

.nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 20px;
    color: #9ca3af;
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.2s;
    border-left: 3px solid transparent;
}

.nav-item:hover, .nav-item.active {
    color: #22c55e;
    background: rgba(34, 197, 94, 0.05);
    border-left-color: #22c55e;
}

.nav-section {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #4b5563;
    padding: 16px 20px 6px;
}

/* Main Content */
.main {
    margin-left: 240px;
    flex: 1;
    padding: 32px;
}

h2 {
    font-size: 24px;
    font-weight: 700;
    color: #f3f4f6;
    margin-bottom: 24px;
}

/* Cards */
.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
}

.card {
    background: rgba(15, 21, 32, 0.8);
    border: 1px solid rgba(34, 197, 94, 0.1);
    border-radius: 12px;
    padding: 20px;
    backdrop-filter: blur(10px);
}

.card-label {
    font-size: 12px;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 6px;
}

.card-value {
    font-size: 28px;
    font-weight: 700;
    color: #22c55e;
}

.card-value.danger { color: #ef4444; }
.card-value.warn { color: #f59e0b; }
.card-value.info { color: #3b82f6; }

/* Tables */
.table-wrap {
    background: rgba(15, 21, 32, 0.8);
    border: 1px solid rgba(34, 197, 94, 0.1);
    border-radius: 12px;
    overflow: hidden;
    margin-bottom: 24px;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th {
    background: rgba(34, 197, 94, 0.08);
    padding: 12px 16px;
    text-align: left;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #9ca3af;
    font-weight: 600;
}

td {
    padding: 10px 16px;
    border-top: 1px solid rgba(255,255,255,0.03);
    font-size: 14px;
}

tr:hover td { background: rgba(34, 197, 94, 0.03); }

/* Buttons */
.btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    border: none;
    cursor: pointer;
    transition: all 0.2s;
    text-decoration: none;
}

.btn-primary {
    background: linear-gradient(135deg, #22c55e, #16a34a);
    color: #fff;
}
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(34,197,94,0.3); }

.btn-danger {
    background: linear-gradient(135deg, #ef4444, #dc2626);
    color: #fff;
}
.btn-danger:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(239,68,68,0.3); }

.btn-sm { padding: 5px 10px; font-size: 12px; }

/* Toggle */
.toggle {
    position: relative;
    width: 44px;
    height: 24px;
    display: inline-block;
}

.toggle input { display: none; }

.toggle-slider {
    position: absolute;
    inset: 0;
    background: #374151;
    border-radius: 12px;
    cursor: pointer;
    transition: 0.3s;
}

.toggle-slider:before {
    content: '';
    position: absolute;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #fff;
    top: 3px;
    left: 3px;
    transition: 0.3s;
}

.toggle input:checked + .toggle-slider { background: #22c55e; }
.toggle input:checked + .toggle-slider:before { left: 23px; }

/* Forms */
input[type="text"], input[type="password"], input[type="number"], select, textarea {
    background: rgba(15, 21, 32, 0.9);
    border: 1px solid rgba(255,255,255,0.1);
    color: #e0e0e0;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 14px;
    font-family: 'Inter', sans-serif;
    width: 100%;
    transition: border-color 0.2s;
}

input:focus, select:focus, textarea:focus {
    outline: none;
    border-color: #22c55e;
}

.form-group {
    margin-bottom: 16px;
}

.form-group label {
    display: block;
    font-size: 12px;
    color: #9ca3af;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.form-row {
    display: flex;
    gap: 12px;
    align-items: end;
}

/* Status badges */
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
}

.badge-on { background: rgba(34,197,94,0.15); color: #22c55e; }
.badge-off { background: rgba(239,68,68,0.15); color: #ef4444; }
.badge-warn { background: rgba(245,158,11,0.15); color: #f59e0b; }

/* Sensitivity slider */
input[type="range"] {
    -webkit-appearance: none;
    width: 120px;
    height: 6px;
    background: #374151;
    border-radius: 3px;
    outline: none;
}

input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #22c55e;
    cursor: pointer;
}

/* Placeholder card */
.placeholder-card {
    background: rgba(15, 21, 32, 0.6);
    border: 2px dashed rgba(34, 197, 94, 0.2);
    border-radius: 12px;
    padding: 40px;
    text-align: center;
    color: #6b7280;
}

/* Alert */
.alert {
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 16px;
    font-size: 14px;
}
.alert-error { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); color: #fca5a5; }
</style>
"""

SIDEBAR_HTML = """
<nav class="sidebar">
    <div class="sidebar-brand">
        <h1><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="url(#g)" stroke-width="2" style="vertical-align:middle;margin-right:6px;"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#22c55e"/><stop offset="100%" stop-color="#059669"/></linearGradient></defs><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg> Paradox</h1>
        <span>AntiCheat Web Panel</span>
    </div>
    <div class="nav-section">Overview</div>
    <a class="nav-item" href="/"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg> Dashboard</a>
    <div class="nav-section">Management</div>
    <a class="nav-item" href="/modules"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg> Modules</a>
    <a class="nav-item" href="/bans"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg> Bans</a>
    <a class="nav-item" href="/players"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg> Players</a>
    <a class="nav-item" href="/permissions"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 11-7.778 7.778 5.5 5.5 0 017.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg> Permissions</a>
    <a class="nav-item" href="/logs"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg> Logs</a>
    <div class="nav-section">Settings</div>
    <a class="nav-item" href="/config"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/></svg> Config</a>
    <a class="nav-item" href="/lists"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg> Allow/Whitelist</a>
    <a class="nav-item" href="/global"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/></svg> Global DB</a>
    <div class="nav-section">Account</div>
    <a class="nav-item" href="/logout"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg> Logout</a>
</nav>
"""

# ── Login Page ──

LOGIN_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paradox — Login</title>
""" + BASE_CSS + """
<style>
.login-container {
    display: flex; align-items: center; justify-content: center;
    min-height: 100vh;
    background: radial-gradient(circle at 50% 50%, rgba(34,197,94,0.05) 0%, #0a0e17 70%);
}
.login-box {
    background: rgba(15,21,32,0.9);
    border: 1px solid rgba(34,197,94,0.15);
    border-radius: 16px;
    padding: 40px;
    width: 380px;
    backdrop-filter: blur(20px);
}
.login-box h1 { text-align: center; margin-bottom: 8px; font-size: 22px; color: #22c55e; }
.login-box p { text-align: center; color: #6b7280; font-size: 13px; margin-bottom: 24px; }
.login-logo { text-align:center; margin-bottom:16px; }
</style>
</head><body>
<div class="login-container">
<div class="login-box">
    <div class="login-logo"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="1.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg></div>
    <h1>Paradox</h1>
    <p>Enter your secret key to continue</p>
    {% if error %}<div class="alert alert-error">{{ error }}</div>{% endif %}
    <form method="POST">
        <div class="form-group">
            <label>Secret Key</label>
            <input type="password" name="secret_key" placeholder="Enter secret key..." autofocus>
        </div>
        <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center;">Login</button>
    </form>
</div>
</div>
</body></html>"""

# ── Dashboard ──

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paradox — Dashboard</title>
""" + BASE_CSS + """
</head><body>
<div class="layout">
""" + SIDEBAR_HTML + """
<div class="main">
    <h2>Dashboard</h2>
    <div class="card-grid">
        <div class="card">
            <div class="card-label">Modules</div>
            <div class="card-value">{{ stats.modules }}</div>
        </div>
        <div class="card">
            <div class="card-label">Banned Players</div>
            <div class="card-value danger">{{ stats.bans }}</div>
            <div style="font-size:11px;color:#6b7280;margin-top:4px;">{{ stats.server_bans }} server · {{ stats.global_bans }} global</div>
        </div>
        <div class="card">
            <div class="card-label">Known Players</div>
            <div class="card-value info">{{ stats.players }}</div>
        </div>
        <div class="card">
            <div class="card-label">Frozen</div>
            <div class="card-value warn">{{ stats.frozen }}</div>
        </div>
        <div class="card">
            <div class="card-label">Vanished</div>
            <div class="card-value info">{{ stats.vanished }}</div>
        </div>
        <div class="card">
            <div class="card-label">Lockdown</div>
            <div class="card-value {% if stats.lockdown %}danger{% endif %}">
                {% if stats.lockdown %}ACTIVE (L{{ stats.lockdown_level }}){% else %}OFF{% endif %}
            </div>
        </div>
        <div class="card">
            <div class="card-label">Allowlist</div>
            <div class="card-value">{{ stats.allowlist }}</div>
        </div>
        <div class="card">
            <div class="card-label">Whitelist</div>
            <div class="card-value">{{ stats.whitelist }}</div>
        </div>
    </div>

    <h2>Module Status</h2>
    <div class="table-wrap">
    <table>
        <tr><th>Module</th><th>Status</th></tr>
        {% for m in modules %}
        <tr>
            <td>{{ m.key }}</td>
            <td>
                {% if m.value %}<span class="badge badge-on">ON</span>
                {% else %}<span class="badge badge-off">OFF</span>{% endif %}
            </td>
        </tr>
        {% endfor %}
    </table>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:24px;">
    <div>
        <h2>High-Risk Players</h2>
        <div class="table-wrap">
        <table>
            <tr><th>Player</th><th>Warnings</th></tr>
            {% for p in high_risk %}
            <tr>
                <td style="font-weight:600;">{{ p.key }}</td>
                <td><span class="badge badge-warn">{{ p.value.warnings }} warnings</span></td>
            </tr>
            {% endfor %}
            {% if not high_risk %}<tr><td colspan="2" style="text-align:center;color:#6b7280;padding:16px;">No high-risk players</td></tr>{% endif %}
        </table>
        </div>
    </div>
    <div>
        <h2>Banned Players</h2>
        <div class="table-wrap">
        <table>
            <tr><th>Player</th><th>Reason</th></tr>
            {% for b in bans %}
            <tr>
                <td style="font-weight:600;">{{ b.key }}</td>
                <td>{{ b.value.reason if b.value is mapping else b.value }}</td>
            </tr>
            {% endfor %}
            {% if not bans %}<tr><td colspan="2" style="text-align:center;color:#6b7280;padding:16px;">No banned players</td></tr>{% endif %}
        </table>
        </div>
    </div>
    </div>
</div>
</div>
</body></html>"""

# ── Modules ──

MODULES_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paradox — Modules</title>
""" + BASE_CSS + """
</head><body>
<div class="layout">
""" + SIDEBAR_HTML + """
<div class="main">
    <h2>Module Management</h2>
    <div class="table-wrap">
    <table>
        <tr><th>Module</th><th>Status</th><th>Toggle</th><th>Sensitivity</th></tr>
        {% for m in modules %}
        <tr>
            <td style="font-weight:600;">{{ m.key }}</td>
            <td>
                {% if m.value %}<span class="badge badge-on">ON</span>
                {% else %}<span class="badge badge-off">OFF</span>{% endif %}
            </td>
            <td>
                <form method="POST" action="/modules/{{ m.key }}/toggle" style="display:inline;">
                    <button type="submit" class="btn btn-sm {% if m.value %}btn-danger{% else %}btn-primary{% endif %}">
                        {% if m.value %}Disable{% else %}Enable{% endif %}
                    </button>
                </form>
            </td>
            <td>
                <form method="POST" action="/modules/{{ m.key }}/sensitivity" style="display:flex;align-items:center;gap:8px;">
                    <input type="range" name="sensitivity" min="1" max="10"
                           value="{{ m.sensitivity }}"
                           oninput="this.nextElementSibling.textContent=this.value">
                    <span style="min-width:20px;color:#22c55e;font-weight:600;">{{ m.sensitivity }}</span>
                    <button type="submit" class="btn btn-sm btn-primary">Set</button>
                </form>
            </td>
        </tr>
        {% endfor %}
    </table>
    </div>
</div>
</div>
</body></html>"""

# ── Bans ──

BANS_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paradox — Bans</title>
""" + BASE_CSS + """
</head><body>
<div class="layout">
""" + SIDEBAR_HTML + """
<div class="main">
    <h2>Ban Management</h2>

    <div class="card" style="margin-bottom:24px;">
        <h3 style="margin-bottom:12px;font-size:16px;color:#f3f4f6;">Add Ban</h3>
        <form method="POST" action="/bans/add">
            <div class="form-row">
                <div class="form-group" style="flex:1;">
                    <label>Player Name</label>
                    <input type="text" name="player_name" placeholder="PlayerName" required>
                </div>
                <div class="form-group" style="flex:2;">
                    <label>Reason</label>
                    <input type="text" name="reason" placeholder="Ban reason..." value="Banned via Web UI">
                </div>
                <button type="submit" class="btn btn-danger" style="height:42px;">Ban</button>
            </div>
        </form>
    </div>

    <div class="table-wrap">
    <table>
        <tr><th>Player</th><th>Reason</th><th>Banned By</th><th>Action</th></tr>
        {% for b in bans %}
        <tr>
            <td style="font-weight:600;">{{ b.key }}</td>
            <td>{{ b.value.reason if b.value is mapping else b.value }}</td>
            <td>{{ b.value.banned_by if b.value is mapping else 'Unknown' }}</td>
            <td>
                <form method="POST" action="/bans/remove" style="display:inline;">
                    <input type="hidden" name="player_name" value="{{ b.key }}">
                    <button type="submit" class="btn btn-sm btn-primary">Unban</button>
                </form>
            </td>
        </tr>
        {% endfor %}
        {% if not bans %}
        <tr><td colspan="4" style="text-align:center;color:#6b7280;padding:24px;">No banned players</td></tr>
        {% endif %}
    </table>
    </div>

    <h2 style="margin-top:32px;">Global Ban List <span class="badge badge-warn" style="font-size:12px;">{{ global_bans|length }} names</span></h2>
    <p style="color:#6b7280;font-size:13px;margin-bottom:12px;">Hardcoded list from the original Paradox AntiCheat. Players matching these names are kicked on join.</p>
    <div style="margin-bottom:12px;">
        <input type="text" id="globalBanSearch" placeholder="Search global bans..."
               oninput="filterGlobalBans()" style="max-width:300px;">
    </div>
    <div class="table-wrap" style="max-height:400px;overflow-y:auto;">
    <table id="globalBanTable">
        <tr><th>#</th><th>Player Name</th></tr>
        {% for name in global_bans %}
        <tr class="gb-row">
            <td style="color:#6b7280;font-size:12px;">{{ loop.index }}</td>
            <td style="font-weight:600;">{{ name }}</td>
        </tr>
        {% endfor %}
    </table>
    </div>
    <script>
    function filterGlobalBans() {
        var q = document.getElementById('globalBanSearch').value.toLowerCase();
        var rows = document.querySelectorAll('.gb-row');
        rows.forEach(function(r) {
            r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none';
        });
    }
    </script>
</div>
</div>
</body></html>"""

# ── Players ──

PLAYERS_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paradox — Players</title>
""" + BASE_CSS + """
</head><body>
<div class="layout">
""" + SIDEBAR_HTML + """
<div class="main">
    <h2>Player Data</h2>

    <h3 style="margin-bottom:12px;font-size:16px;color:#f3f4f6;">👥 Player Records</h3>
    <div class="table-wrap">
    <table>
        <tr><th>Player</th><th>Data</th></tr>
        {% for p in players %}
        <tr>
            <td style="font-weight:600;">{{ p.key }}</td>
            <td style="font-size:12px;font-family:monospace;">{{ p.value }}</td>
        </tr>
        {% endfor %}
        {% if not players %}<tr><td colspan="2" style="text-align:center;color:#6b7280;padding:24px;">No player records</td></tr>{% endif %}
    </table>
    </div>

    <h3 style="margin-bottom:12px;font-size:16px;color:#f3f4f6;">📊 Player Details & Warnings</h3>
    <div class="table-wrap">
    <table>
        <tr><th>Key</th><th>Data</th></tr>
        {% for d in player_data %}
        <tr>
            <td style="font-weight:600;">{{ d.key }}</td>
            <td style="font-size:12px;font-family:monospace;">{{ d.value }}</td>
        </tr>
        {% endfor %}
        {% if not player_data %}<tr><td colspan="2" style="text-align:center;color:#6b7280;padding:24px;">No player data</td></tr>{% endif %}
    </table>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;">
        <div>
            <h3 style="margin-bottom:12px;font-size:16px;color:#f3f4f6;">🧊 Frozen Players</h3>
            <div class="table-wrap">
            <table>
                <tr><th>Player</th></tr>
                {% for f in frozen %}
                <tr><td>{{ f.key }}</td></tr>
                {% endfor %}
                {% if not frozen %}<tr><td style="text-align:center;color:#6b7280;padding:16px;">None</td></tr>{% endif %}
            </table>
            </div>
        </div>
        <div>
            <h3 style="margin-bottom:12px;font-size:16px;color:#f3f4f6;">👻 Vanished Players</h3>
            <div class="table-wrap">
            <table>
                <tr><th>Player</th></tr>
                {% for v in vanished %}
                <tr><td>{{ v.key }}</td></tr>
                {% endfor %}
                {% if not vanished %}<tr><td style="text-align:center;color:#6b7280;padding:16px;">None</td></tr>{% endif %}
            </table>
            </div>
        </div>
    </div>

    <h3 style="margin:24px 0 12px;font-size:16px;color:#f3f4f6;">🏅 Ranks</h3>
    <div class="table-wrap">
    <table>
        <tr><th>Player</th><th>Rank</th></tr>
        {% for r in ranks %}
        <tr><td style="font-weight:600;">{{ r.key }}</td><td>{{ r.value }}</td></tr>
        {% endfor %}
        {% if not ranks %}<tr><td colspan="2" style="text-align:center;color:#6b7280;padding:16px;">No ranks set</td></tr>{% endif %}
    </table>
    </div>
</div>
</div>
</body></html>"""

# ── Logs ──

LOGS_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paradox — Logs</title>
""" + BASE_CSS + """
</head><body>
<div class="layout">
""" + SIDEBAR_HTML + """
<div class="main">
    <h2>Detection Logs</h2>

    <h3 style="margin-bottom:12px;font-size:16px;color:#f3f4f6;">🕵️ Namespoof Log</h3>
    <div class="table-wrap">
    <table>
        <tr><th>Entry</th><th>Details</th></tr>
        {% for s in spoof_log %}
        <tr>
            <td style="font-weight:600;">{{ s.key }}</td>
            <td style="font-size:12px;font-family:monospace;">{{ s.value }}</td>
        </tr>
        {% endfor %}
        {% if not spoof_log %}<tr><td colspan="2" style="text-align:center;color:#6b7280;padding:24px;">No spoof events logged</td></tr>{% endif %}
    </table>
    </div>
</div>
</div>
</body></html>"""

# ── Config ──

CONFIG_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paradox — Config</title>
""" + BASE_CSS + """
</head><body>
<div class="layout">
""" + SIDEBAR_HTML + """
<div class="main">
    <h2>Configuration</h2>

    <h3 style="margin-bottom:12px;font-size:16px;color:#f3f4f6;">🔧 Server Config (Database)</h3>
    <div class="table-wrap">
    <table>
        <tr><th>Setting</th><th>Value</th></tr>
        {% for c in db_config %}
        <tr>
            <td style="font-weight:600;">{{ c.key }}</td>
            <td>
                <form method="POST" action="/config" style="display:flex;align-items:center;gap:8px;">
                    <input type="text" name="{{ c.key }}" value="{{ c.value }}" style="max-width:300px;">
                    <button type="submit" class="btn btn-sm btn-primary">Save</button>
                </form>
            </td>
        </tr>
        {% endfor %}
    </table>
    </div>

    <h3 style="margin:24px 0 12px;font-size:16px;color:#f3f4f6;">📁 File Config (config.yml)</h3>
    <div class="card">
        <pre style="font-size:12px;color:#9ca3af;white-space:pre-wrap;font-family:monospace;">{{ file_config }}</pre>
    </div>

    <h3 style="margin:24px 0 12px;font-size:16px;color:#f3f4f6;">💾 Database Info</h3>
    <div class="card">
        <p style="font-size:13px;color:#6b7280;">
            Mode: <strong style="color:#22c55e;">{{ file_config.get('database', {}).get('mode', 'internal') }}</strong><br>
            {% if file_config.get('database', {}).get('mode') == 'external' %}
            Type: {{ file_config.get('database', {}).get('external', {}).get('type', 'mysql') }}<br>
            Host: {{ file_config.get('database', {}).get('external', {}).get('host', 'localhost') }}
            {% else %}
            Using local SQLite database
            {% endif %}
        </p>
    </div>
</div>
</div>
</body></html>"""

# ── Lists ──

LISTS_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paradox — Lists</title>
""" + BASE_CSS + """
</head><body>
<div class="layout">
""" + SIDEBAR_HTML + """
<div class="main">
    <h2>Allow & Whitelist</h2>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;">
    <div>
        <h3 style="margin-bottom:12px;font-size:16px;color:#f3f4f6;">✅ Allowlist</h3>
        <div class="card" style="margin-bottom:16px;">
            <form method="POST" action="/lists/allow/add">
                <div class="form-row">
                    <div class="form-group" style="flex:1;">
                        <input type="text" name="player_name" placeholder="Player name...">
                    </div>
                    <button type="submit" class="btn btn-sm btn-primary">Add</button>
                </div>
            </form>
        </div>
        <div class="table-wrap">
        <table>
            <tr><th>Player</th><th>Action</th></tr>
            {% for a in allowlist %}
            <tr>
                <td>{{ a.key }}</td>
                <td>
                    <form method="POST" action="/lists/allow/remove" style="display:inline;">
                        <input type="hidden" name="player_name" value="{{ a.key }}">
                        <button type="submit" class="btn btn-sm btn-danger">Remove</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
            {% if not allowlist %}<tr><td colspan="2" style="text-align:center;color:#6b7280;">Empty</td></tr>{% endif %}
        </table>
        </div>
    </div>

    <div>
        <h3 style="margin-bottom:12px;font-size:16px;color:#f3f4f6;">📋 Whitelist</h3>
        <div class="card" style="margin-bottom:16px;">
            <form method="POST" action="/lists/white/add">
                <div class="form-row">
                    <div class="form-group" style="flex:1;">
                        <input type="text" name="player_name" placeholder="Player name...">
                    </div>
                    <button type="submit" class="btn btn-sm btn-primary">Add</button>
                </div>
            </form>
        </div>
        <div class="table-wrap">
        <table>
            <tr><th>Player</th><th>Action</th></tr>
            {% for w in whitelist %}
            <tr>
                <td>{{ w.key }}</td>
                <td>
                    <form method="POST" action="/lists/white/remove" style="display:inline;">
                        <input type="hidden" name="player_name" value="{{ w.key }}">
                        <button type="submit" class="btn btn-sm btn-danger">Remove</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
            {% if not whitelist %}<tr><td colspan="2" style="text-align:center;color:#6b7280;">Empty</td></tr>{% endif %}
        </table>
        </div>
    </div>
    </div>
</div>
</div>
</body></html>"""

# ── Global DB (placeholder) ──

GLOBAL_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paradox — Global Database</title>
""" + BASE_CSS + """
</head><body>
<div class="layout">
""" + SIDEBAR_HTML + """
<div class="main">
    <h2>Global Ban Database</h2>
    <div class="placeholder-card">
        <h3 style="margin-bottom:12px;color:#9ca3af;">Coming Soon</h3>
        <p style="margin-bottom:16px;">
            The Global Ban Database will allow cross-server sharing of:<br>
            <strong style="color:#ef4444;">Banned members</strong> and
            <strong style="color:#f59e0b;">High-risk players</strong>
        </p>
        <div class="card" style="display:inline-block;text-align:left;max-width:400px;">
            <div style="font-size:13px;color:#6b7280;">
                <p><strong>Status:</strong> {% if config.get('enabled', False) %}<span class="badge badge-on">Connected</span>{% else %}<span class="badge badge-off">Not Configured</span>{% endif %}</p>
                <p style="margin-top:8px;"><strong>API URL:</strong> {{ config.get('api_url', 'Not set') or 'Not set' }}</p>
                <p style="margin-top:4px;"><strong>Sync Interval:</strong> {{ config.get('sync_interval', 300) }}s</p>
            </div>
        </div>
        <p style="margin-top:20px;font-size:12px;color:#4b5563;">
            Configure in <code>config.toml</code> &rarr; <code>global_database</code> section
        </p>
    </div>
</div>
</div>
</body></html>"""

# ── Permissions ──

PERMISSIONS_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paradox — Permissions</title>
""" + BASE_CSS + """
<style>
.level-badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; }
.level-1 { background:rgba(107,114,128,0.2); color:#9ca3af; }
.level-2 { background:rgba(59,130,246,0.15); color:#60a5fa; }
.level-3 { background:rgba(245,158,11,0.15); color:#fbbf24; }
.level-4 { background:rgba(239,68,68,0.15); color:#f87171; }
</style>
</head><body>
<div class="layout">
""" + SIDEBAR_HTML + """
<div class="main">
    <h2>Player Permissions</h2>

    <div class="card" style="margin-bottom:24px;">
        <h3 style="margin-bottom:12px;font-size:16px;color:#f3f4f6;">Security Clearance Levels</h3>
        <div style="display:flex;gap:16px;flex-wrap:wrap;">
            <div><span class="level-badge level-1">L1</span> Default — basic commands</div>
            <div><span class="level-badge level-2">L2</span> Moderate — utility</div>
            <div><span class="level-badge level-3">L3</span> High — moderation</div>
            <div><span class="level-badge level-4">L4</span> Full Admin — exempt from checks</div>
        </div>
    </div>

    <div class="table-wrap">
    <table>
        <tr><th>UUID</th><th>Name</th><th>Current Level</th><th>Set Level</th></tr>
        {% for p in players %}
        <tr>
            <td style="font-size:12px;font-family:monospace;max-width:200px;overflow:hidden;text-overflow:ellipsis;">{{ p.key }}</td>
            <td style="font-weight:600;">{{ p.value.name if p.value is mapping else 'Unknown' }}</td>
            <td>
                {% set lvl = p.value.clearance if p.value is mapping else 1 %}
                <span class="level-badge level-{{ lvl|default(1) }}">L{{ lvl|default(1) }}</span>
            </td>
            <td>
                <form method="POST" action="/permissions/set" style="display:flex;align-items:center;gap:8px;">
                    <input type="hidden" name="uuid" value="{{ p.key }}">
                    <select name="level" style="width:auto;min-width:80px;">
                        <option value="1" {% if lvl == 1 %}selected{% endif %}>L1 - Default</option>
                        <option value="2" {% if lvl == 2 %}selected{% endif %}>L2 - Moderate</option>
                        <option value="3" {% if lvl == 3 %}selected{% endif %}>L3 - High</option>
                        <option value="4" {% if lvl == 4 %}selected{% endif %}>L4 - Admin</option>
                    </select>
                    <button type="submit" class="btn btn-sm btn-primary">Set</button>
                </form>
            </td>
        </tr>
        {% endfor %}
        {% if not players %}<tr><td colspan="4" style="text-align:center;color:#6b7280;padding:24px;">No player records yet</td></tr>{% endif %}
    </table>
    </div>
</div>
</div>
</body></html>"""

