"""
Paradox AntiCheat - /ac-home Command

Set, delete, list, and teleport to home locations.
Homes are stored per-player in the database.
"""

import json


MAX_HOMES = 5  # Default max homes per player


def handle_home(plugin, sender, args) -> bool:
    """Handle /ac-home [set|delete|list] [name]"""
    uuid_str = str(sender.unique_id)

    if not args:
        # Teleport to default home
        homes = plugin.db.get("homes", uuid_str, {})
        if "default" in homes:
            _teleport_to_home(plugin, sender, homes["default"])
            return True
        elif homes:
            # Teleport to first home
            first = next(iter(homes.values()))
            _teleport_to_home(plugin, sender, first)
            return True
        sender.send_message("§2[§7Paradox§2]§c No homes set. Use /ac-home set [name]")
        return False

    args_list = args if isinstance(args, list) else str(args).split()
    action = args_list[0].lower()

    if action == "set":
        name = args_list[1] if len(args_list) > 1 else "default"
        homes = plugin.db.get("homes", uuid_str, {})
        if not isinstance(homes, dict):
            homes = {}
        if len(homes) >= MAX_HOMES and name not in homes:
            sender.send_message(f"§2[§7Paradox§2]§c Max homes ({MAX_HOMES}) reached.")
            return False
        loc = sender.location
        homes[name] = {
            "x": loc.x, "y": loc.y, "z": loc.z,
            "dimension": str(sender.dimension.name) if hasattr(sender.dimension, 'name') else "overworld",
        }
        plugin.db.set("homes", uuid_str, homes)
        sender.send_message(f"§2[§7Paradox§2]§a Home '{name}' set!")
        return True

    elif action == "delete":
        name = args_list[1] if len(args_list) > 1 else "default"
        homes = plugin.db.get("homes", uuid_str, {})
        if name in homes:
            del homes[name]
            plugin.db.set("homes", uuid_str, homes)
            sender.send_message(f"§2[§7Paradox§2]§a Home '{name}' deleted.")
        else:
            sender.send_message(f"§2[§7Paradox§2]§c Home '{name}' not found.")
        return True

    elif action == "list":
        homes = plugin.db.get("homes", uuid_str, {})
        if not homes:
            sender.send_message("§2[§7Paradox§2]§7 No homes set.")
        else:
            sender.send_message("§2[§7Paradox§2]§a Your homes:")
            for name, data in homes.items():
                sender.send_message(
                    f"  §7{name}: ({int(data['x'])}, {int(data['y'])}, {int(data['z'])})"
                )
        return True

    else:
        # Treat as home name to teleport to
        homes = plugin.db.get("homes", uuid_str, {})
        if action in homes:
            _teleport_to_home(plugin, sender, homes[action])
            return True
        sender.send_message(f"§2[§7Paradox§2]§c Home '{action}' not found.")
        return False


def _teleport_to_home(plugin, sender, data):
    """Teleport a player to a home location."""
    try:
        from endstone import Location
        loc = Location(data["x"], data["y"], data["z"])
        sender.teleport(loc)
        sender.send_message("§2[§7Paradox§2]§a Teleported home!")
    except Exception:
        # Fallback: try command-based teleport
        plugin.server.dispatch_command(
            plugin.server.command_sender,
            f'tp "{sender.name}" {data["x"]:.1f} {data["y"]:.1f} {data["z"]:.1f}'
        )
        sender.send_message("§2[§7Paradox§2]§a Teleported home!")
