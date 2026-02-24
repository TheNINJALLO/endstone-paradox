"""
Paradox AntiCheat - /ac-modules Command

Display module status dashboard with toggle info.
"""


def handle_modules(plugin, sender, args) -> bool:
    """Handle /ac-modules"""
    lines = [
        "\n§2[§7Paradox§2]§a ── Module Dashboard ──",
        "",
    ]

    for name, module in sorted(plugin._modules.items()):
        status = "§a✓ Enabled" if module.running else "§c✗ Disabled"
        interval = ""
        if module.running and hasattr(module, 'check_interval'):
            interval = f" §8(check every {module.check_interval / 20:.1f}s)"
        lines.append(f"  §7{name}: {status}{interval}")

    lines.append("")
    lines.append(f"§7Total: {len(plugin._modules)} modules")
    lines.append(f"§7Active: {sum(1 for m in plugin._modules.values() if m.running)}")

    sender.send_message("\n".join(lines))
    return True
