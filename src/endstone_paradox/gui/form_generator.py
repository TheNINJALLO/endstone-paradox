"""
Paradox AntiCheat - GUI Form Generator

Creates ActionForm and ModalForm menus for the Paradox Admin GUI.
Uses Endstone's form system to provide an interactive management interface.
"""

from endstone.form import ActionForm, ModalForm


def build_main_menu(plugin, player):
    """Build the main Paradox admin menu."""
    form = ActionForm(
        title="§l§2Paradox §fAntiCheat",
        content="§7Welcome to the Paradox admin panel.\n§7Select a category below:",
    )

    form.add_button(
        "§a§lModules\n§r§7Manage detection modules",
        on_click=lambda p: _show_module_menu(plugin, p)
    )
    form.add_button(
        "§e§lPlayers\n§r§7Manage online players",
        on_click=lambda p: _show_player_menu(plugin, p)
    )
    form.add_button(
        "§6§lSecurity\n§r§7View security dashboard",
        on_click=lambda p: _show_security_info(plugin, p)
    )
    form.add_button(
        "§b§lSettings\n§r§7Configure server settings",
        on_click=lambda p: _show_settings_menu(plugin, p)
    )
    form.add_button(
        "§d§lDatabase\n§r§7Browse database tables",
        on_click=lambda p: _show_db_menu(plugin, p)
    )

    return form


# ─── Module Management ────────────────────────────────────────


def _show_module_menu(plugin, player):
    """Show the module toggle menu."""
    # Count running/total
    running = sum(1 for m in plugin._modules.values() if m.running)
    total = len(plugin._modules)

    form = ActionForm(
        title="§l§aModule Management",
        content=f"§7Active: §a{running}§7/{total} modules\n§7Tap a module to toggle it on/off:",
    )

    for name, module in sorted(plugin._modules.items()):
        if module.running:
            label = f"§a§l{name}\n§r§2Enabled"
        else:
            label = f"§c§l{name}\n§r§4Disabled"
        form.add_button(
            label,
            on_click=lambda p, n=name: _toggle_module(plugin, p, n)
        )

    # Back button
    form.add_button(
        "§8§l< Back\n§r§7Return to main menu",
        on_click=lambda p: p.send_form(build_main_menu(plugin, p))
    )

    player.send_form(form)


def _toggle_module(plugin, player, module_name):
    """Toggle a module and show confirmation."""
    new_state = plugin.toggle_module(module_name)
    status = "§aenabled" if new_state else "§cdisabled"
    player.send_message(f"§2[§7Paradox§2]§7 Module '{module_name}' {status}")
    # Re-show the module menu
    _show_module_menu(plugin, player)


# ─── Player Management ────────────────────────────────────────


def _show_player_menu(plugin, player):
    """Show the player management menu."""
    online = list(plugin.server.online_players)

    form = ActionForm(
        title="§l§ePlayer Management",
        content=f"§7Online: §e{len(online)} players\n§7Select a player to manage:",
    )

    for p in online:
        cl = plugin.security.get_clearance(p)
        form.add_button(
            f"§f§l{p.name}\n§r§7Clearance: §e{cl.name}",
            on_click=lambda sender, target=p: _show_player_actions(plugin, sender, target)
        )

    # Back button
    form.add_button(
        "§8§l< Back\n§r§7Return to main menu",
        on_click=lambda p: p.send_form(build_main_menu(plugin, p))
    )

    player.send_form(form)


def _show_player_actions(plugin, admin, target):
    """Show actions for a specific player."""
    cl = plugin.security.get_clearance(target)
    form = ActionForm(
        title=f"§l§eManage: {target.name}",
        content=f"§7Clearance: §e{cl.name}\n§7Select an action:",
    )

    form.add_button("§c§lKick\n§r§7Remove from server", on_click=lambda p: _kick_player(plugin, p, target))
    form.add_button("§4§lBan\n§r§7Permanently ban", on_click=lambda p: _ban_player(plugin, p, target))
    form.add_button("§6§lFreeze\n§r§7Toggle movement lock", on_click=lambda p: _freeze_player(plugin, p, target))
    form.add_button("§e§lWarn\n§r§7Send warning message", on_click=lambda p: _warn_player(plugin, p, target))
    form.add_button("§b§lTeleport To\n§r§7Go to their location", on_click=lambda p: p.teleport(target.location))

    # Back button
    form.add_button(
        "§8§l< Back\n§r§7Return to player list",
        on_click=lambda p: _show_player_menu(plugin, p)
    )

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


# ─── Security Dashboard ─────────────────────────────────────


def _show_security_info(plugin, player):
    """Show security dashboard as a form."""
    lockdown = "§c§lACTIVE" if plugin._lockdown_active else "§aInactive"
    lines = [
        f"§7Lockdown: {lockdown}",
        f"§7Frozen Players: §f{len(plugin._frozen_players)}",
        f"§7Vanished Admins: §f{len(plugin._vanished_players)}",
        f"§7Banned Players: §f{plugin.db.count('bans')}",
        f"§7Level 4 Admins: §f{len(plugin.security.get_level4_players())}",
        "",
        "§e§lOnline Players:",
    ]
    for p in plugin.server.online_players:
        cl = plugin.security.get_clearance(p)
        lines.append(f"  §f{p.name}: §7{cl.name}")

    form = ActionForm(
        title="§l§6Security Dashboard",
        content="\n".join(lines),
    )
    form.add_button(
        "§8§l< Back\n§r§7Return to main menu",
        on_click=lambda p: p.send_form(build_main_menu(plugin, p))
    )
    player.send_form(form)


# ─── Server Settings ─────────────────────────────────────────


def _show_settings_menu(plugin, player):
    """Show server settings form."""
    form = ModalForm(title="§l§bServer Settings")

    form.add_toggle("Lockdown Mode", default=plugin._lockdown_active)
    form.add_text_input("AFK Timeout (seconds)",
                        default=str(plugin.db.get("config", "afk_timeout", 600)))
    form.add_text_input("Lag Clear Interval (seconds)",
                        default=str(plugin.db.get("config", "lagclear_interval", 300)))
    form.add_text_input("Max CPS",
                        default=str(plugin.db.get("config", "max_cps", 30)))

    def on_submit(p, data):
        if data is None:
            # Cancelled — go back to main menu
            p.send_form(build_main_menu(plugin, p))
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


# ─── Database Viewer ─────────────────────────────────────────


def _show_db_menu(plugin, player):
    """Show database table browser."""
    form = ActionForm(
        title="§l§dDatabase Viewer",
        content="§7Select a table to browse:",
    )

    for table in plugin.db.list_tables():
        count = plugin.db.count(table)
        form.add_button(
            f"§f§l{table}\n§r§7{count} entries",
            on_click=lambda p, t=table: _show_table_contents(plugin, p, t)
        )

    # Back button
    form.add_button(
        "§8§l< Back\n§r§7Return to main menu",
        on_click=lambda p: p.send_form(build_main_menu(plugin, p))
    )

    player.send_form(form)


def _show_table_contents(plugin, player, table):
    """Show the contents of a database table."""
    entries = plugin.db.get_all(table)
    lines = [
        f"§e§lTable: §r§f{table}",
        f"§7Entries: §f{len(entries)}",
        "",
    ]

    for key, value in list(entries.items())[:15]:
        val_str = str(value)[:60]
        lines.append(f"§f{key}: §7{val_str}")

    if len(entries) > 15:
        lines.append(f"§8... and {len(entries) - 15} more")

    form = ActionForm(
        title=f"§l§d{table}",
        content="\n".join(lines),
    )
    form.add_button(
        "§8§l< Back\n§r§7Return to table list",
        on_click=lambda p: _show_db_menu(plugin, p)
    )
    player.send_form(form)
