"""Bubble Fantasy Shooter: a Pygame game with six illustrated worlds.

Install: python -m pip install pygame
Run:     python bubble_shooter_fantasy.py

Controls:
  Mouse aim, left click or Space shoot; A/D or left/right to aim.
  T themes, M mode, C colors, +/- color count.
  P pause, R restart, 1/2/3 difficulty, Shift+D difficulty.
  F11 or Alt+Enter: switch fullscreen/windowed; Esc: exit.

Keep the assets directory next to this Python file.
If pictures are missing, the game uses its procedural fallback background.
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path
from dataclasses import dataclass

import pygame

# ---------------------------------------------------------------------------
# Game settings
# ---------------------------------------------------------------------------
SCREEN_W, SCREEN_H = 960, 760
FPS = 60
RADIUS = 19
CELL_X = 39
CELL_Y = 33
GRID_COLS = 13
GRID_ROWS = 17
GRID_TOP = 116
GRID_X = 80
FIELD_LEFT, FIELD_RIGHT = 42, 586
WALL_LEFT = FIELD_LEFT + RADIUS + 10
WALL_RIGHT = FIELD_RIGHT - RADIUS - 10
SHOOTER_X, SHOOTER_Y = (FIELD_LEFT + FIELD_RIGHT) // 2, 698
SHOT_SPEED = 800.0
MAX_ANGLE = math.radians(78)
MISSES_BEFORE_DROP = 6

BG_TOP = (9, 16, 32)
BG_BOTTOM = (13, 26, 48)
PANEL = (18, 30, 52)
PANEL_EDGE = (43, 65, 94)
WHITE = (238, 246, 255)
MUTED = (142, 162, 190)
CYAN = (92, 217, 238)
GOLD = (255, 194, 99)
RED = (255, 116, 128)
PALETTE = [
    (244, 87, 141),    # pink
    (78, 199, 245),    # blue
    (249, 193, 76),    # yellow
    (161, 115, 248),   # violet
    (93, 219, 158),    # green
    (248, 136, 83),    # orange
]


def lighten(color: tuple[int, int, int], strength: float) -> tuple[int, int, int]:
    return tuple(min(255, int(v + (255 - v) * strength)) for v in color)


def darken(color: tuple[int, int, int], strength: float) -> tuple[int, int, int]:
    return tuple(int(v * (1 - strength)) for v in color)


def make_bubble(color: tuple[int, int, int], radius: int = RADIUS, style: str = "glossy") -> pygame.Surface:
    """Create a shiny circular base under each decorative themed icon."""
    pad = 4
    size = 2 * (radius + pad)
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    center = (radius + pad, radius + pad)
    pygame.draw.circle(surface, darken(color, 0.50), center, radius + 2)
    pygame.draw.circle(surface, color, center, radius)
    if style == "neon":
        pygame.draw.circle(surface, lighten(color, 0.45), center, radius - 4, 3)
        pygame.draw.circle(surface, (255, 255, 255, 150),
                           (center[0] - 5, center[1] - 5), 3)
        return surface
    if style == "flat":
        pygame.draw.circle(surface, lighten(color, 0.22), center, radius - 3)
        pygame.draw.circle(surface, darken(color, 0.20), center, radius, 2)
        return surface
    pygame.draw.circle(surface, lighten(color, 0.18),
                       (center[0] - 3, center[1] - 4), radius - 4)
    highlight = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.ellipse(highlight, (255, 255, 255, 95),
                        (center[0] - radius * 0.55, center[1] - radius * 0.70,
                         radius * 0.95, radius * 0.55))
    pygame.draw.circle(highlight, (255, 255, 255, 175),
                       (center[0] - radius // 3, center[1] - radius // 2),
                       max(2, radius // 6))
    surface.blit(highlight, (0, 0))
    pygame.draw.arc(surface, (*lighten(color, 0.60), 155),
                    (center[0] - radius + 2, center[1] - radius + 2,
                     2 * radius - 4, 2 * radius - 4),
                    math.radians(10), math.radians(125), 2)
    return surface


def make_themed_bubble(color: tuple[int, int, int], index: int,
                       theme: str, style: str) -> pygame.Surface:
    """Render original, recognizable seasonal icons directly onto each bubble."""
    result = make_bubble(color, style=style)
    if theme not in ("CHRISTMAS", "EASTER", "FOREST", "BUTTERFLIES", "HALLOWEEN", "UNDERWATER"):
        return result
    cx = cy = RADIUS + 4
    ink = (250, 250, 243)
    dark = darken(color, .50)
    def circle(c, x, y, r, width=0):
        pygame.draw.circle(result, c, (round(x), round(y)), r, width)
    def line(c, points, width=3):
        pygame.draw.lines(result, c, False, [(round(x), round(y)) for x, y in points], width)
    def ellipse(c, rect, width=0):
        pygame.draw.ellipse(result, c, rect, width)
    if theme == "BUTTERFLIES" or (theme == "EASTER" and index == 4):
        # Every butterfly has its own wing colors, with a contrasting body.
        wing = lighten(color, .38)
        highlight = lighten(color, .75)
        ellipse(wing, (cx-16, cy-12, 16, 15))
        ellipse(wing, (cx, cy-12, 16, 15))
        ellipse(highlight, (cx-13, cy+1, 12, 11))
        ellipse(highlight, (cx+1, cy+1, 12, 11))
        for x in (cx-9, cx+9):
            circle(ink, x, cy-5, 3)
        ellipse(dark, (cx-2, cy-10, 4, 22))
        line(dark, [(cx-1,cy-8),(cx-5,cy-15)], 2)
        line(dark, [(cx+1,cy-8),(cx+5,cy-15)], 2)
    elif theme == "CHRISTMAS":
        if index in (0, 4):  # candy cane with colored stripes
            line(ink, [(cx-7,cy+12),(cx-7,cy-6),(cx-4,cy-12),(cx+4,cy-12),
                       (cx+9,cy-7),(cx+9,cy-2)], 8)
            for dx,dy in [(-7,7),(-7,-1),(-5,-10),(4,-12),(9,-4)]:
                line((205,45,56), [(cx+dx-2,cy+dy-2),(cx+dx+2,cy+dy+2)], 3)
        elif index in (1, 5):  # wrapped presents
            pygame.draw.rect(result, ink, (cx-12,cy-8,24,21), border_radius=3)
            pygame.draw.rect(result, dark, (cx-2,cy-8,5,21))
            pygame.draw.rect(result, dark, (cx-12,cy-2,24,5))
            ellipse((245,200,100), (cx-9,cy-15,10,9), 2)
            ellipse((245,200,100), (cx,cy-15,10,9), 2)
        elif index == 2:  # gold ornament
            circle(ink,cx,cy+2,12)
            circle((236,178,61),cx,cy+2,9)
            pygame.draw.rect(result, ink, (cx-4,cy-15,8,6), border_radius=2)
            circle(ink,cx,cy-16,3,1)
        else:  # Christmas tree
            pygame.draw.polygon(result, (41,122,75), [(cx,cy-16),(cx-14,cy+9),(cx+14,cy+9)])
            pygame.draw.rect(result, (119,70,40), (cx-3,cy+9,6,6))
            circle((250,211,83),cx,cy-11,3)
            for dx,dy in [(-7,3),(5,5),(0,-3)]:circle((238,73,75),cx+dx,cy+dy,2)
    elif theme == "EASTER":
        if index in (0, 1, 2):  # painted eggs
            ellipse(ink, (cx-12,cy-15,24,31))
            pygame.draw.arc(result, color, (cx-12,cy-9,24,20), .1,3.05,3)
            line(color, [(cx-10,cy+3),(cx-5,cy+6),(cx,cy+3),(cx+5,cy+6),(cx+10,cy+3)],3)
            for dx in (-5,5):circle(color,cx+dx,cy-5,2)
        elif index == 3:  # bunny head
            ellipse(ink,(cx-11,cy-6,22,22))
            ellipse(ink,(cx-10,cy-17,8,18))
            ellipse(ink,(cx+2,cy-17,8,18))
            circle(dark,cx-5,cy+3,2)
            circle(dark,cx+5,cy+3,2)
            circle((244,151,165),cx,cy+8,3)
        else:  # spring flower
            for angle in range(0,360,60):
                a=math.radians(angle)
                circle(ink,cx+math.cos(a)*9,cy+math.sin(a)*9,6)
            circle((250,199,80),cx,cy,6)
    elif theme == "FOREST":
        if index in (0, 3):  # leaves
            pygame.draw.ellipse(result, (181,238,151), (cx-12,cy-13,24,28))
            line((41,117,62),[(cx-9,cy+11),(cx+8,cy-10)],2)
            line((41,117,62),[(cx,cy+1),(cx-6,cy-4)],2)
        elif index in (1, 5):  # mushrooms
            pygame.draw.rect(result, (246,223,174), (cx-5,cy-1,10,14),border_radius=3)
            pygame.draw.arc(result, (237,94,78),(cx-15,cy-15,30,26),0,math.pi,13)
            pygame.draw.ellipse(result,(237,94,78),(cx-15,cy-12,30,16))
            for dx,dy in [(-6,-7),(5,-5)]:circle(ink,cx+dx,cy+dy,3)
        elif index == 2:  # acorn
            ellipse((165,98,52),(cx-10,cy-6,20,24))
            ellipse((96,66,38),(cx-12,cy-10,24,12))
            line((96,66,38),[(cx,cy-8),(cx+4,cy-14)],2)
        else:  # pine tree
            pygame.draw.rect(result,(132,89,51),(cx-3,cy+5,6,12))
            for y,w in [(cy-12,11),(cy-5,14),(cy+2,16)]:
                pygame.draw.polygon(result,(79,148,85),[(cx,y-7),(cx-w,y+10),(cx+w,y+10)])
    elif theme == "HALLOWEEN":
        if index % 4 == 0:  # glowing pumpkin with a face
            ellipse((245, 134, 41), (cx-13,cy-10,26,25))
            pygame.draw.rect(result,(58,108,55),(cx-2,cy-15,5,7))
            for dx in (-6,6):
                pygame.draw.polygon(result,(70,45,61),[(cx+dx,cy-4),(cx+dx-3,cy+2),(cx+dx+3,cy+2)])
            line((70,45,61),[(cx-7,cy+8),(cx,cy+11),(cx+7,cy+8)],2)
        elif index % 4 == 1:  # little ghost
            pygame.draw.polygon(result, ink, [(cx-10,cy+13),(cx-10,cy-4), (cx-8,cy-12),
                                                (cx,cy-16),(cx+8,cy-12),(cx+10,cy-4),
                                                (cx+10,cy+13),(cx+5,cy+9),(cx,cy+13),(cx-5,cy+9)])
            for dx in (-4,4): circle(dark,cx+dx,cy-2,2)
        elif index % 4 == 2:  # witch hat
            pygame.draw.polygon(result,(68,54,97),[(cx-3,cy-16),(cx+10,cy+8),(cx-12,cy+8)])
            ellipse((68,54,97),(cx-16,cy+3,32,10))
            pygame.draw.rect(result,(243,175,59),(cx-7,cy+1,14,4))
        else:  # bat
            pygame.draw.polygon(result,(44,42,65),[(cx,cy-2),(cx-7,cy-10),(cx-14,cy-9),
                 (cx-11,cy-1),(cx-15,cy+6),(cx-7,cy+3),(cx,cy+9),
                 (cx+7,cy+3),(cx+15,cy+6),(cx+11,cy-1),(cx+14,cy-9),(cx+7,cy-10)])
            for dx in (-3,3): circle(ink,cx+dx,cy+1,2)
    elif theme == "UNDERWATER":
        if index % 5 == 0:  # tropical fish
            ellipse(ink,(cx-12,cy-9,25,18))
            pygame.draw.polygon(result,(251,170,69),[(cx-7,cy),(cx-17,cy-10),(cx-17,cy+10)])
            circle(dark,cx+6,cy-2,2)
            line(color,[(cx-4,cy-7),(cx-4,cy+7)],2)
        elif index % 5 == 1:  # shell
            pygame.draw.polygon(result,(252,221,190),[(cx,cy-12),(cx-13,cy+10),(cx+13,cy+10)])
            for d in (-8,-4,4,8):
                line(color,[(cx,cy-11),(cx+d,cy+10)],2)
        elif index % 5 == 2:  # starfish
            pts=[]
            for j in range(10):
                a=-math.pi/2+j*math.pi/5
                dist=15 if j%2==0 else 7
                pts.append((round(cx+math.cos(a)*dist),round(cy+math.sin(a)*dist)))
            pygame.draw.polygon(result,(253,204,118),pts)
            for dx in (-4,4): circle(dark,cx+dx,cy-1,1)
        elif index % 5 == 3:  # jellyfish
            ellipse((239,183,251),(cx-12,cy-12,24,18))
            for dx in (-8,-2,4,10):
                line(ink,[(cx+dx,cy+3),(cx+dx+2,cy+8),(cx+dx,cy+14)],2)
        else:  # sea turtle
            ellipse((74,184,135),(cx-11,cy-9,22,19))
            circle((122,224,162),cx+13,cy,5)
            for dx,dy in [(-8,-10),(6,-10),(-8,8),(6,8)]:
                circle((122,224,162),cx+dx,cy+dy,4)
            pygame.draw.ellipse(result,(40,119,97),(cx-7,cy-6,14,12),2)
    return result


def decorate_background(surface: pygame.Surface, theme: str) -> None:
    """Draw themed scenery; no sprite files, downloads, or extra dependencies."""
    rng = random.Random(1042)
    if theme == "CHRISTMAS":
        for i in range(65):
            x,y = rng.randrange(SCREEN_W),rng.randrange(SCREEN_H)
            pygame.draw.circle(surface,(203,224,225),(x,y),rng.choice((1,2,3)))
        for x in range(0, SCREEN_W, 84):
            pygame.draw.line(surface,(46,125,93),(x,0),(x+20,16),3)
            pygame.draw.circle(surface, (242,191,101) if x%3 else (221,80,82),(x+20,16),6)
    elif theme == "EASTER":
        for i in range(34):
            x,y=rng.randrange(SCREEN_W),rng.randrange(SCREEN_H)
            pygame.draw.ellipse(surface,(169,163,208),(x,y,12,17),2)
            pygame.draw.circle(surface,(245,201,139),(x+6,y+8),2)
    elif theme == "FOREST":
        for x in range(0,SCREEN_W,40):
            top = rng.randrange(25,85)
            pygame.draw.polygon(surface,(25,80,61),[(x,top),(x-33,180),(x+33,180)])
            pygame.draw.polygon(surface,(29,92,67),[(x,top+35),(x-40,210),(x+40,210)])
        for i in range(36):
            x,y=rng.randrange(SCREEN_W),rng.randrange(200,SCREEN_H)
            pygame.draw.circle(surface,(128,158,79),(x,y),2)
    elif theme == "BUTTERFLIES":
        for i in range(30):
            x,y=rng.randrange(SCREEN_W),rng.randrange(SCREEN_H)
            color = rng.choice(((240,149,205),(157,175,244),(233,211,117)))
            pygame.draw.ellipse(surface,color,(x-9,y-7,10,9))
            pygame.draw.ellipse(surface,color,(x+1,y-7,10,9))
            pygame.draw.ellipse(surface,color,(x-7,y+1,8,6))
            pygame.draw.ellipse(surface,color,(x+1,y+1,8,6))
            pygame.draw.line(surface,(56,47,86),(x,y-6),(x,y+7),2)
    elif theme == "UNDERWATER":
        for _ in range(105):
            x,y=rng.randrange(SCREEN_W),rng.randrange(SCREEN_H)
            pygame.draw.circle(surface,(95,192,220),(x,y),rng.randrange(2,10),2)
    elif theme == "HALLOWEEN":
        for _ in range(70):
            x,y=rng.randrange(SCREEN_W),rng.randrange(SCREEN_H)
            pygame.draw.circle(surface,(225,156,85),(x,y),rng.randrange(1,4))
        pygame.draw.circle(surface,(253,207,121),(750,112),65)


@dataclass
class FlyingBubble:
    x: float
    y: float
    vx: float
    vy: float
    color: int


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: int
    life: float
    max_life: float


@dataclass
class FallingBubble:
    x: float
    y: float
    vy: float
    color: int
    rotation: float = 0.0


class BubbleShooter:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Bubble Shooter")
        # Gameplay is drawn on a fixed-resolution canvas, and that canvas is
        # scaled to the physical monitor. This preserves the bubble physics,
        # HUD layout, aspect ratio, and accuracy of mouse targeting.
        self.fullscreen = False
        self.windowed_size = self.choose_window_size()
        self.window = None
        self.viewport = pygame.Rect(0, 0, SCREEN_W, SCREEN_H)
        self.display_backdrop = None
        self.set_display_mode(fullscreen=True)  # Start filling the monitor.
        self.screen = pygame.Surface((SCREEN_W, SCREEN_H)).convert()
        self.clock = pygame.time.Clock()
        self.big_font = pygame.font.SysFont("arial", 49, bold=True)
        self.title_font = pygame.font.SysFont("arial", 36, bold=True)
        self.med_font = pygame.font.SysFont("arial", 25, bold=True)
        self.small_font = pygame.font.SysFont("arial", 19)
        self.tiny_font = pygame.font.SysFont("arial", 16)
        self.help_font = pygame.font.SysFont("arial", 12)
        self.number_font = pygame.font.SysFont("arial", 34, bold=True)
        # All worlds are illustrated: no plain/neon default themes.
        # 10 visually distinct color slots in each world; choose 3-10 at runtime.
        self.themes = {
            "CHRISTMAS": ((12, 36, 46), (38, 72, 87), (13, 30, 40), (103, 149, 161),
                [(222,64,69),(61,155,103),(239,193,83),(101,184,220),
                 (231,133,164),(163,112,77),(247,131,58),(164,113,233),
                 (65,205,192),(242,232,168)]),
            "EASTER": ((74, 67, 124), (133, 147, 177), (47, 43, 79), (142, 128, 191),
                [(251,138,171),(115,205,247),(255,210,104),(183,158,249),
                 (136,226,166),(249,165,128),(229,108,212),(89,153,232),
                 (180,227,106),(247,206,232)]),
            "FOREST": ((12, 43, 35), (43, 81, 53), (14, 36, 32), (101, 143, 105),
                [(113,190,95),(224,123,74),(231,199,91),(94,165,139),
                 (187,139,98),(207,99,111),(97,175,235),(203,126,222),
                 (242,167,93),(165,210,123)]),
            "BUTTERFLIES": ((45, 37, 93), (90, 70, 122), (48, 37, 79), (152, 128, 200),
                [(244,119,176),(94,188,248),(251,202,90),(178,126,249),
                 (105,215,168),(250,139,106),(239,86,215),(107,117,236),
                 (222,239,127),(252,181,206)]),
            "HALLOWEEN": ((30, 22, 52), (79, 42, 71), (27, 25, 41), (140, 107, 139),
                [(250,132,47),(159,93,217),(129,207,89),(250,204,81),
                 (231,75,109),(91,171,222),(207,134,74),(104,219,181),
                 (243,151,205),(191,192,104)]),
            "UNDERWATER": ((5, 51, 78), (8, 84, 107), (8, 40, 63), (70, 150, 169),
                [(253,125,130),(64,191,230),(251,213,82),(175,133,240),
                 (82,214,155),(252,149,82),(232,104,190),(80,121,231),
                 (171,227,109),(239,187,226)]),
        }
        self.theme_names = list(self.themes)
        self.theme_index = 0
        self.difficulty = "NORMAL"
        self.game_modes = ("CLASSIC", "RUSH", "BLITZ 60", "BLITZ 120", "CHALLENGE 180")
        self.game_mode = "CLASSIC"
        self.color_count = 5
        self.match_size = 3
        self.fullscreen_button = pygame.Rect(415, 68, 157, 29)
        self.buttons = {
            "mode": pygame.Rect(640, 416, 255, 34),
            "minus": pygame.Rect(767, 480, 56, 32),
            "plus": pygame.Rect(834, 480, 61, 32),
            "theme": pygame.Rect(640, 608, 255, 37),
            "difficulty": pygame.Rect(640, 674, 255, 33),
        }
        self.match_buttons = [(pygame.Rect(640 + i * 88, 553, 79, 29), number)
                              for i, number in enumerate((3, 4, 5))]
        self.apply_theme()
        self.background = self.make_background()
        self.best = 0
        self.reset()

    @staticmethod
    def choose_window_size() -> tuple[int, int]:
        """Use a reasonably large window that still fits smaller monitors."""
        info = pygame.display.Info()
        desktop_w = max(640, info.current_w or 1280)
        desktop_h = max(500, info.current_h or 800)
        return (max(640, min(1200, int(desktop_w * .85))),
                max(500, min(950, int(desktop_h * .87))))

    def update_viewport(self) -> None:
        """Center the 960x760 game canvas without stretching circles."""
        dw, dh = self.window.get_size()
        scale = min(dw / SCREEN_W, dh / SCREEN_H)
        sw = max(1, round(SCREEN_W * scale))
        sh = max(1, round(SCREEN_H * scale))
        self.viewport = pygame.Rect((dw - sw) // 2, (dh - sh) // 2, sw, sh)
        self.display_backdrop = None

    def set_display_mode(self, *, fullscreen: bool) -> None:
        """Switch between real desktop fullscreen and a resizable window."""
        if fullscreen:
            try:
                # (0, 0) asks SDL / Pygame for the current desktop resolution.
                self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                self.fullscreen = True
            except pygame.error:
                # If exclusive fullscreen isn't supported, stay playable.
                self.window = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
                self.fullscreen = False
        else:
            self.window = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
            self.fullscreen = False
        self.update_viewport()

    def toggle_fullscreen(self) -> None:
        self.set_display_mode(fullscreen=not self.fullscreen)

    def screen_to_game(self, pos: tuple[int, int]) -> tuple[int, int] | None:
        """Map monitor coordinates into logical game coordinates for clicks/aim."""
        if not self.viewport.collidepoint(pos):
            return None
        local_x = (pos[0] - self.viewport.x) * SCREEN_W / self.viewport.width
        local_y = (pos[1] - self.viewport.y) * SCREEN_H / self.viewport.height
        return (max(0, min(SCREEN_W - 1, int(local_x))),
                max(0, min(SCREEN_H - 1, int(local_y))))

    def make_display_backdrop(self) -> pygame.Surface:
        """Fill widescreen side areas with softened world art, not black bars."""
        dw, dh = self.window.get_size()
        # Blur the oversized scenery for quiet padding around the actual game.
        reduced_w, reduced_h = max(2, dw // 12), max(2, dh // 12)
        low_res = pygame.transform.smoothscale(self.background, (reduced_w, reduced_h))
        backdrop = pygame.transform.smoothscale(low_res, (dw, dh))
        dimmer = pygame.Surface((dw, dh), pygame.SRCALPHA)
        dimmer.fill((9, 12, 22, 110))
        backdrop.blit(dimmer, (0, 0))
        return backdrop

    def apply_theme(self) -> None:
        global BG_TOP, BG_BOTTOM, PANEL, PANEL_EDGE, PALETTE
        BG_TOP, BG_BOTTOM, PANEL, PANEL_EDGE, PALETTE = self.themes[self.theme_names[self.theme_index]]
        theme = self.theme_names[self.theme_index]
        self.bubbles = [make_themed_bubble(c, i, theme, "glossy")
                        for i, c in enumerate(PALETTE)]

    def refresh_visuals(self) -> None:
        self.apply_theme()
        self.background = self.make_background()
        self.display_backdrop = None

    def make_background(self) -> pygame.Surface:
        theme = self.theme_names[self.theme_index]
        picture = Path(__file__).resolve().parent / "assets" / f"{theme.lower()}.jpg"
        if picture.is_file():
            try:
                image = pygame.image.load(str(picture)).convert()
                if image.get_size() != (SCREEN_W, SCREEN_H):
                    image = pygame.transform.smoothscale(image, (SCREEN_W, SCREEN_H))
                return image
            except pygame.error:
                pass  # Still playable without the JPEG assets.
        surface = pygame.Surface((SCREEN_W, SCREEN_H))
        for y in range(SCREEN_H):
            t = y / SCREEN_H
            rgb = tuple(int(a * (1-t) + b*t) for a,b in zip(BG_TOP, BG_BOTTOM))
            pygame.draw.line(surface, rgb, (0, y), (SCREEN_W, y))
        decorate_background(surface, theme)
        return surface

    def panel(self, rect: pygame.Rect) -> None:
        # Translucent so illustrated scenery remains visible beneath the game UI.
        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (*PANEL, 211), layer.get_rect(), border_radius=24)
        self.screen.blit(layer, rect.topleft)
        pygame.draw.rect(self.screen, PANEL_EDGE, rect, width=2, border_radius=24)

    def cycle_theme(self) -> None:
        self.theme_index = (self.theme_index + 1) % len(self.theme_names)
        self.refresh_visuals()

    def cycle_mode(self) -> None:
        index = self.game_modes.index(self.game_mode)
        self.game_mode = self.game_modes[(index + 1) % len(self.game_modes)]
        self.reset()

    def cycle_difficulty(self) -> None:
        modes = ("EASY", "NORMAL", "HARD")
        self.difficulty = modes[(modes.index(self.difficulty) + 1) % len(modes)]
        self.reset()

    def change_colors(self, amount: int) -> None:
        new_count = max(3, min(10, amount))
        if new_count != self.color_count:
            self.color_count = new_count
            self.reset()  # Avoid orphaned color classes from the previous board.

    def reset(self) -> None:
        self.phase = 0
        self.grid: dict[tuple[int, int], int] = {}
        initial_colors = list(range(self.color_count))
        for row in range(6):
            for col in range(self.row_size(row)):
                if row == 5 and random.random() < 0.25:
                    continue
                # Group some neighboring colors for satisfying early shots.
                nearby = [self.grid[(row, col - 1)]] if (row, col - 1) in self.grid else []
                if row > 0:
                    for nr, nc in self.neighbors(row, col):
                        if nr == row - 1 and (nr, nc) in self.grid:
                            nearby.append(self.grid[(nr, nc)])
                if nearby and random.random() < 0.48:
                    color = random.choice(nearby)
                else:
                    color = random.choice(initial_colors)
                self.grid[row, col] = color

        self.current = self.pick_color()
        self.next_color = self.pick_color()
        self.projectile: FlyingBubble | None = None
        self.particles: list[Particle] = []
        self.falling: list[FallingBubble] = []
        self.aim_angle = 0.0
        self.score = 0
        self.combo = 0
        self.misses = 0
        self.shots = 0
        self.state = "playing"  # playing, paused, won, lost
        self.banner = ""
        self.banner_timer = 0.0
        self.time_total = {"BLITZ 60": 60, "BLITZ 120": 120,
                           "CHALLENGE 180": 180}.get(self.game_mode)
        self.time_left = float(self.time_total) if self.time_total is not None else None

    def row_size(self, row: int) -> int:
        return GRID_COLS - ((row + self.phase) % 2)

    def cell_xy(self, row: int, col: int) -> tuple[float, float]:
        return (GRID_X + col * CELL_X + ((row + self.phase) % 2) * CELL_X / 2,
                GRID_TOP + row * CELL_Y)

    def valid_cell(self, row: int, col: int) -> bool:
        return 0 <= row < GRID_ROWS and 0 <= col < self.row_size(row)

    def neighbors(self, row: int, col: int):
        adjacent = [(row, col - 1), (row, col + 1)]
        if (row + self.phase) % 2 == 0:
            diagonals = (col - 1, col)
        else:
            diagonals = (col, col + 1)
        for nr in (row - 1, row + 1):
            adjacent.extend((nr, nc) for nc in diagonals)
        return [(nr, nc) for nr, nc in adjacent if self.valid_cell(nr, nc)]

    def pick_color(self) -> int:
        available = list(set(self.grid.values()))
        return random.choice(available) if available else random.randrange(len(PALETTE))

    def ensure_shootable_colors(self) -> None:
        available = set(self.grid.values())
        if available and self.current not in available:
            self.current = random.choice(list(available))
        if available and self.next_color not in available:
            self.next_color = random.choice(list(available))

    def set_aim_from_mouse(self, mouse_position: tuple[int, int]) -> None:
        dx = mouse_position[0] - SHOOTER_X
        dy = SHOOTER_Y - mouse_position[1]
        # Restrict shots to the upper half of the play field.
        if dy <= 0:
            dy = 1
        self.aim_angle = max(-MAX_ANGLE, min(MAX_ANGLE, math.atan2(dx, dy)))

    def fire(self) -> None:
        if self.state != "playing" or self.projectile is not None:
            return
        self.projectile = FlyingBubble(
            float(SHOOTER_X), float(SHOOTER_Y),
            math.sin(self.aim_angle) * SHOT_SPEED,
            -math.cos(self.aim_angle) * SHOT_SPEED,
            self.current,
        )
        self.current = self.next_color
        self.next_color = self.pick_color()
        self.shots += 1

    def touching_bubble(self, x: float, y: float) -> tuple[int, int] | None:
        collision_dist_sq = (2 * RADIUS - 2) ** 2
        # Testing the complete grid also handles any sparse layouts correctly.
        for (r, c) in self.grid:
            cx, cy = self.cell_xy(r, c)
            if (x - cx) ** 2 + (y - cy) ** 2 <= collision_dist_sq:
                return r, c
        return None

    def snap_cell(self, x: float, y: float,
                  touched: tuple[int, int] | None) -> tuple[int, int] | None:
        # Prefer direct neighbors of the struck bubble.  When the projectile
        # hits the ceiling instead, place it on the first row.
        if touched is None:
            options = [(0, c) for c in range(self.row_size(0))
                       if (0, c) not in self.grid]
        else:
            options = [p for p in self.neighbors(*touched) if p not in self.grid]

        if not options:
            # Fallback for a bubble whose immediate surroundings are full.
            options = [(r, c) for r in range(GRID_ROWS)
                       for c in range(self.row_size(r))
                       if (r, c) not in self.grid and
                       (r == 0 or any(n in self.grid for n in self.neighbors(r, c)))]
        if not options:
            return None
        return min(options, key=lambda p:
                   (self.cell_xy(*p)[0] - x) ** 2 +
                   (self.cell_xy(*p)[1] - y) ** 2)

    def flood(self, start: tuple[int, int], *, color_match: bool) -> set[tuple[int, int]]:
        if start not in self.grid:
            return set()
        target_color = self.grid[start]
        seen = {start}
        pending = [start]
        while pending:
            row, col = pending.pop()
            for neighbor in self.neighbors(row, col):
                if neighbor in seen or neighbor not in self.grid:
                    continue
                if color_match and self.grid[neighbor] != target_color:
                    continue
                seen.add(neighbor)
                pending.append(neighbor)
        return seen

    def remove_unsupported(self) -> set[tuple[int, int]]:
        """Drop every bubble not connected to a ceiling bubble."""
        supported: set[tuple[int, int]] = set()
        for c in range(self.row_size(0)):
            root = (0, c)
            if root in self.grid and root not in supported:
                supported.update(self.flood(root, color_match=False))
        unsupported = set(self.grid) - supported
        for row, col in unsupported:
            x, y = self.cell_xy(row, col)
            self.falling.append(FallingBubble(x, y, random.uniform(-45, 60),
                                              self.grid[row, col]))
            del self.grid[row, col]
        return unsupported

    def emit_particles(self, x: float, y: float, color: int) -> None:
        for _ in range(9):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(55, 200)
            lifetime = random.uniform(0.35, 0.65)
            self.particles.append(Particle(x, y,
                                           math.cos(angle) * speed,
                                           math.sin(angle) * speed,
                                           color, lifetime, lifetime))

    def land(self, projectile: FlyingBubble,
             touched: tuple[int, int] | None) -> None:
        cell = self.snap_cell(projectile.x, projectile.y, touched)
        self.projectile = None
        if cell is None:
            self.state = "lost"
            return
        self.grid[cell] = projectile.color
        cluster = self.flood(cell, color_match=True)
        if len(cluster) >= self.match_size:
            for row, col in cluster:
                x, y = self.cell_xy(row, col)
                self.emit_particles(x, y, self.grid[row, col])
                del self.grid[row, col]
            dropped = self.remove_unsupported()
            self.combo += 1
            self.misses = 0
            points = len(cluster) * 10 + len(dropped) * 20
            bonus = (self.combo - 1) * 25
            self.score += points + bonus
            self.best = max(self.score, self.best)
            self.banner = f"+{points + bonus}  NICE SHOT!"
            self.banner_timer = 1.1
        else:
            self.combo = 0
            self.misses += 1
            miss_limit = {"EASY": 8, "NORMAL": MISSES_BEFORE_DROP, "HARD": 4}[self.difficulty]
            if self.misses >= miss_limit or (self.game_mode == "RUSH" and self.misses >= 3):
                self.add_row()
                self.misses = 0
                self.banner = "CEILING DROPPED!"
                self.banner_timer = 1.3

        if not self.grid:
            self.state = "won"
            if self.time_left is not None:
                self.score += int(self.time_left) * 5
                self.best = max(self.best, self.score)
        elif any(row >= GRID_ROWS - 1 for row, _ in self.grid):
            self.state = "lost"
        else:
            self.ensure_shootable_colors()

    def add_row(self) -> None:
        # Flip the row parity when shifting the board.  This preserves every
        # existing bubble's x coordinate, even the rightmost ones.
        self.phase ^= 1
        self.grid = {(r + 1, c): color for (r, c), color in self.grid.items()}
        # New ceiling bubbles inherit the level's current color pool.
        remaining_colors = list(set(self.grid.values())) or list(range(5))
        for col in range(self.row_size(0)):
            self.grid[0, col] = random.choice(remaining_colors)

    def update(self, dt: float) -> None:
        if self.state == "paused":
            return
        if self.state == "playing" and self.time_left is not None:
            self.time_left = max(0.0, self.time_left - dt)
            if self.time_left <= 0:
                self.state = "lost" if self.game_mode == "CHALLENGE 180" else "time_up"
                self.projectile = None
                self.best = max(self.best, self.score)
                return
        if self.banner_timer > 0:
            self.banner_timer = max(0.0, self.banner_timer - dt)

        if self.state == "playing" and self.projectile:
            moving = self.projectile
            # Small physics substeps prevent tunneling through the grid.
            steps = max(1, math.ceil(SHOT_SPEED * dt / 7))
            sub_dt = dt / steps
            for _ in range(steps):
                moving.x += moving.vx * sub_dt
                moving.y += moving.vy * sub_dt
                if moving.x <= WALL_LEFT:
                    moving.x = 2 * WALL_LEFT - moving.x
                    moving.vx = abs(moving.vx)
                elif moving.x >= WALL_RIGHT:
                    moving.x = 2 * WALL_RIGHT - moving.x
                    moving.vx = -abs(moving.vx)
                touched = self.touching_bubble(moving.x, moving.y)
                if touched is not None or moving.y <= GRID_TOP:
                    self.land(moving, touched)
                    break

        for particle in self.particles:
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.vy += 280 * dt
            particle.life -= dt
        self.particles = [p for p in self.particles if p.life > 0]

        for bubble in self.falling:
            bubble.y += bubble.vy * dt
            bubble.vy += 650 * dt
        self.falling = [b for b in self.falling if b.y < SCREEN_H + 50]

    def text(self, value: str, font: pygame.font.Font,
             color: tuple[int, int, int], position: tuple[int, int],
             *, center: bool = False) -> None:
        surface = font.render(value, True, color)
        rectangle = surface.get_rect(center=position) if center else surface.get_rect(topleft=position)
        self.screen.blit(surface, rectangle)

    def draw_bubble(self, x: float, y: float, color: int) -> None:
        surface = self.bubbles[color]
        self.screen.blit(surface, (int(x - surface.get_width() / 2),
                                   int(y - surface.get_height() / 2)))

    def draw_aim(self) -> None:
        x = float(SHOOTER_X)
        y = float(SHOOTER_Y)
        vx = math.sin(self.aim_angle) * 10
        vy = -math.cos(self.aim_angle) * 10
        for i in range(95):
            x += vx
            y += vy
            if x < WALL_LEFT:
                x = 2 * WALL_LEFT - x
                vx = abs(vx)
            if x > WALL_RIGHT:
                x = 2 * WALL_RIGHT - x
                vx = -abs(vx)
            if y <= GRID_TOP or self.touching_bubble(x, y):
                break
            if i % 3 == 0 and y < SHOOTER_Y - 40:
                fraction = 1 - i / 95
                color = (int(CYAN[0] * fraction + PANEL[0] * (1 - fraction)),
                         int(CYAN[1] * fraction + PANEL[1] * (1 - fraction)),
                         int(CYAN[2] * fraction + PANEL[2] * (1 - fraction)))
                pygame.draw.circle(self.screen, color, (round(x), round(y)),
                                   max(2, round(4 * fraction)))

    def draw_field(self) -> None:
        self.panel(pygame.Rect(FIELD_LEFT, 61, FIELD_RIGHT - FIELD_LEFT, 672))
        # The ceiling and the lower danger boundary.
        miss_limit = 3 if self.game_mode == "RUSH" else {"EASY": 8, "NORMAL": 6, "HARD": 4}[self.difficulty]
        self.text(f"DROP IN {max(0, miss_limit-self.misses)} MISSES",
                  self.help_font, MUTED, (FIELD_LEFT+21,72))
        pygame.draw.line(self.screen, (62, 90, 126),
                         (WALL_LEFT, GRID_TOP - RADIUS - 8),
                         (WALL_RIGHT, GRID_TOP - RADIUS - 8), 3)
        self.ui_button(self.fullscreen_button,
                       "F11  WINDOW" if self.fullscreen else "F11  FULLSCREEN")
        for x in range(WALL_LEFT + 4, WALL_RIGHT, 21):
            pygame.draw.line(self.screen, darken(RED, 0.35),
                             (x, 660), (min(x + 10, WALL_RIGHT), 660), 2)
        self.text("DANGER ZONE", self.tiny_font, (156, 83, 98), (76, 669))

        if self.state == "playing" and self.projectile is None:
            self.draw_aim()

        for (r, c), color in sorted(self.grid.items()):
            x, y = self.cell_xy(r, c)
            self.draw_bubble(x, y, color)
        for falling in self.falling:
            self.draw_bubble(falling.x, falling.y, falling.color)
        if self.projectile:
            self.draw_bubble(self.projectile.x, self.projectile.y,
                             self.projectile.color)

        for particle in self.particles:
            radius = max(1, int(4 * particle.life / particle.max_life))
            pygame.draw.circle(self.screen, lighten(PALETTE[particle.color], 0.3),
                               (round(particle.x), round(particle.y)), radius)

        # Turret below the danger line.
        pygame.draw.circle(self.screen, (31, 57, 86),
                           (SHOOTER_X, SHOOTER_Y + 7), 32)
        pygame.draw.circle(self.screen, (61, 97, 138),
                           (SHOOTER_X, SHOOTER_Y + 7), 32, 3)
        direction = pygame.Vector2(math.sin(self.aim_angle), -math.cos(self.aim_angle))
        barrel_end = pygame.Vector2(SHOOTER_X, SHOOTER_Y) + direction * 41
        pygame.draw.line(self.screen, (94, 164, 189),
                         (SHOOTER_X, SHOOTER_Y + 7), barrel_end, 14)
        pygame.draw.circle(self.screen, (151, 232, 244),
                           (round(barrel_end.x), round(barrel_end.y)), 8)
        if self.projectile is None:
            self.draw_bubble(SHOOTER_X, SHOOTER_Y, self.current)

        if self.banner_timer > 0 and self.banner:
            self.text(self.banner, self.med_font, GOLD,
                      (SHOOTER_X, 82), center=True)

    def ui_button(self, rect, label: str, *, selected: bool = False) -> None:
        pygame.draw.rect(self.screen, (37, 76, 92) if selected else (29, 55, 71),
                         rect, border_radius=9)
        pygame.draw.rect(self.screen, CYAN if selected else PANEL_EDGE,
                         rect, width=2, border_radius=9)
        self.text(label, self.tiny_font, WHITE, rect.center, center=True)

    def draw_sidebar(self) -> None:
        left, width = 614, 307
        self.panel(pygame.Rect(left, 61, width, 672))
        self.text("BUBBLE", self.title_font, WHITE, (left + 26, 79))
        self.text("FANTASY", self.title_font, CYAN, (left + 26, 120))
        pygame.draw.line(self.screen, PANEL_EDGE, (left + 24, 163), (left + width-24,163))
        self.text("SCORE", self.small_font, MUTED, (left + 26, 174))
        self.text(f"{self.score:,}", self.number_font, WHITE, (left + 26, 199))
        self.text("BEST", self.small_font, MUTED, (left + 179, 174))
        self.text(f"{self.best:,}", self.med_font, GOLD, (left + 179, 205))
        pygame.draw.line(self.screen, PANEL_EDGE, (left+24,240),(left+width-24,240))
        self.text("NEXT", self.tiny_font, MUTED, (left+26,249))
        pygame.draw.circle(self.screen,(30,54,71),(left+74,295),30)
        self.draw_bubble(left+74,295,self.next_color)
        self.text("COMBO", self.tiny_font, MUTED, (left+175,249))
        self.text(f"x{max(self.combo,1)}",self.number_font,
                  GOLD if self.combo>1 else WHITE,(left+175,278))
        pygame.draw.line(self.screen, PANEL_EDGE,(left+24,326),(left+width-24,326))
        self.text("TIME",self.tiny_font,MUTED,(left+26,339))
        if self.time_left is None:
            time_label="NO LIMIT"
        else:
            seconds=math.ceil(self.time_left)
            time_label=f"{seconds//60:02d}:{seconds%60:02d}"
        time_color = RED if self.time_left is not None and self.time_left <= 15 else GOLD
        self.text(time_label,self.med_font,time_color,(left+176,333))
        pygame.draw.rect(self.screen,(37,61,74),(left+26,371,255,9),border_radius=5)
        if self.time_left is not None and self.time_total:
            fraction=max(0,self.time_left/self.time_total)
            if fraction > 0:
                pygame.draw.rect(self.screen,RED if fraction<.20 else CYAN,
                    (left+26,371,max(1,int(255*fraction)),9),border_radius=5)
        self.text("GAME MODE",self.tiny_font,MUTED,(left+26,393))
        self.ui_button(self.buttons["mode"],self.game_mode + "   >")
        self.text("BUBBLE COLORS",self.tiny_font,MUTED,(left+26,462))
        self.text(f"{self.color_count} / 10",self.small_font,GOLD,(left+26,486))
        self.ui_button(self.buttons["minus"],"-",selected=False)
        self.ui_button(self.buttons["plus"],"+",selected=False)
        # Show tiny color swatches for the entire active palette.
        for i in range(self.color_count):
            x=left+28+i*27
            pygame.draw.circle(self.screen, PALETTE[i],(x,525),8)
            pygame.draw.circle(self.screen, lighten(PALETTE[i],.6),(x-2,523),2)
        self.text("MATCH",self.tiny_font,MUTED,(left+26,535))
        for rect,num in self.match_buttons:
            self.ui_button(rect,str(num),selected=num==self.match_size)
        self.text("PICTURE WORLD",self.tiny_font,MUTED,(left+26,590))
        self.ui_button(self.buttons["theme"],self.theme_names[self.theme_index] + "   >")
        self.text("DIFFICULTY",self.tiny_font,MUTED,(left+26,656))
        self.ui_button(self.buttons["difficulty"],self.difficulty + "   >")
        self.text("F11 screen  T theme  M mode  P pause",
                  self.help_font,MUTED,(left+23,710))
        self.text("R restart  1/2/3 difficulty  Esc exit",
                  self.help_font,MUTED,(left+23,723))

    def draw_overlay(self) -> None:
        if self.state not in ("won", "lost", "paused", "time_up"):
            return
        shade=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA)
        shade.fill((5,11,23,173))
        self.screen.blit(shade,(0,0))
        pygame.draw.rect(self.screen,PANEL,(212,239,536,270),border_radius=24)
        pygame.draw.rect(self.screen,PANEL_EDGE,(212,239,536,270),2,border_radius=24)
        if self.state == "won":
            headline, accent, sub="YOU WIN!", CYAN, "All bubbles cleared!"
        elif self.state == "time_up":
            headline, accent, sub="TIME'S UP!", GOLD, "Your time attack is complete."
        elif self.state == "lost":
            sub = "The countdown ran out." if self.time_left == 0 else "The bubbles reached the bottom."
            headline, accent="GAME OVER", RED
        else:
            headline, accent, sub="PAUSED", GOLD, "Press P to continue."
        self.text(headline,self.big_font,accent,(480,297),center=True)
        self.text(sub,self.small_font,WHITE,(480,363),center=True)
        if self.state != "paused":
            self.text(f"Final score: {self.score:,}",self.med_font,WHITE,(480,407),center=True)
            self.text("Press R, Space, or click to restart",self.small_font,MUTED,(480,465),center=True)

    def draw(self) -> None:
        self.screen.blit(self.background, (0, 0))
        self.draw_field()
        self.draw_sidebar()
        self.draw_overlay()
        # Render the logical game into the screen-sized window. On widescreen
        # monitors, themed artwork fills the margins instead of black bars.
        if self.display_backdrop is None or self.display_backdrop.get_size() != self.window.get_size():
            self.display_backdrop = self.make_display_backdrop()
        self.window.blit(self.display_backdrop, (0, 0))
        resized_game = pygame.transform.smoothscale(self.screen, self.viewport.size)
        self.window.blit(resized_game, self.viewport.topleft)
        pygame.display.flip()

    def handle_click(self, pos: tuple[int,int]) -> None:
        if self.fullscreen_button.collidepoint(pos):
            self.toggle_fullscreen()
            return
        if self.state in ("won","lost","time_up"):
            self.reset()
            return
        if self.state == "paused":
            return
        if self.buttons["mode"].collidepoint(pos):
            self.cycle_mode()
        elif self.buttons["minus"].collidepoint(pos):
            self.change_colors(self.color_count-1)
        elif self.buttons["plus"].collidepoint(pos):
            self.change_colors(self.color_count+1)
        elif self.buttons["theme"].collidepoint(pos):
            self.cycle_theme()
        elif self.buttons["difficulty"].collidepoint(pos):
            self.cycle_difficulty()
        elif any(rect.collidepoint(pos) for rect,_ in self.match_buttons):
            self.match_size = next(n for rect,n in self.match_buttons if rect.collidepoint(pos))
            self.reset()
        elif pos[0] < FIELD_RIGHT+5:
            self.set_aim_from_mouse(pos)
            self.fire()

    def run(self) -> None:
        while True:
            dt=min(self.clock.tick(FPS)/1000,1/25)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.VIDEORESIZE and not self.fullscreen:
                    self.windowed_size = (max(640, event.w), max(500, event.h))
                    self.window = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
                    self.update_viewport()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11 or (event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT):
                        self.toggle_fullscreen()
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        return
                    elif event.key == pygame.K_r:
                        self.reset()
                    elif event.key == pygame.K_p:
                        if self.state == "playing":
                            self.state="paused"
                        elif self.state == "paused":
                            self.state="playing"
                    elif event.key == pygame.K_t:
                        self.cycle_theme()
                    elif event.key == pygame.K_m:
                        self.cycle_mode()
                    elif event.key == pygame.K_c:
                        self.change_colors(3 if self.color_count>=10 else self.color_count+1)
                    elif event.key in (pygame.K_EQUALS,pygame.K_KP_PLUS,pygame.K_RIGHTBRACKET):
                        self.change_colors(self.color_count+1)
                    elif event.key in (pygame.K_MINUS,pygame.K_KP_MINUS,pygame.K_LEFTBRACKET):
                        self.change_colors(self.color_count-1)
                    elif event.key == pygame.K_d and pygame.key.get_mods() & pygame.KMOD_SHIFT:
                        self.cycle_difficulty()
                    elif event.key in (pygame.K_1,pygame.K_2,pygame.K_3):
                        self.difficulty={pygame.K_1:"EASY",pygame.K_2:"NORMAL",pygame.K_3:"HARD"}[event.key]
                        self.reset()
                    elif event.key == pygame.K_g:
                        self.game_mode = "RUSH" if self.game_mode == "CLASSIC" else "CLASSIC"
                        self.reset()
                    elif event.key == pygame.K_SPACE:
                        if self.state == "playing":
                            self.fire()
                        elif self.state in ("won","lost","time_up"):
                            self.reset()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    game_pos = self.screen_to_game(event.pos)
                    if game_pos is not None:
                        self.handle_click(game_pos)
                if event.type == pygame.MOUSEMOTION and self.state == "playing":
                    game_pos = self.screen_to_game(event.pos)
                    if game_pos is not None:
                        self.set_aim_from_mouse(game_pos)
            if self.state == "playing":
                keys=pygame.key.get_pressed()
                if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                    self.aim_angle=max(-MAX_ANGLE,self.aim_angle-1.6*dt)
                if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                    self.aim_angle=min(MAX_ANGLE,self.aim_angle+1.6*dt)
            self.update(dt)
            self.draw()


if __name__ == "__main__":
    try:
        BubbleShooter().run()
    except pygame.error as exc:
        print(f"Pygame couldn't open a game window: {exc}", file=sys.stderr)
        sys.exit(1)
