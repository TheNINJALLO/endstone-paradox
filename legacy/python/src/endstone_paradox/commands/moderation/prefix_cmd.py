# prefix_cmd - /ac-prefix Command


def handle_prefix(plugin, sender, args) -> bool:
    """Handle /ac-prefix [prefix]"""
    if not args:
        current = plugin.db.get("config", "display_prefix", "§2[§7Paradox§2]")
        sender.send_message(f"§2[§7Paradox§2]§7 Current prefix: {current}")
        return True

    new_prefix = " ".join(args) if isinstance(args, list) else str(args)
    plugin.db.set("config", "display_prefix", new_prefix)
    sender.send_message(f"§2[§7Paradox§2]§a Display prefix updated to: {new_prefix}")
    return True
