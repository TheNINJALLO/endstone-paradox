# despawn_cmd - /ac-despawn Command


def handle_despawn(plugin, sender, args) -> bool:
    """Handle /ac-despawn [type] [radius]"""
    entity_type = "item"
    radius = 100

    if args:
        args_list = args if isinstance(args, list) else str(args).split()
        if len(args_list) >= 1:
            entity_type = args_list[0]
        if len(args_list) >= 2:
            try:
                radius = int(args_list[1])
            except ValueError:
                sender.send_message("§2[§7Paradox§2]§c Invalid radius.")
                return False

    try:
        loc = sender.location
        cmd = f"kill @e[type={entity_type},x={int(loc.x)},y={int(loc.y)},z={int(loc.z)},r={radius}]"
        plugin.server.dispatch_command(plugin.server.command_sender, cmd)
        sender.send_message(
            f"§2[§7Paradox§2]§a Removed {entity_type} entities within {radius} blocks."
        )
    except Exception as e:
        sender.send_message(f"§2[§7Paradox§2]§c Error: {e}")
        return False

    return True
