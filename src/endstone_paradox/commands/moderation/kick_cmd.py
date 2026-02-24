"""
Paradox AntiCheat - /ac-kick Command

Kick a player from the server.
"""


def handle_kick(plugin, sender, args) -> bool:
    """Handle /ac-kick <player> [reason]"""
    if not args:
        sender.send_message("§2[§7Paradox§2]§c Usage: /ac-kick <player> [reason]")
        return False

    args_list = args if isinstance(args, list) else [str(args)]
    target_name = args_list[0]
    reason = " ".join(args_list[1:]) if len(args_list) > 1 else "Kicked by an admin"

    target = None
    for p in plugin.server.online_players:
        if p.name.lower() == target_name.lower():
            target = p
            break

    if target is None:
        sender.send_message(f"§2[§7Paradox§2]§c Player '{target_name}' not found online.")
        return False

    if plugin.security.is_level4(target):
        sender.send_message("§2[§7Paradox§2]§c Cannot kick a Level 4 player.")
        return False

    target.kick(f"§c{reason}")
    sender.send_message(f"§2[§7Paradox§2]§a Kicked {target.name}: {reason}")
    plugin.send_to_level4(f"§2[§7Paradox§2]§c {sender.name} kicked {target.name}: {reason}")
    return True
