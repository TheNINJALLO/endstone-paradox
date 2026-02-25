# deop_cmd - /ac-deop Command

from endstone_paradox.security import SecurityClearance


def handle_deop(plugin, sender, args) -> bool:
    """Handle /ac-deop [player]"""
    if not args:
        # Deop self
        plugin.security.set_clearance(sender, SecurityClearance.LEVEL_1)
        sender.send_message("§2[§7Paradox§2]§a Your clearance has been revoked.")
        return True

    # Deop target player
    target_name = args[0] if isinstance(args, list) else str(args)
    target = None
    for p in plugin.server.online_players:
        if p.name.lower() == target_name.lower():
            target = p
            break

    if target is None:
        sender.send_message(f"§2[§7Paradox§2]§c Player '{target_name}' not found online.")
        return False

    plugin.security.set_clearance(target, SecurityClearance.LEVEL_1)
    target.send_message("§2[§7Paradox§2]§c Your security clearance has been revoked.")
    sender.send_message(f"§2[§7Paradox§2]§a Revoked clearance for {target.name}.")
    return True
