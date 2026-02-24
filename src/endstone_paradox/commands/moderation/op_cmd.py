"""
Paradox AntiCheat - /ac-op Command

Grant security clearance using a password.
First usage sets the password; subsequent uses verify against it.
"""

from endstone_paradox.security import SecurityClearance, hash_password, verify_password


def handle_op(plugin, sender, args) -> bool:
    """Handle /ac-op <password>"""
    if not args:
        sender.send_message("§2[§7Paradox§2]§c Usage: /ac-op <password>")
        return False

    password = " ".join(args) if isinstance(args, list) else str(args)

    if not plugin.security.has_password_set():
        # First time — set the password
        pw_hash = hash_password(password)
        plugin.security.set_password_hash(pw_hash)
        plugin.security.set_clearance(sender, SecurityClearance.LEVEL_4)
        sender.send_message(
            "§2[§7Paradox§2]§a Password set! You now have Level 4 clearance."
        )
        plugin.logger.info(f"[Paradox] {sender.name} set the operator password and gained Level 4 clearance.")
        return True

    # Verify password
    stored_hash = plugin.security.get_stored_password_hash()
    if verify_password(password, stored_hash):
        plugin.security.set_clearance(sender, SecurityClearance.LEVEL_4)
        sender.send_message(
            "§2[§7Paradox§2]§a Password accepted! You now have Level 4 clearance."
        )
        plugin.send_to_level4(
            f"§2[§7Paradox§2]§7 {sender.name} has been granted Level 4 clearance."
        )
        return True
    else:
        sender.send_message("§2[§7Paradox§2]§c Incorrect password.")
        plugin.send_to_level4(
            f"§2[§7Paradox§2]§c {sender.name} attempted /ac-op with incorrect password!"
        )
        return False
