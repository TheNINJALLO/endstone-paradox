# form_generator - GUI Form Generator

import json
import time
from endstone.form import ActionForm, ModalForm, Toggle, TextInput, Dropdown, Slider


# ═══════════════════════════════════════════════════════════════
#  MAIN MENU
# ═══════════════════════════════════════════════════════════════


def build_main_menu(plugin, player):
    """Build the main Paradox admin menu."""
    form = ActionForm(
        title="§l§2Paradox §fAntiCheat",
        content="§7Welcome to the Paradox admin panel.\n§7Select a category below:",
    )

    form.add_button(
        "§a§lModules\n§r§7Toggle detection modules on/off",
        on_click=lambda p: _show_module_menu(plugin, p)
    )
    form.add_button(
        "§c§lModeration\n§r§7Ban, kick, freeze, punish players",
        on_click=lambda p: _show_moderation_menu(plugin, p)
    )
    form.add_button(
        "§e§lPlayers\n§r§7Manage online players",
        on_click=lambda p: _show_player_menu(plugin, p)
    )
    form.add_button(
        "§b§lUtilities\n§r§7Home, TPR, PvP, channels, ranks",
        on_click=lambda p: _show_utility_menu(plugin, p)
    )
    form.add_button(
        "§6§lSecurity\n§r§7View security dashboard & opsec",
        on_click=lambda p: _show_security_info(plugin, p)
    )
    form.add_button(
        "§3§lSettings\n§r§7Configure server settings",
        on_click=lambda p: _show_settings_menu(plugin, p)
    )
    form.add_button(
        "§5§lCommands\n§r§7Enable/disable Paradox commands",
        on_click=lambda p: _show_command_toggle_menu(plugin, p)
    )
    form.add_button(
        "§d§lDatabase\n§r§7Browse database tables",
        on_click=lambda p: _show_db_menu(plugin, p)
    )

    return form


# ═══════════════════════════════════════════════════════════════
#  MODULE MANAGEMENT
# ═══════════════════════════════════════════════════════════════


def _show_module_menu(plugin, player):
    """Show the module toggle menu."""
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

    form.add_button(
        "§8§l< Back\n§r§7Return to main menu",
        on_click=lambda p: p.send_form(build_main_menu(plugin, p))
    )
    player.send_form(form)


def _toggle_module(plugin, player, module_name):
    """Toggle a module and refresh."""
    new_state = plugin.toggle_module(module_name)
    status = "§aenabled" if new_state else "§cdisabled"
    player.send_message(f"§2[§7Paradox§2]§7 Module '{module_name}' {status}")
    _show_module_menu(plugin, player)


# ═══════════════════════════════════════════════════════════════
#  MODERATION MENU
# ═══════════════════════════════════════════════════════════════


def _show_moderation_menu(plugin, player):
    """Show the moderation tools menu."""
    uuid = str(player.unique_id)
    vanished = uuid in plugin._vanished_players
    lockdown = plugin._lockdown_active

    form = ActionForm(
        title="§l§cModeration Tools",
        content="§7Quick-access admin tools:",
    )

    # Vanish toggle
    v_label = "§a§lUnvanish\n§r§7You are currently hidden" if vanished else "§7§lVanish\n§r§7Become invisible to players"
    form.add_button(v_label, on_click=lambda p: _gui_vanish(plugin, p))

    # Lockdown toggle
    l_label = "§a§lDisable Lockdown\n§r§7Server is locked" if lockdown else "§c§lEnable Lockdown\n§r§7Lock down the server"
    form.add_button(l_label, on_click=lambda p: _gui_lockdown(plugin, p))

    # Player actions
    form.add_button(
        "§c§lKick Player\n§r§7Remove a player from server",
        on_click=lambda p: _show_player_action_picker(plugin, p, "kick")
    )
    form.add_button(
        "§4§lBan Player\n§r§7Permanently ban a player",
        on_click=lambda p: _show_player_action_picker(plugin, p, "ban")
    )
    form.add_button(
        "§e§lUnban Player\n§r§7Unban a previously banned player",
        on_click=lambda p: _show_unban_form(plugin, p)
    )
    form.add_button(
        "§6§lFreeze Player\n§r§7Toggle movement lock on a player",
        on_click=lambda p: _show_player_action_picker(plugin, p, "freeze")
    )
    form.add_button(
        "§e§lPunish Player\n§r§7Warn, mute, kick, or ban",
        on_click=lambda p: _show_player_action_picker(plugin, p, "punish")
    )
    form.add_button(
        "§b§lDespawn Entities\n§r§7Remove entities by type/radius",
        on_click=lambda p: _show_despawn_form(plugin, p)
    )
    form.add_button(
        "§a§lAllowlist\n§r§7Manage server allowlist",
        on_click=lambda p: _show_allowlist_menu(plugin, p)
    )
    form.add_button(
        "§f§lWhitelist\n§r§7Manage server whitelist",
        on_click=lambda p: _show_whitelist_menu(plugin, p)
    )
    form.add_button(
        "§d§lSpoof Log\n§r§7View name spoofing logs",
        on_click=lambda p: _gui_spooflog(plugin, p)
    )
    form.add_button(
        "§3§lSet Prefix\n§r§7Change the chat prefix",
        on_click=lambda p: _show_prefix_form(plugin, p)
    )

    form.add_button(
        "§8§l< Back\n§r§7Return to main menu",
        on_click=lambda p: p.send_form(build_main_menu(plugin, p))
    )
    player.send_form(form)


def _gui_vanish(plugin, player):
    """Toggle vanish via GUI."""
    from endstone_paradox.commands.moderation.vanish_cmd import handle_vanish
    handle_vanish(plugin, player, None)
    _show_moderation_menu(plugin, player)


def _gui_lockdown(plugin, player):
    """Toggle lockdown via GUI."""
    from endstone_paradox.commands.moderation.lockdown_cmd import handle_lockdown
    handle_lockdown(plugin, player, None)
    _show_moderation_menu(plugin, player)


def _show_player_action_picker(plugin, player, action):
    """Show a list of online players to pick one for an action."""
    online = list(plugin.server.online_players)

    action_labels = {
        "kick": ("§l§cKick Player", "§7Select a player to kick:"),
        "ban": ("§l§4Ban Player", "§7Select a player to ban:"),
        "freeze": ("§l§6Freeze Player", "§7Select a player to freeze/unfreeze:"),
        "punish": ("§l§ePunish Player", "§7Select a player to punish:"),
        "invsee": ("§l§bView Inventory", "§7Select a player to inspect:"),
        "rank": ("§l§dSet Rank", "§7Select a player to rank:"),
        "tpa": ("§l§bTeleport To", "§7Select a player to teleport to:"),
    }
    title, content = action_labels.get(action, (f"§l{action}", "§7Select a player:"))

    form = ActionForm(title=title, content=content)

    for p in online:
        frozen = "§c[FROZEN] " if str(p.unique_id) in plugin._frozen_players else ""
        form.add_button(
            f"§f§l{p.name}\n§r{frozen}§7{p.address}",
            on_click=lambda sender, target=p, a=action: _do_player_action(plugin, sender, target, a)
        )

    form.add_button(
        "§8§l< Back\n§r§7Return to moderation",
        on_click=lambda p: _show_moderation_menu(plugin, p)
    )
    player.send_form(form)


def _do_player_action(plugin, admin, target, action):
    """Execute a player action."""
    if action == "kick":
        _show_reason_form(plugin, admin, target, "kick")
    elif action == "ban":
        _show_reason_form(plugin, admin, target, "ban")
    elif action == "freeze":
        _freeze_player(plugin, admin, target)
        _show_moderation_menu(plugin, admin)
    elif action == "punish":
        _show_punish_form(plugin, admin, target)
    elif action == "invsee":
        from endstone_paradox.commands.utility.invsee_cmd import handle_invsee
        handle_invsee(plugin, admin, [target.name])
    elif action == "rank":
        _show_rank_form(plugin, admin, target)
    elif action == "tpa":
        from endstone_paradox.commands.moderation.tpa_cmd import handle_tpa
        handle_tpa(plugin, admin, [target.name])


def _show_reason_form(plugin, admin, target, action):
    """Show a form to enter a reason for kick/ban."""
    title = "§l§cKick" if action == "kick" else "§l§4Ban"
    form = ModalForm(title=f"{title}: {target.name}")
    form.add_control(TextInput("Reason (optional)", "No reason given", ""))

    def on_submit(p, response):
        if response is None:
            _show_moderation_menu(plugin, p)
            return
        try:
            data = json.loads(response) if isinstance(response, str) else response
            reason = data[0] if data[0] else "No reason given"
            if action == "kick":
                target.kick(f"§cKicked: {reason}")
                p.send_message(f"§2[§7Paradox§2]§a Kicked {target.name}: {reason}")
            elif action == "ban":
                uuid_str = str(target.unique_id)
                plugin.db.set("bans", uuid_str, {
                    "name": target.name,
                    "reason": reason,
                    "banned_by": p.name,
                    "time": time.time(),
                })
                target.kick(f"§cBanned: {reason}")
                p.send_message(f"§2[§7Paradox§2]§a Banned {target.name}: {reason}")
        except Exception as e:
            p.send_message(f"§2[§7Paradox§2]§c Error: {e}")

    form.on_submit = on_submit
    admin.send_form(form)


def _show_unban_form(plugin, player):
    """Show form to unban a player."""
    bans = plugin.db.get_all("bans")

    if not bans:
        player.send_message("§2[§7Paradox§2]§7 No banned players.")
        _show_moderation_menu(plugin, player)
        return

    form = ActionForm(
        title="§l§eUnban Player",
        content=f"§7Banned players: §f{len(bans)}\n§7Select a player to unban:",
    )

    for uuid_str, data in bans.items():
        name = data.get("name", uuid_str) if isinstance(data, dict) else str(data)
        reason = data.get("reason", "N/A") if isinstance(data, dict) else "N/A"
        form.add_button(
            f"§f§l{name}\n§r§7Reason: {reason}",
            on_click=lambda p, u=uuid_str, n=name: _do_unban(plugin, p, u, n)
        )

    form.add_button(
        "§8§l< Back\n§r§7Return to moderation",
        on_click=lambda p: _show_moderation_menu(plugin, p)
    )
    player.send_form(form)


def _do_unban(plugin, admin, uuid_str, name):
    """Unban a player."""
    plugin.db.delete("bans", uuid_str)
    admin.send_message(f"§2[§7Paradox§2]§a Unbanned {name}.")
    _show_unban_form(plugin, admin)


def _show_punish_form(plugin, admin, target):
    """Show punishment options for a player."""
    form = ActionForm(
        title=f"§l§ePunish: {target.name}",
        content="§7Select a punishment:",
    )

    form.add_button("§e§lWarn\n§r§7Send a warning", on_click=lambda p: _warn_player(plugin, p, target))
    form.add_button("§6§lMute\n§r§7Mute the player", on_click=lambda p: _mute_player(plugin, p, target))
    form.add_button("§c§lKick\n§r§7Kick from server", on_click=lambda p: _show_reason_form(plugin, p, target, "kick"))
    form.add_button("§4§lBan\n§r§7Permanently ban", on_click=lambda p: _show_reason_form(plugin, p, target, "ban"))

    form.add_button(
        "§8§l< Back\n§r§7Return to moderation",
        on_click=lambda p: _show_moderation_menu(plugin, p)
    )
    admin.send_form(form)


def _show_despawn_form(plugin, player):
    """Show despawn entity form."""
    form = ModalForm(title="§l§bDespawn Entities")
    form.add_control(TextInput("Entity Type", "item", "item"))
    form.add_control(TextInput("Radius", "100", "100"))

    def on_submit(p, response):
        if response is None:
            _show_moderation_menu(plugin, p)
            return
        try:
            data = json.loads(response) if isinstance(response, str) else response
            entity_type = data[0] or "item"
            radius = int(data[1]) if data[1] else 100
            from endstone_paradox.commands.moderation.despawn_cmd import handle_despawn
            handle_despawn(plugin, p, [entity_type, str(radius)])
        except Exception as e:
            p.send_message(f"§2[§7Paradox§2]§c Error: {e}")

    form.on_submit = on_submit
    player.send_form(form)


def _show_allowlist_menu(plugin, player):
    """Show allowlist management."""
    from endstone_paradox.commands.moderation.allowlist_cmd import handle_allowlist
    form = ActionForm(
        title="§l§aAllowlist",
        content="§7Manage the server allowlist:",
    )
    form.add_button("§a§lView List\n§r§7Show current allowlist", on_click=lambda p: handle_allowlist(plugin, p, ["list"]))
    form.add_button("§e§lAdd Player\n§r§7Add a player name", on_click=lambda p: _show_text_action_form(plugin, p, "allowlist_add", "Add to Allowlist", "Player name"))
    form.add_button("§c§lRemove Player\n§r§7Remove a player name", on_click=lambda p: _show_text_action_form(plugin, p, "allowlist_remove", "Remove from Allowlist", "Player name"))
    form.add_button("§8§l< Back\n§r§7Return to moderation", on_click=lambda p: _show_moderation_menu(plugin, p))
    player.send_form(form)


def _show_whitelist_menu(plugin, player):
    """Show whitelist management."""
    from endstone_paradox.commands.moderation.whitelist_cmd import handle_whitelist
    form = ActionForm(
        title="§l§fWhitelist",
        content="§7Manage the server whitelist:",
    )
    form.add_button("§a§lView List\n§r§7Show current whitelist", on_click=lambda p: handle_whitelist(plugin, p, ["list"]))
    form.add_button("§e§lAdd Player\n§r§7Add a player name", on_click=lambda p: _show_text_action_form(plugin, p, "whitelist_add", "Add to Whitelist", "Player name"))
    form.add_button("§c§lRemove Player\n§r§7Remove a player name", on_click=lambda p: _show_text_action_form(plugin, p, "whitelist_remove", "Remove from Whitelist", "Player name"))
    form.add_button("§8§l< Back\n§r§7Return to moderation", on_click=lambda p: _show_moderation_menu(plugin, p))
    player.send_form(form)


def _show_text_action_form(plugin, player, action_key, title, placeholder):
    """Generic text-input form for actions needing a player name."""
    form = ModalForm(title=f"§l{title}")
    form.add_control(TextInput(placeholder, placeholder, ""))

    def on_submit(p, response):
        if response is None:
            _show_moderation_menu(plugin, p)
            return
        try:
            data = json.loads(response) if isinstance(response, str) else response
            value = data[0]
            if not value:
                p.send_message("§2[§7Paradox§2]§c Please enter a value.")
                return

            if action_key == "allowlist_add":
                from endstone_paradox.commands.moderation.allowlist_cmd import handle_allowlist
                handle_allowlist(plugin, p, ["add", value])
            elif action_key == "allowlist_remove":
                from endstone_paradox.commands.moderation.allowlist_cmd import handle_allowlist
                handle_allowlist(plugin, p, ["remove", value])
            elif action_key == "whitelist_add":
                from endstone_paradox.commands.moderation.whitelist_cmd import handle_whitelist
                handle_whitelist(plugin, p, ["add", value])
            elif action_key == "whitelist_remove":
                from endstone_paradox.commands.moderation.whitelist_cmd import handle_whitelist
                handle_whitelist(plugin, p, ["remove", value])
        except Exception as e:
            p.send_message(f"§2[§7Paradox§2]§c Error: {e}")

    form.on_submit = on_submit
    player.send_form(form)


def _gui_spooflog(plugin, player):
    """Show spoof logs."""
    from endstone_paradox.commands.moderation.spooflog_cmd import handle_spooflog
    handle_spooflog(plugin, player, None)


def _show_prefix_form(plugin, player):
    """Show prefix change form."""
    current = plugin.db.get("config", "prefix", "§2[§7Paradox§2]")
    form = ModalForm(title="§l§3Change Prefix")
    form.add_control(TextInput("New chat prefix", "§2[§7Paradox§2]", current))

    def on_submit(p, response):
        if response is None:
            _show_moderation_menu(plugin, p)
            return
        try:
            data = json.loads(response) if isinstance(response, str) else response
            prefix = data[0]
            if prefix:
                from endstone_paradox.commands.moderation.prefix_cmd import handle_prefix
                handle_prefix(plugin, p, [prefix])
        except Exception as e:
            p.send_message(f"§2[§7Paradox§2]§c Error: {e}")

    form.on_submit = on_submit
    player.send_form(form)


# ═══════════════════════════════════════════════════════════════
#  PLAYER MANAGEMENT
# ═══════════════════════════════════════════════════════════════


def _show_player_menu(plugin, player):
    """Show the player management menu."""
    online = list(plugin.server.online_players)

    form = ActionForm(
        title="§l§ePlayer Management",
        content=f"§7Online: §e{len(online)} players\n§7Select a player to manage:",
    )

    for p in online:
        cl = plugin.security.get_clearance(p)
        frozen = "§c[FROZEN] " if str(p.unique_id) in plugin._frozen_players else ""
        vanished = "§7[VANISHED] " if str(p.unique_id) in plugin._vanished_players else ""
        form.add_button(
            f"§f§l{p.name}\n§r{frozen}{vanished}§eClearance: {cl.name}",
            on_click=lambda sender, target=p: _show_player_actions(plugin, sender, target)
        )

    form.add_button(
        "§8§l< Back\n§r§7Return to main menu",
        on_click=lambda p: p.send_form(build_main_menu(plugin, p))
    )
    player.send_form(form)


def _show_player_actions(plugin, admin, target):
    """Show all actions for a specific player."""
    cl = plugin.security.get_clearance(target)
    frozen = str(target.unique_id) in plugin._frozen_players
    pvp_mod = plugin.get_module("pvp")
    pvp_status = ""
    if pvp_mod and pvp_mod.running:
        pvp_on = pvp_mod.is_pvp_enabled(target)
        pvp_status = f"\n§7PvP: {'§aOn' if pvp_on else '§cOff'}"

    rank = plugin.db.get("ranks", str(target.unique_id), "none")

    form = ActionForm(
        title=f"§l§eManage: {target.name}",
        content=f"§7Clearance: §e{cl.name}\n§7Rank: §a{rank}\n§7Frozen: {'§cYes' if frozen else '§aNo'}{pvp_status}",
    )

    form.add_button("§c§lKick\n§r§7Remove from server", on_click=lambda p: _show_reason_form(plugin, p, target, "kick"))
    form.add_button("§4§lBan\n§r§7Permanently ban", on_click=lambda p: _show_reason_form(plugin, p, target, "ban"))
    freeze_label = "§a§lUnfreeze\n§r§7Allow movement" if frozen else "§6§lFreeze\n§r§7Lock movement"
    form.add_button(freeze_label, on_click=lambda p: (_freeze_player(plugin, p, target), _show_player_actions(plugin, p, target)))
    form.add_button("§e§lWarn\n§r§7Send warning message", on_click=lambda p: (_warn_player(plugin, p, target), _show_player_actions(plugin, p, target)))
    form.add_button("§b§lTeleport To\n§r§7Go to their location", on_click=lambda p: _gui_tp_to(plugin, p, target))
    form.add_button("§3§lTeleport Here\n§r§7Bring them to you", on_click=lambda p: _gui_tp_here(plugin, p, target))
    form.add_button("§d§lSet Rank\n§r§7Change display rank", on_click=lambda p: _show_rank_form(plugin, p, target))
    form.add_button("§9§lView Inventory\n§r§7Inspect their items", on_click=lambda p: _gui_invsee(plugin, p, target))

    form.add_button(
        "§8§l< Back\n§r§7Return to player list",
        on_click=lambda p: _show_player_menu(plugin, p)
    )
    admin.send_form(form)


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


def _mute_player(plugin, admin, target):
    uuid_str = str(target.unique_id)
    plugin.db.set("muted_players", uuid_str, {"name": target.name, "muted_by": admin.name})
    target.send_message("§2[§7Paradox§2]§c You have been muted.")
    admin.send_message(f"§2[§7Paradox§2]§a Muted {target.name}.")


def _gui_tp_to(plugin, admin, target):
    try:
        plugin.server.dispatch_command(
            plugin.server.command_sender,
            f'tp "{admin.name}" "{target.name}"'
        )
        admin.send_message(f"§2[§7Paradox§2]§a Teleported to {target.name}.")
    except Exception as e:
        admin.send_message(f"§2[§7Paradox§2]§c Error: {e}")


def _gui_tp_here(plugin, admin, target):
    try:
        plugin.server.dispatch_command(
            plugin.server.command_sender,
            f'tp "{target.name}" "{admin.name}"'
        )
        admin.send_message(f"§2[§7Paradox§2]§a Teleported {target.name} to you.")
    except Exception as e:
        admin.send_message(f"§2[§7Paradox§2]§c Error: {e}")


def _gui_invsee(plugin, admin, target):
    from endstone_paradox.commands.utility.invsee_cmd import handle_invsee
    handle_invsee(plugin, admin, [target.name])


def _show_rank_form(plugin, admin, target):
    """Show form to set a player's rank."""
    current = plugin.db.get("ranks", str(target.unique_id), "")
    form = ModalForm(title=f"§l§dRank: {target.name}")
    form.add_control(TextInput("Rank (leave empty to remove)", "Member", current or ""))

    def on_submit(p, response):
        if response is None:
            _show_player_actions(plugin, p, target)
            return
        try:
            data = json.loads(response) if isinstance(response, str) else response
            rank = data[0]
            if not rank or rank.lower() in ("none", "remove", "clear"):
                plugin.db.delete("ranks", str(target.unique_id))
                p.send_message(f"§2[§7Paradox§2]§a Removed rank from {target.name}.")
            else:
                plugin.db.set("ranks", str(target.unique_id), rank)
                p.send_message(f"§2[§7Paradox§2]§a Set {target.name}'s rank to: {rank}")
                try:
                    target.send_message(f"§2[§7Paradox§2]§7 Your rank is now: §a{rank}")
                except Exception:
                    pass
        except Exception as e:
            p.send_message(f"§2[§7Paradox§2]§c Error: {e}")

    form.on_submit = on_submit
    admin.send_form(form)


# ═══════════════════════════════════════════════════════════════
#  UTILITY MENU
# ═══════════════════════════════════════════════════════════════


def _show_utility_menu(plugin, player):
    """Show utility tools menu."""
    form = ActionForm(
        title="§l§bUtilities",
        content="§7Player utility tools:",
    )

    form.add_button("§a§lHomes\n§r§7Manage your home locations", on_click=lambda p: _show_home_menu(plugin, p))
    form.add_button("§b§lRandom TP\n§r§7Teleport to a random location", on_click=lambda p: _show_tpr_form(plugin, p))
    form.add_button("§e§lPvP\n§r§7Toggle PvP on/off", on_click=lambda p: _show_pvp_menu(plugin, p))
    form.add_button("§d§lChannels\n§r§7Private chat channels", on_click=lambda p: _show_channels_menu(plugin, p))
    form.add_button("§f§lTeleport Request\n§r§7Send TPA to a player", on_click=lambda p: _show_player_action_picker(plugin, p, "tpa"))
    form.add_button("§9§lView Inventory\n§r§7Inspect a player's items", on_click=lambda p: _show_player_action_picker(plugin, p, "invsee"))
    form.add_button("§3§lSet Rank\n§r§7Change a player's display rank", on_click=lambda p: _show_player_action_picker(plugin, p, "rank"))
    form.add_button("§6§lAbout\n§r§7View Paradox info", on_click=lambda p: _gui_about(plugin, p))

    form.add_button(
        "§8§l< Back\n§r§7Return to main menu",
        on_click=lambda p: p.send_form(build_main_menu(plugin, p))
    )
    player.send_form(form)


# ─── Home ────────────────────────────────────────────────────


def _show_home_menu(plugin, player):
    """Show home management menu."""
    uuid_str = str(player.unique_id)
    homes = plugin.db.get("homes", uuid_str, {})
    if not isinstance(homes, dict):
        homes = {}

    form = ActionForm(
        title="§l§aHomes",
        content=f"§7Your homes: §f{len(homes)}/5\n§7Select a home to teleport, or set a new one:",
    )

    # Set new home
    form.add_button("§a§l+ Set Home Here\n§r§7Save current location", on_click=lambda p: _show_set_home_form(plugin, p))

    # Existing homes
    for name, data in homes.items():
        dim = data.get("dimension", "overworld")
        form.add_button(
            f"§f§l{name}\n§r§7{int(data['x'])}, {int(data['y'])}, {int(data['z'])} ({dim})",
            on_click=lambda p, n=name, d=data: _show_home_actions(plugin, p, n, d)
        )

    form.add_button(
        "§8§l< Back\n§r§7Return to utilities",
        on_click=lambda p: _show_utility_menu(plugin, p)
    )
    player.send_form(form)


def _show_home_actions(plugin, player, home_name, home_data):
    """Show actions for a specific home."""
    form = ActionForm(
        title=f"§l§aHome: {home_name}",
        content=f"§7Location: §f{int(home_data['x'])}, {int(home_data['y'])}, {int(home_data['z'])}\n§7Dimension: §f{home_data.get('dimension', 'overworld')}",
    )

    form.add_button("§a§lTeleport\n§r§7Go to this home", on_click=lambda p: _gui_tp_home(plugin, p, home_name, home_data))
    form.add_button("§c§lDelete\n§r§7Remove this home", on_click=lambda p: _gui_delete_home(plugin, p, home_name))
    form.add_button("§e§lUpdate\n§r§7Move to current location", on_click=lambda p: _gui_update_home(plugin, p, home_name))
    form.add_button("§8§l< Back\n§r§7Return to homes", on_click=lambda p: _show_home_menu(plugin, p))
    player.send_form(form)


def _gui_tp_home(plugin, player, name, data):
    from endstone_paradox.commands.utility.home_cmd import _teleport_to_home
    _teleport_to_home(plugin, player, name, data)


def _gui_delete_home(plugin, player, name):
    uuid_str = str(player.unique_id)
    homes = plugin.db.get("homes", uuid_str, {})
    if name in homes:
        del homes[name]
        plugin.db.set("homes", uuid_str, homes)
        player.send_message(f"§2[§7Paradox§2]§a Deleted home '{name}'.")
    _show_home_menu(plugin, player)


def _gui_update_home(plugin, player, name):
    uuid_str = str(player.unique_id)
    homes = plugin.db.get("homes", uuid_str, {})
    loc = player.location
    homes[name] = {
        "x": loc.x, "y": loc.y, "z": loc.z,
        "dimension": str(player.dimension.name) if hasattr(player.dimension, 'name') else "overworld",
    }
    plugin.db.set("homes", uuid_str, homes)
    player.send_message(f"§2[§7Paradox§2]§a Updated home '{name}' to current location.")
    _show_home_menu(plugin, player)


def _show_set_home_form(plugin, player):
    """Show form to set a new home."""
    form = ModalForm(title="§l§aSet New Home")
    form.add_control(TextInput("Home name", "default", "default"))

    def on_submit(p, response):
        if response is None:
            _show_home_menu(plugin, p)
            return
        try:
            data = json.loads(response) if isinstance(response, str) else response
            name = data[0] or "default"
            from endstone_paradox.commands.utility.home_cmd import handle_home
            handle_home(plugin, p, ["set", name])
        except Exception as e:
            p.send_message(f"§2[§7Paradox§2]§c Error: {e}")
        _show_home_menu(plugin, p)

    form.on_submit = on_submit
    player.send_form(form)


# ─── Random TP ───────────────────────────────────────────────


def _show_tpr_form(plugin, player):
    """Show random teleport form."""
    form = ModalForm(title="§l§bRandom Teleport")
    form.add_control(TextInput("Radius (max 30000)", "5000", "5000"))

    def on_submit(p, response):
        if response is None:
            _show_utility_menu(plugin, p)
            return
        try:
            data = json.loads(response) if isinstance(response, str) else response
            radius = data[0] or "5000"
            from endstone_paradox.commands.utility.tpr_cmd import handle_tpr
            handle_tpr(plugin, p, [radius])
        except Exception as e:
            p.send_message(f"§2[§7Paradox§2]§c Error: {e}")

    form.on_submit = on_submit
    player.send_form(form)


# ─── PvP ─────────────────────────────────────────────────────


def _show_pvp_menu(plugin, player):
    """Show PvP toggle menu."""
    pvp_mod = plugin.get_module("pvp")
    if pvp_mod is None or not pvp_mod.running:
        player.send_message("§2[§7Paradox§2]§c PvP module is not active.")
        _show_utility_menu(plugin, player)
        return

    global_pvp = pvp_mod._global_pvp
    personal_pvp = pvp_mod.is_pvp_enabled(player)
    in_combat = pvp_mod.is_in_combat(player)

    form = ActionForm(
        title="§l§ePvP Settings",
        content=f"§7Global PvP: {'§aEnabled' if global_pvp else '§cDisabled'}\n§7Your PvP: {'§aEnabled' if personal_pvp else '§cDisabled'}\n§7In Combat: {'§cYes' if in_combat else '§aNo'}",
    )

    # Personal toggle
    p_label = "§c§lDisable Your PvP\n§r§7Stop receiving/dealing player damage" if personal_pvp else "§a§lEnable Your PvP\n§r§7Allow player-vs-player combat"
    form.add_button(p_label, on_click=lambda p: _gui_toggle_pvp(plugin, p, "personal"))

    # Global toggle (admin)
    if plugin.security.is_level4(player):
        g_label = "§c§lDisable Global PvP\n§r§7Turn off PvP server-wide" if global_pvp else "§a§lEnable Global PvP\n§r§7Turn on PvP server-wide"
        form.add_button(g_label, on_click=lambda p: _gui_toggle_pvp(plugin, p, "global"))

    form.add_button("§8§l< Back\n§r§7Return to utilities", on_click=lambda p: _show_utility_menu(plugin, p))
    player.send_form(form)


def _gui_toggle_pvp(plugin, player, mode):
    from endstone_paradox.commands.utility.pvp_cmd import handle_pvp
    if mode == "global":
        handle_pvp(plugin, player, ["global"])
    else:
        handle_pvp(plugin, player, None)
    _show_pvp_menu(plugin, player)


# ─── Channels ────────────────────────────────────────────────


def _show_channels_menu(plugin, player):
    """Show channels management menu."""
    channels = plugin.db.get_all("channels")

    form = ActionForm(
        title="§l§dChat Channels",
        content=f"§7Active channels: §f{len(channels) if channels else 0}",
    )

    form.add_button("§a§l+ Create Channel\n§r§7Create a new private channel", on_click=lambda p: _show_channel_create_form(plugin, p))
    form.add_button("§b§lList Channels\n§r§7View all channels", on_click=lambda p: _gui_channel_list(plugin, p))

    if channels:
        for ch_name, data in channels.items():
            members = data.get("members", []) if isinstance(data, dict) else []
            uuid = str(player.unique_id)
            joined = uuid in members
            status = "§a[Joined]" if joined else "§7[Not joined]"
            form.add_button(
                f"§f§l#{ch_name}\n§r{status} §7{len(members)} members",
                on_click=lambda p, n=ch_name: _show_channel_actions(plugin, p, n)
            )

    form.add_button("§8§l< Back\n§r§7Return to utilities", on_click=lambda p: _show_utility_menu(plugin, p))
    player.send_form(form)


def _show_channel_actions(plugin, player, channel_name):
    """Show actions for a channel."""
    uuid = str(player.unique_id)
    data = plugin.db.get("channels", channel_name, {})
    members = data.get("members", []) if isinstance(data, dict) else []
    joined = uuid in members

    form = ActionForm(
        title=f"§l§d#{channel_name}",
        content=f"§7Members: §f{len(members)}\n§7Your status: {'§aJoined' if joined else '§cNot joined'}",
    )

    if joined:
        form.add_button("§e§lSend Message\n§r§7Send to this channel", on_click=lambda p: _show_channel_send_form(plugin, p, channel_name))
        form.add_button("§c§lLeave\n§r§7Leave this channel", on_click=lambda p: _gui_channel_action(plugin, p, channel_name, "leave"))
    else:
        form.add_button("§a§lJoin\n§r§7Join this channel", on_click=lambda p: _gui_channel_action(plugin, p, channel_name, "join"))

    form.add_button("§8§l< Back\n§r§7Return to channels", on_click=lambda p: _show_channels_menu(plugin, p))
    player.send_form(form)


def _gui_channel_action(plugin, player, channel_name, action):
    from endstone_paradox.commands.utility.channels_cmd import handle_channels
    handle_channels(plugin, player, [action, channel_name])
    _show_channels_menu(plugin, player)


def _gui_channel_list(plugin, player):
    from endstone_paradox.commands.utility.channels_cmd import handle_channels
    handle_channels(plugin, player, ["list"])


def _show_channel_create_form(plugin, player):
    form = ModalForm(title="§l§aCreate Channel")
    form.add_control(TextInput("Channel name", "my-channel", ""))

    def on_submit(p, response):
        if response is None:
            _show_channels_menu(plugin, p)
            return
        try:
            data = json.loads(response) if isinstance(response, str) else response
            name = data[0]
            if name:
                from endstone_paradox.commands.utility.channels_cmd import handle_channels
                handle_channels(plugin, p, ["create", name])
        except Exception as e:
            p.send_message(f"§2[§7Paradox§2]§c Error: {e}")
        _show_channels_menu(plugin, p)

    form.on_submit = on_submit
    player.send_form(form)


def _show_channel_send_form(plugin, player, channel_name):
    form = ModalForm(title=f"§l§eSend to #{channel_name}")
    form.add_control(TextInput("Message", "Hello!", ""))

    def on_submit(p, response):
        if response is None:
            _show_channel_actions(plugin, p, channel_name)
            return
        try:
            data = json.loads(response) if isinstance(response, str) else response
            msg = data[0]
            if msg:
                from endstone_paradox.commands.utility.channels_cmd import handle_channels
                handle_channels(plugin, p, ["send", channel_name, msg])
        except Exception as e:
            p.send_message(f"§2[§7Paradox§2]§c Error: {e}")

    form.on_submit = on_submit
    player.send_form(form)


def _gui_about(plugin, player):
    from endstone_paradox.commands.utility.about_cmd import handle_about
    handle_about(plugin, player, None)


# ═══════════════════════════════════════════════════════════════
#  SECURITY DASHBOARD
# ═══════════════════════════════════════════════════════════════


def _show_security_info(plugin, player):
    """Show security dashboard."""
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
        frozen = " §c[F]" if str(p.unique_id) in plugin._frozen_players else ""
        vanished = " §7[V]" if str(p.unique_id) in plugin._vanished_players else ""
        lines.append(f"  §f{p.name}: §7{cl.name}{frozen}{vanished}")

    form = ActionForm(
        title="§l§6Security Dashboard",
        content="\n".join(lines),
    )

    form.add_button("§e§lOpsec Report\n§r§7View detailed security info", on_click=lambda p: _gui_opsec(plugin, p))
    form.add_button(
        "§8§l< Back\n§r§7Return to main menu",
        on_click=lambda p: p.send_form(build_main_menu(plugin, p))
    )
    player.send_form(form)


def _gui_opsec(plugin, player):
    from endstone_paradox.commands.moderation.opsec_cmd import handle_opsec
    handle_opsec(plugin, player, None)


# ═══════════════════════════════════════════════════════════════
#  SERVER SETTINGS
# ═══════════════════════════════════════════════════════════════


def _show_settings_menu(plugin, player):
    """Show server settings form."""
    form = ModalForm(title="§l§bServer Settings")

    form.add_control(Toggle("Lockdown Mode", plugin._lockdown_active))
    form.add_control(TextInput(
        "AFK Timeout (seconds)", "600",
        str(plugin.db.get("config", "afk_timeout", 600))
    ))
    form.add_control(TextInput(
        "Lag Clear Interval (seconds)", "300",
        str(plugin.db.get("config", "lagclear_interval", 300))
    ))
    form.add_control(TextInput(
        "Max CPS (autoclicker)", "30",
        str(plugin.db.get("config", "max_cps", 30))
    ))
    form.add_control(TextInput(
        "World Border Radius", "10000",
        str(plugin.db.get("config", "worldborder_radius", 10000))
    ))

    pvp_mod = plugin.get_module("pvp")
    if pvp_mod:
        form.add_control(Toggle("Global PvP", pvp_mod._global_pvp if hasattr(pvp_mod, '_global_pvp') else True))

    def on_submit(p, response):
        if response is None:
            p.send_form(build_main_menu(plugin, p))
            return
        try:
            data = json.loads(response) if isinstance(response, str) else response

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

            # World border radius
            if data[4]:
                radius = int(data[4])
                plugin.db.set("config", "worldborder_radius", radius)
                wb_mod = plugin.get_module("worldborder")
                if wb_mod:
                    wb_mod._radius = radius

            # Global PvP
            if pvp_mod and len(data) > 5:
                if data[5] != (pvp_mod._global_pvp if hasattr(pvp_mod, '_global_pvp') else True):
                    pvp_mod.toggle_global_pvp()

            p.send_message("§2[§7Paradox§2]§a Settings updated!")
        except Exception as e:
            p.send_message(f"§2[§7Paradox§2]§c Error: {e}")

    form.on_submit = on_submit
    player.send_form(form)


# ═══════════════════════════════════════════════════════════════
#  COMMAND ENABLE/DISABLE
# ═══════════════════════════════════════════════════════════════


def _show_command_toggle_menu(plugin, player):
    """Show all commands with enable/disable toggles."""
    disabled_cmds = plugin.db.get("config", "disabled_commands", [])
    if not isinstance(disabled_cmds, list):
        disabled_cmds = []

    all_cmds = sorted(plugin.commands.keys())

    form = ActionForm(
        title="§l§5Command Management",
        content=f"§7Total commands: §f{len(all_cmds)}\n§7Disabled: §c{len(disabled_cmds)}\n§7Tap to toggle a command on/off:",
    )

    for cmd in all_cmds:
        enabled = cmd not in disabled_cmds
        desc = plugin.commands[cmd].get("description", "")
        if enabled:
            label = f"§a§l{cmd}\n§r§2Enabled §8- {desc}"
        else:
            label = f"§c§l{cmd}\n§r§4Disabled §8- {desc}"
        form.add_button(
            label,
            on_click=lambda p, c=cmd: _toggle_command(plugin, p, c)
        )

    form.add_button(
        "§8§l< Back\n§r§7Return to main menu",
        on_click=lambda p: p.send_form(build_main_menu(plugin, p))
    )
    player.send_form(form)


def _toggle_command(plugin, player, cmd_name):
    """Toggle a command on/off."""
    disabled_cmds = plugin.db.get("config", "disabled_commands", [])
    if not isinstance(disabled_cmds, list):
        disabled_cmds = []

    if cmd_name in disabled_cmds:
        disabled_cmds.remove(cmd_name)
        player.send_message(f"§2[§7Paradox§2]§a Enabled command: §f{cmd_name}")
    else:
        disabled_cmds.append(cmd_name)
        player.send_message(f"§2[§7Paradox§2]§c Disabled command: §f{cmd_name}")

    plugin.db.set("config", "disabled_commands", disabled_cmds)
    _show_command_toggle_menu(plugin, player)


# ═══════════════════════════════════════════════════════════════
#  DATABASE VIEWER
# ═══════════════════════════════════════════════════════════════


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
