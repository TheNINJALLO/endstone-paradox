# vanish_cmd - /ac-vanish Command


def handle_vanish(plugin, sender, args) -> bool:
    """Handle /ac-vanish"""
    uuid_str = str(sender.unique_id)

    if uuid_str in plugin._vanished_players:
        # Unvanish
        plugin._vanished_players.discard(uuid_str)
        plugin.db.delete("vanished_players", uuid_str)

        # Remove invisibility effect
        try:
            plugin.server.dispatch_command(
                plugin.server.command_sender,
                f'effect "{sender.name}" invisibility 0'
            )
        except Exception:
            pass

        sender.send_message("§2[§7Paradox§2]§a You are now visible.")
        plugin.send_to_level4(f"§2[§7Paradox§2]§7 {sender.name} unvanished.")
    else:
        # Vanish
        plugin._vanished_players.add(uuid_str)
        plugin.db.set("vanished_players", uuid_str, {"name": sender.name})

        # Apply invisibility effect (max duration)
        try:
            plugin.server.dispatch_command(
                plugin.server.command_sender,
                f'effect "{sender.name}" invisibility 999999 1 true'
            )
        except Exception:
            pass

        sender.send_message("§2[§7Paradox§2]§a You are now vanished.")
        plugin.send_to_level4(f"§2[§7Paradox§2]§7 {sender.name} vanished.")

    return True
