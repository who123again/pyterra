"""Entities: physics body, player, enemies (slime/zombie) and item drops."""
import math
import random

import pygame

import tiles
from inventory import Inventory
from settings import (GRAVITY, TILE_SIZE, PLAYER_W, PLAYER_H, PLAYER_SPEED,
                      PLAYER_JUMP, PLAYER_MAX_HP)

T = TILE_SIZE


def _overlapping_solid(world, rect):
    x0 = rect.left // T
    x1 = (rect.right - 1) // T
    y0 = rect.top // T
    y1 = (rect.bottom - 1) // T
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            if world.is_solid(tx, ty):
                yield tx, ty


class Entity:
    def __init__(self, x, y, w, h):
        self.x, self.y = float(x), float(y)  # top-left, pixels
        self.vx = self.vy = 0.0
        self.w, self.h = w, h
        self.on_ground = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    @property
    def center(self):
        return self.x + self.w / 2, self.y + self.h / 2

    def tile_pos(self):
        cx, cy = self.center
        return int(cx // T), int(cy // T)

    def physics(self, world, dt, gravity=True):
        if gravity:
            self.vy = min(self.vy + GRAVITY * dt, 1400)
        # X axis
        self.x += self.vx * dt
        r = self.rect
        for tx, ty in _overlapping_solid(world, r):
            if self.vx > 0:
                self.x = tx * T - self.w
            elif self.vx < 0:
                self.x = (tx + 1) * T
            self.vx = 0
            r = self.rect
        # Y axis
        self.y += self.vy * dt
        self.on_ground = False
        r = self.rect
        for tx, ty in _overlapping_solid(world, r):
            if self.vy > 0:
                self.y = ty * T - self.h
                self.on_ground = True
            elif self.vy < 0:
                self.y = (ty + 1) * T
            self.vy = 0
            r = self.rect


class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, PLAYER_W, PLAYER_H)
        self.max_hp = PLAYER_MAX_HP
        self.hp = float(self.max_hp)
        self.facing = 1
        self.inventory = Inventory()
        self.selected = 0
        self.attack_cd = 0.0
        self.invuln = 0.0
        self.since_damage = 999.0
        self.mine_progress = 0.0
        self.mine_target = None
        self.deaths = 0

    def selected_item(self):
        slot = self.inventory.slots[self.selected]
        return slot[0] if slot else None

    def update(self, world, dt, move):
        self.vx = move * PLAYER_SPEED
        if move:
            self.facing = 1 if move > 0 else -1
        self.physics(world, dt)
        self.attack_cd = max(0.0, self.attack_cd - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.since_damage += dt
        if self.since_damage > 8 and self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + 1.5 * dt)

    def jump(self):
        if self.on_ground:
            self.vy = -PLAYER_JUMP

    def hurt(self, dmg, knock_dir):
        if self.invuln > 0:
            return
        self.hp -= dmg
        self.invuln = 1.0
        self.since_damage = 0.0
        self.vx = knock_dir * 260
        self.vy = -220

    def respawn(self, world):
        sx, sy = world.spawn
        self.x, self.y = sx * T, sy * T
        self.vx = self.vy = 0
        self.hp = float(self.max_hp)
        self.invuln = 2.0
        self.deaths += 1

    def serialize(self):
        return {
            "x": self.x, "y": self.y, "hp": self.hp,
            "inventory": self.inventory.to_list(), "selected": self.selected,
        }

    def deserialize(self, d):
        self.x, self.y = d["x"], d["y"]
        self.hp = d["hp"]
        self.inventory = Inventory.from_list(d["inventory"])
        self.selected = d["selected"]

    # ---------------------------------------------------------------- drawing
    def draw(self, surf, cam):
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        flash = self.invuln > 0 and int(self.invuln * 12) % 2 == 0
        skin = (240, 200, 160) if not flash else (255, 255, 255)
        shirt = (60, 110, 200) if not flash else (255, 255, 255)
        pants = (70, 70, 90) if not flash else (255, 255, 255)
        # legs
        pygame.draw.rect(surf, pants, (x + 2, y + 30, 6, 14))
        pygame.draw.rect(surf, pants, (x + 10, y + 30, 6, 14))
        # torso
        pygame.draw.rect(surf, shirt, (x + 1, y + 14, 16, 18))
        # head
        pygame.draw.rect(surf, skin, (x + 2, y, 14, 13))
        # eye looks toward facing
        ex = x + (11 if self.facing > 0 else 4)
        pygame.draw.rect(surf, (30, 30, 30), (ex, y + 5, 3, 3))
        # hair
        pygame.draw.rect(surf, (90, 55, 30), (x + 2, y, 14, 4))


class Drop(Entity):
    """A lying item that bounces, then magnetises to the player."""
    def __init__(self, x, y, item_id, count=1):
        super().__init__(x, y, 12, 12)
        self.item_id = item_id
        self.count = count
        self.age = random.random() * 10
        self.vx = random.uniform(-60, 60)
        self.vy = random.uniform(-160, -60)
        self.kind = "heart" if item_id == "heart" else "item"

    def update(self, world, player, dt):
        self.age += dt
        px, py = player.center
        cx, cy = self.center
        dist = math.hypot(px - cx, py - cy)
        if dist < 2.6 * T:  # magnet
            dx, dy = (px - cx) / max(dist, 1), (py - cy) / max(dist, 1)
            self.vx, self.vy = dx * 420, dy * 420
            self.x += self.vx * dt
            self.y += self.vy * dt
        else:
            self.physics(world, dt)
            self.vx *= 0.92
        return dist < 0.9 * T  # picked up


class Enemy(Entity):
    CONTACT = 10
    HP = 30

    def __init__(self, x, y, w, h):
        super().__init__(x, y, w, h)
        self.hp = float(self.HP)
        self.hurt_cd = 0.0

    def hurt(self, dmg, knock_dir):
        self.hp -= dmg
        self.vx = knock_dir * 300
        self.vy = -180
        self.hurt_cd = 0.25

    def update(self, world, player, dt):
        self.hurt_cd = max(0.0, self.hurt_cd - dt)
        self.physics(world, dt)

    def drops(self):
        return []


class Slime(Enemy):
    CONTACT = 12
    HP = 30

    def __init__(self, x, y):
        super().__init__(x, y, 30, 22)
        self.hop_timer = random.uniform(0.4, 1.4)
        self.color = random.choice([(70, 170, 255), (120, 220, 120), (230, 120, 220)])

    def update(self, world, player, dt):
        super().update(world, player, dt)
        self.hop_timer -= dt
        if self.on_ground and self.hop_timer <= 0:
            direction = 1 if player.x > self.x else -1
            self.vx = direction * random.uniform(120, 200)
            self.vy = -random.uniform(300, 460)
            self.hop_timer = random.uniform(0.7, 1.5)
        if self.on_ground:
            self.vx *= 0.8

    def drops(self):
        out = [("gel", random.randint(2, 3))]
        if random.random() < 0.12:
            out.append(("heart", 1))
        return out

    def draw(self, surf, cam):
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        body = pygame.Rect(x, y + 6, self.w, self.h - 6)
        c = (200, 90, 90) if self.hurt_cd > 0 else self.color
        pygame.draw.ellipse(surf, c, body)
        pygame.draw.ellipse(surf, tuple(min(255, v + 40) for v in c),
                            (x + 4, y, self.w - 8, 12))
        pygame.draw.circle(surf, (20, 30, 40), (x + 9, y + 12), 2)
        pygame.draw.circle(surf, (20, 30, 40), (x + 20, y + 12), 2)


class Zombie(Enemy):
    CONTACT = 18
    HP = 60

    def __init__(self, x, y):
        super().__init__(x, y, 18, 44)
        self.speed = random.uniform(70, 105)

    def update(self, world, player, dt):
        direction = 1 if player.x > self.x else -1
        self.vx = direction * self.speed
        # jump over obstacles and up ledges
        if self.on_ground:
            ahead_x = int((self.x + (self.w + 4) * direction) // T)
            feet_y = int((self.y + self.h - 4) // T)
            head_y = int((self.y + 6) // T)
            if world.is_solid(ahead_x, feet_y) or world.is_solid(ahead_x, head_y):
                self.vy = -560
        super().update(world, player, dt)

    def drops(self):
        return [("heart", 1)] if random.random() < 0.18 else []

    def draw(self, surf, cam):
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        skin = (110, 170, 110) if self.hurt_cd <= 0 else (230, 230, 230)
        cloth = (90, 80, 70)
        pygame.draw.rect(surf, cloth, (x + 2, y + 30, 6, 14))
        pygame.draw.rect(surf, cloth, (x + 10, y + 30, 6, 14))
        pygame.draw.rect(surf, (70, 90, 120), (x + 1, y + 14, 16, 18))
        pygame.draw.rect(surf, skin, (x + 2, y, 14, 13))
        d = 1 if self.vx >= 0 else -1
        pygame.draw.rect(surf, (200, 40, 40), (x + (11 if d > 0 else 4), y + 5, 3, 3))
