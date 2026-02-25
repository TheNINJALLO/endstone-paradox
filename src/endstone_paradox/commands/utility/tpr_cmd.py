# tpr_cmd - /ac-tpr Command

import random


def handle_tpr(plugin, sender, args) -> bool:
    """Handle /ac-tpr [radius]"""
    radius = 5000  # Default radius

    if args:
        try:
            radius = int(args[0] if isinstance(args, list) else args)
            radius = min(radius, 30000)  # Cap at 30000
        except ValueError:
            sender.send_message("§2[§7Paradox§2]§c Invalid radius value.")
            return False

    # Generate random coordinates
    angle = random.uniform(0, 2 * 3.14159)
    dist = random.uniform(100, radius)
    x = int(dist * random.choice([-1, 1]) * abs(random.gauss(0.5, 0.3)))
    z = int(dist * random.choice([-1, 1]) * abs(random.gauss(0.5, 0.3)))

    # Teleport to surface at those coords
    try:
        plugin.server.dispatch_command(
            plugin.server.command_sender,
            f'tp "{sender.name}" {x} 320 {z}'
        )
        sender.send_message(f"§2[§7Paradox§2]§a Randomly teleported to ({x}, {z})!")
        sender.send_message("§2[§7Paradox§2]§7 You may fall briefly while chunks load.")
    except Exception as e:
        sender.send_message(f"§2[§7Paradox§2]§c Teleport failed: {e}")
        return False

    return True
