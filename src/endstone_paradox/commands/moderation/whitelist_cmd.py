"""
Paradox AntiCheat - /ac-whitelist Command

Manage the server whitelist (alias for allowlist with different table).
"""


def handle_whitelist(plugin, sender, args) -> bool:
    """Handle /ac-whitelist <add|remove|list> [player]"""
    if not args:
        sender.send_message("§2[§7Paradox§2]§c Usage: /ac-whitelist <add|remove|list> [player]")
        return False

    args_list = args if isinstance(args, list) else str(args).split()
    action = args_list[0].lower()

    if action == "list":
        entries = plugin.db.get_all("whitelist")
        if not entries:
            sender.send_message("§2[§7Paradox§2]§7 Whitelist is empty.")
        else:
            sender.send_message("§2[§7Paradox§2]§a Whitelist:")
            for key, data in entries.items():
                name = data.get("name", key) if isinstance(data, dict) else key
                sender.send_message(f"  §7- {name}")
        return True

    if len(args_list) < 2:
        sender.send_message("§2[§7Paradox§2]§c Please specify a player name.")
        return False

    player_name = args_list[1]

    if action == "add":
        target = None
        for p in plugin.server.online_players:
            if p.name.lower() == player_name.lower():
                target = p
                break
        if target:
            plugin.db.set("whitelist", str(target.unique_id), {"name": target.name})
        else:
            plugin.db.set("whitelist", player_name.lower(), {"name": player_name})
        sender.send_message(f"§2[§7Paradox§2]§a Added {player_name} to whitelist.")
        return True

    elif action == "remove":
        removed = plugin.db.delete("whitelist", player_name.lower())
        all_entries = plugin.db.get_all("whitelist")
        for key, data in all_entries.items():
            if isinstance(data, dict) and data.get("name", "").lower() == player_name.lower():
                plugin.db.delete("whitelist", key)
                removed = True
        if removed:
            sender.send_message(f"§2[§7Paradox§2]§a Removed {player_name} from whitelist.")
        else:
            sender.send_message(f"§2[§7Paradox§2]§c {player_name} not on whitelist.")
        return True

    sender.send_message("§2[§7Paradox§2]§c Unknown action. Use: add, remove, or list.")
    return False
