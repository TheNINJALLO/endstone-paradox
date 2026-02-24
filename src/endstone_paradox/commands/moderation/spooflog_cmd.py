"""
Paradox AntiCheat - /ac-spooflog Command

View namespoof detection logs.
"""


def handle_spooflog(plugin, sender, args) -> bool:
    """Handle /ac-spooflog"""
    entries = plugin.db.get_all("spoof_log")

    if not entries:
        sender.send_message("§2[§7Paradox§2]§7 No namespoof logs recorded.")
        return True

    lines = ["§2[§7Paradox§2]§a ── Namespoof Log ──", ""]

    # Show last 20 entries
    sorted_entries = sorted(entries.items(), key=lambda x: x[0], reverse=True)[:20]
    for key, data in sorted_entries:
        if isinstance(data, dict):
            import time
            t = data.get("time", 0)
            time_str = time.strftime("%m/%d %H:%M", time.localtime(t)) if t else "?"
            lines.append(
                f"  §7[{time_str}] {data.get('name', '?')} - {data.get('reason', '?')}"
            )
        else:
            lines.append(f"  §7{key}: {data}")

    sender.send_message("\n".join(lines))
    return True
