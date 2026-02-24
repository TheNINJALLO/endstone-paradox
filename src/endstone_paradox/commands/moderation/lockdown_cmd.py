"""
Paradox AntiCheat - /ac-lockdown Command

Toggle server lockdown mode. When active, only Level 4 players
can join or use commands.
"""


def handle_lockdown(plugin, sender, args) -> bool:
    """Handle /ac-lockdown"""
    plugin._lockdown_active = not plugin._lockdown_active
    plugin.db.set("config", "lockdown", plugin._lockdown_active)

    if plugin._lockdown_active:
        sender.send_message("§2[§7Paradox§2]§c Server is now in LOCKDOWN mode.")
        # Notify and kick non-Level4 players
        for player in plugin.server.online_players:
            if not plugin.security.is_level4(player):
                player.kick("§cServer entering lockdown mode.")
        plugin.send_to_level4("§2[§7Paradox§2]§c§l LOCKDOWN ACTIVATED by " + sender.name)
    else:
        sender.send_message("§2[§7Paradox§2]§a Server lockdown has been lifted.")
        plugin.send_to_level4("§2[§7Paradox§2]§a Lockdown lifted by " + sender.name)

    return True
