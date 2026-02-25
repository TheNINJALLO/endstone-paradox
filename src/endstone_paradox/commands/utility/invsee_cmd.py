# invsee_cmd - /ac-invsee Command


def handle_invsee(plugin, sender, args) -> bool:
    """Handle /ac-invsee <player>"""
    if not args:
        sender.send_message("§2[§7Paradox§2]§c Usage: /ac-invsee <player>")
        return False

    target_name = args[0] if isinstance(args, list) else str(args)
    target = None
    for p in plugin.server.online_players:
        if p.name.lower() == target_name.lower():
            target = p
            break

    if target is None:
        sender.send_message(f"§2[§7Paradox§2]§c Player '{target_name}' not found online.")
        return False

    lines = [f"\n§2[§7Paradox§2]§a ── {target.name}'s Inventory ──", ""]

    try:
        inv = target.inventory
        if inv:
            for slot in range(inv.size):
                item = inv.get_item(slot)
                if item and item.type and str(item.type) != "air":
                    name = str(item.type).replace("minecraft:", "")
                    amount = item.amount if hasattr(item, 'amount') else 1
                    lines.append(f"  §7Slot {slot}: §f{name} x{amount}")
        else:
            lines.append("  §7(Could not read inventory)")
    except Exception as e:
        lines.append(f"  §c(Error reading inventory: {e})")

    if len(lines) <= 2:
        lines.append("  §7(Empty inventory)")

    sender.send_message("\n".join(lines))
    return True
