# about_cmd - /ac-about Command


def handle_about(plugin, sender, args) -> bool:
    """Handle /ac-about"""
    lines = [
        "",
        "§2═══════════════════════════════════",
        "",
        "  §f§lParadox AntiCheat §r§7v1.0.0",
        "",
        "§2═══════════════════════════════════",
        "",
        "  §eOriginally created by:",
        "  §fVisual1mpact §7& §fPete9xi",
        "",
        "  §eOriginal repository:",
        "  §bgithub.com/Visual1mpact/Paradox_AntiCheat",
        "",
        "  §ePorted to Endstone by:",
        "  §a§lTheN1NJ4LL0",
        "",
        "  §7A Python port of the original Paradox",
        "  §7AntiCheat for Minecraft Bedrock Edition,",
        "  §7rebuilt as a native Endstone plugin with",
        "  §7SQLite persistence, SHA-256 auth, and",
        "  §716 detection modules.",
        "",
        "  §dAPI: §fEndstone 0.11",
        "  §dModules: §f16 §8| §dCommands: §f42+",
        "",
        "§2═══════════════════════════════════",
        "",
    ]
    sender.send_message("\n".join(lines))
    return True
