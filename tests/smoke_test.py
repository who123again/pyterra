"""Headless smoke test: boots the game, simulates input, saves screenshots.

Run:  python tests/smoke_test.py
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from main import Game, daylight_factor  # noqa: E402


def run():
    game = Game(seed=1234, fresh=True)
    assert game.world.tiles, "world not generated"
    sx, sy = game.world.spawn
    assert game.world.get(sx, sy) == 0, "spawn should be open air"

    # simulate ~3 in-game seconds through the full update loop
    for frame in range(180):
        game.update(1 / 60)
    game.help_open = False  # keep screenshots unobstructed

    # give materials, craft a workbench by hand
    game.player.inventory.add("wood", 20)
    game.player.inventory.add("gel", 4)
    import crafting
    wb = next(r for r in crafting.RECIPES if r.result == "workbench")
    assert crafting.craftable(wb, game.player.inventory, bench_near=False)
    crafting.craft(wb, game.player.inventory)
    assert game.player.inventory.count_of("workbench") == 1
    assert game.player.inventory.count_of("wood") == 12

    # mining sanity: hardness/power gates
    import tiles
    assert tiles.TILES[tiles.IRON].min_power == 2
    assert tiles.TILES[tiles.GOLD].min_power == 3

    # render one day frame and one night frame
    os.makedirs("docs", exist_ok=True)
    game.render()
    pygame.image.save(game.screen, "docs/screenshot.png")
    game.time_of_day = 0.8  # deep night
    # place a torch next to the player to showcase lighting
    tx, ty = game.player.tile_pos()
    game.world.set(tx + 2, ty + 1, tiles.TORCH)
    game.world.compute_lighting()
    game.render()
    pygame.image.save(game.screen, "docs/screenshot_night.png")

    # inventory & crafting screen
    game.inv_open = True
    game._last_zones = []
    game.render()
    pygame.image.save(game.screen, "docs/screenshot_inventory.png")
    game.inv_open = False

    # save / load round-trip
    game.world.save(game.player, game.time_of_day, path="/tmp/pyterra_test_save.pkl")
    from world import World
    w2, pdata, t2 = World.load("/tmp/pyterra_test_save.pkl")
    assert w2.tiles == game.world.tiles
    assert pdata["hp"] == game.player.hp

    print("SMOKE TEST PASSED")
    print(f"  daylight@noon={daylight_factor(0.3):.2f}  daylight@night={daylight_factor(0.8):.2f}")
    print("  screenshots written to docs/")


if __name__ == "__main__":
    run()
