# Step Hack Detection

> Detects players stepping up full blocks without jumping.

## How It Works

Monitors player position changes for ascending full blocks (0.6+ block threshold) without a corresponding jump action in the PlayerAuthInputPacket. Exempts stairs, slabs, slime blocks, and other legitimate step-up sources. Requires **3 consecutive flags**.

## Detection Details

| Parameter | Value |
|-----------|-------|
| Height threshold | 0.6 blocks |
| Flags required | 3 consecutive |
| Exemptions | Stairs, slabs, slime blocks |
| Level 4 exempt | Yes |

## Default State

**ON**
