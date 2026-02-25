# unban_cmd - /ac-unban Command


def handle_unban(plugin, sender, args) -> bool:
    """Handle /ac-unban <name>"""
    if not args:
        sender.send_message("§2[§7Paradox§2]§c Usage: /ac-unban <name>")
        return False

    target_name = args[0] if isinstance(args, list) else str(args)
    name_lower = target_name.lower()

    # Try to remove by name
    removed = plugin.db.delete("bans", name_lower)

    # Also try to find and remove by UUID
    all_bans = plugin.db.get_all("bans")
    for key, data in all_bans.items():
        if isinstance(data, dict) and data.get("name", "").lower() == name_lower:
            plugin.db.delete("bans", key)
            removed = True

    if removed:
        sender.send_message(f"§2[§7Paradox§2]§a Unbanned {target_name}.")
        plugin.send_to_level4(f"§2[§7Paradox§2]§7 {sender.name} unbanned {target_name}.")
    else:
        sender.send_message(f"§2[§7Paradox§2]§c {target_name} is not banned.")

    return removed
