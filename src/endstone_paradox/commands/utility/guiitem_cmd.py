# guiitem_cmd - /ac-guiitem Command

def handle_guiitem(plugin, sender, args) -> bool:
    """Handle /ac-guiitem [item_id]"""
    if not plugin.security.is_level4(sender):
        sender.send_message("§2[§7Paradox§2]§c You do not have permission to use this command.")
        return False
        
    if not args:
        # Toggle or show current
        current = plugin.db.get("config", "gui_item", "")
        if current:
            sender.send_message(f"§2[§7Paradox§2]§7 Current GUI trigger item: §e{current}")
            sender.send_message("§7Use §f/ac-guiitem clear §7to remove it.")
        else:
            sender.send_message("§2[§7Paradox§2]§7 No GUI trigger item is set.")
            sender.send_message("§7Usage: §f/ac-guiitem <item_id>")
        return True

    action = str(args[0]).lower() if isinstance(args, list) else str(args).lower()
    
    if action in ("clear", "remove", "none", "delete"):
        plugin.db.set("config", "gui_item", "")
        sender.send_message("§2[§7Paradox§2]§a GUI trigger item cleared.")
        return True
        
    item_id = " ".join(args) if isinstance(args, list) else str(args)
    if not item_id.startswith("minecraft:"):
        item_id = f"minecraft:{item_id}"
        
    plugin.db.set("config", "gui_item", item_id)
    sender.send_message(f"§2[§7Paradox§2]§a GUI trigger item set to: §e{item_id}")
    sender.send_message("§7Right-click this item to open the Paradox menu.")
    return True
