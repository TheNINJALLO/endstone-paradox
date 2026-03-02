# toggle_cmds - Settings Toggle Commands


# Map command names to module names
COMMAND_MODULE_MAP = {
    "ac-fly": "fly",
    "ac-killaura": "killaura",
    "ac-reach": "reach",
    "ac-autoclicker": "autoclicker",
    "ac-scaffold": "scaffold",
    "ac-xray": "xray",
    "ac-gamemode": "gamemode",
    "ac-afk": "afk",
    "ac-vision": "vision",
    "ac-worldborder": "worldborder",
    "ac-lagclear": "lagclear",
    "ac-ratelimit": "ratelimit",
    "ac-namespoof": "namespoof",
    "ac-packetmonitor": "packetmonitor",
    "ac-containersee": "containersee",
}


def handle_toggle(plugin, sender, args) -> bool:
    """Handle any /ac-<module> toggle command."""
    # Get the command name from the sender's last command
    # The plugin passes this through on_command which knows the command name
    # We need to determine which module to toggle based on how we were called
    # Since all these commands route here, we inspect the calling context
    cmd_name = None

    # Walk up the call stack to find the command name
    import inspect
    frame = inspect.currentframe()
    try:
        # The on_command method stores cmd_name locally
        outer_frames = inspect.getouterframes(frame)
        for f_info in outer_frames:
            if 'cmd_name' in f_info[0].f_locals:
                cmd_name = f_info[0].f_locals['cmd_name']
                break
    finally:
        del frame

    if cmd_name is None:
        sender.send_message("§2[§7Paradox§2]§c Could not determine which module to toggle.")
        return False

    module_name = COMMAND_MODULE_MAP.get(cmd_name)
    if module_name is None:
        sender.send_message(f"§2[§7Paradox§2]§c Unknown module: {cmd_name}")
        return False

    # Handle special arguments for configurable modules
    if args:
        args_list = args if isinstance(args, list) else str(args).split()
        _handle_module_config(plugin, sender, module_name, args_list)
        return True

    # Toggle the module
    new_state = plugin.toggle_module(module_name)
    status = "§aenabled" if new_state else "§cdisabled"
    sender.send_message(f"§2[§7Paradox§2]§7 Module '{module_name}' {status}")
    plugin.send_to_level4(
        f"§2[§7Paradox§2]§7 {sender.name} {status}§7 module '{module_name}'"
    )
    return True


def _handle_module_config(plugin, sender, module_name, args):
    """Handle module-specific configuration arguments."""
    module = plugin.get_module(module_name)
    if module is None:
        return

    # Universal: handle 'sensitivity N' for any module
    if len(args) >= 2 and args[0].lower() == "sensitivity":
        try:
            level = int(args[1])
            module.set_sensitivity(level)
            sender.send_message(
                f"§2[§7Paradox§2]§a Module '{module_name}' sensitivity set to {module.sensitivity}/10."
            )
            return
        except ValueError:
            sender.send_message("§2[§7Paradox§2]§c Invalid sensitivity value (1-10).")
            return

    if module_name == "autoclicker" and args:
        try:
            max_cps = int(args[0])
            module.MAX_CPS = max_cps
            plugin.db.set("config", "max_cps", max_cps)
            sender.send_message(f"§2[§7Paradox§2]§a Max CPS set to {max_cps}.")
        except ValueError:
            sender.send_message("§2[§7Paradox§2]§c Invalid CPS value.")

    elif module_name == "afk" and args:
        try:
            timeout = int(args[0])
            module._timeout = timeout
            plugin.db.set("config", "afk_timeout", timeout)
            sender.send_message(f"§2[§7Paradox§2]§a AFK timeout set to {timeout}s.")
        except ValueError:
            sender.send_message("§2[§7Paradox§2]§c Invalid timeout value.")

    elif module_name == "worldborder" and args:
        try:
            radius = int(args[0])
            cx = int(args[1]) if len(args) > 1 else 0
            cz = int(args[2]) if len(args) > 2 else 0
            module.set_border(radius, cx, cz)
            sender.send_message(
                f"§2[§7Paradox§2]§a World border: radius={radius}, center=({cx}, {cz})"
            )
        except (ValueError, IndexError):
            sender.send_message("§2[§7Paradox§2]§c Usage: /ac-worldborder <radius> [centerX] [centerZ]")

    elif module_name == "lagclear" and args:
        try:
            interval = int(args[0])
            module.set_interval(interval)
            sender.send_message(f"§2[§7Paradox§2]§a Lag clear interval set to {interval}s.")
        except ValueError:
            sender.send_message("§2[§7Paradox§2]§c Invalid interval value.")

    else:
        # For modules without specific config, try to parse a bare number as sensitivity
        try:
            level = int(args[0])
            if 1 <= level <= 10:
                module.set_sensitivity(level)
                sender.send_message(
                    f"§2[§7Paradox§2]§a Module '{module_name}' sensitivity set to {module.sensitivity}/10."
                )
            else:
                sender.send_message("§2[§7Paradox§2]§c Sensitivity must be 1-10.")
        except ValueError:
            sender.send_message(f"§2[§7Paradox§2]§c Unknown argument: {args[0]}")
