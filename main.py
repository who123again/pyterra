"""PyTerra - a Terraria-like sandbox. Entry point and game loop.

Run:  python main.py
"""
import math
import os
import random
import sys
import time

import pygame

import tiles
import ui
from crafting import RECIPES, craft, craftable, near_workbench
from entities import Drop, Player, Slime, Zombie
from inventory import HOTBAR
from items import get as get_item
from settings import (FPS, GRAVITY, REACH, SAVE_FILE, SCREEN_H, SCREEN_W,
                      TILE_SIZE as T, WORLD_H, WORLD_W)
from world import World

TILE_IDS = tiles.TILES


def daylight_factor(t: float) -> float:
    """t in [0,1). Day, dusk, night, dawn."""
    if t < 0.58:
        return 1.0
    if t < 0.66:
        return 1.0 - (t - 0.58) / 0.08 * 0.88
    if t < 0.94:
        return 0.12
    return 0.12 + (t - 0.94) / 0.06 * 0.88


def lerp(a, b, k):
    return a + (b - a) * k


class Game:
    def __init__(self, seed=None, fresh=False, headless=False):
        pygame.init()
        flags = 0
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), flags)
        pygame.display.set_caption("PyTerra")
        self.clock = pygame.time.Clock()
        ui.init_fonts()
        self.tile_surfaces = ui.build_tile_surfaces()
        self.toasts = []                # (text, ttl)

        if not fresh and os.path.exists(SAVE_FILE):
            self.world, pdata, self.time_of_day = World.load(SAVE_FILE)
            self.player = Player(0, 0)
            self.player.deserialize(pdata)
            self.toast("World loaded.")
        else:
            self.world = World(seed if seed is not None else random.randint(0, 10**9))
            t0 = time.time()
            self.world.generate()
            sx, sy = self.world.spawn
            self.player = Player(sx * T, sy * T)
            self.player.inventory.add("wooden_pickaxe")
            self.player.inventory.add("wooden_sword")
            self.player.inventory.add("torch", 10)
            self.time_of_day = 0.08
            self.toast(f"New world generated in {time.time()-t0:.1f}s")

        self.enemies = []
        self.drops = []
        self.spawn_timer = 3.0
        self.running = True
        self.inv_open = False
        self.help_open = True
        self.held_stack = None          # item stack dragged in the inventory UI
        self.held_from = None
        self.stars = [(random.randrange(SCREEN_W), random.randrange(SCREEN_H // 2),
                       random.random()) for _ in range(160)]
        self.cam = [0.0, 0.0]

    # ------------------------------------------------------------- helpers
    def toast(self, s, ttl=3.0):
        self.toasts.append([s, ttl])

    def is_night(self):
        return 0.62 < self.time_of_day < 0.96

    def mouse_tile(self):
        mx, my = pygame.mouse.get_pos()
        return int((mx + self.cam[0]) // T), int((my + self.cam[1]) // T)

    def in_reach(self, tx, ty):
        px, py = self.player.center
        return math.hypot((tx + 0.5) * T - px, (ty + 0.5) * T - py) <= REACH * T

    # -------------------------------------------------------------- events
    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if self.inv_open:
                        self.inv_open = False
                    else:
                        self.running = False
                elif e.key == pygame.K_SPACE:
                    self.player.jump()
                elif e.key == pygame.K_e:
                    self.inv_open = not self.inv_open
                    if not self.inv_open and self.held_stack:
                        self.player.inventory.add(*self.held_stack)
                        self.held_stack = None
                elif e.key == pygame.K_F5:
                    self.world.save(self.player, self.time_of_day)
                    self.toast("Game saved.")
                elif e.key == pygame.K_h:
                    self.help_open = not self.help_open
                elif pygame.K_0 <= e.key <= pygame.K_9:
                    n = (e.key - pygame.K_1 + 1) % 10
                    self.player.selected = n
                elif e.key == pygame.K_RETURN and self.player.hp <= 0:
                    self.player.respawn(self.world)
            elif e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == 4:  # wheel up
                    self.player.selected = (self.player.selected - 1) % HOTBAR
                elif e.button == 5:
                    self.player.selected = (self.player.selected + 1) % HOTBAR
                elif self.inv_open and e.button in (1, 3):
                    self.ui_click(e.pos)
            elif e.type == pygame.MOUSEMOTION and self.inv_open:
                pass

    def ui_click(self, pos):
        zones = self._last_zones
        for rect, (kind, payload) in zones:
            if not rect.collidepoint(pos):
                continue
            if kind == "slot":
                i = payload
                slot = self.player.inventory.slots[i]
                self.player.inventory.slots[i] = self.held_stack
                self.held_stack = slot
            elif kind == "craft":
                recipe = RECIPES[payload]
                bench = near_workbench(self.world, *self.player.tile_pos())
                if craftable(recipe, self.player.inventory, bench):
                    craft(recipe, self.player.inventory)
                    self.toast(f"Crafted {get_item(recipe.result).name}!")
                else:
                    need = " (need Work Bench)" if recipe.bench and not bench else ""
                    self.toast(f"Missing materials{need}.")
            return

    # -------------------------------------------------------------- update
    def update(self, dt):
        keys = pygame.key.get_pressed()
        move = (1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0)
        if self.player.hp > 0:
            self.player.update(self.world, dt, move if not self.inv_open else 0)

        mouse = pygame.mouse.get_pressed()
        if not self.inv_open and self.player.hp > 0:
            if mouse[0]:
                self.use_primary(dt)
            else:
                self.player.mine_progress = 0.0
                self.player.mine_target = None
            if mouse[2]:
                self.use_secondary()

        # enemies
        for en in list(self.enemies):
            en.update(self.world, self.player, dt)
            if self.player.hp > 0 and en.rect.colliderect(self.player.rect):
                d = 1 if self.player.x > en.x else -1
                self.player.hurt(en.CONTACT, d)
            # despawn far away
            if abs(en.x - self.player.x) > 90 * T:
                self.enemies.remove(en)
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_timer = 2.2
            self.try_spawn()

        # drops
        for d in list(self.drops):
            if d.update(self.world, self.player, dt):
                if d.item_id == "heart":
                    self.player.hp = min(self.player.max_hp, self.player.hp + 20)
                else:
                    self.player.inventory.add(d.item_id, d.count)
                self.drops.remove(d)

        # death
        if self.player.hp <= 0:
            self.player.hp = 0
            self.player.respawn(self.world)
            self.toast("You were slain... respawned at spawn.", 4)

        # time flows
        from settings import DAY_LENGTH
        self.time_of_day = (self.time_of_day + dt / DAY_LENGTH) % 1.0

        for t in self.toasts:
            t[1] -= dt
        self.toasts = [t for t in self.toasts if t[1] > 0]

        # camera follows, clamped to world
        px, py = self.player.center
        self.cam[0] = max(0, min(px - SCREEN_W / 2, WORLD_W * T - SCREEN_W))
        self.cam[1] = max(0, min(py - SCREEN_H / 2, WORLD_H * T - SCREEN_H))

    def try_spawn(self):
        night = self.is_night()
        cap = 8 if night else 4
        if len(self.enemies) >= cap:
            return
        ptx, _ = self.player.tile_pos()
        side = random.choice((-1, 1))
        tx = ptx + side * random.randint(30, 48)
        if not (0 <= tx < WORLD_W):
            return
        ty = self.world.surface_at(tx)
        x, y = tx * T, (ty - 2) * T
        self.enemies.append(Zombie(x, y) if night else Slime(x, y))

    # ------------------------------------------------------- primary action
    def use_primary(self, dt):
        tx, ty = self.mouse_tile()
        if not self.in_reach(tx, ty):
            self.player.mine_progress = 0.0
            return
        mx, my = pygame.mouse.get_pos()
        wx, wy = mx + self.cam[0], my + self.cam[1]

        # attacking takes priority when an enemy sits under the cursor
        sel_id = self.player.selected_item()
        item = get_item(sel_id) if sel_id else None
        dmg = item.damage if item and item.damage else 2
        for en in list(self.enemies):
            if en.rect.inflate(10, 10).collidepoint(wx, wy):
                if self.player.attack_cd <= 0:
                    speed = item.attack_speed if item else 1.0
                    self.player.attack_cd = 1.0 / max(0.4, speed)
                    d = 1 if en.x > self.player.x else -1
                    en.hurt(dmg, d)
                    if en.hp <= 0:
                        for iid, n in en.drops():
                            self.drops.append(Drop(en.x, en.y, iid, n))
                        self.enemies.remove(en)
                return

        # otherwise mine the tile
        tid = self.world.get(tx, ty)
        tile = TILE_IDS[tid]
        if tid == tiles.AIR or tile.hardness is None:
            self.player.mine_progress = 0.0
            return
        power = item.pick_power if item else 0
        if tile.min_power > power:
            self.toast(f"Need a pickaxe of power {tile.min_power}+!", 1.2)
            self.player.mine_progress = 0.0
            return
        speed = item.mine_speed if item and item.pick_power else 0.4
        if self.player.mine_target != (tx, ty):
            self.player.mine_target = (tx, ty)
            self.player.mine_progress = 0.0
        self.player.mine_progress += dt * speed / tile.hardness
        if self.player.mine_progress >= 1.0:
            self.player.mine_progress = 0.0
            self.player.mine_target = None
            self.world.set(tx, ty, tiles.AIR)
            self.world.compute_lighting()
            if tile.drop:
                self.drops.append(Drop(tx * T + 6, ty * T + 6, tile.drop, 1))

    def use_secondary(self):
        sel_id = self.player.selected_item()
        if not sel_id:
            return
        item = get_item(sel_id)
        if not item.placeable:
            return
        tx, ty = self.mouse_tile()
        if not self.in_reach(tx, ty):
            return
        cur = self.world.get(tx, ty)
        if TILE_IDS[cur].solid or cur in (tiles.TORCH, tiles.WORKBENCH):
            return
        # needs an adjacent block to attach to
        if not any(self.world.get(nx, ny) != tiles.AIR
                   for nx, ny in ((tx+1, ty), (tx-1, ty), (tx, ty+1), (tx, ty-1))):
            return
        place_rect = pygame.Rect(tx * T, ty * T, T, T)
        if place_rect.colliderect(self.player.rect):
            return
        if any(place_rect.colliderect(e.rect) for e in self.enemies):
            return
        if self.player.inventory.remove(sel_id, 1):
            self.world.set(tx, ty, item.tile_id)
            self.world.compute_lighting()

    # -------------------------------------------------------------- render
    def render(self):
        dl = daylight_factor(self.time_of_day)
        # sky
        top = (int(lerp(10, 120, dl)), int(lerp(12, 180, dl)), int(lerp(30, 235, dl)))
        bot = (int(lerp(16, 170, dl)), int(lerp(16, 210, dl)), int(lerp(40, 245, dl)))
        for i in range(0, SCREEN_H, 4):
            k = i / SCREEN_H
            pygame.draw.rect(self.screen,
                             (int(lerp(top[0], bot[0], k)), int(lerp(top[1], bot[1], k)),
                              int(lerp(top[2], bot[2], k))), (0, i, SCREEN_W, 4))
        # stars
        if dl < 0.5:
            for sx, sy, tw in self.stars:
                a = int((1 - dl * 2) * (150 + 100 * tw))
                pygame.draw.circle(self.screen, (a, a, min(255, a + 30)), (sx, sy), 1)
        # sun & moon
        t = self.time_of_day
        if t < 0.62:
            k = t / 0.62
            sunx = int(lerp(60, SCREEN_W - 60, k))
            suny = int(SCREEN_H * 0.42 - math.sin(k * math.pi) * SCREEN_H * 0.3)
            pygame.draw.circle(self.screen, (255, 236, 160), (sunx, suny), 26)
            pygame.draw.circle(self.screen, (255, 248, 210), (sunx, suny), 20)
        if t > 0.60:
            k = (t - 0.62) / 0.38 if t >= 0.62 else 0
            k = min(1.0, max(0.0, k))
            mx = int(lerp(60, SCREEN_W - 60, k))
            my = int(SCREEN_H * 0.42 - math.sin(k * math.pi) * SCREEN_H * 0.3)
            pygame.draw.circle(self.screen, (215, 220, 235), (mx, my), 18)
            pygame.draw.circle(self.screen, (180, 186, 205), (mx - 5, my - 4), 4)

        # tiles
        x0 = int(self.cam[0] // T)
        y0 = int(self.cam[1] // T)
        x1 = min(WORLD_W, x0 + SCREEN_W // T + 2)
        y1 = min(WORLD_H, y0 + SCREEN_H // T + 2)
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for ty in range(max(0, y0), y1):
            for tx in range(max(0, x0), x1):
                tid = self.world.tiles[ty][tx]
                if tid == tiles.AIR:
                    b = self.world.brightness(tx, ty, dl)
                    if b < 0.98:
                        a = int((1 - b) * 240)
                        pygame.draw.rect(overlay, (0, 0, 8, a),
                                         (tx * T - self.cam[0], ty * T - self.cam[1], T, T))
                    continue
                variant = self.tile_surfaces[tid][(tx * 7 + ty * 13) % 4]
                self.screen.blit(variant, (tx * T - self.cam[0], ty * T - self.cam[1]))
                b = self.world.brightness(tx, ty, dl)
                if b < 0.98:
                    a = int((1 - b) * 240)
                    pygame.draw.rect(overlay, (0, 0, 8, a),
                                     (tx * T - self.cam[0], ty * T - self.cam[1], T, T))
        self.screen.blit(overlay, (0, 0))

        # drops
        for d in self.drops:
            r = d.rect.move(-self.cam[0], -self.cam[1]).inflate(10, 10)
            ui.draw_item_icon(self.screen, d.item_id, r)

        # enemies & player
        for en in self.enemies:
            en.draw(self.screen, self.cam)
            if en.hp < en.HP:
                x, y = int(en.x - self.cam[0]), int(en.y - self.cam[1]) - 8
                pygame.draw.rect(self.screen, (60, 20, 20), (x, y, en.w, 4))
                pygame.draw.rect(self.screen, (220, 60, 60),
                                 (x, y, int(en.w * en.hp / en.HP), 4))
        self.player.draw(self.screen, self.cam)

        # mining progress
        if self.player.mine_target and self.player.mine_progress > 0:
            tx, ty = self.player.mine_target
            r = pygame.Rect(tx * T - self.cam[0], ty * T - 8 - self.cam[1], T, 5)
            pygame.draw.rect(self.screen, (40, 40, 40), r)
            pygame.draw.rect(self.screen, (255, 220, 120),
                             (r.x, r.y, int(T * self.player.mine_progress), 5))
            pygame.draw.rect(self.screen, (255, 255, 255),
                             (tx * T - self.cam[0], ty * T - self.cam[1], T, T), 1)

        # HUD
        ui.draw_hearts(self.screen, self.player.hp, self.player.max_hp)
        ui.draw_hotbar(self.screen, self.player, pygame.mouse.get_pos())
        clock_text = "Night" if self.is_night() else "Day"
        ui.text(self.screen, f"{clock_text}  ({int(t*24)%24:02d}:00)",
                (SCREEN_W - 130, 12),
                (255, 240, 200) if not self.is_night() else (160, 170, 220))
        ui.text(self.screen, f"FPS {int(self.clock.get_fps())}", (SCREEN_W - 90, 34),
                (140, 140, 140))
        for i, (s, ttl) in enumerate(self.toasts[-5:]):
            ui.text(self.screen, s, (12, 40 + i * 20), (255, 230, 170))

        if self.inv_open:
            bench = near_workbench(self.world, *self.player.tile_pos())
            self._last_zones = ui.draw_inventory(
                self.screen, self.player, pygame.mouse.get_pos(), bench)
            if self.held_stack:
                mx, my = pygame.mouse.get_pos()
                r = pygame.Rect(mx - 16, my - 16, 40, 40)
                ui.draw_item_icon(self.screen, self.held_stack[0], r)
                if self.held_stack[1] > 1:
                    ui.text(self.screen, str(self.held_stack[1]), (mx + 6, my + 6))
        if self.help_open and not self.inv_open:
            ui.draw_help(self.screen)

        pygame.display.flip()

    # ----------------------------------------------------------------- run
    def run(self):
        self._last_zones = []
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.handle_events()
            self.update(dt)
            self.render()
        self.world.save(self.player, self.time_of_day)
        pygame.quit()


def main():
    fresh = "--new" in sys.argv
    Game(fresh=fresh).run()


if __name__ == "__main__":
    main()
