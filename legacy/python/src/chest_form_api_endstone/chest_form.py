# Copyright © 2025 - 2026 GlacieTeam.All rights reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0. If a copy of the MPL was not
# distributed with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0

from uuid import UUID
from typing import Dict, Callable, Optional, List
from endstone import Player
from endstone.inventory import ItemStack
from endstone.plugin import Plugin
from endstone.level import Dimension
from endstone.event import PacketReceiveEvent, EventPriority
from rapidnbt import CompoundTag, ByteTag, ShortTag
from bedrock_protocol.packets.packet import (
    UpdateBlockPacket,
    BlockActorDataPacket,
    ItemStackRequestPacket,
    ContainerClosePacket,
    ContainerOpenPacket,
)
from bedrock_protocol.packets import MinecraftPacketIds
from bedrock_protocol.packets.enums import ItemStackRequestActionType
from bedrock_protocol.packets.types import NetworkBlockPosition
import endstone.nbt


class ChestForm:
    """
    Chest form API
    """

    title: str
    large_chest: bool
    ui_items: Dict[int, CompoundTag]
    call_backs: Dict[int, Callable[[Player, int], None]]
    plugin: Plugin

    def __init__(self, plugin: Plugin, title: str = "ChestUI", large_chest=True):
        """
        Create a chest form

        Args:
            plugin (Plugin): The plugin using chest form
            title (str): The title of the chest sent to client
            large_chest (bool): Whether to send a large chest
        """

        self.title = title
        self.large_chest = large_chest
        self.ui_items = {}
        self.call_backs = {}
        if not hasattr(plugin, "__chest_form_api_listener"):

            def on_incoming_packet(event: PacketReceiveEvent):
                if event.packet_id == MinecraftPacketIds.ItemStackRequest:
                    ChestFormCallbackHandler.handle_chest_callback(
                        event.player, event.payload
                    )
                elif event.packet_id == MinecraftPacketIds.ContainerClose:
                    ChestFormCallbackHandler.handle_chest_close(
                        event.player, event.payload
                    )

            plugin.server.plugin_manager.register_event(
                "PacketReceiveEvent",
                on_incoming_packet,
                EventPriority.NORMAL,
                plugin,
                False,
            )
            setattr(plugin, "__chest_form_api_listener", True)
        self.plugin = plugin
        for index in range(54):
            set_form_slot(self, index, None, None)

    def set_title(self, title: str) -> None:
        """
        Set the title of the chest

        Args:
            title (str): The title of the chest sent to client
        """

        self.title = title

    def set_slot(
        self,
        slot: int,
        item_type: str,
        callback: Optional[Callable[[Player, int], None]] = None,
        *,
        item_amount: int = 1,
        item_data: int = 0,
        display_name: Optional[str] = None,
        lore: Optional[List[str]] = None,
        enchants: Optional[Dict[str, int]] = None,
        nbt: Optional[endstone.nbt.CompoundTag] = None,
    ) -> None:
        """
        Set item in a specfic slot with click callback

        Args:
            slot (int): The index of the slot
            item_type (str): The full type name of the item
            callback (Optional[Callable[[Player, int], None]]): The click callback of the slot
            item_amount (int): The amount of the item
            item_data (int): The aux value of the item
            display_name (Optional[str]): The custom name (display name) of the item
            lore (Optional[List[str]]): The lore of the item
            enchants (Optional[Dict[str, int]]): The enchantments on the item (ingore vanilla limit)
        """

        item = ItemStack(item_type, item_amount, item_data)
        meta = item.item_meta
        if display_name is not None:
            meta.display_name = display_name
        if lore is not None:
            meta.lore = lore
        if enchants is not None:
            for name, level in enchants.items():
                meta.add_enchant(name, level, True)
        item.set_item_meta(meta)
        if nbt is not None:
            item.nbt = nbt
        set_form_slot(self, slot, item, callback)

    def fill_slots(
        self,
        item_type: str,
        *,
        item_amount: int = 1,
        item_data: int = 0,
        display_name: Optional[str] = None,
        lore: Optional[List[str]] = None,
        enchants: Optional[Dict[str, int]] = None,
        nbt: Optional[endstone.nbt.CompoundTag] = None,
    ) -> None:
        """
        Fill all slots with a default item with no callback (default placeholder item)
        This method is recommend to call at first

        Args:
            item_type (str): The full type name of the item
            item_amount (int): The amount of the item
            item_data (int): The aux value of the item
            display_name (Optional[str]): The custom name (display name) of the item
            lore (Optional[List[str]]): The lore of the item
            enchants (Optional[Dict[str, int]]): The enchantments on the item (ingore vanilla limit)
        """

        for index in range(54):
            self.set_slot(
                index,
                item_type,
                None,
                item_amount=item_amount,
                item_data=item_data,
                display_name=display_name,
                lore=lore,
                enchants=enchants,
                nbt=nbt,
            )

    def send_to(self, player: Player) -> None:
        """
        Send the form to a player

        Args:
            player (Player): The player who receive the form
        """

        x = player.location.block_x
        y = player.location.block_y + 4
        z = player.location.block_z
        d = player.location.dimension.type
        if (
            (d == Dimension.Type.OVERWORLD and y > 319)
            or (d == Dimension.Type.NETHER and y > 127)
            or (d == Dimension.Type.THE_END and y > 255)
        ):
            y = player.location.block_y - 3

        update_chest_block(self, player, x, y, z, False)
        update_chest_block_actor(self, player, x, y, z)

        def open_chest():
            player.send_packet(
                MinecraftPacketIds.ContainerOpen,
                ContainerOpenPacket(
                    114, 0, NetworkBlockPosition(x, y, z), -1
                ).serialize(),
            )
            ChestFormCallbackHandler.add_runtime_form(player, FormData(self, x, y, z))

        run_delay_task(open_chest, 10, self.plugin)


class FormData:
    form: ChestForm
    x: int
    y: int
    z: int

    def __init__(self, form: ChestForm, x: int, y: int, z: int):
        self.form = form
        self.x = x
        self.y = y
        self.z = z


class ChestFormCallbackHandler:
    runtime_forms: Dict[UUID, FormData] = {}

    @classmethod
    def add_runtime_form(cls, player: Player, data: FormData):
        cls.runtime_forms[player.unique_id] = data

    @classmethod
    def handle_chest_callback(cls, player: Player, payload: bytes):
        packet = ItemStackRequestPacket()
        packet.deserialize(payload)
        uuid = player.unique_id
        if uuid in cls.runtime_forms:
            data = cls.runtime_forms[uuid]
            form = data.form
            for req in packet.request.request_data:
                for action in req.request_actions:
                    if (action.action_type == ItemStackRequestActionType.Take) and (
                        action.action_data.source.net_id == 0
                    ):
                        index = action.action_data.source.slot
                        if index in form.call_backs:
                            player.send_packet(
                                MinecraftPacketIds.ContainerClose,
                                ContainerClosePacket(114, 0, True).serialize(),
                            )
                            update_chest_block(
                                form, player, data.x, data.y, data.z, True
                            )
                            del cls.runtime_forms[uuid]
                            run_delay_task(
                                lambda: form.call_backs[index](player, index),
                                2,
                                form.plugin,
                            )
                            return

    @classmethod
    def handle_chest_close(cls, player: Player, payload: bytes):
        packet = ContainerClosePacket()
        packet.deserialize(payload)
        uuid = player.unique_id
        if packet.container_id == 114:
            if uuid in cls.runtime_forms:
                data = cls.runtime_forms[uuid]
                form = data.form
                update_chest_block(form, player, data.x, data.y, data.z, True)
                del cls.runtime_forms[uuid]


ENCHANTMENTS_MAP = {
    "protection": 0,
    "fire_protection": 1,
    "feather_falling": 2,
    "blast_protection": 3,
    "projectile_protection": 4,
    "thorns": 5,
    "respiration": 6,
    "depth_strider": 7,
    "aqua_affinity": 8,
    "sharpness": 9,
    "smite": 10,
    "bane_of_arthropods": 11,
    "knockback": 12,
    "fire_aspect": 13,
    "looting": 14,
    "efficiency": 15,
    "silk_touch": 16,
    "unbreaking": 17,
    "fortune": 18,
    "power": 19,
    "punch": 20,
    "flame": 21,
    "infinity": 22,
    "luck_of_the_sea": 23,
    "lure": 24,
    "frost_walker": 25,
    "mending": 26,
    "curse_of_binding": 27,
    "curse_of_vanishing": 28,
    "impaling": 29,
    "riptide": 30,
    "loyalty": 31,
    "channeling": 32,
    "multishot": 33,
    "piercing": 34,
    "quick_charge": 35,
    "soul_speed": 36,
    "swift_sneak": 37,
    "wind_burst": 38,
    "density": 39,
    "breach": 40,
    "lunge": 41,
}


def set_form_slot(
    form: ChestForm,
    index: int,
    item: ItemStack,
    callback: Optional[Callable[[Player, int], None]],
):
    item_nbt = CompoundTag()
    if item is not None:
        slot = index
        if slot >= 27:
            slot -= 27
        item_nbt = CompoundTag(
            {
                "Count": ByteTag(item.amount),
                "Damage": ShortTag(item.data),
                "Name": item.type.id,
                "WasPickedUp": False,
                "Slot": ByteTag(slot),
            }
        )
        tag = CompoundTag()
        if item.item_meta.has_display_name:
            tag["display"]["Name"] = item.item_meta.display_name
        if item.item_meta.has_lore:
            tag["display"]["Lore"] = item.item_meta.lore
        if item.item_meta.has_enchants:
            tag["ench"] = []
            for name, level in item.item_meta.enchants.items():
                if name in ENCHANTMENTS_MAP:
                    ench = ENCHANTMENTS_MAP[name]
                    tag["ench"].append({"id": ShortTag(ench), "lvl": ShortTag(level)})
        if not tag.empty():
            item_nbt["tag"] = tag
    form.ui_items[index] = item_nbt
    if callback is not None:
        form.call_backs[index] = callback


def update_chest_block(
    form: ChestForm, player: Player, x: int, y: int, z: int, is_close: bool
) -> None:
    block_runtime_id = 741882976  # hash runtime id for minecraft:chest
    if is_close:
        block_runtime_id = player.dimension.get_block_at(x, y, z).data.runtime_id
    player.send_packet(
        MinecraftPacketIds.UpdateBlock,
        UpdateBlockPacket(
            NetworkBlockPosition(x, y, z), block_runtime_id, 3, 0
        ).serialize(),
    )
    if form.large_chest:
        if is_close:
            block_runtime_id = player.dimension.get_block_at(
                x + 1, y, z
            ).data.runtime_id
        player.send_packet(
            MinecraftPacketIds.UpdateBlock,
            UpdateBlockPacket(
                NetworkBlockPosition(x + 1, y, z), block_runtime_id, 3, 0
            ).serialize(),
        )


def update_chest_block_actor(
    form: ChestForm, player: Player, x: int, y: int, z: int
) -> None:
    block_nbt = CompoundTag(
        {
            "CustomName": form.title,
            "Findable": False,
            "id": "Chest",
            "isMovable": True,
            "x": x,
            "y": y,
            "z": z,
            "pairx": x + 1,
            "pairz": z,
            "pairlead": True,
            "Items": [],
        }
    )
    for index in range(27):
        block_nbt["Items"].append(form.ui_items[index])
    player.send_packet(
        MinecraftPacketIds.BlockActorData,
        BlockActorDataPacket(NetworkBlockPosition(x, y, z), block_nbt).serialize(),
    )
    if form.large_chest:
        block_nbt["x"] = x + 1
        block_nbt["pairx"] = x
        block_nbt["pairlead"] = False
        block_nbt["Items"].clear()
        for index in range(27):
            block_nbt["Items"].append(form.ui_items[index + 27])
        player.send_packet(
            MinecraftPacketIds.BlockActorData,
            BlockActorDataPacket(
                NetworkBlockPosition(x + 1, y, z), block_nbt
            ).serialize(),
        )


def run_delay_task(task: Callable[[], None], delay: int, plugin: Plugin):
    plugin.server.scheduler.run_task(plugin, task, delay)
