"""Rendering helpers: procedural tile sprites, HUD, inventory & crafting UI."""
import random

import pygame

import tiles
from crafting import RECIPES, craftable
from inventory import HOTBAR, SIZE
from items import get as get_item
from settings import SCREEN_H, SCREEN_W, TILE_SIZE as T

FONT = None
BIG_FONT = None


def init_fonts():
    global FONT, BIG_FONT
    FONT = pygame.font.Font(None, 20)
    BIG_FONT = pygame.font.Font(None, 34)


def text(surf, s, pos, color=(255, 255, 255), font=None, shadow=True):
    f = font or FONT
    if shadow:
        img0 = f.render(s, True, (0, 0, 0))
        surf.blit(img0, (pos[0] + 1, pos[1] + 1))
    img = f.render(s, True, color)
    surf.blit(img, pos)
    return img.get_rect(topleft=pos)


# ---------------------------------------------------------------- tile sprites
def _variant_rng(x, y):
    return random.Random((x * 73856093) ^ (y * 19349663))


def build_tile_surfaces():
    """Pre-render 4 variants per tile type for visual variety."""
    surfaces = {}
    for tid, tile in tiles.TILES.items():
        if tid == tiles.AIR:
            continue
        variants = []
        for v in range(4):
            rng = random.Random(tid * 1000 + v)
            s = pygame.Surface((T, T))
            base = tile.base
            s.fill(base)
            # subtle per-pixel noise
            for _ in range(28):
                px, py = rng.randrange(T), rng.randrange(T)
                d = rng.randint(-14, 14)
                s.set_at((px, py), tuple(max(0, min(255, c + d)) for c in base))
            if tid == tiles.GRASS:
                pygame.draw.rect(s, (84, 158, 60), (0, 0, T, 8))
                for gx in range(0, T, 3):
                    pygame.draw.line(s, (66, 132, 46), (gx, 8),
                                     (gx, 8 + rng.randint(2, 5)))
            if tile.speckle:
                for _ in range(6):
                    px, py = rng.randrange(2, T - 6), rng.randrange(2, T - 6)
                    pygame.draw.rect(s, tile.speckle, (px, py, 4, 4))
            if tid == tiles.WOOD:
                for wx in range(3, T, 7):
                    pygame.draw.line(s, (96, 64, 36), (wx, 0), (wx, T))
            if tid == tiles.LEAF:
                for _ in range(5):
                    px, py = rng.randrange(T - 5), rng.randrange(T - 5)
                    pygame.draw.circle(s, (44, 108, 44), (px, py), 3)
            if tid == tiles.TORCH:
                s.fill((0, 0, 0))
                s.set_colorkey((0, 0, 0))
                pygame.draw.rect(s, (150, 100, 50), (T // 2 - 2, 8, 4, T - 8))
                pygame.draw.circle(s, (255, 210, 90), (T // 2, 7), 5)
                pygame.draw.circle(s, (255, 240, 170), (T // 2, 7), 2)
            if tid == tiles.WORKBENCH:
                s.fill((0, 0, 0))
                s.set_colorkey((0, 0, 0))
                pygame.draw.rect(s, base, (0, 6, T, 7))
                pygame.draw.rect(s, (110, 70, 36), (2, 13, 5, 11))
                pygame.draw.rect(s, (110, 70, 36), (T - 7, 13, 5, 11))
            variants.append(s)
        surfaces[tid] = variants
    return surfaces


# ------------------------------------------------------------------ item icons
def draw_item_icon(surf, item_id, rect):
    item = get_item(item_id)
    if item.kind in ("pickaxe", "sword"):
        c = item.color
        if item.kind == "pickaxe":
            pygame.draw.line(surf, (140, 96, 52),
                             (rect.left + 5, rect.bottom - 5),
                             (rect.right - 6, rect.top + 6), 3)
            pygame.draw.arc(surf, c, (rect.left + 3, rect.top + 2,
                                      rect.w - 6, rect.h // 2 + 4), 3.4, 6.0, 4)
        else:
            pygame.draw.line(surf, c, (rect.left + 6, rect.bottom - 8),
                             (rect.right - 6, rect.top + 4), 5)
            pygame.draw.line(surf, (140, 96, 52),
                             (rect.left + 4, rect.bottom - 5),
                             (rect.left + 9, rect.bottom - 10), 3)
            pygame.draw.line(surf, (120, 120, 130),
                             (rect.left + 8, rect.bottom - 12),
                             (rect.left + 14, rect.bottom - 6), 2)
    elif item_id == "heart":
        c = (230, 60, 80)
        pygame.draw.circle(surf, c, rect.center, rect.w // 3)
    else:
        pygame.draw.rect(surf, item.color, rect.inflate(-8, -8), border_radius=3)
        pygame.draw.rect(surf, (0, 0, 0), rect.inflate(-8, -8), 1, border_radius=3)


# ------------------------------------------------------------------------ HUD
def draw_hearts(surf, hp, max_hp):
    hearts = max_hp // 10
    for i in range(hearts):
        x, y = 12 + i * 24, 12
        fill = max(0.0, min(1.0, (hp - i * 10) / 10))
        pygame.draw.rect(surf, (60, 20, 25), (x, y, 18, 16), border_radius=4)
        if fill > 0:
            w = int(18 * fill)
            clip = pygame.Rect(x, y, w, 16)
            prev = surf.get_clip()
            surf.set_clip(clip)
            pygame.draw.rect(surf, (222, 52, 70), (x, y, 18, 16), border_radius=4)
            surf.set_clip(prev)
        pygame.draw.rect(surf, (20, 10, 12), (x, y, 18, 16), 1, border_radius=4)


def draw_hotbar(surf, player, mouse_pos):
    slot = 46
    total = HOTBAR * slot
    x0 = (SCREEN_W - total) // 2
    y0 = SCREEN_H - slot - 10
    hovered = None
    for i in range(HOTBAR):
        r = pygame.Rect(x0 + i * slot, y0, slot - 4, slot - 4)
        sel = i == player.selected
        pygame.draw.rect(surf, (25, 25, 32), r, border_radius=5)
        pygame.draw.rect(surf, (255, 220, 120) if sel else (90, 90, 100), r,
                         2 if sel else 1, border_radius=5)
        entry = player.inventory.slots[i]
        if entry:
            draw_item_icon(surf, entry[0], r)
            if entry[1] > 1:
                text(surf, str(entry[1]), (r.right - 18, r.bottom - 18))
        if r.collidepoint(mouse_pos):
            hovered = entry[0] if entry else None
    if hovered:
        text(surf, get_item(hovered).name, (x0, y0 - 22), (255, 240, 200))


# ------------------------------------------------------ inventory & crafting
def draw_inventory(surf, player, mouse_pos, bench_near):
    """Returns list of (rect, payload) click zones."""
    zones = []
    panel = pygame.Rect(60, 60, SCREEN_W - 120, SCREEN_H - 160)
    pygame.draw.rect(surf, (18, 18, 26), panel, border_radius=8)
    pygame.draw.rect(surf, (120, 110, 90), panel, 2, border_radius=8)
    text(surf, "Inventory", (panel.x + 16, panel.y + 12), font=BIG_FONT)
    text(surf, "Crafting" + ("  (near Work Bench)" if bench_near else ""),
         (panel.x + 320, panel.y + 12), font=BIG_FONT)

    slot = 46
    x0, y0 = panel.x + 16, panel.y + 56
    for i in range(SIZE):
        row, col = divmod(i, 10)
        r = pygame.Rect(x0 + col * slot, y0 + row * slot, slot - 4, slot - 4)
        pygame.draw.rect(surf, (32, 32, 42), r, border_radius=4)
        pygame.draw.rect(surf, (80, 80, 92), r, 1, border_radius=4)
        entry = player.inventory.slots[i]
        if entry:
            draw_item_icon(surf, entry[0], r)
            if entry[1] > 1:
                text(surf, str(entry[1]), (r.right - 18, r.bottom - 18))
        zones.append((r, ("slot", i)))
        if entry and r.collidepoint(mouse_pos):
            tip = get_item(entry[0])
            text(surf, tip.name + (" - " + tip.desc if tip.desc else ""),
                 (panel.x + 16, panel.bottom - 30), (255, 240, 200))

    cx, cy = panel.x + 320, panel.y + 56
    for idx, recipe in enumerate(RECIPES):
        ok = craftable(recipe, player.inventory, bench_near)
        r = pygame.Rect(cx, cy + idx * 44, panel.width - 340, 38)
        pygame.draw.rect(surf, (30, 42, 30) if ok else (34, 30, 30), r,
                         border_radius=5)
        pygame.draw.rect(surf, (110, 170, 110) if ok else (90, 80, 80), r, 1,
                         border_radius=5)
        name_col = (220, 255, 220) if ok else (170, 160, 160)
        res = get_item(recipe.result)
        label = f"{res.name}" + (f" x{recipe.count}" if recipe.count > 1 else "")
        text(surf, label, (r.x + 10, r.y + 4), name_col)
        req = recipe.describe_needs() + ("  [Workbench]" if recipe.bench else "")
        text(surf, req, (r.x + 10, r.y + 21), (150, 150, 150))
        zones.append((r, ("craft", idx)))
    text(surf, "E: close    Click a recipe to craft    Click slots to swap",
         (panel.x + 16, panel.bottom - 56), (140, 140, 150))
    return zones


def draw_help(surf):
    lines = [
        "PyTerra - controls",
        "",
        "A / D .......... move",
        "SPACE .......... jump",
        "LMB ............ mine block / attack enemy",
        "RMB ............ place selected block",
        "1-0 / wheel .... select hotbar slot",
        "E .............. inventory & crafting",
        "F5 ............. save game",
        "H .............. toggle this help",
        "ESC ............ quit",
        "",
        "Dig deep for copper, iron and gold. Beware the night.",
    ]
    w, h = 520, 24 + len(lines) * 24
    panel = pygame.Rect((SCREEN_W - w) // 2, (SCREEN_H - h) // 2, w, h)
    pygame.draw.rect(surf, (16, 16, 24), panel, border_radius=8)
    pygame.draw.rect(surf, (120, 110, 90), panel, 2, border_radius=8)
    for i, line in enumerate(lines):
        text(surf, line, (panel.x + 20, panel.y + 14 + i * 24),
             (230, 225, 210) if i else (255, 220, 120),
             font=FONT if i else BIG_FONT)
