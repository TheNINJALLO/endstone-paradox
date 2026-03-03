# watch_cmd.py - /ac-watch <player> [minutes] - Stream violations in real-time


def handle_watch(plugin, sender, args):
    """Start or stop watching a player's violations."""
    if not args or not args[0].strip():
        sender.send_message("§2[§7Paradox§2]§e Usage: /ac-watch <player> [minutes]")
        sender.send_message("§2[§7Paradox§2]§7 Use /ac-watch stop to stop watching.")
        return True

    parts = args[0].split()
    engine = plugin.violation_engine
    if not engine:
        sender.send_message("§2[§7Paradox§2]§c Violation engine not available.")
        return True

    watcher_uuid = str(sender.unique_id)

    if parts[0].lower() == "stop":
        engine.remove_watcher(watcher_uuid)
        sender.send_message("§2[§7Paradox§2]§a Stopped watching.")
        return True

    target_name = parts[0]
    minutes = 5
    if len(parts) > 1:
        try:
            minutes = int(parts[1])
        except ValueError:
            minutes = 5

    # Find target
    target_uuid = None
    for p in plugin.server.online_players:
        if p.name.lower() == target_name.lower():
            target_uuid = str(p.unique_id)
            target_name = p.name
            break

    if target_uuid is None:
        sender.send_message(f"§2[§7Paradox§2]§c Player '{target_name}' not found online.")
        return True

    engine.add_watcher(watcher_uuid, target_uuid, minutes * 60)
    sender.send_message(
        f"§2[§7Paradox§2]§a Now watching §c{target_name}§a for {minutes} minutes. "
        f"Use §e/ac-watch stop§a to stop."
    )
    return True
