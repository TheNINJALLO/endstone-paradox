# command_cmd - /ac-command Command


def handle_command(plugin, sender, args) -> bool:
    """Handle /ac-command <enable|disable> <command>"""
    if not args or len(args) < 2:
        sender.send_message("§2[§7Paradox§2]§c Usage: /ac-command <enable|disable> <command>")
        return False

    args_list = args if isinstance(args, list) else str(args).split()
    action = args_list[0].lower()
    cmd_name = args_list[1].lower()

    # Ensure the command name has the ac- prefix
    if not cmd_name.startswith("ac-"):
        cmd_name = f"ac-{cmd_name}"

    # Prevent disabling critical commands
    protected = {"ac-op", "ac-command", "ac-lockdown"}
    if cmd_name in protected:
        sender.send_message(f"§2[§7Paradox§2]§c Cannot disable protected command: {cmd_name}")
        return False

    if action == "disable":
        plugin.db.set("disabled_commands", cmd_name, True)
        sender.send_message(f"§2[§7Paradox§2]§a Disabled command: {cmd_name}")
    elif action == "enable":
        plugin.db.delete("disabled_commands", cmd_name)
        sender.send_message(f"§2[§7Paradox§2]§a Enabled command: {cmd_name}")
    else:
        sender.send_message("§2[§7Paradox§2]§c Use: enable or disable.")
        return False

    return True
