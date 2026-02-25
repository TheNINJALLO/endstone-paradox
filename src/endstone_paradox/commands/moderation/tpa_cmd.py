# tpa_cmd - /ac-tpa Command

import time


_pending_requests = {}  # target_uuid -> {sender_uuid, sender_name, time}


def handle_tpa(plugin, sender, args) -> bool:
    """Handle /ac-tpa <player>"""
    if not args:
        sender.send_message("§2[§7Paradox§2]§c Usage: /ac-tpa <player>")
        return False

    target_name = args[0] if isinstance(args, list) else str(args)

    # Check for accept/deny
    if target_name.lower() == "accept":
        return _handle_accept(plugin, sender)
    elif target_name.lower() == "deny":
        return _handle_deny(plugin, sender)

    # Find target
    target = None
    for p in plugin.server.online_players:
        if p.name.lower() == target_name.lower():
            target = p
            break

    if target is None:
        sender.send_message(f"§2[§7Paradox§2]§c Player '{target_name}' not found online.")
        return False

    if target == sender:
        sender.send_message("§2[§7Paradox§2]§c You can't teleport to yourself.")
        return False

    # Send request
    target_uuid = str(target.unique_id)
    _pending_requests[target_uuid] = {
        "sender_uuid": str(sender.unique_id),
        "sender_name": sender.name,
        "time": time.time(),
    }

    sender.send_message(f"§2[§7Paradox§2]§a TPA request sent to {target.name}.")
    target.send_message(
        f"§2[§7Paradox§2]§e {sender.name} wants to teleport to you.\n"
        f"§7Use /ac-tpa accept or /ac-tpa deny"
    )

    # Auto-expire after 60 seconds
    def expire():
        req = _pending_requests.get(target_uuid)
        if req and req["sender_name"] == sender.name:
            _pending_requests.pop(target_uuid, None)

    plugin.server.scheduler.run_task(plugin, expire, delay=1200)  # 60 seconds
    return True


def _handle_accept(plugin, sender):
    """Accept a pending TPA request."""
    uuid_str = str(sender.unique_id)
    req = _pending_requests.pop(uuid_str, None)

    if req is None:
        sender.send_message("§2[§7Paradox§2]§c No pending TPA request.")
        return False

    # Check if expired (60 seconds)
    if time.time() - req["time"] > 60:
        sender.send_message("§2[§7Paradox§2]§c TPA request expired.")
        return False

    # Find the requester
    requester = None
    for p in plugin.server.online_players:
        if str(p.unique_id) == req["sender_uuid"]:
            requester = p
            break

    if requester is None:
        sender.send_message("§2[§7Paradox§2]§c The requester is no longer online.")
        return False

    requester.teleport(sender.location)
    requester.send_message(f"§2[§7Paradox§2]§a Teleported to {sender.name}!")
    sender.send_message(f"§2[§7Paradox§2]§a {requester.name} teleported to you.")
    return True


def _handle_deny(plugin, sender):
    """Deny a pending TPA request."""
    uuid_str = str(sender.unique_id)
    req = _pending_requests.pop(uuid_str, None)

    if req is None:
        sender.send_message("§2[§7Paradox§2]§c No pending TPA request.")
        return False

    # Notify the requester
    for p in plugin.server.online_players:
        if str(p.unique_id) == req["sender_uuid"]:
            p.send_message(f"§2[§7Paradox§2]§c {sender.name} denied your TPA request.")
            break

    sender.send_message("§2[§7Paradox§2]§a TPA request denied.")
    return True
