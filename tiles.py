"""Tile registry: ids, rendering colours and gameplay properties."""

# Tile ids
AIR = 0
GRASS = 1
DIRT = 2
STONE = 3
WOOD = 4
LEAF = 5
COAL = 6
COPPER = 7
IRON = 8
GOLD = 9
TORCH = 10
WORKBENCH = 11
BEDROCK = 12


class Tile:
    def __init__(self, name, solid, base, hardness=1.0, min_power=0,
                 drop=None, light=0, speckle=None):
        self.name = name
        self.solid = solid            # blocks movement
        self.base = base              # base RGB colour
        self.hardness = hardness      # seconds baseline to mine
        self.min_power = min_power    # required pickaxe power (0 = by hand)
        self.drop = drop              # item id dropped when mined
        self.light = light            # emitted light level 0..15
        self.speckle = speckle        # ore speckle RGB colour (drawn on base)


TILES = {
    AIR:       Tile("Air", False, (0, 0, 0), hardness=0),
    GRASS:     Tile("Grass Block", True, (122, 84, 55), hardness=0.55, drop="dirt"),
    DIRT:      Tile("Dirt", True, (122, 84, 55), hardness=0.5, drop="dirt"),
    STONE:     Tile("Stone", True, (112, 112, 118), hardness=1.7, min_power=1, drop="stone"),
    WOOD:      Tile("Wood", False, (126, 88, 52), hardness=0.8, drop="wood"),
    LEAF:      Tile("Leaves", False, (58, 132, 58), hardness=0.2, drop=None),
    COAL:      Tile("Coal Ore", True, (112, 112, 118), hardness=2.0, min_power=1,
                    drop="coal", speckle=(48, 48, 54)),
    COPPER:    Tile("Copper Ore", True, (112, 112, 118), hardness=2.2, min_power=1,
                    drop="copper_ore", speckle=(206, 122, 58)),
    IRON:      Tile("Iron Ore", True, (112, 112, 118), hardness=3.0, min_power=2,
                    drop="iron_ore", speckle=(196, 172, 148)),
    GOLD:      Tile("Gold Ore", True, (112, 112, 118), hardness=3.4, min_power=3,
                    drop="gold_ore", speckle=(242, 202, 82)),
    TORCH:     Tile("Torch", False, (255, 196, 90), hardness=0.1, drop="torch", light=14),
    WORKBENCH: Tile("Work Bench", False, (156, 104, 56), hardness=0.6, drop="workbench"),
    BEDROCK:   Tile("Bedrock", True, (42, 42, 48), hardness=None),
}


def is_solid(tile_id: int) -> bool:
    return TILES[tile_id].solid
