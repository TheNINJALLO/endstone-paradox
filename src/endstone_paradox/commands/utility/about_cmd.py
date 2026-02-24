"""
Paradox AntiCheat - /ac-about Command

Display plugin information, credits, and version.
"""


def handle_about(plugin, sender, args) -> bool:
    """Handle /ac-about"""
    lines = [
        "",
        "§2╔══════════════════════════════════════╗",
        "§2║     §f§lParadox AntiCheat §r§7v1.0.0       §2║",
        "§2╠══════════════════════════════════════╣",
        "§2║                                      §2║",
        "§2║  §eOriginally created by:              §2║",
        "§2║    §fVisual1mpact §7& §fPete9xi            §2║",
        "§2║                                      §2║",
        "§2║  §eOriginal repository:                §2║",
        "§2║    §bgithub.com/Visual1mpact/           §2║",
        "§2║    §bParadox_AntiCheat                  §2║",
        "§2║                                      §2║",
        "§2║  §ePorted to Endstone by:              §2║",
        "§2║    §a§lTheN1NJ4LL0                       §2║",
        "§2║                                      §2║",
        "§2║  §7This is a Python port of the         §2║",
        "§2║  §7original Paradox AntiCheat for       §2║",
        "§2║  §7Minecraft Bedrock Edition, rebuilt    §2║",
        "§2║  §7as a native Endstone plugin with     §2║",
        "§2║  §7SQLite persistence, SHA-256 auth,    §2║",
        "§2║  §7and 16 detection modules.            §2║",
        "§2║                                      §2║",
        "§2║  §dAPI: §fEndstone 0.11                  §2║",
        "§2║  §dModules: §f16 §8| §dCommands: §f42+        §2║",
        "§2║                                      §2║",
        "§2╚══════════════════════════════════════╝",
        "",
    ]
    sender.send_message("\n".join(lines))
    return True
