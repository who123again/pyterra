"""Tile world: procedural generation and the two-channel lighting system."""
import pickle
from collections import deque

import noise
import tiles
from settings import WORLD_W, WORLD_H, SURFACE_BASE, SAVE_FILE
from tiles import (AIR, GRASS, DIRT, STONE, WOOD, LEAF, COAL, COPPER, IRON,
                   GOLD, TORCH, BEDROCK)


class World:
    def __init__(self, seed: int = 0, width: int = WORLD_W, height: int = WORLD_H):
        self.seed = seed
        self.width = width
        self.height = height
        self.tiles = [[AIR] * width for _ in range(height)]
        self.sky_light = [[0] * width for _ in range(height)]
        self.torch_light = [[0] * width for _ in range(height)]
        self.surface = [SURFACE_BASE] * width
        self.spawn = (width // 2, SURFACE_BASE - 4)  # tile coords

    # ------------------------------------------------------------- generation
    def generate(self):
        w, h = self.width, self.height
        # 1) heightmap
        for x in range(w):
            n = noise.fbm1(x * 0.016, octaves=4, seed=self.seed)
            self.surface[x] = int(SURFACE_BASE + (n - 0.5) * 2 * 18)
        # 2) strata + caves + ores (single pass)
        for x in range(w):
            surf = self.surface[x]
            for y in range(h):
                if y < surf:
                    continue
                depth = y - surf
                if y >= h - 2:
                    self.tiles[y][x] = BEDROCK
                    continue
                # caves (only below some depth)
                if depth > 6:
                    c = noise.fbm2(x * 0.055, y * 0.055, octaves=3,
                                   seed=self.seed + 7)
                    if c > 0.64:
                        continue  # leave AIR
                if depth < 5:
                    t = DIRT
                else:
                    t = STONE
                    # ores hidden in stone, rarer with depth requirements
                    o = noise.fbm2(x * 0.09, y * 0.09, octaves=2,
                                   seed=self.seed + 13)
                    if o > 0.72:
                        if depth > 90 and o > 0.80:
                            t = GOLD
                        elif depth > 40:
                            t = IRON
                        elif depth > 14:
                            t = COPPER if o < 0.78 else COAL
                        else:
                            t = COAL
                self.tiles[y][x] = t
            # grass cap
            if self.tiles[surf][x] == DIRT:
                self.tiles[surf][x] = GRASS
        # 3) trees
        for x in range(3, w - 3):
            if self.tiles[self.surface[x]][x] != GRASS:
                continue
            if noise._hash2(x, 0, self.seed + 99) > 0.14:
                continue
            top = self.surface[x] - 1
            height = 4 + int(noise._hash2(x, 1, self.seed + 98) * 4)
            for i in range(height):
                y = top - i
                if 0 <= y < h:
                    self.tiles[y][x] = WOOD
            crown_y = top - height
            for dy in range(-2, 2):
                for dx in range(-2, 3):
                    if abs(dx) == 2 and abs(dy) == 2:
                        continue
                    y, xx = crown_y + dy, x + dx
                    if 0 <= y < h and 0 <= xx < w and self.tiles[y][xx] == AIR:
                        self.tiles[y][xx] = LEAF
        # 4) spawn point on the surface, centre of the map
        sx = w // 2
        self.spawn = (sx, self.surface[sx] - 3)
        self.compute_lighting()

    # ---------------------------------------------------------------- access
    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def get(self, x: int, y: int) -> int:
        if y < 0:
            return AIR
        if not self.in_bounds(x, y):
            return BEDROCK  # world edges behave as unbreakable walls
        return self.tiles[y][x]

    def set(self, x: int, y: int, tile_id: int):
        if self.in_bounds(x, y):
            self.tiles[y][x] = tile_id

    def is_solid(self, x: int, y: int) -> bool:
        if y < 0:
            return False
        if not self.in_bounds(x, y):
            return True
        return tiles.TILES[self.tiles[y][x]].solid

    def surface_at(self, x: int) -> int:
        x = max(0, min(self.width - 1, x))
        return self.surface[x]

    # --------------------------------------------------------------- lighting
    def compute_lighting(self):
        """Recompute both light channels. Bounded BFS keeps this cheap."""
        w, h = self.width, self.height
        sky = self.sky_light
        tor = self.torch_light
        for y in range(h):
            row_s = sky[y]
            row_t = tor[y]
            for x in range(w):
                row_s[x] = 0
                row_t[x] = 0

        def spread(grid, sources):
            q = deque(sources)
            while q:
                x, y = q.popleft()
                level = grid[y][x]
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if not (0 <= nx < w and 0 <= ny < h):
                        continue
                    cost = 3 if tiles.TILES[self.tiles[ny][nx]].solid else 1
                    nv = level - cost
                    if nv > grid[ny][nx] and nv > 0:
                        grid[ny][nx] = nv
                        q.append((nx, ny))

        # sunlight pours down each column until the first solid tile
        sun_sources = []
        for x in range(w):
            for y in range(h):
                if tiles.TILES[self.tiles[y][x]].solid:
                    break
                sky[y][x] = 15
                sun_sources.append((x, y))
        spread(sky, sun_sources)

        torch_sources = []
        for y in range(h):
            for x in range(w):
                lv = tiles.TILES[self.tiles[y][x]].light
                if lv:
                    tor[y][x] = lv
                    torch_sources.append((x, y))
        spread(tor, torch_sources)

    def brightness(self, x: int, y: int, daylight: float) -> float:
        """0..1 render brightness combining sun (scaled by time) and torches."""
        if not self.in_bounds(x, y):
            return 0.05
        s = self.sky_light[y][x] * daylight
        t = self.torch_light[y][x]
        v = max(s, t) / 15.0
        return max(0.04, min(1.0, v))

    # ---------------------------------------------------------------- save
    def save(self, player, time_of_day: float, path: str = SAVE_FILE):
        data = {
            "seed": self.seed, "width": self.width, "height": self.height,
            "tiles": self.tiles, "surface": self.surface, "spawn": self.spawn,
            "time": time_of_day, "player": player.serialize(),
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)

    @classmethod
    def load(cls, path: str = SAVE_FILE):
        with open(path, "rb") as f:
            d = pickle.load(f)
        w = cls(d["seed"], d["width"], d["height"])
        w.tiles = d["tiles"]
        w.surface = d["surface"]
        w.spawn = tuple(d["spawn"])
        w.compute_lighting()
        return w, d["player"], d["time"]
