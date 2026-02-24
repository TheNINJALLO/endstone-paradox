"""
Paradox AntiCheat - /ac-pvp Command

Toggle PvP for the sending player or globally.
"""


def handle_pvp(plugin, sender, args) -> bool:
    """Handle /ac-pvp"""
    pvp_module = plugin.get_module("pvp")
    if pvp_module is None or not pvp_module.running:
        sender.send_message("§2[§7Paradox§2]§c PvP module is not active.")
        return False

    # Check if this is a global toggle (admin only)
    if args and isinstance(args, list) and args[0].lower() == "global":
        if not plugin.security.is_level4(sender):
            sender.send_message("§2[§7Paradox§2]§c Only Level 4 can toggle global PvP.")
            return False
        state = pvp_module.toggle_global_pvp()
        status = "§aenabled" if state else "§cdisabled"
        for p in plugin.server.online_players:
            p.send_message(f"§2[§7Paradox§2]§e Global PvP has been {status}§e.")
        return True

    # Per-player toggle
    if pvp_module.is_in_combat(sender):
        sender.send_message("§2[§7Paradox§2]§c Cannot toggle PvP while in combat!")
        return False

    state = pvp_module.toggle_pvp(sender)
    status = "§aenabled" if state else "§cdisabled"
    sender.send_message(f"§2[§7Paradox§2]§7 Your PvP is now {status}§7.")
    return True
