"""
Paradox AntiCheat - /ac-allowlist Command

Manage the server allow list.
"""


def handle_allowlist(plugin, sender, args) -> bool:
    """Handle /ac-allowlist <add|remove|list> [player]"""
    if not args:
        sender.send_message("§2[§7Paradox§2]§c Usage: /ac-allowlist <add|remove|list> [player]")
        return False

    args_list = args if isinstance(args, list) else str(args).split()
    action = args_list[0].lower()

    if action == "list":
        entries = plugin.db.get_all("allowlist")
        if not entries:
            sender.send_message("§2[§7Paradox§2]§7 Allow list is empty.")
        else:
            sender.send_message("§2[§7Paradox§2]§a Allow list:")
            for key, data in entries.items():
                name = data.get("name", key) if isinstance(data, dict) else key
                sender.send_message(f"  §7- {name}")
        return True

    if len(args_list) < 2:
        sender.send_message("§2[§7Paradox§2]§c Please specify a player name.")
        return False

    player_name = args_list[1]

    if action == "add":
        # Try to find online player for UUID
        target = None
        for p in plugin.server.online_players:
            if p.name.lower() == player_name.lower():
                target = p
                break
        if target:
            plugin.db.set("allowlist", str(target.unique_id), {"name": target.name})
        else:
            plugin.db.set("allowlist", player_name.lower(), {"name": player_name})
        sender.send_message(f"§2[§7Paradox§2]§a Added {player_name} to allow list.")
        return True

    elif action == "remove":
        removed = plugin.db.delete("allowlist", player_name.lower())
        # Also try UUID-based removal
        all_entries = plugin.db.get_all("allowlist")
        for key, data in all_entries.items():
            if isinstance(data, dict) and data.get("name", "").lower() == player_name.lower():
                plugin.db.delete("allowlist", key)
                removed = True
        if removed:
            sender.send_message(f"§2[§7Paradox§2]§a Removed {player_name} from allow list.")
        else:
            sender.send_message(f"§2[§7Paradox§2]§c {player_name} not found in allow list.")
        return True

    sender.send_message("§2[§7Paradox§2]§c Unknown action. Use: add, remove, or list.")
    return False
