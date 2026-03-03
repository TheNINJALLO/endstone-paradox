# case_cmd.py - /ac-case <player> [count] - View violation evidence

import time


def handle_case(plugin, sender, args):
    """Show last N violation entries for a player."""
    if not args:
        sender.send_message("§2[§7Paradox§2]§e Usage: /ac-case <player> [count]")
        return True

    # Parse player name and optional count
    parts = args[0].split() if args else []
    if not parts:
        sender.send_message("§2[§7Paradox§2]§e Usage: /ac-case <player> [count]")
        return True

    target_name = parts[0]
    count = 5
    if len(parts) > 1:
        try:
            count = int(parts[1])
        except ValueError:
            count = 5

    # Find player UUID
    target_uuid = None
    for p in plugin.server.online_players:
        if p.name.lower() == target_name.lower():
            target_uuid = str(p.unique_id)
            target_name = p.name
            break

    if target_uuid is None:
        # Try to find in player records
        all_players = plugin.db.get_all("players")
        for uuid, data in all_players.items():
            if isinstance(data, dict) and data.get("name", "").lower() == target_name.lower():
                target_uuid = uuid
                break

    if target_uuid is None:
        sender.send_message(f"§2[§7Paradox§2]§c Player '{target_name}' not found.")
        return True

    engine = plugin.violation_engine
    if not engine:
        sender.send_message("§2[§7Paradox§2]§c Violation engine not available.")
        return True

    entries = engine.get_recent(target_uuid, count)

    if not entries:
        sender.send_message(f"§2[§7Paradox§2]§7 No violations recorded for §f{target_name}§7.")
        return True

    sender.send_message(f"§2[§7Paradox§2]§e Last {len(entries)} violations for §c{target_name}§e:")
    for entry in entries[-count:]:
        t = entry.get("time", 0)
        ago = int(time.time() - t)
        module = entry.get("module", "?")
        severity = entry.get("severity", 0)
        action = entry.get("action", "?")
        evidence = entry.get("evidence", {})
        ev_str = ", ".join(f"{k}={v}" for k, v in evidence.items())
        sender.send_message(
            f"  §7{ago}s ago §e{module} §7[sev={severity}] §f{ev_str} §7→ {action}"
        )

    return True
