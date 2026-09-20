# In-game GUI

Run `/ac-gui` to open the native Endstone form, or `/ac-guiitem` to receive a compass named **Paradox Menu**. Using that compass opens the same controls. A full inventory prevents adding it.

| Button | Behavior and authorization |
| --- | --- |
| Module settings | List and toggle modules; clearance 4 or `paradox.settings` |
| Recent evidence | Display the recent bounded evidence list; clearance 3 or `paradox.case` |
| My homes | Run the current player's home listing; `paradox.home` |
| Connection health | Show ping and detection readiness; `paradox.ping` |

The menu rechecks authorization when buttons run. Opening it does not grant staff privileges. The native GUI has these four entry points; the Python eight-section menu and sensitivity forms are historical.

Module switches persist to SQLite. Utilities such as PvP, chunk display and claims also have player commands; see [utility commands](commands/utility.md) and [module controls](commands/toggles.md).
