"""
Paradox AntiCheat - /ac-rank Command

Player rank management: set custom display ranks.
"""


def handle_rank(plugin, sender, args) -> bool:
    """Handle /ac-rank <player> [rank]"""
    if not args:
        sender.send_message("§2[§7Paradox§2]§c Usage: /ac-rank <player> [rank]")
        return False

    args_list = args if isinstance(args, list) else str(args).split()
    target_name = args_list[0]

    target = None
    for p in plugin.server.online_players:
        if p.name.lower() == target_name.lower():
            target = p
            break

    if target is None:
        sender.send_message(f"§2[§7Paradox§2]§c Player '{target_name}' not found online.")
        return False

    uuid_str = str(target.unique_id)

    if len(args_list) < 2:
        # View current rank
        rank = plugin.db.get("ranks", uuid_str, "none")
        sender.send_message(f"§2[§7Paradox§2]§7 {target.name}'s rank: §a{rank}")
        return True

    # Set rank
    rank = " ".join(args_list[1:])
    if rank.lower() in ("none", "remove", "clear"):
        plugin.db.delete("ranks", uuid_str)
        sender.send_message(f"§2[§7Paradox§2]§a Removed rank from {target.name}.")
        target.send_message("§2[§7Paradox§2]§7 Your rank has been removed.")
    else:
        plugin.db.set("ranks", uuid_str, rank)
        sender.send_message(f"§2[§7Paradox§2]§a Set {target.name}'s rank to: {rank}")
        target.send_message(f"§2[§7Paradox§2]§7 Your rank has been set to: §a{rank}")

    return True
