# report_cmd.py - /ac-report command handler
# Any player can report another player.

from endstone import Player


def handle_report(plugin, sender, args, **kwargs) -> bool:
    """Handle /ac-report <player> [reason]"""
    if not isinstance(sender, Player):
        sender.send_message("§2[§7Paradox§2]§c This command can only be used by players.")
        return False

    # Check if report system module is running
    module = plugin.get_module("reportsystem")
    if module is None or not module.running:
        sender.send_message("§2[§7Paradox§2]§c Player report system is not enabled.")
        return False

    args_str = str(args).strip() if args else ""

    # Handle help
    if not args_str or args_str.lower() in ("help", "?"):
        sender.send_message("§2[§7Paradox§2]§e Usage: /ac-report <player> [reason]")
        sender.send_message("§7  Report a player for suspicious behavior.")
        return True

    # Parse: first word = player name, rest = reason
    parts = args_str.split(None, 1)
    target_name = parts[0]
    reason = parts[1] if len(parts) > 1 else "No reason given"

    # Verify target exists (optional — allow reporting offline players too)
    target_player = None
    for p in plugin.server.online_players:
        if p.name.lower() == target_name.lower():
            target_player = p
            target_name = p.name  # Use exact name
            break

    # Can't report yourself
    if target_player and str(target_player.unique_id) == str(sender.unique_id):
        sender.send_message("§2[§7Paradox§2]§c You cannot report yourself.")
        return False

    # Submit the report
    result = module.submit_report(sender, target_name, reason)

    if result.get("error"):
        sender.send_message(f"§2[§7Paradox§2]§c {result['error']}")
        return False

    sender.send_message(
        f"§2[§7Paradox§2]§a Report submitted for §f{target_name}§a. "
        f"Staff have been notified."
    )
    return True
