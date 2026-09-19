# exempt_cmd.py - /ac-exempt <player> <module|all> [minutes]


def handle_exempt(plugin, sender, args):
    """Temporarily exempt a player from a module."""
    if not args or not args[0].strip():
        sender.send_message("§2[§7Paradox§2]§e Usage: /ac-exempt <player> <module|all> [minutes]")
        return True

    engine = plugin.violation_engine
    if not engine:
        sender.send_message("§2[§7Paradox§2]§c Violation engine not available.")
        return True

    parts = args[0].split()
    if len(parts) < 2:
        sender.send_message("§2[§7Paradox§2]§e Usage: /ac-exempt <player> <module|all> [minutes]")
        return True

    target_name = parts[0]
    module_name = parts[1].lower()
    minutes = 10  # default
    if len(parts) > 2:
        try:
            minutes = int(parts[2])
        except ValueError:
            minutes = 10

    # Find target
    target_uuid = None
    for p in plugin.server.online_players:
        if p.name.lower() == target_name.lower():
            target_uuid = str(p.unique_id)
            target_name = p.name
            break

    if target_uuid is None:
        sender.send_message(f"§2[§7Paradox§2]§c Player '{target_name}' not found online.")
        return True

    # Validate module name
    if module_name != "all" and module_name not in plugin._modules:
        available = ", ".join(sorted(plugin._modules.keys()))
        sender.send_message(f"§2[§7Paradox§2]§c Unknown module '{module_name}'.")
        sender.send_message(f"§2[§7Paradox§2]§7 Available: {available}, all")
        return True

    engine.add_exemption(target_uuid, module_name, minutes * 60)
    sender.send_message(
        f"§2[§7Paradox§2]§a Exempted §c{target_name}§a from §f{module_name}§a "
        f"for {minutes} minutes."
    )
    return True
