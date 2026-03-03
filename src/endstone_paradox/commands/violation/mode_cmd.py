# mode_cmd.py - /ac-mode <logonly|soft|hard> - Set enforcement mode

from endstone_paradox.core.violation_engine import EnforcementMode


def handle_mode(plugin, sender, args):
    """Set or view the enforcement mode."""
    engine = plugin.violation_engine
    if not engine:
        sender.send_message("§2[§7Paradox§2]§c Violation engine not available.")
        return True

    if not args or not args[0].strip():
        current = engine.mode
        sender.send_message(f"§2[§7Paradox§2]§e Current enforcement mode: §f{current}")
        sender.send_message("§2[§7Paradox§2]§7 Usage: /ac-mode <logonly|soft|hard>")
        sender.send_message("§2[§7Paradox§2]§7  logonly = log violations, no enforcement")
        sender.send_message("§2[§7Paradox§2]§7  soft = cancel + setback + notify (default)")
        sender.send_message("§2[§7Paradox§2]§7  hard = faster escalation, shorter ladder")
        return True

    mode = args[0].strip().lower()
    if mode not in (EnforcementMode.LOGONLY, EnforcementMode.SOFT, EnforcementMode.HARD):
        sender.send_message(f"§2[§7Paradox§2]§c Invalid mode '{mode}'. Use: logonly, soft, or hard")
        return True

    engine.set_mode(mode)
    sender.send_message(f"§2[§7Paradox§2]§a Enforcement mode set to: §f{mode}")

    # Notify all L4 admins
    plugin.send_to_level4(
        f"§2[§7Paradox§2]§e Enforcement mode changed to §f{mode}§e by §c{sender.name}"
    )
    return True
