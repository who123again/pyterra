"""Crafting recipes. `bench=True` recipes require a Work Bench nearby."""
from items import get


class Recipe:
    def __init__(self, result, count, needs, bench=False):
        self.result = result        # item id
        self.count = count
        self.needs = needs          # {item_id: count}
        self.bench = bench

    def describe_needs(self):
        return ", ".join(f"{get(k).name} x{v}" for k, v in self.needs.items())


RECIPES = [
    Recipe("workbench", 1, {"wood": 8}),
    Recipe("torch", 4, {"wood": 1, "gel": 1}),
    Recipe("wooden_pickaxe", 1, {"wood": 6}),
    Recipe("wooden_sword", 1, {"wood": 5}),
    Recipe("stone_pickaxe", 1, {"stone": 10, "wood": 4}, bench=True),
    Recipe("iron_pickaxe", 1, {"iron_ore": 8, "wood": 4}, bench=True),
    Recipe("iron_sword", 1, {"iron_ore": 8, "wood": 2}, bench=True),
    Recipe("gold_pickaxe", 1, {"gold_ore": 8, "wood": 4}, bench=True),
]


def near_workbench(world, tx: int, ty: int, radius: int = 5) -> bool:
    import tiles as _t
    for y in range(ty - radius, ty + radius + 1):
        for x in range(tx - radius, tx + radius + 1):
            if world.get(x, y) == _t.WORKBENCH:
                return True
    return False


def craftable(recipe: Recipe, inventory, bench_near: bool) -> bool:
    if recipe.bench and not bench_near:
        return False
    return inventory.has_all(recipe.needs)


def craft(recipe: Recipe, inventory) -> bool:
    if inventory.consume(recipe.needs):
        inventory.add(recipe.result, recipe.count)
        return True
    return False
