"""Bubble Shooter - a self-contained Pygame arcade game.

Install: python -m pip install pygame
Run:     python bubble_shooter.py

Controls:
  Mouse: aim               Left click / Space: shoot
  Left/Right or A/D: aim    P: pause
  R: restart               Esc: quit
"""

from __future__ import annotations

import math
import random
import sys
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


def make_bubble(color: tuple[int, int, int], radius: int = RADIUS) -> pygame.Surface:
    """Paint a shaded, translucent-highlight bubble without image assets."""
    pad = 4
    size = 2 * (radius + pad)
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    center = (radius + pad, radius + pad)
    pygame.draw.circle(surface, darken(color, 0.50), center, radius + 2)
    pygame.draw.circle(surface, color, center, radius)
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
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        self.big_font = pygame.font.SysFont("arial", 49, bold=True)
        self.title_font = pygame.font.SysFont("arial", 36, bold=True)
        self.med_font = pygame.font.SysFont("arial", 25, bold=True)
        self.small_font = pygame.font.SysFont("arial", 19)
        self.tiny_font = pygame.font.SysFont("arial", 16)
        self.number_font = pygame.font.SysFont("arial", 34, bold=True)
        self.bubbles = [make_bubble(c) for c in PALETTE]
        self.background = self.make_background()
        self.best = 0
        self.reset()

    def make_background(self) -> pygame.Surface:
        surface = pygame.Surface((SCREEN_W, SCREEN_H))
        for y in range(SCREEN_H):
            t = y / SCREEN_H
            rgb = tuple(int(a * (1 - t) + b * t)
                        for a, b in zip(BG_TOP, BG_BOTTOM))
            pygame.draw.line(surface, rgb, (0, y), (SCREEN_W, y))
        # Calm, subtle dots behind the panels.
        for x in range(16, SCREEN_W, 28):
            for y in range(14, SCREEN_H, 28):
                pygame.draw.circle(surface, (32, 48, 73), (x, y), 1)
        return surface

    def reset(self) -> None:
        self.phase = 0
        self.grid: dict[tuple[int, int], int] = {}
        initial_colors = list(range(5))
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
        if len(cluster) >= 3:
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
            if self.misses >= MISSES_BEFORE_DROP:
                self.add_row()
                self.misses = 0
                self.banner = "CEILING DROPPED!"
                self.banner_timer = 1.3

        if not self.grid:
            self.state = "won"
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
        pygame.draw.rect(self.screen, PANEL, (FIELD_LEFT, 61,
                         FIELD_RIGHT - FIELD_LEFT, 672), border_radius=24)
        pygame.draw.rect(self.screen, PANEL_EDGE,
                         (FIELD_LEFT, 61, FIELD_RIGHT - FIELD_LEFT, 672),
                         width=2, border_radius=24)
        # The ceiling and the lower danger boundary.
        pygame.draw.line(self.screen, (62, 90, 126),
                         (WALL_LEFT, GRID_TOP - RADIUS - 8),
                         (WALL_RIGHT, GRID_TOP - RADIUS - 8), 3)
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

    def draw_sidebar(self) -> None:
        left, width = 614, 307
        pygame.draw.rect(self.screen, PANEL, (left, 61, width, 672), border_radius=24)
        pygame.draw.rect(self.screen, PANEL_EDGE,
                         (left, 61, width, 672), width=2, border_radius=24)
        self.text("BUBBLE", self.title_font, WHITE, (left + 25, 91))
        self.text("SHOOTER", self.title_font, CYAN, (left + 25, 128))
        pygame.draw.line(self.screen, PANEL_EDGE,
                         (left + 24, 190), (left + width - 24, 190), 1)

        self.text("SCORE", self.small_font, MUTED, (left + 26, 212))
        self.text(f"{self.score:,}", self.number_font, WHITE, (left + 26, 235))
        self.text("BEST", self.small_font, MUTED, (left + 186, 212))
        self.text(f"{self.best:,}", self.med_font, GOLD, (left + 186, 244))
        pygame.draw.line(self.screen, PANEL_EDGE,
                         (left + 24, 300), (left + width - 24, 300), 1)

        self.text("NEXT", self.small_font, MUTED, (left + 26, 325))
        pygame.draw.circle(self.screen, (33, 53, 76),
                           (left + 69, 398), 38)
        self.draw_bubble(left + 69, 398, self.next_color)
        self.text("COMBO", self.small_font, MUTED, (left + 172, 325))
        self.text(f"x{max(self.combo, 1)}", self.number_font,
                  GOLD if self.combo > 1 else WHITE, (left + 172, 368))
        pygame.draw.line(self.screen, PANEL_EDGE,
                         (left + 24, 457), (left + width - 24, 457), 1)

        self.text("MISSES BEFORE DROP", self.tiny_font, MUTED, (left + 26, 474))
        for i in range(MISSES_BEFORE_DROP):
            color = RED if i < self.misses else (46, 67, 90)
            pygame.draw.rect(self.screen, color,
                             (left + 26 + i * 43, 508, 34, 10), border_radius=5)
        self.text(f"{MISSES_BEFORE_DROP - self.misses} left", self.tiny_font,
                  MUTED, (left + 26, 532))

        pygame.draw.line(self.screen, PANEL_EDGE,
                         (left + 24, 575), (left + width - 24, 575), 1)
        self.text("CONTROLS", self.small_font, WHITE, (left + 26, 592))
        controls = ["Move mouse  -  aim",
                    "Click / Space  -  shoot",
                    "A / D  -  fine aim",
                    "P  -  pause     R  -  restart"]
        for i, line in enumerate(controls):
            self.text(line, self.tiny_font, MUTED, (left + 26, 625 + i * 24))

    def draw_overlay(self) -> None:
        if self.state not in ("won", "lost", "paused"):
            return
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((5, 11, 23, 175))
        self.screen.blit(shade, (0, 0))
        pygame.draw.rect(self.screen, PANEL,
                         (230, 241, 500, 255), border_radius=24)
        pygame.draw.rect(self.screen, PANEL_EDGE,
                         (230, 241, 500, 255), width=2, border_radius=24)
        if self.state == "won":
            headline, accent, sub = "YOU WIN!", CYAN, "Every bubble cleared!"
        elif self.state == "lost":
            headline, accent, sub = "GAME OVER", RED, "The bubbles reached the bottom."
        else:
            headline, accent, sub = "PAUSED", GOLD, "Press P to continue"
        self.text(headline, self.big_font, accent, (480, 304), center=True)
        self.text(sub, self.small_font, WHITE, (480, 367), center=True)
        if self.state != "paused":
            self.text(f"Final score: {self.score:,}", self.med_font, WHITE,
                      (480, 409), center=True)
            self.text("Press R or click to play again", self.small_font,
                      MUTED, (480, 461), center=True)

    def draw(self) -> None:
        self.screen.blit(self.background, (0, 0))
        self.draw_field()
        self.draw_sidebar()
        self.draw_overlay()
        pygame.display.flip()

    def run(self) -> None:
        while True:
            dt = min(self.clock.tick(FPS) / 1000.0, 1 / 25)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        return
                    if event.key == pygame.K_r:
                        self.reset()
                    elif event.key == pygame.K_p:
                        if self.state == "playing":
                            self.state = "paused"
                        elif self.state == "paused":
                            self.state = "playing"
                    elif event.key == pygame.K_SPACE:
                        if self.state == "playing":
                            self.fire()
                        elif self.state in ("won", "lost"):
                            self.reset()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.state in ("won", "lost"):
                        self.reset()
                    elif self.state == "playing":
                        self.set_aim_from_mouse(event.pos)
                        self.fire()
                if event.type == pygame.MOUSEMOTION and self.state == "playing":
                    self.set_aim_from_mouse(event.pos)

            if self.state == "playing":
                keys = pygame.key.get_pressed()
                if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                    self.aim_angle = max(-MAX_ANGLE, self.aim_angle - 1.6 * dt)
                if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                    self.aim_angle = min(MAX_ANGLE, self.aim_angle + 1.6 * dt)

            self.update(dt)
            self.draw()


if __name__ == "__main__":
    try:
        BubbleShooter().run()
    except pygame.error as exc:
        print(f"Pygame couldn't open a game window: {exc}", file=sys.stderr)
        sys.exit(1)
