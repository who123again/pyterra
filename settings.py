"""Global configuration for PyTerra."""

# --- Display ---
TILE_SIZE = 24
SCREEN_W = 1280
SCREEN_H = 720
FPS = 60

# --- World ---
WORLD_W = 840          # tiles
WORLD_H = 240          # tiles
SURFACE_BASE = 66      # average surface height (tiles from top)

# --- Physics ---
GRAVITY = 2000.0       # px / s^2

# --- Gameplay ---
REACH = 5              # block interaction reach, in tiles
DAY_LENGTH = 480.0     # seconds for a full day+night cycle
SAVE_FILE = "savegame.pkl"

# --- Player ---
PLAYER_W = 18
PLAYER_H = 44
PLAYER_SPEED = 190.0
PLAYER_JUMP = 640.0
PLAYER_MAX_HP = 100
