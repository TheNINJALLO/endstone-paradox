# opsec_cmd - /ac-opsec Command


def handle_opsec(plugin, sender, args) -> bool:
    """Handle /ac-opsec"""
    lines = [
        "\n§2[§7Paradox§2]§a ── Security Dashboard ──",
        "",
        "§eOnline Players & Clearance:",
    ]

    for player in plugin.server.online_players:
        cl = plugin.security.get_clearance(player)
        frozen = " §c[FROZEN]" if plugin.is_player_frozen(player) else ""
        vanished = " §7[VANISHED]" if str(player.unique_id) in plugin._vanished_players else ""
        lines.append(f"  §7{player.name}: §a{cl.name}{frozen}{vanished}")

    lines.append("")
    lines.append(f"§eLockdown: {'§cACTIVE' if plugin._lockdown_active else '§aInactive'}")
    lines.append(f"§eFrozen Players: §7{len(plugin._frozen_players)}")
    lines.append(f"§eVanished Players: §7{len(plugin._vanished_players)}")
    lines.append(f"§eBanned Players: §7{plugin.db.count('bans')}")
    lines.append(f"§eLevel 4 UUIDs: §7{len(plugin.security.get_level4_players())}")

    # Module status
    lines.append("")
    lines.append("§eModules:")
    for name, module in plugin._modules.items():
        status = "§a●" if module.running else "§c●"
        lines.append(f"  {status} §7{name}")

    sender.send_message("\n".join(lines))
    return True
