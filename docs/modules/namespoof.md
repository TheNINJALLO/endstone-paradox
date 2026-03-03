# NameSpoof Detection

## Overview
Detects name manipulation including invalid characters, excessive length, and duplicate names.

## How It Works
1. **Length Check**: Flags names that are too short or too long
2. **Character Validation**: Checks for non-ASCII characters, control characters, and banned symbols
3. **Duplicate Detection**: Flags players with names that match or closely resemble existing online players

## Configuration
| Setting | Default | Description |
|---------|---------|-------------|
| Sensitivity | 5 | Higher = stricter character and length rules |
| Command | `/ac-namespoof` | Toggle on/off |