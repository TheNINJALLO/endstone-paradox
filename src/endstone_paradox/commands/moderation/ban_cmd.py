# ban_cmd - /ac-ban Command

import time


def handle_ban(plugin, sender, args) -> bool:
    """Handle /ac-ban <player> [reason]"""
    if not args:
        sender.send_message("§2[§7Paradox§2]§c Usage: /ac-ban <player> [reason]")
        return False

    args_list = args if isinstance(args, list) else [str(args)]
    target_name = args_list[0]
    reason = " ".join(args_list[1:]) if len(args_list) > 1 else "Banned by an admin"

    # Find target
    target = None
    for p in plugin.server.online_players:
        if p.name.lower() == target_name.lower():
            target = p
            break

    if target is not None:
        # Can't ban Level 4 players
        if plugin.security.is_level4(target):
            sender.send_message("§2[§7Paradox§2]§c Cannot ban a Level 4 player.")
            return False

        uuid_str = str(target.unique_id)
        plugin.db.set("bans", uuid_str, {
            "name": target.name,
            "reason": reason,
            "banned_by": sender.name,
            "time": time.time(),
        })
        # Also store by name for offline lookup
        plugin.db.set("bans", target.name.lower(), {
            "name": target.name,
            "uuid": uuid_str,
            "reason": reason,
            "banned_by": sender.name,
            "time": time.time(),
        })
        target.kick(f"§cBanned: {reason}")
        sender.send_message(f"§2[§7Paradox§2]§a Banned {target.name}: {reason}")
        plugin.send_to_level4(f"§2[§7Paradox§2]§c {sender.name} banned {target.name}: {reason}")
    else:
        # Offline ban by name
        plugin.db.set("bans", target_name.lower(), {
            "name": target_name,
            "reason": reason,
            "banned_by": sender.name,
            "time": time.time(),
        })
        sender.send_message(f"§2[§7Paradox§2]§a Banned (offline) {target_name}: {reason}")

    return True
