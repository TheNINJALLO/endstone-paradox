"""
Paradox AntiCheat - /ac-gui Command

Open the main Paradox GUI menu using Endstone's ActionForm.
"""

from endstone_paradox.gui.form_generator import build_main_menu


def handle_gui(plugin, sender, args) -> bool:
    """Handle /ac-gui"""
    form = build_main_menu(plugin, sender)
    sender.send_form(form)
    return True
