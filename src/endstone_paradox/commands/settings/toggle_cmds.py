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
    # Tier 1
    "ac-skinguard": "skinguard",
    "ac-noclip": "noclip",
    "ac-waterwalk": "waterwalk",
    "ac-stephack": "stephack",
    "ac-timer": "timer",
    "ac-blink": "blink",
    "ac-antikb": "antikb",
    "ac-criticals": "criticals",
    "ac-wallhit": "wallhit",
    "ac-triggerbot": "triggerbot",
    "ac-illegalitems": "illegalitems",
    "ac-selfinfliction": "selfinfliction",
    "ac-pvptoggle": "pvp",
    "ac-antidupe": "antidupe",
    "ac-crashdrop": "crashdrop",
    "ac-invsync": "invsync",
    # Tier 2
    "ac-discord": "discord",
    "ac-chatprotection": "chatprotection",
    "ac-antigrief": "antigrief",
    "ac-evidencereplay": "evidencereplay",
    # Tier 3
    "ac-adaptivecheck": "adaptivecheck",
    "ac-botdetection": "botdetection",
    "ac-reportsystem": "reportsystem",
    "ac-fingerprint": "fingerprint",
}


def handle_toggle(plugin, sender, args, **kwargs) -> bool:
    """Handle any /ac-<module> toggle command."""
    cmd_name = kwargs.get('cmd_name')

    if cmd_name is None:
        # Fallback: try frame inspection
        import inspect
        frame = inspect.currentframe()
        try:
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

    elif module_name == "fingerprint" and args:
        sub = args[0].lower()
        if sub == "trust" and len(args) >= 3:
            _handle_fingerprint_trust(plugin, sender, args[1], args[2])
        elif sub == "untrust" and len(args) >= 3:
            _handle_fingerprint_untrust(plugin, sender, args[1], args[2])
        elif sub == "list":
            _handle_fingerprint_list(plugin, sender)
        else:
            sender.send_message(
                "§2[§7Paradox§2]§e Usage: /ac-fingerprint trust <A> <B> | untrust <A> <B> | list"
            )
        return

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


# ── Fingerprint trust helpers ─────────────────────────────

def _resolve_player(plugin, name: str):
    """Find an online player by name, return (uuid_str, display_name) or None."""
    for p in plugin.server.online_players:
        if p.name.lower() == name.lower():
            return str(p.unique_id), p.name
    return None


def _handle_fingerprint_trust(plugin, sender, name_a: str, name_b: str):
    fp_module = plugin.get_module("fingerprint")
    if fp_module is None:
        sender.send_message("§2[§7Paradox§2]§c Fingerprint module not loaded.")
        return

    result_a = _resolve_player(plugin, name_a)
    result_b = _resolve_player(plugin, name_b)
    if result_a is None:
        sender.send_message(f"§2[§7Paradox§2]§c Player '{name_a}' not found online.")
        return
    if result_b is None:
        sender.send_message(f"§2[§7Paradox§2]§c Player '{name_b}' not found online.")
        return
    uuid_a, disp_a = result_a
    uuid_b, disp_b = result_b
    if uuid_a == uuid_b:
        sender.send_message("§2[§7Paradox§2]§c Cannot trust a player with themselves.")
        return

    fp_module.add_trusted_link(uuid_a, uuid_b, disp_a, disp_b)
    sender.send_message(
        f"§2[§7Paradox§2]§a Trusted link created: §f{disp_a} §a↔ §f{disp_b}"
    )


def _handle_fingerprint_untrust(plugin, sender, name_a: str, name_b: str):
    fp_module = plugin.get_module("fingerprint")
    if fp_module is None:
        sender.send_message("§2[§7Paradox§2]§c Fingerprint module not loaded.")
        return

    result_a = _resolve_player(plugin, name_a)
    result_b = _resolve_player(plugin, name_b)
    if result_a is None:
        sender.send_message(f"§2[§7Paradox§2]§c Player '{name_a}' not found online.")
        return
    if result_b is None:
        sender.send_message(f"§2[§7Paradox§2]§c Player '{name_b}' not found online.")
        return
    uuid_a, disp_a = result_a
    uuid_b, disp_b = result_b

    fp_module.remove_trusted_link(uuid_a, uuid_b)
    sender.send_message(
        f"§2[§7Paradox§2]§a Trusted link removed: §f{disp_a} §a↔ §f{disp_b}"
    )


def _handle_fingerprint_list(plugin, sender):
    fp_module = plugin.get_module("fingerprint")
    if fp_module is None:
        sender.send_message("§2[§7Paradox§2]§c Fingerprint module not loaded.")
        return

    links = fp_module.get_all_trusted_links()
    if not links:
        sender.send_message("§2[§7Paradox§2]§7 No trusted links configured.")
        return

    sender.send_message(f"§2[§7Paradox§2]§a Trusted Links ({len(links)}):")
    for key, data in links.items():
        if isinstance(data, dict):
            a = data.get("name_a", "?") or "?"
            b = data.get("name_b", "?") or "?"
        else:
            parts = key.split("|")
            a, b = parts[0][:8], parts[1][:8] if len(parts) > 1 else "?"
        sender.send_message(f"  §f{a} §7↔ §f{b}")
