# channels_cmd - /ac-channels Command


def handle_channels(plugin, sender, args) -> bool:
    """Handle /ac-channels <create|join|leave|list|send> [name] [message]"""
    if not args:
        sender.send_message(
            "§2[§7Paradox§2]§c Usage: /ac-channels <create|join|leave|list|send> "
            "[name] [message]"
        )
        return False

    args_list = args if isinstance(args, list) else str(args).split()
    action = args_list[0].lower()

    if action == "list":
        channels = plugin.db.get_all("channels")
        if not channels:
            sender.send_message("§2[§7Paradox§2]§7 No channels exist.")
        else:
            sender.send_message("§2[§7Paradox§2]§a Channels:")
            for name, data in channels.items():
                members = data.get("members", []) if isinstance(data, dict) else []
                sender.send_message(f"  §7#{name} ({len(members)} members)")
        return True

    if len(args_list) < 2:
        sender.send_message("§2[§7Paradox§2]§c Please specify a channel name.")
        return False

    channel_name = args_list[1].lower()
    uuid_str = str(sender.unique_id)

    if action == "create":
        if plugin.db.has("channels", channel_name):
            sender.send_message(f"§2[§7Paradox§2]§c Channel #{channel_name} already exists.")
            return False
        plugin.db.set("channels", channel_name, {
            "owner": uuid_str,
            "members": [uuid_str],
        })
        sender.send_message(f"§2[§7Paradox§2]§a Created channel #{channel_name}!")
        return True

    elif action == "join":
        data = plugin.db.get("channels", channel_name)
        if data is None:
            sender.send_message(f"§2[§7Paradox§2]§c Channel #{channel_name} not found.")
            return False
        members = data.get("members", [])
        if uuid_str not in members:
            members.append(uuid_str)
            data["members"] = members
            plugin.db.set("channels", channel_name, data)
        sender.send_message(f"§2[§7Paradox§2]§a Joined #{channel_name}!")
        return True

    elif action == "leave":
        data = plugin.db.get("channels", channel_name)
        if data is None:
            sender.send_message(f"§2[§7Paradox§2]§c Channel #{channel_name} not found.")
            return False
        members = data.get("members", [])
        if uuid_str in members:
            members.remove(uuid_str)
            data["members"] = members
            plugin.db.set("channels", channel_name, data)
        sender.send_message(f"§2[§7Paradox§2]§a Left #{channel_name}.")
        return True

    elif action == "send":
        if len(args_list) < 3:
            sender.send_message("§2[§7Paradox§2]§c Usage: /ac-channels send <name> <message>")
            return False
        message = " ".join(args_list[2:])
        data = plugin.db.get("channels", channel_name)
        if data is None:
            sender.send_message(f"§2[§7Paradox§2]§c Channel #{channel_name} not found.")
            return False
        members = data.get("members", [])
        if uuid_str not in members:
            sender.send_message(f"§2[§7Paradox§2]§c You're not in #{channel_name}.")
            return False
        # Send message to all channel members
        for player in plugin.server.online_players:
            if str(player.unique_id) in members:
                player.send_message(
                    f"§7[§a#{channel_name}§7] §f{sender.name}: §7{message}"
                )
        return True

    sender.send_message("§2[§7Paradox§2]§c Unknown action. Use: create, join, leave, list, send.")
    return False
