# lockdown_cmd - /ac-lockdown Command


def handle_lockdown(plugin, sender, args) -> bool:
    """Handle /ac-lockdown

    Usage:
        /ac-lockdown              - Toggle lockdown on/off (uses current lockdown level)
        /ac-lockdown level 1      - Set lockdown level 1 (L4 only)
        /ac-lockdown level 2      - Set lockdown level 2 (L4 + L3 moderators)
    """
    # Handle level configuration
    if args:
        args_list = args if isinstance(args, list) else str(args).split()
        if len(args_list) >= 2 and args_list[0].lower() == "level":
            try:
                level = int(args_list[1])
                if level == 1:
                    plugin._lockdown_level = 1
                    plugin.db.set("config", "lockdown_level", 1)
                    sender.send_message(
                        "§2[§7Paradox§2]§a Lockdown level set to §e1§a (Level 4 only)."
                    )
                elif level == 2:
                    plugin._lockdown_level = 2
                    plugin.db.set("config", "lockdown_level", 2)
                    sender.send_message(
                        "§2[§7Paradox§2]§a Lockdown level set to §e2§a (Level 4 + Level 3 moderators)."
                    )
                else:
                    sender.send_message("§2[§7Paradox§2]§c Invalid level. Use 1 (L4 only) or 2 (L4 + L3).")
                return True
            except ValueError:
                sender.send_message("§2[§7Paradox§2]§c Invalid level number.")
                return False

    # Toggle lockdown on/off
    plugin._lockdown_active = not plugin._lockdown_active
    plugin.db.set("config", "lockdown", plugin._lockdown_active)

    if plugin._lockdown_active:
        level_desc = "Level 4 only" if plugin._lockdown_level == 1 else "Level 4 + Level 3"
        sender.send_message(
            f"§2[§7Paradox§2]§c Server is now in LOCKDOWN mode. ({level_desc})"
        )
        # Notify and kick players below the lockdown threshold
        for player in plugin.server.online_players:
            if not _player_meets_lockdown(plugin, player):
                player.kick("§cServer entering lockdown mode.")
        plugin.send_to_level4(
            f"§2[§7Paradox§2]§c§l LOCKDOWN ACTIVATED by {sender.name} ({level_desc})"
        )
    else:
        sender.send_message("§2[§7Paradox§2]§a Server lockdown has been lifted.")
        plugin.send_to_level4("§2[§7Paradox§2]§a Lockdown lifted by " + sender.name)

    return True


def _player_meets_lockdown(plugin, player) -> bool:
    """Check if a player meets the lockdown minimum clearance."""
    from endstone_paradox.security import SecurityClearance

    if plugin._lockdown_level == 2:
        # Level 2 lockdown: L4 + L3 can stay
        return plugin.security.has_clearance(player, SecurityClearance.LEVEL_3)
    else:
        # Level 1 lockdown (default): L4 only
        return plugin.security.is_level4(player)
