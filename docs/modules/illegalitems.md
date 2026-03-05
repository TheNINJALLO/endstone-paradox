# Illegal Items Scanner

> Detects and removes illegal items from player inventories.

## How It Works

Scans player inventories for items that shouldn't exist in survival mode:

| Check | Description |
|-------|-------------|
| **Enchantment Levels** | Detects enchantments above max vanilla levels (e.g., Sharpness 32767) |
| **Stack Sizes** | Flags items with impossible stack sizes (e.g., 64 swords) |
| **Creative-Only Items** | Detects items that can only be obtained in creative mode |

Items are automatically removed with evidence logged to the violation engine.

## Detection Details

| Parameter | Value |
|-----------|-------|
| Scan trigger | On player join, periodically, on inventory change |
| Action | Auto-remove + violation emit |
| Level 4 exempt | Yes |

## Default State

**ON**
