"""
Paradox AntiCheat - /ac-freeze Command

Freeze/unfreeze a player (prevent all movement).
"""


def handle_freeze(plugin, sender, args) -> bool:
    """Handle /ac-freeze <player>"""
    if not args:
        sender.send_message("§2[§7Paradox§2]§c Usage: /ac-freeze <player>")
        return False

    target_name = args[0] if isinstance(args, list) else str(args)
    target = None
    for p in plugin.server.online_players:
        if p.name.lower() == target_name.lower():
            target = p
            break

    if target is None:
        sender.send_message(f"§2[§7Paradox§2]§c Player '{target_name}' not found online.")
        return False

    if plugin.security.is_level4(target):
        sender.send_message("§2[§7Paradox§2]§c Cannot freeze a Level 4 player.")
        return False

    uuid_str = str(target.unique_id)
    if uuid_str in plugin._frozen_players:
        # Unfreeze
        plugin._frozen_players.discard(uuid_str)
        plugin.db.delete("frozen_players", uuid_str)
        target.send_message("§2[§7Paradox§2]§a You have been unfrozen.")
        sender.send_message(f"§2[§7Paradox§2]§a Unfroze {target.name}.")
    else:
        # Freeze
        plugin._frozen_players.add(uuid_str)
        plugin.db.set("frozen_players", uuid_str, {"name": target.name})
        target.send_message("§2[§7Paradox§2]§c You have been frozen! You cannot move.")
        sender.send_message(f"§2[§7Paradox§2]§a Froze {target.name}.")

    return True
