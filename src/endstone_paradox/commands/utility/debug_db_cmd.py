"""
Paradox AntiCheat - /ac-debug-db Command

Direct SQLite database inspection and modification for admins.
"""


def handle_debug_db(plugin, sender, args) -> bool:
    """Handle /ac-debug-db <table> [key] [value]"""
    if not args:
        # Show available tables
        tables = plugin.db.list_tables()
        sender.send_message("§2[§7Paradox§2]§a Database Tables:")
        for table in tables:
            count = plugin.db.count(table)
            sender.send_message(f"  §7{table}: {count} entries")
        return True

    args_list = args if isinstance(args, list) else str(args).split()
    table = args_list[0]

    if len(args_list) == 1:
        # Show all entries in table
        entries = plugin.db.get_all(table)
        if not entries:
            sender.send_message(f"§2[§7Paradox§2]§7 Table '{table}' is empty.")
        else:
            sender.send_message(f"§2[§7Paradox§2]§a Table '{table}':")
            for key, value in list(entries.items())[:20]:  # Limit to 20 entries
                value_str = str(value)[:80]
                sender.send_message(f"  §7{key}: §f{value_str}")
            if len(entries) > 20:
                sender.send_message(f"  §7... and {len(entries) - 20} more entries")
        return True

    key = args_list[1]

    if len(args_list) == 2:
        # Read specific key
        value = plugin.db.get(table, key)
        if value is None:
            sender.send_message(f"§2[§7Paradox§2]§c Key '{key}' not found in '{table}'.")
        else:
            import json
            try:
                formatted = json.dumps(value, indent=2)
            except Exception:
                formatted = str(value)
            sender.send_message(f"§2[§7Paradox§2]§a {table}.{key}:")
            sender.send_message(f"§7{formatted}")
        return True

    # Set a value
    raw_value = " ".join(args_list[2:])
    try:
        import json
        value = json.loads(raw_value)
    except (json.JSONDecodeError, ValueError):
        value = raw_value  # Store as string if not valid JSON

    plugin.db.set(table, key, value)
    sender.send_message(f"§2[§7Paradox§2]§a Set {table}.{key} = {value}")
    return True
