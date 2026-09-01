"""Item registry: materials, placeable tiles, tools and weapons."""
import tiles


class Item:
    def __init__(self, name, kind, color, tile_id=None, stack=999,
                 pick_power=0, damage=0, mine_speed=1.0, attack_speed=1.0, desc=""):
        self.name = name
        self.kind = kind            # 'tile' | 'material' | 'pickaxe' | 'sword'
        self.color = color          # icon colour
        self.tile_id = tile_id      # set when placeable
        self.stack = stack
        self.pick_power = pick_power
        self.damage = damage
        self.mine_speed = mine_speed
        self.attack_speed = attack_speed
        self.desc = desc

    @property
    def placeable(self):
        return self.tile_id is not None


ITEMS = {
    # Placeable tiles
    "dirt":      Item("Dirt", "tile", (122, 84, 55), tile_id=tiles.DIRT),
    "stone":     Item("Stone", "tile", (112, 112, 118), tile_id=tiles.STONE),
    "wood":      Item("Wood", "tile", (126, 88, 52), tile_id=tiles.WOOD),
    "torch":     Item("Torch", "tile", (255, 196, 90), tile_id=tiles.TORCH, stack=999),
    "workbench": Item("Work Bench", "tile", (156, 104, 56), tile_id=tiles.WORKBENCH),
    # Materials
    "coal":       Item("Coal", "material", (52, 52, 58)),
    "copper_ore": Item("Copper Ore", "material", (206, 122, 58)),
    "iron_ore":   Item("Iron Ore", "material", (196, 172, 148)),
    "gold_ore":   Item("Gold Ore", "material", (242, 202, 82)),
    "gel":        Item("Gel", "material", (96, 180, 255)),
    # Tools & weapons (stacks of 1)
    "wooden_pickaxe": Item("Wooden Pickaxe", "pickaxe", (170, 120, 64), stack=1,
                           pick_power=1, damage=4, mine_speed=1.0, attack_speed=1.0,
                           desc="Mines stone, coal and copper."),
    "stone_pickaxe": Item("Stone Pickaxe", "pickaxe", (150, 150, 156), stack=1,
                          pick_power=2, damage=6, mine_speed=1.45, attack_speed=1.05,
                          desc="Mines iron ore."),
    "iron_pickaxe": Item("Iron Pickaxe", "pickaxe", (206, 178, 150), stack=1,
                         pick_power=3, damage=9, mine_speed=1.95, attack_speed=1.1,
                         desc="Mines gold ore."),
    "gold_pickaxe": Item("Golden Pickaxe", "pickaxe", (246, 206, 90), stack=1,
                         pick_power=4, damage=12, mine_speed=2.6, attack_speed=1.2,
                         desc="The fastest pickaxe around."),
    "wooden_sword": Item("Wooden Sword", "sword", (190, 140, 78), stack=1,
                         damage=10, attack_speed=1.6),
    "iron_sword":   Item("Iron Sword", "sword", (210, 210, 220), stack=1,
                         damage=22, attack_speed=1.8),
}


def get(item_id: str) -> Item:
    return ITEMS[item_id]
