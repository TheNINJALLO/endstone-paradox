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
    "antidupe": False, "crashdrop": False, "invsync": False,
    "skinguard": True, "noclip": True, "waterwalk": True, "stephack": True,
    "timer": True, "blink": True, "antikb": True, "criticals": True,
    "wallhit": True, "triggerbot": True, "illegalitems": True,
    "discord": False, "chatprotection": False, "antigrief": False,
    "evidencereplay": False,
    # Tier 3
    "adaptivecheck": False, "botdetection": False,
    "reportsystem": False, "fingerprint": False,
}

# Modules that DON'T use sensitivity (utility/feature modules)
NO_SENSITIVITY = {
    "containersee", "afk", "lagclear", "worldborder", "gamemode",
    "pvp", "invsync", "discord", "evidencereplay", "crashdrop",
    "reportsystem", "adaptivecheck",
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
        # Build two separate lists: detection (has sensitivity) and utility (toggle only)
        detection = []
        utility = []
        for name, default_on in ALL_MODULES.items():
            enabled = _db_get("modules", name, default_on)
            sens = _db_get("modules", f"{name}_sensitivity", 5)
            has_sens = name not in NO_SENSITIVITY
            item = {"key": name, "value": enabled, "sensitivity": sens, "has_sensitivity": has_sens}
            if has_sens:
                detection.append(item)
            else:
                utility.append(item)
        return render_template_string(MODULES_HTML, detection=detection, utility=utility)

    @app.route("/modules/<name>/toggle", methods=["POST"])
    @login_required
    def toggle_module(name):
        default = ALL_MODULES.get(name, False)
        current = _db_get("modules", name, default)
        new_state = not bool(current)
        _db_set("modules", name, new_state)
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
            # Handle max enchant level
            max_ench = request.form.get("max_enchant_level")
            if max_ench is not None and max_ench.isdigit():
                _db_set("config", "max_enchant_level", max(1, int(max_ench)))
            # Handle enforcement mode
            enf_mode = request.form.get("enforcement_mode")
            if enf_mode in ("logonly", "soft", "hard"):
                _db_set("config", "enforcement_mode", enf_mode)
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
            _db_set(table, name.lower(), True)
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
        g_bans = _db_get_all("global_bans")
        g_flags = _db_get_all("global_flags")
        return render_template_string(
            GLOBAL_HTML, config=global_cfg,
            global_bans=g_bans, global_flags=g_flags
        )

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

    # ── Anti-Dupe Monitoring ──

    @app.route("/antidupe")
    @login_required
    def antidupe():
        antidupe_events = _db_get("antidupe_log", "events", [])
        crashdrop_events = _db_get("crashdrop_log", "events", [])
        invsync_events = _db_get("invsync_log", "events", [])
        if not isinstance(antidupe_events, list): antidupe_events = []
        if not isinstance(crashdrop_events, list): crashdrop_events = []
        if not isinstance(invsync_events, list): invsync_events = []
        return render_template_string(
            ANTIDUPE_HTML,
            antidupe_events=antidupe_events,
            crashdrop_events=crashdrop_events,
            invsync_events=invsync_events,
        )

    # ── Analytics Dashboard (Tier 3) ──

    @app.route("/analytics")
    @login_required
    def analytics():
        return render_template_string(ANALYTICS_HTML)

    @app.route("/api/analytics/violations")
    @login_required
    def api_analytics_violations():
        """Return violation time-series data for the last 24 hours."""
        import time as _time
        hours = int(request.args.get("hours", 24))
        now = _time.time()
        data = []
        for h in range(hours):
            ts = now - (h * 3600)
            t = _time.gmtime(ts)
            hour_key = f"{t.tm_year:04d}-{t.tm_mon:02d}-{t.tm_mday:02d}T{t.tm_hour:02d}"
            bucket = _db_get("analytics", hour_key, {})
            if not isinstance(bucket, dict):
                bucket = {}
            data.append({
                "hour": hour_key,
                "violations": bucket.get("violations", 0),
                "modules": bucket.get("modules", {}),
                "actions": bucket.get("actions", {}),
                "player_count": len(bucket.get("players", [])),
            })
        data.reverse()
        return jsonify(data)

    @app.route("/api/analytics/top-players")
    @login_required
    def api_analytics_top_players():
        """Return top flagged players by violation count."""
        from collections import defaultdict as _dd
        all_violations = _db_get_all("violations")
        counts = _dd(lambda: {"count": 0, "name": "?", "last_module": "?"})
        for key, data in all_violations:
            if not isinstance(data, dict):
                continue
            uid = data.get("uuid", key)
            counts[uid]["count"] += 1
            counts[uid]["name"] = data.get("name", "?")
            counts[uid]["last_module"] = data.get("module", "?")
        top = sorted(counts.items(), key=lambda x: x[1]["count"], reverse=True)[:10]
        return jsonify([{"uuid": u, **d} for u, d in top])

    @app.route("/api/analytics/modules")
    @login_required
    def api_analytics_modules():
        """Return per-module violation counts across all time."""
        import time as _time
        now = _time.time()
        module_totals = {}
        for h in range(168):  # last 7 days
            ts = now - (h * 3600)
            t = _time.gmtime(ts)
            hour_key = f"{t.tm_year:04d}-{t.tm_mon:02d}-{t.tm_mday:02d}T{t.tm_hour:02d}"
            bucket = _db_get("analytics", hour_key, {})
            if isinstance(bucket, dict):
                for mod, cnt in bucket.get("modules", {}).items():
                    module_totals[mod] = module_totals.get(mod, 0) + cnt
        return jsonify(module_totals)

    # ── Reports (Tier 3) ──

    @app.route("/reports")
    @login_required
    def reports_page():
        all_reports = _db_get_all("reports")
        reports = []
        for item in all_reports:
            data = item.get("value", item) if isinstance(item, dict) else item
            if isinstance(data, dict):
                reports.append(data)
        reports.sort(key=lambda r: (
            0 if r.get("status") == "priority" else (1 if r.get("status") == "open" else 2),
            r.get("created_at", 0),
        ))
        return render_template_string(REPORTS_HTML, reports=reports)

    @app.route("/reports/claim", methods=["POST"])
    @login_required
    def claim_report():
        report_id = request.form.get("report_id", "").strip()
        if report_id:
            report = _db_get("reports", report_id)
            if isinstance(report, dict) and report.get("status") in ("open", "priority"):
                report["status"] = "claimed"
                report["claimed_by"] = "WebUI"
                _db_set("reports", report_id, report)
        return redirect(url_for("reports_page"))

    @app.route("/reports/resolve", methods=["POST"])
    @login_required
    def resolve_report():
        import time as _time
        report_id = request.form.get("report_id", "").strip()
        resolution = request.form.get("resolution", "Resolved via Web UI")
        if report_id:
            report = _db_get("reports", report_id)
            if isinstance(report, dict):
                report["status"] = "resolved"
                report["resolved_at"] = _time.time()
                report["resolution"] = resolution
                _db_set("reports", report_id, report)
        return redirect(url_for("reports_page"))

    @app.route("/reports/delete", methods=["POST"])
    @login_required
    def delete_report():
        report_id = request.form.get("report_id", "").strip()
        if report_id:
            try:
                _db_delete("reports", report_id)
            except Exception:
                pass
        return redirect(url_for("reports_page"))

    @app.route("/reports/clear-all", methods=["POST"])
    @login_required
    def clear_all_reports():
        db = _get_db()
        try:
            db.execute("DELETE FROM [reports]")
            db.commit()
        except Exception:
            pass
        return redirect(url_for("reports_page"))

    @app.route("/analytics/clear", methods=["POST"])
    @login_required
    def clear_analytics():
        db = _get_db()
        try:
            db.execute("DELETE FROM [analytics]")
            db.commit()
        except Exception:
            pass
        return redirect(url_for("analytics"))

    # ── Violations (Intelligence) ──

    @app.route("/violations")
    @login_required
    def violations_page():
        """List all players with violations, sorted by count."""
        import time as _time
        from collections import defaultdict as _dd
        all_violations = _db_get_all("violations")
        players = _dd(lambda: {
            "name": "?", "count": 0, "modules": set(),
            "last_time": 0, "last_module": "?", "last_action": "?",
            "severity_max": 0,
        })
        for item in all_violations:
            # all_violations returns list of (key, value) or list of dicts
            if isinstance(item, (list, tuple)) and len(item) == 2:
                uuid_str, entries = item
            elif isinstance(item, dict):
                uuid_str = item.get("key", "?")
                entries = item.get("value", [])
            else:
                continue
            if not isinstance(entries, list):
                continue
            p = players[uuid_str]
            p["count"] = len(entries)
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                name = entry.get("name", "?")
                if name != "?":
                    p["name"] = name
                p["modules"].add(entry.get("module", "?"))
                t = entry.get("time", 0)
                if t > p["last_time"]:
                    p["last_time"] = t
                    p["last_module"] = entry.get("module", "?")
                    p["last_action"] = entry.get("action", "?")
                sev = entry.get("severity", 0)
                if sev > p["severity_max"]:
                    p["severity_max"] = sev
        # Convert sets to lists for Jinja
        player_list = []
        for uuid_str, data in players.items():
            data["uuid"] = uuid_str
            data["modules"] = list(data["modules"])
            data["last_time_str"] = _time.strftime(
                "%Y-%m-%d %H:%M", _time.gmtime(data["last_time"])
            ) if data["last_time"] else "Never"
            player_list.append(data)
        # Sort by count descending
        player_list.sort(key=lambda x: x["count"], reverse=True)
        return render_template_string(VIOLATIONS_HTML, players=player_list)

    @app.route("/violations/<uuid_str>")
    @login_required
    def violations_detail(uuid_str):
        """Show full violation history for a specific player."""
        import time as _time
        entries = _db_get("violations", uuid_str, [])
        if not isinstance(entries, list):
            entries = []
        player_name = "?"
        for e in entries:
            if isinstance(e, dict) and e.get("name", "?") != "?":
                player_name = e["name"]
        # Add formatted time and format evidence for display
        for e in entries:
            if isinstance(e, dict):
                t = e.get("time", 0)
                e["time_str"] = _time.strftime(
                    "%Y-%m-%d %H:%M:%S", _time.gmtime(t)
                ) if t else "?"
                # Format evidence dict into readable pairs
                ev = e.get("evidence", {})
                if isinstance(ev, dict):
                    e["desc"] = ev.get("desc", "")
                    e["evidence_items"] = [
                        (k, v) for k, v in ev.items() if k != "desc"
                    ]
                else:
                    e["desc"] = ""
                    e["evidence_items"] = []
        entries.reverse()  # newest first
        return render_template_string(
            VIOLATIONS_DETAIL_HTML,
            player_name=player_name,
            player_uuid=uuid_str,
            violations=entries,
            total=len(entries),
        )

    @app.route("/violations/<uuid_str>/clear", methods=["POST"])
    @login_required
    def violations_clear(uuid_str):
        """Clear all violations and baselines for a player."""
        try:
            _db_delete("violations", uuid_str)
        except Exception:
            pass
        try:
            _db_delete("baselines", uuid_str)
        except Exception:
            pass
        return redirect(url_for("violations_page"))

    @app.route("/violations/clear-all", methods=["POST"])
    @login_required
    def violations_clear_all():
        """Clear all violations and baselines for all players."""
        db = _get_db()
        try:
            db.execute("DELETE FROM [violations]")
            db.commit()
        except Exception:
            pass
        try:
            db.execute("DELETE FROM [baselines]")
            db.commit()
        except Exception:
            pass
        return redirect(url_for("violations_page"))

    # ── Trusted Links (Fingerprint Exemptions) ─────────────

    @app.route("/trusted-links")
    @login_required
    def trusted_links_page():
        """Manage trusted player pairs (family/household)."""
        import time as _time
        # Ensure table exists
        db = _get_db()
        db.execute("""CREATE TABLE IF NOT EXISTS [trusted_links] (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at REAL DEFAULT (julianday('now'))
        )""")
        db.commit()

        links = _db_get_all("trusted_links")
        # Also get all known players for dropdowns
        players = _db_get_all("players")
        player_list = []
        for item in players:
            if isinstance(item, dict):
                val = item.get("value", {})
                key = item.get("key", "")
                name = val.get("name", key[:8]) if isinstance(val, dict) else key[:8]
                player_list.append({"uuid": key, "name": name})
        player_list.sort(key=lambda p: p["name"].lower())

        # Format links for display
        link_list = []
        for item in links:
            if isinstance(item, dict):
                val = item.get("value", {})
                key = item.get("key", "")
            else:
                continue
            if isinstance(val, dict):
                link_list.append({
                    "key": key,
                    "name_a": val.get("name_a", key.split("|")[0][:8] if "|" in key else "?"),
                    "name_b": val.get("name_b", key.split("|")[1][:8] if "|" in key else "?"),
                    "uuid_a": val.get("uuid_a", ""),
                    "uuid_b": val.get("uuid_b", ""),
                    "created_at": _time.strftime(
                        "%Y-%m-%d %H:%M", _time.gmtime(val.get("created_at", 0))
                    ) if val.get("created_at") else "?",
                })

        return render_template_string(
            TRUSTED_LINKS_HTML,
            links=link_list,
            players=player_list,
            total=len(link_list),
        )

    @app.route("/trusted-links/add", methods=["POST"])
    @login_required
    def add_trusted_link():
        import time as _time
        uuid_a = request.form.get("uuid_a", "").strip()
        uuid_b = request.form.get("uuid_b", "").strip()
        if not uuid_a or not uuid_b or uuid_a == uuid_b:
            flash("Please select two different players.", "error")
            return redirect(url_for("trusted_links_page"))
        # Resolve names
        data_a = _db_get("players", uuid_a, {})
        data_b = _db_get("players", uuid_b, {})
        name_a = data_a.get("name", uuid_a[:8]) if isinstance(data_a, dict) else uuid_a[:8]
        name_b = data_b.get("name", uuid_b[:8]) if isinstance(data_b, dict) else uuid_b[:8]
        # Build deterministic key
        key = "|".join(sorted([uuid_a, uuid_b]))
        _db_set("trusted_links", key, {
            "uuid_a": uuid_a,
            "uuid_b": uuid_b,
            "name_a": name_a,
            "name_b": name_b,
            "created_at": _time.time(),
        })
        return redirect(url_for("trusted_links_page"))

    @app.route("/trusted-links/remove", methods=["POST"])
    @login_required
    def remove_trusted_link():
        key = request.form.get("key", "").strip()
        if key:
            _db_delete("trusted_links", key)
        return redirect(url_for("trusted_links_page"))

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
        <h1><img src="https://raw.githubusercontent.com/TheNINJALLO/endstone-paradox/main/Icon.png" alt="Paradox" style="width:28px;height:28px;border-radius:6px;vertical-align:middle;margin-right:8px;"> Paradox</h1>
        <span>AntiCheat Web Panel</span>
    </div>
    <div class="nav-section">Overview</div>
    <a class="nav-item" href="/"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg> Dashboard</a>
    <div class="nav-section">Management</div>
    <a class="nav-item" href="/modules"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg> Modules</a>
    <a class="nav-item" href="/bans"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg> Bans</a>
    <a class="nav-item" href="/players"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg> Players</a>
    <a class="nav-item" href="/permissions"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 11-7.778 7.778 5.5 5.5 0 017.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg> Permissions</a>
    <a class="nav-item" href="/antidupe"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="9" y1="12" x2="15" y2="12"/></svg> Anti-Dupe</a>
    <a class="nav-item" href="/logs"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg> Logs</a>
    <div class="nav-section">Intelligence</div>
    <a class="nav-item" href="/analytics"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg> Analytics</a>
    <a class="nav-item" href="/reports"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg> Reports</a>
    <a class="nav-item" href="/violations"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg> Violations</a>
    <a class="nav-item" href="/trusted-links"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="8.5" cy="7" r="4"/><path d="M20 8v6"/><path d="M23 11h-6"/></svg> Trusted Links</a>
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
<style>
.mod-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin-bottom: 32px; }
.mod-card {
    background: rgba(17,24,39,0.7); border: 1px solid rgba(34,197,94,0.15);
    border-radius: 12px; padding: 16px; transition: border-color 0.2s;
}
.mod-card:hover { border-color: rgba(34,197,94,0.4); }
.mod-card.off { opacity: 0.6; }
.mod-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.mod-name { font-weight: 700; font-size: 14px; color: #f3f4f6; text-transform: capitalize; }
.mod-badge { padding: 2px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; letter-spacing: 0.5px; }
.mod-badge.on { background: rgba(34,197,94,0.15); color: #22c55e; }
.mod-badge.off { background: rgba(239,68,68,0.15); color: #ef4444; }
.mod-toggle { margin-top: 10px; }
.mod-toggle form { display: inline; }
.mod-toggle button {
    padding: 6px 18px; border: none; border-radius: 8px; cursor: pointer;
    font-size: 12px; font-weight: 600; transition: all 0.2s;
}
.mod-toggle .btn-enable { background: rgba(34,197,94,0.2); color: #22c55e; }
.mod-toggle .btn-enable:hover { background: rgba(34,197,94,0.35); }
.mod-toggle .btn-disable { background: rgba(239,68,68,0.2); color: #ef4444; }
.mod-toggle .btn-disable:hover { background: rgba(239,68,68,0.35); }
.sens-row {
    display: flex; align-items: center; gap: 8px; margin-top: 10px;
    padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.06);
}
.sens-row input[type=range] { flex: 1; accent-color: #22c55e; height: 4px; }
.sens-val { min-width: 22px; color: #22c55e; font-weight: 700; font-size: 13px; text-align: center; }
.sens-btn {
    padding: 3px 10px; background: rgba(34,197,94,0.15); border: none;
    border-radius: 6px; color: #22c55e; font-size: 11px; font-weight: 600; cursor: pointer;
}
.sens-btn:hover { background: rgba(34,197,94,0.3); }
.section-title {
    font-size: 18px; font-weight: 700; color: #f3f4f6; margin: 24px 0 14px 0;
    padding-bottom: 8px; border-bottom: 1px solid rgba(34,197,94,0.2);
}
.section-sub { font-size: 13px; color: #9ca3af; font-weight: 400; margin-left: 8px; }
</style>
</head><body>
<div class="layout">
""" + SIDEBAR_HTML + """
<div class="main">
    <h2>Module Management</h2>

    <div class="section-title">🛡️ Detection Modules <span class="section-sub">Anti-cheat detection with adjustable sensitivity</span></div>
    <div class="mod-grid">
        {% for m in detection %}
        <div class="mod-card {% if not m.value %}off{% endif %}">
            <div class="mod-header">
                <span class="mod-name">{{ m.key }}</span>
                <span class="mod-badge {% if m.value %}on{% else %}off{% endif %}">{% if m.value %}ON{% else %}OFF{% endif %}</span>
            </div>
            <div class="mod-toggle">
                <form method="POST" action="/modules/{{ m.key }}/toggle">
                    <button type="submit" class="{% if m.value %}btn-disable{% else %}btn-enable{% endif %}">
                        {% if m.value %}Disable{% else %}Enable{% endif %}
                    </button>
                </form>
            </div>
            <form method="POST" action="/modules/{{ m.key }}/sensitivity" class="sens-row">
                <span style="color:#9ca3af;font-size:12px;">Sens:</span>
                <input type="range" name="sensitivity" min="1" max="10" value="{{ m.sensitivity }}"
                       oninput="this.nextElementSibling.textContent=this.value">
                <span class="sens-val">{{ m.sensitivity }}</span>
                <button type="submit" class="sens-btn">Set</button>
            </form>
        </div>
        {% endfor %}
    </div>

    <div class="section-title">⚙️ Server Features <span class="section-sub">Utilities and tools — toggle only</span></div>
    <div class="mod-grid">
        {% for m in utility %}
        <div class="mod-card {% if not m.value %}off{% endif %}">
            <div class="mod-header">
                <span class="mod-name">{{ m.key }}</span>
                <span class="mod-badge {% if m.value %}on{% else %}off{% endif %}">{% if m.value %}ON{% else %}OFF{% endif %}</span>
            </div>
            <div class="mod-toggle">
                <form method="POST" action="/modules/{{ m.key }}/toggle">
                    <button type="submit" class="{% if m.value %}btn-disable{% else %}btn-enable{% endif %}">
                        {% if m.value %}Disable{% else %}Enable{% endif %}
                    </button>
                </form>
            </div>
        </div>
        {% endfor %}
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

    <h3 style="margin:24px 0 12px;font-size:16px;color:#f3f4f6;">⚔️ Illegal Items Config</h3>
    <div class="card" style="margin-bottom:24px;">
        <form method="POST" action="/config" style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
            <div class="form-group" style="margin-bottom:0;">
                <label style="margin-bottom:4px;">Max Enchantment Level</label>
                <input type="number" name="max_enchant_level" value="{% for c in db_config %}{% if c.key == 'max_enchant_level' %}{{ c.value }}{% endif %}{% endfor %}{% set found = [] %}{% for c in db_config %}{% if c.key == 'max_enchant_level' %}{% if found.append(1) %}{% endif %}{% endif %}{% endfor %}{% if not found %}10{% endif %}" min="1" max="255" style="width:100px;">
            </div>
            <button type="submit" class="btn btn-sm btn-primary" style="margin-top:18px;">Save</button>
            <span style="font-size:12px;color:#6b7280;margin-top:18px;">Any enchantment above this level will be flagged and removed.</span>
        </form>
    </div>

    <h3 style="margin:24px 0 12px;font-size:16px;color:#f3f4f6;">🛡️ Enforcement Mode</h3>
    <div class="card" style="margin-bottom:24px;">
        <form method="POST" action="/config" style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
            <div class="form-group" style="margin-bottom:0;">
                <label style="margin-bottom:4px;">Mode</label>
                <select name="enforcement_mode" style="width:200px;padding:8px 12px;background:#1a1f2e;border:1px solid rgba(255,255,255,0.08);border-radius:8px;color:#e0e0e0;font-size:14px;">
                    {% set current_mode = '' %}{% for c in db_config %}{% if c.key == 'enforcement_mode' %}{% set current_mode = c.value %}{% endif %}{% endfor %}
                    <option value="logonly" {{ 'selected' if current_mode == 'logonly' else '' }}>📋 Log Only</option>
                    <option value="soft" {{ 'selected' if current_mode == 'soft' or not current_mode else '' }}>⚖️ Soft (Default)</option>
                    <option value="hard" {{ 'selected' if current_mode == 'hard' else '' }}>🔨 Hard</option>
                </select>
            </div>
            <button type="submit" class="btn btn-sm btn-primary" style="margin-top:18px;">Save</button>
            <span style="font-size:12px;color:#6b7280;margin-top:18px;">Log Only = log violations only. Soft = cancel/setback/kick. Hard = faster escalation.</span>
        </form>
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

# ── Global DB ──

GLOBAL_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paradox — Global Database</title>
""" + BASE_CSS + """
<style>
.stat-row { display:flex; gap:20px; flex-wrap:wrap; margin-bottom:24px; }
.stat-item { background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); border-radius:10px; padding:16px 20px; min-width:160px; }
.stat-label { font-size:11px; color:#6b7280; text-transform:uppercase; letter-spacing:0.5px; }
.stat-value { font-size:22px; font-weight:700; color:#f3f4f6; margin-top:4px; }
.cat-ban { color:#ef4444; }
.cat-high { color:#f59e0b; }
.cat-flag { color:#3b82f6; }
</style>
</head><body>
<div class="layout">
""" + SIDEBAR_HTML + """
<div class="main">
    <h2>🌍 Global Ban Database</h2>

    <div class="stat-row">
        <div class="stat-item">
            <div class="stat-label">Status</div>
            <div class="stat-value">{% if config.get('enabled', False) %}<span class="badge badge-on">Connected</span>{% else %}<span class="badge badge-off">Disabled</span>{% endif %}</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">API Key</div>
            <div class="stat-value">{% if config.get('api_key', '') %}<span class="badge badge-on">Registered</span>{% else %}<span class="badge badge-off">Pending</span>{% endif %}</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">Server Name</div>
            <div class="stat-value" style="font-size:16px;">{{ config.get('server_name', '') or 'Auto' }}</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">Sync Interval</div>
            <div class="stat-value">{{ config.get('sync_interval', 300) }}s</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">Global Bans</div>
            <div class="stat-value cat-ban">{{ global_bans|length }}</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">Flags / High-Risk</div>
            <div class="stat-value cat-high">{{ global_flags|length }}</div>
        </div>
    </div>

    <div class="card" style="margin-bottom:24px;">
        <h3 style="margin-bottom:12px;font-size:16px;color:#ef4444;">🚫 Global Bans ({{ global_bans|length }})</h3>
        <p style="font-size:12px;color:#6b7280;margin-bottom:12px;">Players banned across all servers — kicked on every join attempt.</p>
        <table>
        <tr><th>Player</th><th>Reason</th><th>Source</th></tr>
        {% for ban in global_bans %}
        <tr>
            <td style="color:#f87171;font-weight:600;">{{ ban.get('name', '') }}</td>
            <td>{{ ban.get('reason', '') }}</td>
            <td style="color:#6b7280;font-size:12px;">{{ ban.get('source', 'global') }}</td>
        </tr>
        {% endfor %}
        {% if not global_bans %}<tr><td colspan="3" style="text-align:center;color:#6b7280;">No global bans synced yet</td></tr>{% endif %}
        </table>
    </div>

    <div class="card">
        <h3 style="margin-bottom:12px;font-size:16px;color:#f59e0b;">⚠️ Flags &amp; High-Risk ({{ global_flags|length }})</h3>
        <p style="font-size:12px;color:#6b7280;margin-bottom:12px;">Players flagged across servers — staff alerted on join, NOT kicked.</p>
        <table>
        <tr><th>Player</th><th>Category</th><th>Reason</th><th>Source</th></tr>
        {% for flag in global_flags %}
        <tr>
            <td style="color:#fbbf24;font-weight:600;">{{ flag.get('name', '') }}</td>
            <td>{% if flag.get('category') == 'high_risk' %}<span class="cat-high">High Risk</span>{% else %}<span class="cat-flag">Flagged</span>{% endif %}</td>
            <td>{{ flag.get('reason', '') }}</td>
            <td style="color:#6b7280;font-size:12px;">{{ flag.get('source', 'global') }}</td>
        </tr>
        {% endfor %}
        {% if not global_flags %}<tr><td colspan="4" style="text-align:center;color:#6b7280;">No flags synced yet</td></tr>{% endif %}
        </table>
    </div>

    <p style="margin-top:16px;font-size:12px;color:#4b5563;">
        Data syncs automatically every {{ config.get('sync_interval', 300) }} seconds. Bans from <code>/ac-ban</code> and auto-bans from the violation engine are pushed to all servers.
    </p>
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

# -- Anti-Dupe Page --

ANTIDUPE_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paradox - Anti-Dupe Monitor</title>
""" + BASE_CSS + """
<style>
.event-card {
    background: rgba(15,21,32,0.6);
    border: 1px solid rgba(34,197,94,0.1);
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 12px;
}
.event-card:hover { border-color: rgba(34,197,94,0.3); }
.event-type {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.event-type.dupe { background: rgba(239,68,68,0.2); color: #ef4444; }
.event-type.info { background: rgba(59,130,246,0.2); color: #3b82f6; }
.event-type.warning { background: rgba(245,158,11,0.2); color: #f59e0b; }
.event-type.success { background: rgba(34,197,94,0.2); color: #22c55e; }
.event-time { color: #6b7280; font-size: 12px; font-family: monospace; }
.event-details { margin-top: 8px; font-size: 13px; color: #9ca3af; line-height: 1.6; }
.event-details strong { color: #e5e7eb; }
.section-title {
    font-size: 18px; font-weight: 700; color: #e5e7eb;
    margin: 24px 0 12px 0; display: flex; align-items: center; gap: 8px;
}
.section-title .count {
    background: rgba(34,197,94,0.15); color: #22c55e;
    padding: 2px 10px; border-radius: 12px; font-size: 13px; font-weight: 600;
}
.no-events { text-align: center; color: #4b5563; padding: 32px; font-size: 14px; }
.filter-bar { display: flex; gap: 8px; margin-bottom: 16px; }
.filter-bar input {
    flex: 1; padding: 8px 12px;
    background: rgba(15,21,32,0.8); border: 1px solid rgba(55,65,81,0.5);
    border-radius: 8px; color: #e5e7eb; font-size: 13px;
}
</style>
</head><body>
<div class="layout">
""" + SIDEBAR_HTML + """
<div class="main">
    <h1>Anti-Dupe Monitor</h1>
    <p style="color:#6b7280;margin-bottom:16px;">Tracks suspected duplication exploits across 4 detection layers: bundle blocking, hopper cluster monitoring, piston entity tracking, and packet analysis.</p>

    <div class="filter-bar">
        <input type="text" id="searchFilter" placeholder="Search events by player, type, location..." onkeyup="filterEvents()">
    </div>

    <div class="section-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="9" y1="12" x2="15" y2="12"/></svg>
        Dupe Detection Events
        <span class="count">{{ antidupe_events|length }}</span>
    </div>
    {% for event in antidupe_events|reverse %}
    <div class="event-card event-item">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <span class="event-type {% if 'dupe' in event.type %}dupe{% elif 'rapid' in event.type %}warning{% else %}info{% endif %}">{{ event.type }}</span>
            <span class="event-time">{{ event.time|int }}</span>
        </div>
        <div class="event-details">
            {% for k, v in event.details.items() %}
            <div><strong>{{ k }}:</strong> {{ v }}</div>
            {% endfor %}
        </div>
    </div>
    {% endfor %}
    {% if not antidupe_events %}
    <div class="no-events">No dupe detection events recorded yet. Enable the antidupe module to start monitoring.</div>
    {% endif %}

    <div class="section-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        Crash-Drop Events
        <span class="count">{{ crashdrop_events|length }}</span>
    </div>
    {% for event in crashdrop_events|reverse %}
    <div class="event-card event-item">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <span class="event-type {% if 'removed' in event.type %}success{% elif 'rapid' in event.type %}dupe{% else %}info{% endif %}">{{ event.type }}</span>
            <span class="event-time">{{ event.time|int }}</span>
        </div>
        <div class="event-details">
            {% for k, v in event.details.items() %}
            <div><strong>{{ k }}:</strong> {{ v }}</div>
            {% endfor %}
        </div>
    </div>
    {% endfor %}
    {% if not crashdrop_events %}
    <div class="no-events">No crash-drop events recorded yet. Enable the crashdrop module to start monitoring.</div>
    {% endif %}

    <div class="section-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16"/></svg>
        Inventory Sync Events
        <span class="count">{{ invsync_events|length }}</span>
    </div>
    {% for event in invsync_events|reverse %}
    <div class="event-card event-item">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <span class="event-type warning">{{ event.type }}</span>
            <span class="event-time">{{ event.time|int }}</span>
        </div>
        <div class="event-details">
            {% for k, v in event.details.items() %}
            <div><strong>{{ k }}:</strong> {{ v }}</div>
            {% endfor %}
        </div>
    </div>
    {% endfor %}
    {% if not invsync_events %}
    <div class="no-events">No inventory sync events recorded yet. Enable the invsync module to start monitoring.</div>
    {% endif %}
</div>
</div>
<script>
function filterEvents() {
    const q = document.getElementById('searchFilter').value.toLowerCase();
    document.querySelectorAll('.event-item').forEach(el => {
        el.style.display = el.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
}
</script>
</body></html>"""


# ── Analytics Dashboard (Tier 3) ──

ANALYTICS_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paradox — Analytics</title>
""" + BASE_CSS + """
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
.chart-container {
    background: rgba(15,21,32,0.8);
    border: 1px solid rgba(34,197,94,0.1);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
}
.chart-container canvas { width: 100% !important; max-height: 300px; }
.chart-title {
    font-size: 16px; font-weight: 600; color: #f3f4f6;
    margin-bottom: 16px;
    display: flex; align-items: center; gap: 8px;
}
.stat-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.stat-card {
    background: rgba(15,21,32,0.8);
    border: 1px solid rgba(34,197,94,0.1);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}
.stat-number { font-size: 32px; font-weight: 700; color: #22c55e; }
.stat-label { font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }
.module-bars { display: grid; gap: 8px; }
.module-bar {
    display: flex; align-items: center; gap: 12px;
}
.module-bar-name { width: 120px; font-size: 13px; color: #9ca3af; text-align: right; }
.module-bar-fill {
    flex: 1; height: 24px; background: rgba(34,197,94,0.1); border-radius: 6px; overflow: hidden;
    position: relative;
}
.module-bar-fill .bar {
    height: 100%; background: linear-gradient(90deg, #22c55e, #10b981);
    border-radius: 6px; transition: width 0.5s;
    display: flex; align-items: center; padding-left: 8px;
    font-size: 11px; font-weight: 600; color: #fff;
}
</style>
</head><body>
<div class="layout">
""" + SIDEBAR_HTML + """
<div class="main">
    <h2 style="display:flex;align-items:center;gap:16px;">📊 Analytics Dashboard
        <form method="POST" action="/analytics/clear" style="margin-left:auto;" onsubmit="return confirm('Clear ALL analytics data? This cannot be undone.');">
            <button type="submit" class="btn btn-sm btn-danger">🗑️ Clear Analytics</button>
        </form>
    </h2>

    <div id="stats-row" class="stat-row">
        <div class="stat-card"><div class="stat-number" id="total-violations">—</div><div class="stat-label">Violations (24h)</div></div>
        <div class="stat-card"><div class="stat-number info" id="unique-players">—</div><div class="stat-label">Unique Players</div></div>
        <div class="stat-card"><div class="stat-number warn" id="total-actions">—</div><div class="stat-label">Actions Taken</div></div>
        <div class="stat-card"><div class="stat-number" id="top-module">—</div><div class="stat-label">Top Module</div></div>
    </div>

    <div class="chart-container">
        <div class="chart-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
            Violations Over Time (24 Hours)
        </div>
        <canvas id="violationChart"></canvas>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;">
        <div class="chart-container">
            <div class="chart-title">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2"><circle cx="12" cy="12" r="10"/></svg>
                Violations by Module
            </div>
            <div id="module-bars" class="module-bars"></div>
        </div>

        <div class="chart-container">
            <div class="chart-title">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
                Enforcement Actions
            </div>
            <canvas id="actionsChart"></canvas>
        </div>
    </div>
</div>
</div>

<script>
const chartColors = {
    green: 'rgba(34, 197, 94, 0.8)',
    greenBg: 'rgba(34, 197, 94, 0.1)',
    blue: 'rgba(59, 130, 246, 0.8)',
    yellow: 'rgba(245, 158, 11, 0.8)',
    red: 'rgba(239, 68, 68, 0.8)',
    purple: 'rgba(168, 85, 247, 0.8)',
};

async function loadAnalytics() {
    try {
        const resp = await fetch('/api/analytics/violations?hours=24');
        const data = await resp.json();

        // Stats
        let totalViols = 0, allPlayers = 0, allActions = 0, moduleCounts = {};
        data.forEach(h => {
            totalViols += h.violations;
            allPlayers += h.player_count;
            Object.entries(h.modules || {}).forEach(([m, c]) => {
                moduleCounts[m] = (moduleCounts[m] || 0) + c;
            });
            Object.values(h.actions || {}).forEach(c => allActions += c);
        });

        document.getElementById('total-violations').textContent = totalViols;
        document.getElementById('unique-players').textContent = allPlayers;
        document.getElementById('total-actions').textContent = allActions;

        const topMod = Object.entries(moduleCounts).sort((a,b) => b[1]-a[1])[0];
        document.getElementById('top-module').textContent = topMod ? topMod[0] : 'None';

        // Line chart
        const labels = data.map(h => h.hour.split('T')[1] + ':00');
        const values = data.map(h => h.violations);
        new Chart(document.getElementById('violationChart'), {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: 'Violations',
                    data: values,
                    borderColor: chartColors.green,
                    backgroundColor: chartColors.greenBg,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 2,
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#6b7280', maxTicksLimit: 12 } },
                    y: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#6b7280' }, beginAtZero: true }
                }
            }
        });

        // Module bars
        const barContainer = document.getElementById('module-bars');
        const maxCount = Math.max(...Object.values(moduleCounts), 1);
        const sorted = Object.entries(moduleCounts).sort((a,b) => b[1]-a[1]).slice(0, 10);
        sorted.forEach(([mod, count]) => {
            const pct = (count / maxCount * 100).toFixed(0);
            barContainer.innerHTML += `
                <div class="module-bar">
                    <div class="module-bar-name">${mod}</div>
                    <div class="module-bar-fill"><div class="bar" style="width:${pct}%">${count}</div></div>
                </div>`;
        });
        if (sorted.length === 0) {
            barContainer.innerHTML = '<div style="color:#6b7280;text-align:center;padding:20px;">No violation data yet</div>';
        }

        // Actions doughnut chart
        const actionLabels = Object.keys(data.reduce((acc, h) => { Object.keys(h.actions || {}).forEach(a => acc[a]=1); return acc; }, {}));
        const actionValues = actionLabels.map(a => data.reduce((s, h) => s + (h.actions?.[a] || 0), 0));
        const actionColors = [chartColors.yellow, chartColors.red, chartColors.blue, chartColors.green, chartColors.purple];
        if (actionLabels.length > 0) {
            new Chart(document.getElementById('actionsChart'), {
                type: 'doughnut',
                data: {
                    labels: actionLabels,
                    datasets: [{ data: actionValues, backgroundColor: actionColors.slice(0, actionLabels.length), borderWidth: 0 }]
                },
                options: {
                    responsive: true,
                    plugins: { legend: { position: 'bottom', labels: { color: '#9ca3af', padding: 12 } } }
                }
            });
        } else {
            document.getElementById('actionsChart').parentElement.innerHTML += '<div style="color:#6b7280;text-align:center;padding:20px;">No action data yet</div>';
        }

    } catch (err) {
        console.error('Analytics load error:', err);
    }
}

loadAnalytics();
</script>
</body></html>"""


# ── Reports Queue (Tier 3) ──

REPORTS_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paradox — Reports</title>
""" + BASE_CSS + """
<style>
.report-card {
    background: rgba(15,21,32,0.8);
    border: 1px solid rgba(34,197,94,0.1);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 12px;
    transition: border-color 0.2s;
}
.report-card:hover { border-color: rgba(34,197,94,0.3); }
.report-card.priority { border-left: 3px solid #f59e0b; }
.report-card.claimed { border-left: 3px solid #3b82f6; }
.report-card.resolved { border-left: 3px solid #22c55e; opacity: 0.6; }
.report-header {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 12px;
}
.report-target { font-size: 16px; font-weight: 600; color: #f3f4f6; }
.report-meta { font-size: 12px; color: #6b7280; }
.report-reason { color: #9ca3af; font-size: 14px; margin-bottom: 12px; }
.report-footer { display: flex; gap: 8px; align-items: center; }
.report-actions { display: flex; gap: 8px; margin-left: auto; }
.filter-bar {
    display: flex; gap: 12px; margin-bottom: 24px; align-items: center;
}
.filter-btn {
    padding: 6px 14px; border-radius: 8px; font-size: 13px; font-weight: 500;
    border: 1px solid rgba(255,255,255,0.1); background: transparent;
    color: #9ca3af; cursor: pointer; transition: all 0.2s;
}
.filter-btn.active, .filter-btn:hover {
    background: rgba(34,197,94,0.1); border-color: #22c55e; color: #22c55e;
}
.empty-state {
    text-align: center; padding: 60px 20px; color: #6b7280;
}
.empty-state svg { margin-bottom: 16px; opacity: 0.5; }
</style>
</head><body>
<div class="layout">
""" + SIDEBAR_HTML + """
<div class="main">
    <h2 style="display:flex;align-items:center;gap:16px;">📋 Player Reports
        <form method="POST" action="/reports/clear-all" style="margin-left:auto;" onsubmit="return confirm('Delete ALL reports? This cannot be undone.');">
            <button type="submit" class="btn btn-sm btn-danger">🗑️ Clear All</button>
        </form>
    </h2>

    <div class="filter-bar">
        <button class="filter-btn active" onclick="filterReports('all')">All</button>
        <button class="filter-btn" onclick="filterReports('priority')">⚠ Priority</button>
        <button class="filter-btn" onclick="filterReports('open')">Open</button>
        <button class="filter-btn" onclick="filterReports('claimed')">Claimed</button>
        <button class="filter-btn" onclick="filterReports('resolved')">Resolved</button>
        <span style="margin-left:auto;color:#6b7280;font-size:13px;">{{ reports|length }} total reports</span>
    </div>

    {% if reports %}
    {% for r in reports %}
    <div class="report-card {{ r.status }}" data-status="{{ r.status }}">
        <div class="report-header">
            <div>
                <span class="report-target">{{ r.target }}</span>
                <span class="badge {% if r.status == 'priority' %}badge-warn{% elif r.status == 'open' %}badge-on{% elif r.status == 'claimed' %}badge-off{% else %}badge-on{% endif %}" style="margin-left:8px;">{{ r.status|upper }}</span>
            </div>
            <div class="report-meta">
                ID: {{ r.id or r.get('id', '?') }} &bull; Reported by {{ r.reporter }}
            </div>
        </div>
        <div class="report-reason">{{ r.reason }}</div>
        <div class="report-footer">
            <span class="report-meta">
                {% if r.claimed_by %}Claimed by: {{ r.claimed_by }}{% endif %}
                {% if r.resolution %} &bull; Resolution: {{ r.resolution }}{% endif %}
            </span>
            <div class="report-actions">
                {% if r.status in ['open', 'priority'] %}
                <form method="POST" action="/reports/claim" style="display:inline;">
                    <input type="hidden" name="report_id" value="{{ r.id or r.get('id', '') }}">
                    <button type="submit" class="btn btn-primary btn-sm">Claim</button>
                </form>
                {% endif %}
                {% if r.status != 'resolved' %}
                <form method="POST" action="/reports/resolve" style="display:inline;">
                    <input type="hidden" name="report_id" value="{{ r.id or r.get('id', '') }}">
                    <input type="hidden" name="resolution" value="Resolved via Web UI">
                    <button type="submit" class="btn btn-sm" style="background:rgba(34,197,94,0.2);color:#22c55e;">Resolve</button>
                </form>
                {% endif %}
                <form method="POST" action="/reports/delete" style="display:inline;" onsubmit="return confirm('Delete this report?');">
                    <input type="hidden" name="report_id" value="{{ r.id or r.get('id', '') }}">
                    <button type="submit" class="btn btn-sm btn-danger">🗑️</button>
                </form>
            </div>
        </div>
    </div>
    {% endfor %}
    {% else %}
    <div class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
        <div style="font-size:16px;font-weight:600;margin-bottom:4px;">No Reports Yet</div>
        <div>Player reports submitted via /ac-report will appear here.</div>
    </div>
    {% endif %}
</div>
</div>
<script>
function filterReports(status) {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    document.querySelectorAll('.report-card').forEach(card => {
        if (status === 'all' || card.dataset.status === status) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}
</script>
</body></html>"""

# ── Violations List Page ──

VIOLATIONS_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paradox — Violations</title>
""" + BASE_CSS + """
<style>
.player-row {
    display: grid;
    grid-template-columns: 1fr auto auto auto auto;
    align-items: center;
    gap: 16px;
    padding: 14px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.03);
    text-decoration: none;
    color: inherit;
    transition: background 0.15s;
}
.player-row:hover { background: rgba(34,197,94,0.05); cursor: pointer; }
.player-name { font-weight: 600; font-size: 15px; color: #f3f4f6; }
.player-uuid { font-size: 11px; color: #6b7280; font-family: monospace; }
.viol-count {
    display: inline-flex; align-items: center; justify-content: center;
    min-width: 36px; height: 28px;
    border-radius: 14px;
    font-size: 13px; font-weight: 700;
    padding: 0 10px;
}
.viol-low { background: rgba(59,130,246,0.15); color: #60a5fa; }
.viol-medium { background: rgba(245,158,11,0.15); color: #fbbf24; }
.viol-high { background: rgba(239,68,68,0.15); color: #f87171; }
.viol-critical { background: rgba(220,38,38,0.25); color: #ef4444; }
.module-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.module-tag {
    font-size: 10px; padding: 2px 8px; border-radius: 10px;
    background: rgba(34,197,94,0.1); color: #22c55e;
    font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;
}
.meta-text { font-size: 12px; color: #9ca3af; }
.search-box {
    margin-bottom: 16px;
}
.search-box input {
    max-width: 400px;
}
</style>
</head><body>
<div class="layout">
""" + SIDEBAR_HTML + """
<div class="main">
<h2 style="display:flex;align-items:center;gap:16px;">⚠️ Violations
    <form method="POST" action="/violations/clear-all" style="margin-left:auto;" onsubmit="return confirm('Clear ALL violations and baselines for ALL players?');">
        <button type="submit" class="btn btn-sm btn-danger">🗑️ Clear All</button>
    </form>
</h2>
<p style="color:#9ca3af;margin-bottom:20px;font-size:14px;">All players flagged by detection modules. Click a player to view full violation history.</p>

<div class="search-box">
    <input type="text" id="searchInput" placeholder="Search by player name..." oninput="filterPlayers()">
</div>

<div class="table-wrap">
    <div style="padding:12px 20px;background:rgba(34,197,94,0.08);display:grid;grid-template-columns:1fr auto auto auto auto;gap:16px;font-size:12px;text-transform:uppercase;letter-spacing:1px;color:#9ca3af;font-weight:600;">
        <div>Player</div>
        <div>Violations</div>
        <div>Max Severity</div>
        <div>Modules</div>
        <div>Last Seen</div>
    </div>
    <div id="playerList">
    {% if players %}
    {% for p in players %}
    <a class="player-row" href="/violations/{{ p.uuid }}" data-name="{{ p.name|lower }}">
        <div>
            <div class="player-name">{{ p.name }}</div>
            <div class="player-uuid">{{ p.uuid }}</div>
        </div>
        <div>
            <span class="viol-count {% if p.count >= 20 %}viol-critical{% elif p.count >= 10 %}viol-high{% elif p.count >= 5 %}viol-medium{% else %}viol-low{% endif %}">{{ p.count }}</span>
        </div>
        <div>
            <span class="badge {% if p.severity_max >= 4 %}badge-off{% elif p.severity_max >= 3 %}badge-warn{% else %}badge-on{% endif %}">{{ {1:'Info',2:'Low',3:'Medium',4:'High',5:'Critical'}.get(p.severity_max, 'Unknown') }}</span>
        </div>
        <div class="module-tags">
            {% for m in p.modules[:4] %}<span class="module-tag">{{ m }}</span>{% endfor %}
            {% if p.modules|length > 4 %}<span class="module-tag" style="background:rgba(107,114,128,0.2);color:#9ca3af;">+{{ p.modules|length - 4 }}</span>{% endif %}
        </div>
        <div class="meta-text">{{ p.last_time_str }}</div>
    </a>
    {% endfor %}
    {% else %}
    <div style="padding:48px;text-align:center;color:#6b7280;">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom:12px;"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        <div style="font-size:16px;font-weight:600;margin-bottom:4px;">No Violations Recorded</div>
        <div>Violations from detection modules will appear here as players are flagged.</div>
    </div>
    {% endif %}
    </div>
</div>
</div>
</div>
<script>
function filterPlayers() {
    const q = document.getElementById('searchInput').value.toLowerCase();
    document.querySelectorAll('.player-row').forEach(row => {
        row.style.display = row.dataset.name.includes(q) ? '' : 'none';
    });
}
</script>
</body></html>"""

# ── Violations Detail Page ──

VIOLATIONS_DETAIL_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paradox — {{ player_name }} Violations</title>
""" + BASE_CSS + """
<style>
.back-link {
    display: inline-flex; align-items: center; gap: 6px;
    color: #22c55e; text-decoration: none; font-size: 13px;
    margin-bottom: 16px;
    font-weight: 500;
}
.back-link:hover { text-decoration: underline; }
.player-header {
    background: rgba(15,21,32,0.8);
    border: 1px solid rgba(34,197,94,0.1);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.player-header h3 { font-size: 20px; font-weight: 700; color: #f3f4f6; }
.player-header .uuid { font-size: 12px; color: #6b7280; font-family: monospace; margin-top: 4px; }
.violation-card {
    background: rgba(15,21,32,0.8);
    border: 1px solid rgba(34,197,94,0.08);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 10px;
    transition: border-color 0.15s;
}
.violation-card:hover { border-color: rgba(34,197,94,0.25); }
.violation-card.sev-5 { border-left: 3px solid #ef4444; }
.violation-card.sev-4 { border-left: 3px solid #f97316; }
.violation-card.sev-3 { border-left: 3px solid #f59e0b; }
.violation-card.sev-2 { border-left: 3px solid #3b82f6; }
.violation-card.sev-1 { border-left: 3px solid #6b7280; }
.violation-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}
.violation-module {
    font-weight: 600; font-size: 14px; color: #f3f4f6;
    text-transform: uppercase; letter-spacing: 0.5px;
}
.violation-time { font-size: 12px; color: #6b7280; }
.violation-meta {
    display: flex; gap: 12px; flex-wrap: wrap;
    margin-bottom: 8px;
}
.violation-meta span {
    font-size: 12px; padding: 3px 10px;
    border-radius: 6px; background: rgba(255,255,255,0.04);
    color: #9ca3af;
}
.evidence-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 8px;
    margin-top: 8px;
}
.evidence-item {
    background: rgba(0,0,0,0.3);
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
}
.evidence-key { color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; font-size: 10px; }
.evidence-val { color: #e0e0e0; font-family: monospace; margin-top: 2px; word-break: break-all; }
.filter-bar {
    display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;
}
.filter-btn {
    padding: 6px 14px; border-radius: 20px; font-size: 12px;
    font-weight: 600; border: 1px solid rgba(255,255,255,0.08);
    background: rgba(15,21,32,0.8); color: #9ca3af;
    cursor: pointer; transition: all 0.15s;
}
.filter-btn:hover, .filter-btn.active {
    background: rgba(34,197,94,0.15); color: #22c55e;
    border-color: rgba(34,197,94,0.3);
}
</style>
</head><body>
<div class="layout">
""" + SIDEBAR_HTML + """
<div class="main">
<a class="back-link" href="/violations">&larr; Back to Violations</a>
<div class="player-header">
    <div>
        <h3>{{ player_name }}</h3>
        <div class="uuid">{{ player_uuid }}</div>
    </div>
    <div style="text-align:right;display:flex;align-items:center;gap:16px;">
        <div>
            <div style="font-size:28px;font-weight:700;color:#ef4444;">{{ total }}</div>
            <div style="font-size:12px;color:#6b7280;text-transform:uppercase;">Total Violations</div>
        </div>
        <form method="POST" action="/violations/{{ player_uuid }}/clear" onsubmit="return confirm('Clear all violations and baselines for {{ player_name }}?');">
            <button type="submit" class="btn btn-sm btn-danger">🗑️ Clear</button>
        </form>
    </div>
</div>

<div class="filter-bar">
    <button class="filter-btn active" onclick="filterViolations('all')">All</button>
    <button class="filter-btn" onclick="filterViolations('5')">🔴 Critical</button>
    <button class="filter-btn" onclick="filterViolations('4')">🟠 High</button>
    <button class="filter-btn" onclick="filterViolations('3')">🟡 Medium</button>
    <button class="filter-btn" onclick="filterViolations('2')">🔵 Low</button>
    <button class="filter-btn" onclick="filterViolations('1')">⚪ Info</button>
</div>

{% if violations %}
{% for v in violations %}
<div class="violation-card sev-{{ v.severity|default(1) }}" data-severity="{{ v.severity|default(1) }}">
    <div class="violation-top">
        <span class="violation-module">{{ v.module|default('?') }}</span>
        <span class="violation-time">{{ v.time_str }}</span>
    </div>
    <div class="violation-meta">
        <span>Severity: <strong>{{ {1:'Info',2:'Low',3:'Medium',4:'High',5:'Critical'}.get(v.severity|default(1), '?') }}</strong></span>
        <span>Action: <strong>{{ v.action|default('?') }}</strong></span>
    </div>
    {% if v.desc %}
    <div style="padding:8px 14px;background:rgba(99,102,241,0.10);border-left:3px solid #6366f1;border-radius:6px;margin:8px 0;font-size:13px;color:#c7d2fe;">
        {{ v.desc }}
    </div>
    {% endif %}
    {% if v.evidence_items %}
    <div class="evidence-grid">
        {% for key, val in v.evidence_items %}
        <div class="evidence-item">
            <div class="evidence-key">{{ key }}</div>
            <div class="evidence-val">{{ val }}</div>
        </div>
        {% endfor %}
    </div>
    {% endif %}
</div>
{% endfor %}
{% else %}
<div style="padding:48px;text-align:center;color:#6b7280;">
    <div style="font-size:16px;font-weight:600;">No violation data found for this player.</div>
</div>
{% endif %}
</div>
</div>
<script>
function filterViolations(sev) {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');
    document.querySelectorAll('.violation-card').forEach(card => {
        if (sev === 'all' || card.dataset.severity === sev) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}
</script>
</body></html>"""

# ── Trusted Links Page ──

TRUSTED_LINKS_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paradox — Trusted Links</title>
""" + BASE_CSS + """</head><body>
<div class="layout">
""" + SIDEBAR_HTML + """
<div class="main">
<h2>🤝 Trusted Links</h2>
<p style="color:#9ca3af;margin-bottom:24px;">Trusted links exempt pairs of players (family, spouses, roommates) from alt-account detection and ban-evasion enforcement. Players sharing the same IP or device will not be flagged if linked here.</p>

<!-- Add form -->
<div class="card" style="margin-bottom:24px;">
<h3 style="font-size:16px;color:#f3f4f6;margin-bottom:16px;">➕ Add Trusted Pair</h3>
<form method="POST" action="/trusted-links/add">
<div class="form-row">
<div class="form-group" style="flex:1;">
    <label>Player A</label>
    <select name="uuid_a" required>
        <option value="">Select player...</option>
        {% for p in players %}
        <option value="{{ p.uuid }}">{{ p.name }}</option>
        {% endfor %}
    </select>
</div>
<div style="padding-bottom:16px;color:#6b7280;font-size:20px;">↔</div>
<div class="form-group" style="flex:1;">
    <label>Player B</label>
    <select name="uuid_b" required>
        <option value="">Select player...</option>
        {% for p in players %}
        <option value="{{ p.uuid }}">{{ p.name }}</option>
        {% endfor %}
    </select>
</div>
<div style="padding-bottom:16px;"><button type="submit" class="btn">Link</button></div>
</div>
</form>
</div>

<!-- Existing links -->
{% if links %}
<div class="card-grid" style="grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));">
{% for link in links %}
<div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
            <span style="color:#22c55e;font-weight:600;">{{ link.name_a }}</span>
            <span style="color:#6b7280;"> ↔ </span>
            <span style="color:#22c55e;font-weight:600;">{{ link.name_b }}</span>
        </div>
        <form method="POST" action="/trusted-links/remove" style="margin:0;">
            <input type="hidden" name="key" value="{{ link.key }}">
            <button type="submit" class="btn btn-danger btn-sm" onclick="return confirm('Remove this trusted link?')">✕</button>
        </form>
    </div>
    <div style="margin-top:8px;font-size:12px;color:#6b7280;">Created: {{ link.created_at }}</div>
</div>
{% endfor %}
</div>
{% else %}
<div class="placeholder-card">
    <p>No trusted links configured yet.</p>
    <p style="font-size:13px;margin-top:8px;">Use the form above or <code>/ac-fingerprint trust &lt;A&gt; &lt;B&gt;</code> in-game.</p>
</div>
{% endif %}

<div style="margin-top:24px;font-size:13px;color:#6b7280;">
    <strong>Total pairs:</strong> {{ total }}
</div>
</div>
</div>
</body></html>"""
