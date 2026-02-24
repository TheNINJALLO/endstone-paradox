"""
Paradox AntiCheat - /ac-punish Command

Apply a configurable punishment to a player.
Actions: warn, kick, tempban, ban, smite (lightning)
"""

import time


def handle_punish(plugin, sender, args) -> bool:
    """Handle /ac-punish <player> <action>"""
    if not args or len(args) < 2:
        sender.send_message(
            "§2[§7Paradox§2]§c Usage: /ac-punish <player> <warn|kick|tempban|ban|smite>"
        )
        return False

    args_list = args if isinstance(args, list) else str(args).split()
    target_name = args_list[0]
    action = args_list[1].lower()

    target = None
    for p in plugin.server.online_players:
        if p.name.lower() == target_name.lower():
            target = p
            break

    if target is None:
        sender.send_message(f"§2[§7Paradox§2]§c Player '{target_name}' not found online.")
        return False

    if plugin.security.is_level4(target):
        sender.send_message("§2[§7Paradox§2]§c Cannot punish a Level 4 player.")
        return False

    if action == "warn":
        target.send_message(
            f"§2[§7Paradox§2]§e§l WARNING: §r§eYou have been warned by {sender.name}."
        )
        sender.send_message(f"§2[§7Paradox§2]§a Warned {target.name}.")

    elif action == "kick":
        target.kick(f"§cPunished by {sender.name}")
        sender.send_message(f"§2[§7Paradox§2]§a Kicked {target.name}.")

    elif action == "tempban":
        duration = 3600  # 1 hour default
        uuid_str = str(target.unique_id)
        plugin.db.set("bans", uuid_str, {
            "name": target.name,
            "reason": f"Temp banned by {sender.name}",
            "banned_by": sender.name,
            "time": time.time(),
            "expires": time.time() + duration,
        })
        target.kick(f"§cTemp banned for 1 hour by {sender.name}")
        sender.send_message(f"§2[§7Paradox§2]§a Temp banned {target.name} for 1 hour.")

    elif action == "ban":
        uuid_str = str(target.unique_id)
        plugin.db.set("bans", uuid_str, {
            "name": target.name,
            "reason": f"Punished by {sender.name}",
            "banned_by": sender.name,
            "time": time.time(),
        })
        plugin.db.set("bans", target.name.lower(), {
            "name": target.name,
            "uuid": uuid_str,
            "reason": f"Punished by {sender.name}",
            "banned_by": sender.name,
            "time": time.time(),
        })
        target.kick(f"§cBanned by {sender.name}")
        sender.send_message(f"§2[§7Paradox§2]§a Permanently banned {target.name}.")

    elif action == "smite":
        try:
            loc = target.location
            plugin.server.dispatch_command(
                plugin.server.command_sender,
                f"summon lightning_bolt {int(loc.x)} {int(loc.y)} {int(loc.z)}"
            )
        except Exception:
            pass
        sender.send_message(f"§2[§7Paradox§2]§a Smote {target.name} with lightning!")

    else:
        sender.send_message(f"§2[§7Paradox§2]§c Unknown action: {action}")
        return False

    plugin.send_to_level4(
        f"§2[§7Paradox§2]§c {sender.name} punished {target.name} ({action})"
    )
    return True
