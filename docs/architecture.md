# Native architecture

Paradox 2.0.1 is a C++23 Endstone plugin. The active implementation lives in `native/`; `legacy/python/` retains the previous implementation for history and migration reference.

| Component | Responsibility |
| --- | --- |
| `native/src/plugin.cpp` | Endstone lifecycle, public API events, packet hooks, commands, forms and server policies |
| `native/src/engine.cpp` | Module registry, health/recovery guards, detector evidence and enforcement decisions |
| `native/src/protocol.cpp` | Typed decoding of inspected protocol-2193 packets with bounded inspection |
| `native/src/store.cpp` | Compatible SQLite store, consistent backup and bounded asynchronous writes |
| `native/src/web.cpp` | Bearer-authenticated dashboard and bounded HTTPS integration worker |

Game API operations stay on the server thread. HTTP requests queue supported Paradox commands for that thread; worker threads handle storage and network I/O. Shutdown flushes persistence and joins workers.

## Hooks and ABI

Endstone's pinned native headers, plugin export, event API, scheduler and native packet hooks provide the server boundary. The plugin does not invent private BDS layouts, vtables or offsets. Decoded protocol values are not casts of server memory. Linux uses libc++ to match Endstone's ABI; Windows uses clang-cl and the dynamic MSVC runtime.

The supplied Linux BDS executable is stripped and lacks DWARF type information, so `dwarf2cpp` cannot derive complete private class headers from it. The actual protocol dumper output was compared with pinned schema references. See [validation and the seven requested repositories](validation.md).

A different BDS/protocol requires another schema and ABI review. Unknown versions disable packet inspection while retaining management and supported API event monitoring. This fallback does not certify a new runtime.

See [building](building.md), [module audit](module-audit.md), [migration limitations](migration.md) and [pinned source/checksum references](https://github.com/TheNINJALLO/endstone-paradox/blob/main/native/references.lock.json).
