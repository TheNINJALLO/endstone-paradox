# pvp_cmd - /ac-pvp Command


def handle_pvp(plugin, sender, args) -> bool:
    """Handle /ac-pvp"""
    pvp_module = plugin.get_module("pvp")
    if pvp_module is None or not pvp_module.running:
        sender.send_message("§2[§7Paradox§2]§c PvP module is not active.")
        return False

    # Parse args
    args_list = args if isinstance(args, list) else str(args).split() if args else []
    action = args_list[0].lower() if args_list else ""

    # ─── Status ──────────────────────────────────────────
    if action == "status" or action == "info":
        global_state = "§aEnabled" if pvp_module._global_pvp else "§cDisabled"
        personal_state = "§aEnabled" if pvp_module.is_pvp_enabled(sender) else "§cDisabled"
        combat_state = "§cYes" if pvp_module.is_in_combat(sender) else "§aNo"

        sender.send_message("§2[§7Paradox§2]§b PvP Status:")
        sender.send_message(f"  §7Global PvP: {global_state}")
        sender.send_message(f"  §7Your PvP: {personal_state}")
        sender.send_message(f"  §7In Combat: {combat_state}")
        sender.send_message("")
        sender.send_message("§7Commands:")
        sender.send_message("  §f/ac-pvp §7- Toggle your personal PvP")
        sender.send_message("  §f/ac-pvp global §7- Toggle server-wide PvP §8(admin)")
        sender.send_message("  §f/ac-pvp status §7- View this info")
        return True

    # ─── Global Toggle (admin only) ──────────────────────
    if action == "global":
        if not plugin.security.is_level4(sender):
            sender.send_message("§2[§7Paradox§2]§c Only Level 4 can toggle global PvP.")
            return False
        state = pvp_module.toggle_global_pvp()
        status = "§aENABLED" if state else "§cDISABLED"
        for p in plugin.server.online_players:
            p.send_message(f"§2[§7Paradox§2]§e Global PvP has been {status}§e by §f{sender.name}§e.")
        return True

    # ─── Help ────────────────────────────────────────────
    if action == "help":
        sender.send_message("§2[§7Paradox§2]§b PvP Commands:")
        sender.send_message("  §f/ac-pvp §7- Toggle your personal PvP on/off")
        sender.send_message("  §f/ac-pvp global §7- Toggle PvP for the entire server")
        sender.send_message("  §f/ac-pvp status §7- View current PvP status")
        sender.send_message("")
        sender.send_message("§7When PvP is off, you cannot deal or receive")
        sender.send_message("§7player damage. You cannot toggle PvP while in combat.")
        return True

    # ─── Per-player Toggle (default) ─────────────────────
    if pvp_module.is_in_combat(sender):
        sender.send_message("§2[§7Paradox§2]§c Cannot toggle PvP while in combat!")
        sender.send_message(f"§7Combat tag expires in §f{int(pvp_module.COMBAT_TAG_DURATION)}s§7 after last hit.")
        return False

    state = pvp_module.toggle_pvp(sender)
    if state:
        sender.send_message("§2[§7Paradox§2]§a Your PvP is now §lENABLED§r§a.")
        sender.send_message("§7You can now deal and receive player damage.")
    else:
        sender.send_message("§2[§7Paradox§2]§c Your PvP is now §lDISABLED§r§c.")
        sender.send_message("§7You will not deal or receive player damage.")
    return True
