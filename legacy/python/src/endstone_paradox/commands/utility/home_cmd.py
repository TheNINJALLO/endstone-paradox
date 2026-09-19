# home_cmd - /ac-home Command

import json


MAX_HOMES = 5  # Default max homes per player


def handle_home(plugin, sender, args) -> bool:
    """Handle /ac-home [set|delete|list|help] [name]"""
    uuid_str = str(sender.unique_id)

    # Parse args — handle both list and string formats
    if not args:
        args_list = []
    elif isinstance(args, list):
        args_list = args
    else:
        args_list = str(args).split()

    # ─── No args: teleport to default home ───────────────
    if not args_list:
        homes = plugin.db.get("homes", uuid_str, {})
        if "default" in homes:
            _teleport_to_home(plugin, sender, "default", homes["default"])
            return True
        elif homes:
            first_name = next(iter(homes))
            _teleport_to_home(plugin, sender, first_name, homes[first_name])
            return True
        sender.send_message("§2[§7Paradox§2]§c You have no homes set!")
        sender.send_message("§7Use §f/ac-home set §7to save your current location.")
        sender.send_message("§7Use §f/ac-home help §7for all commands.")
        return False

    action = args_list[0].lower()

    # ─── Help ────────────────────────────────────────────
    if action == "help":
        sender.send_message("§2[§7Paradox§2]§b Home Commands:")
        sender.send_message("")
        sender.send_message("  §f/ac-home §7- Teleport to your default home")
        sender.send_message("  §f/ac-home §e<name> §7- Teleport to a named home")
        sender.send_message("  §f/ac-home set §7- Save location as §edefault §7home")
        sender.send_message("  §f/ac-home set §e<name> §7- Save location with a name")
        sender.send_message("  §f/ac-home delete §e<name> §7- Delete a named home")
        sender.send_message("  §f/ac-home list §7- List all your saved homes")
        sender.send_message("")
        sender.send_message(f"§7Max homes per player: §f{MAX_HOMES}")
        return True

    # ─── Set ─────────────────────────────────────────────
    if action == "set":
        name = args_list[1] if len(args_list) > 1 else "default"
        homes = plugin.db.get("homes", uuid_str, {})
        if not isinstance(homes, dict):
            homes = {}

        is_overwrite = name in homes
        if len(homes) >= MAX_HOMES and not is_overwrite:
            sender.send_message(f"§2[§7Paradox§2]§c Max homes ({MAX_HOMES}) reached!")
            sender.send_message("§7Delete a home first with §f/ac-home delete <name>")
            return False

        loc = sender.location
        dim_name = str(sender.dimension.name) if hasattr(sender.dimension, 'name') else "overworld"
        homes[name] = {
            "x": loc.x, "y": loc.y, "z": loc.z,
            "dimension": dim_name,
        }
        plugin.db.set("homes", uuid_str, homes)

        action_word = "Updated" if is_overwrite else "Set"
        sender.send_message(f"§2[§7Paradox§2]§a {action_word} home '§f{name}§a'!")
        sender.send_message(f"  §7Location: §f{int(loc.x)}, {int(loc.y)}, {int(loc.z)} §7({dim_name})")
        sender.send_message(f"  §7Homes used: §f{len(homes)}/{MAX_HOMES}")
        sender.send_message(f"§7Teleport here with: §f/ac-home {name}")
        return True

    # ─── Delete ──────────────────────────────────────────
    if action == "delete" or action == "del" or action == "remove":
        if len(args_list) < 2:
            sender.send_message("§2[§7Paradox§2]§c Specify a home name to delete!")
            sender.send_message("§7Usage: §f/ac-home delete <name>")
            sender.send_message("§7See your homes with: §f/ac-home list")
            return False

        name = args_list[1]
        homes = plugin.db.get("homes", uuid_str, {})
        if name in homes:
            data = homes[name]
            del homes[name]
            plugin.db.set("homes", uuid_str, homes)
            sender.send_message(f"§2[§7Paradox§2]§a Deleted home '§f{name}§a'.")
            sender.send_message(f"  §7Was at: §f{int(data['x'])}, {int(data['y'])}, {int(data['z'])}")
            sender.send_message(f"  §7Homes remaining: §f{len(homes)}/{MAX_HOMES}")
        else:
            sender.send_message(f"§2[§7Paradox§2]§c Home '§f{name}§c' not found!")
            _suggest_homes(sender, homes)
        return True

    # ─── List ────────────────────────────────────────────
    if action == "list":
        homes = plugin.db.get("homes", uuid_str, {})
        if not homes:
            sender.send_message("§2[§7Paradox§2]§7 You have no homes set.")
            sender.send_message("§7Use §f/ac-home set [name] §7to create one!")
        else:
            sender.send_message(f"§2[§7Paradox§2]§b Your Homes §7({len(homes)}/{MAX_HOMES}):")
            for name, data in homes.items():
                dim = data.get('dimension', 'overworld')
                sender.send_message(
                    f"  §a{name} §7- §f{int(data['x'])}, {int(data['y'])}, {int(data['z'])} §8({dim})"
                )
            sender.send_message("")
            sender.send_message("§7Teleport: §f/ac-home <name>")
            sender.send_message("§7Delete: §f/ac-home delete <name>")
        return True

    # ─── Treat as home name to teleport to ───────────────
    homes = plugin.db.get("homes", uuid_str, {})
    if action in homes:
        _teleport_to_home(plugin, sender, action, homes[action])
        return True

    sender.send_message(f"§2[§7Paradox§2]§c Home '§f{action}§c' not found!")
    _suggest_homes(sender, homes)
    return False


def _teleport_to_home(plugin, sender, name, data):
    """Teleport a player to a home location."""
    try:
        dim = data.get('dimension', 'overworld')
        # Use command-based teleport for reliability
        plugin.server.dispatch_command(
            plugin.server.command_sender,
            f'tp "{sender.name}" {data["x"]:.1f} {data["y"]:.1f} {data["z"]:.1f}'
        )
        sender.send_message(f"§2[§7Paradox§2]§a Teleported to home '§f{name}§a'!")
        sender.send_message(f"  §7Location: §f{int(data['x'])}, {int(data['y'])}, {int(data['z'])} §8({dim})")
    except Exception as e:
        sender.send_message(f"§2[§7Paradox§2]§c Failed to teleport: {e}")


def _suggest_homes(sender, homes):
    """Show available homes as suggestions."""
    if homes:
        names = ", ".join(f"§f{n}" for n in homes)
        sender.send_message(f"§7Your homes: {names}")
        sender.send_message("§7Use §f/ac-home list §7for details.")
    else:
        sender.send_message("§7You have no homes. Use §f/ac-home set §7to create one!")
