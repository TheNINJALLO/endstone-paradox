"""
Paradox AntiCheat - GUI Form Generator

Creates ActionForm and ModalForm menus for the Paradox Admin GUI.
Uses Endstone's form system to provide an interactive management interface.
"""

from endstone.form import ActionForm, ModalForm


def build_main_menu(plugin, player):
    """Build the main Paradox admin menu."""
    form = ActionForm(
        title="§2Paradox AntiCheat",
        content="§7Select a category to manage:",
    )

    # Module Management
    form.add_button(
        "§aModule Management",
        on_click=lambda p: _show_module_menu(plugin, p)
    )

    # Player Management
    form.add_button(
        "§ePlayer Management",
        on_click=lambda p: _show_player_menu(plugin, p)
    )

    # Security Dashboard
    form.add_button(
        "§6Security Dashboard",
        on_click=lambda p: _show_security_info(plugin, p)
    )

    # Server Settings
    form.add_button(
        "§bServer Settings",
        on_click=lambda p: _show_settings_menu(plugin, p)
    )

    # Database Viewer
    form.add_button(
        "§dDatabase Viewer",
        on_click=lambda p: _show_db_menu(plugin, p)
    )

    return form


def _show_module_menu(plugin, player):
    """Show the module toggle menu."""
    form = ActionForm(
        title="§2Module Management",
        content="§7Toggle modules on/off:",
    )

    for name, module in sorted(plugin._modules.items()):
        status = "§a●" if module.running else "§c●"
        form.add_button(
            f"{status} {name}",
            on_click=lambda p, n=name: _toggle_module(plugin, p, n)
        )

    player.send_form(form)


def _toggle_module(plugin, player, module_name):
    """Toggle a module and show confirmation."""
    new_state = plugin.toggle_module(module_name)
    status = "§aenabled" if new_state else "§cdisabled"
    player.send_message(f"§2[§7Paradox§2]§7 Module '{module_name}' {status}")
    # Re-show the module menu
    _show_module_menu(plugin, player)


def _show_player_menu(plugin, player):
    """Show the player management menu."""
    form = ActionForm(
        title="§ePlayer Management",
        content="§7Select a player to manage:",
    )

    for p in plugin.server.online_players:
        cl = plugin.security.get_clearance(p)
        form.add_button(
            f"§f{p.name} §7({cl.name})",
            on_click=lambda sender, target=p: _show_player_actions(plugin, sender, target)
        )

    player.send_form(form)


def _show_player_actions(plugin, admin, target):
    """Show actions for a specific player."""
    form = ActionForm(
        title=f"§eManage {target.name}",
        content=f"§7Clearance: {plugin.security.get_clearance(target).name}",
    )

    form.add_button("§cKick", on_click=lambda p: _kick_player(plugin, p, target))
    form.add_button("§4Ban", on_click=lambda p: _ban_player(plugin, p, target))
    form.add_button("§6Freeze", on_click=lambda p: _freeze_player(plugin, p, target))
    form.add_button("§eWarn", on_click=lambda p: _warn_player(plugin, p, target))
    form.add_button("§7Teleport To", on_click=lambda p: p.teleport(target.location))

    admin.send_form(form)


def _kick_player(plugin, admin, target):
    target.kick("§cKicked by admin (GUI)")
    admin.send_message(f"§2[§7Paradox§2]§a Kicked {target.name}.")


def _ban_player(plugin, admin, target):
    import time
    uuid_str = str(target.unique_id)
    plugin.db.set("bans", uuid_str, {
        "name": target.name,
        "reason": "Banned via GUI",
        "banned_by": admin.name,
        "time": time.time(),
    })
    target.kick("§cBanned by admin")
    admin.send_message(f"§2[§7Paradox§2]§a Banned {target.name}.")


def _freeze_player(plugin, admin, target):
    uuid_str = str(target.unique_id)
    if uuid_str in plugin._frozen_players:
        plugin._frozen_players.discard(uuid_str)
        plugin.db.delete("frozen_players", uuid_str)
        admin.send_message(f"§2[§7Paradox§2]§a Unfroze {target.name}.")
    else:
        plugin._frozen_players.add(uuid_str)
        plugin.db.set("frozen_players", uuid_str, {"name": target.name})
        admin.send_message(f"§2[§7Paradox§2]§a Froze {target.name}.")


def _warn_player(plugin, admin, target):
    target.send_message(f"§2[§7Paradox§2]§e§l WARNING §r§efrom {admin.name}.")
    admin.send_message(f"§2[§7Paradox§2]§a Warned {target.name}.")


def _show_security_info(plugin, player):
    """Show security dashboard as a form."""
    lines = [
        f"Lockdown: {'ACTIVE' if plugin._lockdown_active else 'Inactive'}",
        f"Frozen: {len(plugin._frozen_players)}",
        f"Vanished: {len(plugin._vanished_players)}",
        f"Banned: {plugin.db.count('bans')}",
        f"Level 4 Admins: {len(plugin.security.get_level4_players())}",
        "",
        "Online Players:",
    ]
    for p in plugin.server.online_players:
        cl = plugin.security.get_clearance(p)
        lines.append(f"  {p.name}: {cl.name}")

    form = ActionForm(
        title="§6Security Dashboard",
        content="\n".join(lines),
    )
    form.add_button("§7Close")
    player.send_form(form)


def _show_settings_menu(plugin, player):
    """Show server settings form."""
    form = ModalForm(title="§bServer Settings")

    form.add_toggle("Lockdown Mode", default=plugin._lockdown_active)
    form.add_text_input("AFK Timeout (seconds)",
                        default=str(plugin.db.get("config", "afk_timeout", 600)))
    form.add_text_input("Lag Clear Interval (seconds)",
                        default=str(plugin.db.get("config", "lagclear_interval", 300)))
    form.add_text_input("Max CPS",
                        default=str(plugin.db.get("config", "max_cps", 20)))

    def on_submit(p, data):
        if data is None:
            return
        try:
            # Lockdown
            if data[0] != plugin._lockdown_active:
                plugin._lockdown_active = data[0]
                plugin.db.set("config", "lockdown", data[0])

            # AFK timeout
            if data[1]:
                timeout = int(data[1])
                plugin.db.set("config", "afk_timeout", timeout)
                afk_mod = plugin.get_module("afk")
                if afk_mod:
                    afk_mod._timeout = timeout

            # Lag clear interval
            if data[2]:
                interval = int(data[2])
                lc_mod = plugin.get_module("lagclear")
                if lc_mod:
                    lc_mod.set_interval(interval)

            # Max CPS
            if data[3]:
                max_cps = int(data[3])
                plugin.db.set("config", "max_cps", max_cps)
                ac_mod = plugin.get_module("autoclicker")
                if ac_mod:
                    ac_mod.MAX_CPS = max_cps

            p.send_message("§2[§7Paradox§2]§a Settings updated!")
        except Exception as e:
            p.send_message(f"§2[§7Paradox§2]§c Error: {e}")

    form.on_submit = on_submit
    player.send_form(form)


def _show_db_menu(plugin, player):
    """Show database table browser."""
    form = ActionForm(
        title="§dDatabase Viewer",
        content="§7Select a table to browse:",
    )

    for table in plugin.db.list_tables():
        count = plugin.db.count(table)
        form.add_button(
            f"§7{table} ({count})",
            on_click=lambda p, t=table: _show_table_contents(plugin, p, t)
        )

    player.send_form(form)


def _show_table_contents(plugin, player, table):
    """Show the contents of a database table."""
    entries = plugin.db.get_all(table)
    lines = [f"Table: {table}", f"Entries: {len(entries)}", ""]

    for key, value in list(entries.items())[:15]:
        val_str = str(value)[:60]
        lines.append(f"{key}: {val_str}")

    if len(entries) > 15:
        lines.append(f"... and {len(entries) - 15} more")

    form = ActionForm(
        title=f"§d{table}",
        content="\n".join(lines),
    )
    form.add_button("§7Back", on_click=lambda p: _show_db_menu(plugin, p))
    player.send_form(form)
