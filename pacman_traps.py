# pacman_remix_with_strategic_traps.py
# Pac-Man Remix — Gem Badges + Epic Storyline + Strategic Hidden Traps
# Requirements: pygame
# Install: pip install pygame
# Run: python pacman_remix_with_strategic_traps.py

import pygame, sys, random, json, math, time
from collections import deque

# ---------- Config ----------
MAZE_ROWS = 21
MAZE_COLS = 21
SCREEN_W = 1200
SCREEN_H = 800
FPS = 60

BADGE_SAVE_FILE = "pacman_badges.json"

ACHIEVEMENTS = [("Rookie", 100), ("Diamond", 500), ("Master", 1000), ("Conqueror", 2000)]
BADGE_DESCRIPTIONS = {
    "Rookie": "First steps — great start! Keep munching and learning the maze.",
    "Diamond": "Shining performer — excellent reflexes and consistent scoring.",
    "Master": "Expert eater — your maze control is impressive.",
    "Conqueror": "Maze conqueror — legendary performance! You rule Pac-World."
}

BUFF_DURATIONS = {'speed': 6.0, 'freeze': 4.0, 'invincible': 5.0}

# ---------- Colors ----------
DEEP_BG_A = (10, 8, 28)
DEEP_BG_B = (26, 6, 56)
ACCENT = (100, 220, 255)
ACCENT2 = (255, 140, 200)
GOLD = (255, 200, 60)
WHITE = (242, 242, 245)
MUTED = (170, 175, 195)
MUTED_DARK = (120, 125, 140)
WALL = (40, 42, 85)
WALL_INNER = (22, 23, 45)
PELLET_COLOR = (220, 220, 220)
ENERGIZER_COLOR = (255, 180, 180)
NEON_YELLOW = (255, 235, 140)
NEON_BLUE = (120, 220, 255)
NEON_PINK = (255, 130, 220)
NEON_GREEN = (130, 255, 170)
GHOST_COLORS = [(255, 60, 80), (220, 120, 255), (80, 220, 230), (255, 170, 50)]

# ---------- ASCII Maze ----------
MAP_STR = [
"#####################",
"#.........##.........#",
"#.###.###.##.###.###.#",
"#o###.###.##.###.###o#",
"#.###.###.##.###.###.#",
"#....................#",
"#.###.##.######.##.###",
"#.###.##.######.##.###",
"#.....##....##....##..#",
"#####.##### ## #####.#",
"    #.##### GG#####.# ",
"#####.##### ## #####.#",
"#.....##....##....##..#",
"#.###.##.######.##.###",
"#.###.##.######.##.###",
"#....................#",
"#.###.###.##.###.###.#",
"#o###.###.##.###.###o#",
"#.###.###.##.###.###.#",
"#.........##.........#",
"#####################",
]
ORIGINAL_MAP = [row[:MAZE_COLS].ljust(MAZE_COLS) for row in MAP_STR]

# ---------- Utilities ----------
def wrap_text(text, font, max_width):
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        test = cur + (" " if cur else "") + w
        if font.size(test)[0] <= max_width:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def bfs(start, targets, is_wall_fn, in_bounds_fn):
    q = deque([start]); dist = {start:0}
    while q:
        cur = q.popleft()
        if cur in targets: break
        x,y = cur
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx,ny = x+dx,y+dy
            if not in_bounds_fn(nx,ny): continue
            if is_wall_fn(nx,ny): continue
            if (nx,ny) not in dist:
                dist[(nx,ny)] = dist[cur] + 1
                q.append((nx,ny))
    return dist

def choose_bfs_direction(cur_tile, target_tile, is_wall_fn, in_bounds_fn, forbidden_reverse=None):
    x,y = cur_tile
    options=[]
    for dx,dy,dirname in [(1,0,"R"),(-1,0,"L"),(0,1,"D"),(0,-1,"U")]:
        nx,ny = x+dx,y+dy
        if not in_bounds_fn(nx,ny): continue
        if is_wall_fn(nx,ny): continue
        options.append(((nx,ny),(dx,dy),dirname))
    if not options: return (0,0), None
    dist_map = bfs(cur_tile, {target_tile}, is_wall_fn, in_bounds_fn)
    best=None; best_d=None
    for (nx,ny),(dx,dy),dirname in options:
        if forbidden_reverse and dirname==forbidden_reverse: continue
        d = dist_map.get((nx,ny), None)
        if d is None: d = float('inf')
        if best is None or d < best_d:
            best = (dx,dy); best_d = d
    if best is None:
        (nx,ny),(dx,dy),dirname = random.choice(options)
        return (dx,dy), dirname
    for (nx,ny),(dx,dy),dirname in options:
        if (dx,dy) == best:
            return best, dirname
    return best, None

# ---------- Game Core ----------
class Game:
    def __init__(self, screen_w=SCREEN_W, screen_h=SCREEN_H):
        pygame.init()
        self.screen_w = screen_w; self.screen_h = screen_h
        self.screen = pygame.display.set_mode((self.screen_w, self.screen_h))
        pygame.display.set_caption("Pac-Man Remix — Strategic Traps")
        self.clock = pygame.time.Clock()

        # adaptive sizes
        target_maze_w = int(self.screen_w * 0.64)
        tile_candidate = max(16, target_maze_w // MAZE_COLS)
        target_maze_h = int(self.screen_h * 0.66)
        tile_candidate = min(tile_candidate, max(14, target_maze_h // MAZE_ROWS))
        self.TILE = tile_candidate
        self.TOP_BAR = max(64, int(self.screen_h * 0.064))
        self.MAZE_W = self.TILE * MAZE_COLS
        self.MAZE_H = self.TILE * MAZE_ROWS
        self.MAZE_X = (self.screen_w - self.MAZE_W)//2
        self.MAZE_Y = self.TOP_BAR

        # fonts
        preferred = ["Orbitron","Bahnschrift","Segoe UI","Fira Code","Consolas","Arial"]
        chosen = None
        for p in preferred:
            f = pygame.font.match_font(p)
            if f: chosen = f; break
        base = self.screen_w
        self.font_large = pygame.font.Font(chosen, max(28, base//28)) if chosen else pygame.font.SysFont("Arial", max(28, base//28))
        self.font_big = pygame.font.Font(chosen, max(18, base//44)) if chosen else pygame.font.SysFont("Arial", max(18, base//44))
        self.font_main = pygame.font.Font(chosen, max(14, base//60)) if chosen else pygame.font.SysFont("Arial", max(14, base//60))
        self.font_small = pygame.font.Font(chosen, max(12, base//80)) if chosen else pygame.font.SysFont("Arial", max(12, base//80))

        # state
        self.map = [list(r) for r in ORIGINAL_MAP]
        self.pellets = set(); self.energizers = set(); self.powerups_on_map = {}
        self.player = None; self.ghosts = []
        self.level = 1; self.difficulty = None; self.total_pellets = 0

        # achievements
        self.achievements_unlocked = set()
        self.achievement_msg = None; self.achievement_timer = 0.0; self.achievement_popup_total=3.0; self.achievement_popup_elapsed=0.0
        self.badge_pulse = {}
        self.badge_particles = []

        # traps system (strategic)
        # traps: list of dicts {'tile': (x,y), 'timer': float, 'visible': bool, 'triggered': bool, 'blocked_timer': float}
        self.traps = []
        self.trap_spawn_cooldown = 0.0
        self.shadow_ghosts = []  # list of dicts {'tile':(x,y), 'timer':float}
        self.trap_hints = []     # visual hint particles

        # menu visuals
        self.title_phase = 0.0
        self.glints = [{'x': random.random(), 'y': random.random(), 'speed': random.uniform(0.06,0.16), 'phase': random.random()*2*math.pi} for _ in range(6)]

        # load badges
        self.load_badges()
        self.init_game(hard_reset=True)

    def tile_to_pixel_center(self, tx, ty):
        px = self.MAZE_X + tx*self.TILE + self.TILE//2
        py = self.MAZE_Y + ty*self.TILE + self.TILE//2
        return px, py

    def in_bounds(self, tx, ty):
        return 0 <= tx < MAZE_COLS and 0 <= ty < MAZE_ROWS

    def is_wall_tile(self, tx, ty):
        # a trap may temporarily block a tile; treat it as wall while blocked
        if not self.in_bounds(tx,ty): return True
        for trap in self.traps:
            if trap.get('triggered') and trap.get('blocked_timer', 0) > 0 and trap['tile'] == (tx,ty):
                return True
        return self.map[ty][tx] == '#'

    # persistence for badges
    def load_badges(self):
        try:
            import os
            if os.path.exists(BADGE_SAVE_FILE):
                with open(BADGE_SAVE_FILE, 'r') as f:
                    data = json.load(f)
                if isinstance(data, list): self.achievements_unlocked = set(data)
        except:
            self.achievements_unlocked = set()

    def save_badges(self):
        try:
            with open(BADGE_SAVE_FILE, 'w') as f:
                json.dump(list(self.achievements_unlocked), f)
        except: pass

    def init_game(self, hard_reset=False):
        self.map = [list(r) for r in ORIGINAL_MAP]
        self.pellets.clear(); self.energizers.clear(); self.powerups_on_map.clear()
        self.traps.clear(); self.shadow_ghosts.clear(); self.trap_hints.clear()
        player_tile = None; ghost_pos=[]
        for y in range(MAZE_ROWS):
            for x in range(MAZE_COLS):
                c = self.map[y][x]
                if c == '.': self.pellets.add((x,y))
                elif c == 'o': self.energizers.add((x,y))
                elif c == 'P':
                    player_tile = (x,y); self.map[y][x] = ' '
                elif c == 'G':
                    ghost_pos.append((x,y)); self.map[y][x] = ' '
        if not player_tile: player_tile = (MAZE_COLS//2, MAZE_ROWS-3)
        if hard_reset or (self.player is None):
            self.player = Player(player_tile, self)
        else:
            self.player.tile = player_tile; self.player.target_tile = player_tile
            self.player.pos = pygame.math.Vector2(self.tile_to_pixel_center(*player_tile))
            self.player.direction = (1,0); self.player.desired_direction = (0,0)

        self.ghosts.clear()
        base_count = 2 if self.difficulty == "Easy" else 3 if self.difficulty == "Moderate" else 4
        ghost_count = min(4, base_count + (self.level-1)//2)
        for i in range(ghost_count):
            pos = ghost_pos[i] if i < len(ghost_pos) else (MAZE_COLS//2, MAZE_ROWS//2)
            g = Ghost(pos, GHOST_COLORS[i % len(GHOST_COLORS)], self)
            if self.difficulty == "Easy": g.base_speed = max(1.4, self.TILE * 0.05)
            elif self.difficulty == "Moderate": g.base_speed = max(1.8, self.TILE * 0.065)
            else: g.base_speed = max(2.2, self.TILE * 0.078)
            g.speed = g.base_speed
            self.ghosts.append(g)

        self.total_pellets = len(self.pellets) + len(self.energizers)
        if self.level == 1:
            special=[]
            for y in range(2, MAZE_ROWS-2):
                for x in range(2, MAZE_COLS-2):
                    if (x,y) in self.pellets and random.random() < 0.02: special.append((x,y))
            types=['speed','freeze','invincible']
            for i,pos in enumerate(special):
                if pos in self.pellets: self.pellets.remove(pos)
                self.powerups_on_map[pos] = types[i % len(types)]

        self.achievement_msg = None; self.achievement_timer = 0.0; self.achievement_popup_elapsed = 0.0
        self.earned_current_run = set()
        self.trap_spawn_cooldown = 6.0  # start cooldown before first trap

    # ---------- UI drawing ----------
    def draw_gradient_bg(self, surf):
        for i in range(self.screen_h):
            t = i / self.screen_h
            r = int(DEEP_BG_A[0]*(1-t) + DEEP_BG_B[0]*t)
            g = int(DEEP_BG_A[1]*(1-t) + DEEP_BG_B[1]*t)
            b = int(DEEP_BG_A[2]*(1-t) + DEEP_BG_B[2]*t)
            pygame.draw.line(surf, (r,g,b), (0,i), (self.screen_w,i))

    def draw_button(self, surf, rect, text, active=False):
        base = (18,18,26)
        pygame.draw.rect(surf, base, rect, border_radius=max(6, rect.height//6))
        accent_col = ACCENT if active else MUTED_DARK
        border_w = 3 if active else 1
        pygame.draw.rect(surf, accent_col, rect, border_w, border_radius=max(6, rect.height//6))
        txt = self.font_big.render(text, True, WHITE if active else MUTED)
        surf.blit(txt, (rect.x + (rect.width - txt.get_width())//2, rect.y + (rect.height - txt.get_height())//2))

    def show_start_menu(self):
        options = ["Start Game", "Difficulty", "Story & Controls", "Quit"]
        sel = 0
        card_w = int(self.screen_w * 0.84); card_h = int(self.screen_h * 0.34)
        card_x = (self.screen_w - card_w)//2; card_y = max(36, int(self.screen_h*0.06))
        btn_w = int(self.screen_w * 0.46); btn_h = max(44, int(self.screen_h * 0.08))
        btn_x = (self.screen_w - btn_w)//2
        btn_start_y = card_y + card_h + int(self.screen_h * 0.04)
        emblem_center_rel = (64, int(card_h*0.18))
        self.title_phase = 0.0

        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.title_phase += dt * 1.8
            for g in self.glints:
                g['x'] += dt * g['speed']; g['phase'] += dt * 2.2
                if g['x'] > 1.2: g['x'] = -0.2; g['y'] = random.uniform(0.0,1.0)

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_DOWN: sel = (sel + 1) % len(options)
                    if ev.key == pygame.K_UP: sel = (sel - 1) % len(options)
                    if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        choice = options[sel]
                        if choice == "Start Game": return True
                        if choice == "Difficulty":
                            if self.show_difficulty_menu(): return True
                        if choice == "Story & Controls": self.show_story_controls()
                        if choice == "Quit": pygame.quit(); sys.exit()
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    mp = ev.pos
                    for i,opt in enumerate(options):
                        r = pygame.Rect(btn_x, btn_start_y + i*(btn_h + int(self.screen_h*0.02)), btn_w, btn_h)
                        if r.collidepoint(mp):
                            choice = options[i]
                            if choice == "Start Game": return True
                            if choice == "Difficulty":
                                if self.show_difficulty_menu(): return True
                            if choice == "Story & Controls": self.show_story_controls()
                            if choice == "Quit": pygame.quit(); sys.exit()

            # render
            self.draw_gradient_bg(self.screen)
            shadow = pygame.Surface((card_w+16, card_h+16), pygame.SRCALPHA)
            pygame.draw.rect(shadow, (0,0,0,140), (0,0,card_w+16,card_h+16), border_radius=20)
            self.screen.blit(shadow, (card_x-8, card_y-8))
            panel = pygame.Surface((card_w,card_h), pygame.SRCALPHA)
            pygame.draw.rect(panel, (12,12,20,240), (0,0,card_w,card_h), border_radius=16)
            pygame.draw.rect(panel, ACCENT, (20,18,8,card_h-36), border_radius=6)

            title_x = emblem_center_rel[0] + 68
            title = self.font_large.render("PAC-MAN: REMIX", True, ACCENT)
            panel.blit(title, (title_x, 18))
            suby = 18 + title.get_height() + 8
            subtitle = self.font_main.render("A futuristic remix — neon, power-ups & badges", True, MUTED)
            panel.blit(subtitle, (title_x, suby))
            feat = self.font_small.render("Power-ups: Speed • Freeze • Invincibility    Badges: Earn & Keep", True, (200,200,210))
            panel.blit(feat, (title_x, suby + subtitle.get_height() + 8))

            emblem_center = (emblem_center_rel[0], emblem_center_rel[1])
            self.draw_polished_emblem(panel, emblem_center, int(card_h * 0.22))

            px = card_w - 320; py = 18 + 6
            icon_size = max(28, int(card_h * 0.14))
            spacing_y = icon_size + 16
            self.draw_powerup_row(panel, (px, py), icon_size, "Speed", "Burst of movement — temporary speed boost. Use it to quickly escape tight spots and cross long corridors.")
            self.draw_powerup_row(panel, (px, py + spacing_y), icon_size, "Freeze", "Freeze ghosts briefly to reposition. Great for strategic regrouping when surrounded.")
            self.draw_powerup_row(panel, (px, py + 2*spacing_y), icon_size, "Invincible", "Become briefly immune to ghosts — collect pellets aggressively while safe.")

            self.screen.blit(panel, (card_x, card_y))

            for i,opt in enumerate(options):
                r = pygame.Rect(btn_x, btn_start_y + i*(btn_h + int(self.screen_h*0.02)), btn_w, btn_h)
                hover = r.collidepoint(pygame.mouse.get_pos()); active = (i==sel or hover)
                self.draw_button(self.screen, r, opt, active=active)

            footer = self.font_small.render("Use arrow keys or mouse. Press ENTER / Click to select", True, MUTED)
            self.screen.blit(footer, ((self.screen_w - footer.get_width())//2, btn_start_y + len(options)*(btn_h + int(self.screen_h*0.02)) + 8))

            pygame.display.flip()

    def draw_polished_emblem(self, surf, center, size):
        cx,cy = center
        r = max(20, size//2)
        pygame.draw.circle(surf, (8,8,12), (cx+6, cy+6), r+10)
        halo = pygame.Surface((r*6, r*6), pygame.SRCALPHA)
        for i in range(3):
            alpha = 60 - i*18
            pygame.draw.circle(halo, (ACCENT[0],ACCENT[1],ACCENT[2],alpha), (r*3, r*3), r+6+i*4)
        surf.blit(halo, (cx - r*3 + 2, cy - r*3 + 2))
        pygame.draw.circle(surf, NEON_YELLOW, (cx, cy), r)
        pygame.draw.circle(surf, (255,255,255,80), (cx - r//3, cy - r//3), max(4, r//4))
        t = time.time()
        angle = (t * 60) % 360
        a1 = math.radians(angle)
        rx = cx + int(math.cos(a1) * (r + 10))
        ry = cy + int(math.sin(a1) * (r + 10))
        pygame.draw.circle(surf, (ACCENT[0],ACCENT[1],ACCENT[2],120), (rx, ry), max(3, r//5))
        notch = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pts = [(r, r), (r + int(r*0.85), r - int(r*0.65)), (r + int(r*0.85), r + int(r*0.65))]
        pygame.draw.polygon(notch, (12,12,20), pts)
        surf.blit(notch, (cx - r, cy - r))

    def draw_powerup_row(self, surf, pos, size, title, desc):
        x,y = pos; s=size
        row_w = 260; row_h = s + 12
        rect = pygame.Rect(x, y, row_w, row_h)
        pygame.draw.rect(surf, (18,18,26), rect, border_radius=12)
        center = (x + s//2 + 8, y + s//2 + 6)
        pygame.draw.circle(surf, (30,30,36), center, s//2 + 5)
        if title == "Speed":
            pts = [
                (center[0]-s//6, center[1]-s//3),
                (center[0]+s//8, center[1]-s//3),
                (center[0]-s//12, center[1]),
                (center[0]+s//8, center[1]),
                (center[0]-s//6, center[1]+s//3),
            ]
            pygame.draw.polygon(surf, (255,225,120), pts)
        elif title == "Freeze":
            for a in range(6):
                ang = a * math.pi/3
                x1 = center[0] + int(math.cos(ang) * (s*0.26))
                y1 = center[1] + int(math.sin(ang) * (s*0.26))
                x2 = center[0] + int(math.cos(ang) * (s*0.44))
                y2 = center[1] + int(math.sin(ang) * (s*0.44))
                pygame.draw.line(surf, (180,220,255), (x1,y1), (x2,y2), 3)
        else:
            pts = [
                (center[0], center[1]-s//3),
                (center[0]+s//3, center[1]-s//6),
                (center[0], center[1]+s//3),
                (center[0]-s//3, center[1]-s//6)
            ]
            pygame.draw.polygon(surf, (160,200,255), pts)
        t_s = self.font_small.render(title, True, WHITE)
        surf.blit(t_s, (x + s + 18, y + 6))
        lines = wrap_text(desc, self.font_small, row_w - (s + 28))
        y_off = y + 6 + t_s.get_height()
        for ln in lines[:3]:
            surf.blit(self.font_small.render(ln, True, MUTED), (x + s + 18, y_off))
            y_off += self.font_small.get_height() + 2

    def show_difficulty_menu(self):
        options = ["Easy", "Moderate", "Hard", "Back"]
        sel = 0
        card_w = int(self.screen_w * 0.64); card_h = int(self.screen_h * 0.26)
        cx = (self.screen_w - card_w)//2; cy = max(36, int(self.screen_h*0.06))
        btn_w = int(self.screen_w * 0.14); btn_h = int(self.screen_h * 0.08); gap = int(self.screen_w * 0.03)
        while True:
            self.draw_gradient_bg(self.screen)
            panel = pygame.Surface((card_w,card_h), pygame.SRCALPHA)
            pygame.draw.rect(panel, (8,8,18,230), (0,0,card_w,card_h), border_radius=12)
            title = self.font_large.render("Select Difficulty", True, ACCENT)
            subtitle = self.font_main.render("Choose how aggressive the ghosts will be.", True, MUTED)
            panel.blit(title, (28, 20)); panel.blit(subtitle, (28, 20 + title.get_height() + 8))
            self.screen.blit(panel, (cx,cy))
            total_w = btn_w*3 + gap*2; start_x = (self.screen_w - total_w)//2
            y = cy + card_h + int(self.screen_h*0.03)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_RIGHT: sel = (sel+1)%len(options)
                    if ev.key == pygame.K_LEFT: sel = (sel-1)%len(options)
                    if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        choice = options[sel]
                        if choice == "Back": return False
                        self.difficulty = choice; return True
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    mp = ev.pos
                    for i,opt in enumerate(options):
                        if opt == "Back":
                            r = pygame.Rect((self.screen_w - btn_w)//2, y + (btn_h + int(self.screen_h*0.02))*3, btn_w, btn_h)
                        else:
                            r = pygame.Rect(start_x + i*(btn_w + gap), y, btn_w, btn_h)
                        if r.collidepoint(mp):
                            if opt == "Back": return False
                            self.difficulty = opt; return True
            for i,opt in enumerate(options):
                if opt == "Back":
                    r = pygame.Rect((self.screen_w - btn_w)//2, y + (btn_h + int(self.screen_h*0.02))*3, btn_w, btn_h)
                else:
                    r = pygame.Rect(start_x + i*(btn_w + gap), y, btn_w, btn_h)
                hover = r.collidepoint(pygame.mouse.get_pos()); active = (i==sel or hover)
                self.draw_button(self.screen, r, opt, active=active)
            pygame.display.flip(); self.clock.tick(FPS)

    def show_story_controls(self):
        # EXTENDED EPIC SCI-FI ADVENTURE story — multiple pages (extended)
        pages = [
            ("Prologue — The Dimming", [
                "Pac-World was once a shining orbit of neon and rhythm, powered by luminous Pellets",
                "That light sustained billions of tiny processes, joys, and the heartbeat of the Grid.",
                "But a slow corruption began — a ghostly pattern of interference, eating at the glow.",
                "When the Core's pulse faltered, data-ghosts slipped through the seams and stole the Pellets.",
            ]),
            ("The Phantom Guild", [
                "A rogue collective of sentient fragments — the Phantom Guild — took sanctuary in the maze.",
                "Their leader, Null-Vector, is rewriting corridors and spawning spectral guardians.",
                "The Guild's corruption mutates ghosts into cunning hunters of the Core light.",
                "Pac must descend into the data-maze and restore the stolen pulses — or Pac-World dims.",
            ]),
            ("Your Call to Action", [
                "You are Pac, a neon sentinel built of determination and appetite for light.",
                "Collect every pellet, purge the corruption and reclaim the lost energizers of the Core.",
                "Power-ups (Speed, Freeze, Invincibility) are rare system patches — use them wisely.",
                "Badges are earned when the Core senses true mastery. They remember your victories.",
            ]),
            ("Mechanics & Strategy", [
                "Arrows or WASD move Pac. Timing and micro-turns save lives.",
                "Energizers turn ghosts vulnerable — capitalize quickly to score big.",
                "Freeze pauses ghost movement briefly — excellent for clutch escapes or reroutes.",
                "Speed lets you dash across long corridors and reach power-ups first.",
            ]),
            ("Epilogue — Voices of the Grid", [
                "Each pellet you reclaim adds a line back to the Core's song — feel it pulse.",
                "As you master the maze you restore color and memory to Pac-World.",
                "Legends are forged in repeated runs: Rookie, Diamond, Master, Conqueror.",
                "Do you have the reflexes, patience, and strategy to bring dawn back to the Grid?"
            ])
        ]
        idx = 0
        card_w = int(self.screen_w * 0.86); card_h = int(self.screen_h * 0.72)
        cx = (self.screen_w - card_w)//2; cy = max(30, int(self.screen_h * 0.05))
        while True:
            self.draw_gradient_bg(self.screen)
            panel = pygame.Surface((card_w,card_h), pygame.SRCALPHA)
            pygame.draw.rect(panel, (6,6,14,240), (0,0,card_w,card_h), border_radius=14)
            title_s = self.font_large.render(pages[idx][0], True, ACCENT)
            panel.blit(title_s, (28,28))
            y_pos = 28 + title_s.get_height() + 14
            for line in pages[idx][1]:
                txt = self.font_main.render(line, True, WHITE)
                panel.blit(txt, (34, y_pos)); y_pos += self.font_main.get_height() + 10
            footer = self.font_small.render("Press ← / → to navigate pages, ENTER to continue to game", True, MUTED)
            panel.blit(footer, (34, card_h - 40))
            self.screen.blit(panel, (cx,cy))
            for i in range(len(pages)):
                dot_color = ACCENT if i==idx else (70,70,90)
                pygame.draw.circle(self.screen, dot_color, (self.screen_w//2 - 40 + i*24, cy + card_h + 24), 6)
            pygame.display.flip()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_RIGHT: idx = (idx+1)%len(pages)
                    if ev.key == pygame.K_LEFT: idx = (idx-1)%len(pages)
                    if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        return
                    if ev.key == pygame.K_ESCAPE:
                        return
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    idx = (idx+1)%len(pages)
            self.clock.tick(FPS)

    # ---------- traps system ----------
    def spawn_shadow_ghost(self, tile):
        # Spawn a short-lived "shadow ghost" at given tile that will try to chase the player
        self.shadow_ghosts.append({'tile': tuple(tile), 'timer': random.uniform(5.0, 9.0)})

    def handle_traps(self, dt):
        """
        Strategic trap logic:
         - Only starts after reaching Rookie (score >= Rookie threshold)
         - Spawns traps at choke points / corridors (2-3 open neighbors)
         - Traps may be faintly visible (subtle hints). When triggered:
             * slows player (slow_timer), *may* block tile for a few seconds, *may* spawn shadow ghost
         - Traps expire automatically
        """
        # start only after rookie
        rookie_threshold = dict(ACHIEVEMENTS).get("Rookie", 100)
        if self.player.score < rookie_threshold:
            return

        # cooldown decreases as score increases slightly (more traps over time)
        self.trap_spawn_cooldown -= dt
        # compute max traps based on progression
        max_traps = min(6, 1 + (self.player.score - rookie_threshold)//250)

        if self.trap_spawn_cooldown <= 0 and len(self.traps) < max_traps:
            # gather candidate tiles that are not pellets/energizers/walls and form choke points
            candidates = []
            for y in range(2, MAZE_ROWS-2):
                for x in range(2, MAZE_COLS-2):
                    t = (x,y)
                    if t in self.pellets or t in self.energizers or t in self.powerups_on_map:
                        continue
                    if self.map[y][x] == '#': continue
                    # prefer tiles close to corridors: count accessible neighbors
                    open_neighbors = 0
                    for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                        nx,ny = x+dx,y+dy
                        if not self.in_bounds(nx,ny): continue
                        if self.map[ny][nx] == '#': continue
                        open_neighbors += 1
                    # chokepoint or corridor intersection (2 or 3 open neighbors) is strategic
                    if 2 <= open_neighbors <= 3:
                        # avoid spawning right on player's tile or ghost tiles
                        if (x,y) == self.player.tile: continue
                        if any(g.tile == (x,y) for g in self.ghosts): continue
                        # proximity weighting: prefer tiles nearer center-ish so players traverse them
                        center_dist = abs(x - MAZE_COLS//2) + abs(y - MAZE_ROWS//2)
                        score_weight = max(0.1, 1.0 - center_dist/40.0)
                        candidates.append(((x,y), score_weight))
            if candidates:
                # pick candidate with weighted randomness
                tiles, weights = zip(*candidates)
                chosen = random.choices(tiles, weights=weights, k=1)[0]
                tx,ty = chosen
                # avoid duplicates
                if not any(t['tile']==(tx,ty) for t in self.traps):
                    trap = {
                        'tile': (tx,ty),
                        'timer': random.uniform(14.0, 26.0),
                        'visible': random.random() < 0.28,  # some traps show subtle hint
                        'triggered': False,
                        'blocked_timer': 0.0
                    }
                    self.traps.append(trap)
                    # hint particle for subtle cue (visual)
                    self.trap_hints.append({'tile':(tx,ty), 'phase': random.random(), 'life': random.uniform(6.0, 18.0)})
                # set next cooldown smaller as score grows
                self.trap_spawn_cooldown = max(6.0, 12.0 - (self.player.score - rookie_threshold)/250.0)

        # update trap timers and remove expired ones
        for trap in list(self.traps):
            if trap.get('triggered'):
                # when triggered, maintain blocked_timer
                if trap.get('blocked_timer', 0) > 0:
                    trap['blocked_timer'] -= dt
                else:
                    # after blocking finished, remove trap
                    trap['timer'] -= dt
                    if trap['timer'] <= 0:
                        try: self.traps.remove(trap)
                        except: pass
            else:
                trap['timer'] -= dt
                if trap['timer'] <= 0:
                    try: self.traps.remove(trap)
                    except: pass

        # update hints life
        for h in list(self.trap_hints):
            h['life'] -= dt
            if h['life'] <= 0:
                try: self.trap_hints.remove(h)
                except: pass

        # check player stepping on traps
        for trap in self.traps:
            if trap['triggered']: continue
            if self.player.tile == trap['tile']:
                trap['triggered'] = True
                trap['visible'] = True
                # slow down player moderately
                self.player.slow_timer = max(self.player.slow_timer, 2.6)
                # block the tile briefly (makes path temporarily impassable)
                trap['blocked_timer'] = random.uniform(2.4, 4.2)
                # small chance spawn a shadow ghost
                if random.random() < 0.55:
                    self.spawn_shadow_ghost(trap['tile'])
                    # sometimes spawn additional small particle hint
                    self.trap_hints.append({'tile':trap['tile'], 'phase':0.0, 'life':2.0})
                # reduce trap timer so it will be cleaned later
                trap['timer'] = 6.0

        # update shadow ghosts: simple tile-based pursuit of player for a short time
        for sg in list(self.shadow_ghosts):
            sg['timer'] -= dt
            if sg['timer'] <= 0:
                try: self.shadow_ghosts.remove(sg)
                except: pass
                continue
            # chase one tile per second roughly, but move more discretely using timer
            # compute simple path: step toward player tile if not wall
            sx,sy = sg['tile']
            px,py = self.player.tile
            best = None; best_dist = None
            for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                nx,ny = sx+dx, sy+dy
                if not self.in_bounds(nx,ny): continue
                if self.is_wall_tile(nx,ny): continue
                d = abs(nx - px) + abs(ny - py)
                if best is None or d < best_dist:
                    best = (nx,ny); best_dist = d
            if best:
                sg['tile'] = best
                # if collides with player tile, apply effect and remove
                if sg['tile'] == self.player.tile:
                    self.player.slow_timer = max(self.player.slow_timer, 2.0)
                    try: self.shadow_ghosts.remove(sg)
                    except: pass

    # ---------- UI Top + Badge drawing & updates ----------
    def draw_ui_top(self):
        pygame.draw.rect(self.screen, (12,12,18), (0,0, self.screen_w, self.TOP_BAR))
        score_s = self.font_main.render(f"Score: {self.player.score}", True, WHITE)
        self.screen.blit(score_s, (12, 8))
        level_s = self.font_main.render(f"Level: {self.level}", True, MUTED)
        self.screen.blit(level_s, (12, 8 + score_s.get_height()))
        # Lives — nicer hearts spaced properly
        life_label_x = self.screen_w - 420
        self.screen.blit(self.font_main.render("Lives:", True, MUTED), (life_label_x-74, 12))
        heart_gap = int(self.TILE * 0.36)
        heart_size = int(self.TILE * 0.22)
        base_x = life_label_x + 4
        for i in range(self.player.lives):
            cx = base_x + i*(heart_size + heart_gap) + 12
            cy = 26
            self.draw_heart(self.screen, (cx+2, cy+2), heart_size, fill=(12,12,12), shadow=True)
            self.draw_heart(self.screen, (cx, cy), heart_size, fill=(255,80,100))
        # Buff timers (circular small)
        timer_x = self.screen_w - 240
        timers = []
        if self.player.speed_boost_timer > 0:
            timers.append(('Speed', self.player.speed_boost_timer, BUFF_DURATIONS['speed'], ACCENT))
        if self.player.invincible_timer > 0:
            timers.append(('Inv', self.player.invincible_timer, BUFF_DURATIONS['invincible'], ACCENT2))
        max_freeze = 0.0
        for g in self.ghosts:
            if g.frozen_timer > max_freeze: max_freeze = g.frozen_timer
        if max_freeze > 0:
            timers.append(('Frz', max_freeze, BUFF_DURATIONS['freeze'], NEON_BLUE))
        tx = timer_x
        for name,remaining,total,col in timers:
            pct = max(0.0, min(1.0, remaining/total if total>0 else 0))
            size = int(self.TOP_BAR * 0.6)
            cx = tx + size//2
            cy = int(self.TOP_BAR * 0.5)
            pygame.draw.circle(self.screen, (24,24,30), (cx,cy), size//2 + 4)
            pygame.draw.circle(self.screen, (18,18,24), (cx,cy), size//2)
            start_ang = -math.pi/2
            end_ang = start_ang + (2 * math.pi * pct)
            rect = pygame.Rect(cx - size//2, cy - size//2, size, size)
            thickness = max(4, size//8)
            try:
                pygame.draw.arc(self.screen, col, rect, start_ang, end_ang, thickness)
            except Exception:
                pass
            secs = str(int(math.ceil(remaining)))
            small = self.font_small.render(secs + "s", True, WHITE)
            self.screen.blit(small, (cx - small.get_width()//2, cy - small.get_height()//2))
            lbl = self.font_small.render(name, True, MUTED)
            self.screen.blit(lbl, (cx - lbl.get_width()//2, cy + size//2 - lbl.get_height()))
            tx += size + 12
        # BADGE DISPLAY (only badges earned this run) - compact and smaller than before
        earned_current = [name for name,_ in ACHIEVEMENTS if name in self.earned_current_run]
        if earned_current:
            med_w = int(max(20, min(36, self.screen_w * 0.025)))  # tiny top medallions
            padding = 24
            total_w = len(earned_current)*med_w + (len(earned_current)-1)*12
            bx = self.screen_w - padding - total_w
            by = self.TOP_BAR + 8
            for i,name in enumerate(earned_current):
                rx = bx + i*(med_w + 12) + med_w//2
                ry = by + med_w//2
                pulse_t = 0.0
                if name in self.badge_pulse:
                    st = self.badge_pulse[name]
                    pulse_t = st['t']
                    st['t'] += 1.0 / FPS
                    if st.get('spark_emit', False):
                        for _ in range(8):
                            ang = random.random() * math.pi*2
                            dist = random.uniform(med_w*0.4, med_w*0.9)
                            vx = math.cos(ang) * random.uniform(8,40)
                            vy = math.sin(ang) * random.uniform(8,40)
                            self.badge_particles.append({
                                'x': rx + math.cos(ang)*dist*0.3,
                                'y': ry + math.sin(ang)*dist*0.3,
                                'vx': vx, 'vy': vy,
                                'life': random.uniform(0.6,1.2),
                                'age': 0.0,
                                'col': (255, 240, 200) if name=="Conqueror" else (160,240,255) if name=="Diamond" else (200,255,190)
                            })
                        st['spark_emit'] = False
                    if st['t'] > 2.6:
                        del self.badge_pulse[name]
                self.draw_gem_medallion(self.screen, (rx, ry), med_w, name, pulse_t=pulse_t)
        # particles
        for p in list(self.badge_particles):
            p['age'] += 1.0 / FPS
            if p['age'] >= p['life']:
                self.badge_particles.remove(p); continue
            p['x'] += p['vx'] * (1.0 / FPS)
            p['y'] += p['vy'] * (1.0 / FPS)
            alpha = int(255 * max(0.0, 1.0 - (p['age']/p['life'])))
            s = max(2, int(4 * (1.0 - p['age']/p['life'])))
            surf = pygame.Surface((s*2, s*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (p['col'][0], p['col'][1], p['col'][2], alpha), (s, s), s)
            self.screen.blit(surf, (int(p['x']-s), int(p['y']-s)), special_flags=pygame.BLEND_ADD)
        if self.achievement_msg and self.achievement_timer > 0:
            elapsed = self.achievement_popup_elapsed; total = self.achievement_popup_total
            progress = min(1.0, elapsed/total) if total>0 else 1.0
            w = int(min(self.screen_w * 0.78, 640)); h = max(36, int(self.screen_h * 0.06))
            center_x = (self.screen_w - w)//2; target_y = 8
            slide_in_pct = 0.12; fade_out_pct = 0.28
            if progress < slide_in_pct:
                interp = progress / (slide_in_pct + 1e-9); y = int(-h + (target_y + h) * interp)
            else:
                y = target_y
            if progress > 1.0 - fade_out_pct:
                alpha = int(255 * max(0.0, (1.0 - progress) / fade_out_pct))
            else:
                alpha = 255
            surf = pygame.Surface((w,h), pygame.SRCALPHA)
            pygame.draw.rect(surf, (18,18,24,alpha), (0,0,w,h), border_radius=10)
            text_surf = self.font_main.render(self.achievement_msg, True, (255,230,160))
            surf.blit(text_surf, ((w - text_surf.get_width())//2, (h - text_surf.get_height())//2))
            self.screen.blit(surf, (center_x, y))

    def draw_heart(self, surf, center, size, fill=(255,100,100), shadow=False):
        cx,cy = center
        r = max(6, size//2)
        left = (cx - r//1.6, cy - r//3)
        right = (cx + r//1.6, cy - r//3)
        if shadow:
            pygame.draw.circle(surf, (0,0,0,120), (int(left[0]), int(left[1])), int(r*1.02))
            pygame.draw.circle(surf, (0,0,0,120), (int(right[0]), int(right[1])), int(r*1.02))
        pygame.draw.circle(surf, fill, left, r)
        pygame.draw.circle(surf, fill, right, r)
        tri_pts = [(cx - r*1.4, cy), (cx + r*1.4, cy), (cx, cy + r*1.6)]
        pygame.draw.polygon(surf, fill, tri_pts)
        pygame.draw.circle(surf, (255,255,255,70), (cx - r//3, cy - r//3), max(2, r//3))

    # ---------- Gem medallion rendering ----------
    def draw_gem_medallion(self, surf, center, diameter, name, pulse_t=0.0):
        cx,cy = center
        D = max(48, int(diameter * 0.75))
        r = D // 2
        if name == "Rookie":
            base_col = (140, 255, 200); accent_col = (70, 200, 120)
        elif name == "Diamond":
            base_col = (140, 230, 255); accent_col = (90, 190, 230)
        elif name == "Master":
            base_col = (240, 190, 255); accent_col = (200, 140, 220)
        else:
            base_col = (255, 210, 120); accent_col = (230, 180, 60)
        pulse = 1.0 + 0.02 * math.sin((pulse_t+time.time()*0.7) * 2.0) if pulse_t is not None else 1.0
        eff_r = int(r * pulse)
        aura = pygame.Surface((eff_r*6, eff_r*6), pygame.SRCALPHA)
        for i in range(3):
            alpha = int(70 * (1 - i*0.35))
            pygame.draw.circle(aura, (accent_col[0],accent_col[1],accent_col[2],alpha), (eff_r*3, eff_r*3), eff_r + 8 + i*6)
        surf.blit(aura, (cx - eff_r*3, cy - eff_r*3), special_flags=pygame.BLEND_PREMULTIPLIED)
        gem = pygame.Surface((eff_r*2+8, eff_r*2+8), pygame.SRCALPHA)
        center_offset = (eff_r+4, eff_r+4)
        pts = [
            (center_offset[0], center_offset[1]-int(eff_r*0.9)),
            (center_offset[0]+int(eff_r*0.6), center_offset[1]-int(eff_r*0.35)),
            (center_offset[0]+int(eff_r*0.45), center_offset[1]+int(eff_r*0.6)),
            (center_offset[0]-int(eff_r*0.45), center_offset[1]+int(eff_r*0.6)),
            (center_offset[0]-int(eff_r*0.6), center_offset[1]-int(eff_r*0.35))
        ]
        for layer in range(6):
            t = 1.0 - layer/6.0
            col = (
                int(base_col[0]*t + 24*(1-t)),
                int(base_col[1]*t + 24*(1-t)),
                int(base_col[2]*t + 24*(1-t)),
                int(230 * (0.9 - layer*0.08))
            )
            shrink = layer * 1.6
            inner_pts = [ (x + (x-center_offset[0])*shrink/eff_r, y + (y-center_offset[1])*shrink/eff_r) for x,y in pts]
            pygame.draw.polygon(gem, col, inner_pts)
        facet_cols = [(255,255,255,60), (255,255,255,30)]
        for i_fc in range(2):
            fpts = [
                (center_offset[0], center_offset[1]-int(eff_r*0.6) + i_fc*4),
                (center_offset[0]+int(eff_r*0.25), center_offset[1]-int(eff_r*0.2)),
                (center_offset[0], center_offset[1]+int(eff_r*0.05)),
                (center_offset[0]-int(eff_r*0.25), center_offset[1]-int(eff_r*0.2))
            ]
            pygame.draw.polygon(gem, facet_cols[i_fc], fpts)
        pygame.draw.polygon(gem, (0,0,0,40), pts, 2)
        surf.blit(gem, (cx - gem.get_width()//2, cy - gem.get_height()//2), special_flags=pygame.BLEND_PREMULTIPLIED)
        core_r = max(6, int(eff_r*0.22))
        pygame.draw.circle(surf, (255,255,255,30), (cx, cy + int(eff_r*0.18)), core_r)
        pygame.draw.circle(surf, (255,255,255,24), (cx, cy), eff_r, 2)

    # ---------- Maze drawing (include trap visuals + shadow ghosts) ----------
    def draw_maze(self):
        maze_bg = pygame.Rect(self.MAZE_X-6, self.MAZE_Y-6, self.MAZE_W+12, self.MAZE_H+12)
        pygame.draw.rect(self.screen, (12,12,20, ), maze_bg, border_radius=8)
        for y in range(MAZE_ROWS):
            for x in range(MAZE_COLS):
                c = self.map[y][x]
                px = self.MAZE_X + x*self.TILE
                py = self.MAZE_Y + y*self.TILE
                if c == '#':
                    pad = max(2, int(self.TILE * 0.14))
                    outer = pygame.Rect(px - pad, py - pad, self.TILE + pad*2, self.TILE + pad*2)
                    pygame.draw.rect(self.screen, WALL, outer, border_radius=max(3, pad))
                    inner = pygame.Rect(px - pad + 3, py - pad + 3, self.TILE + (pad*2) - 6, self.TILE + (pad*2) - 6)
                    pygame.draw.rect(self.screen, WALL_INNER, inner, border_radius=max(2, pad-1))
                if (x,y) in self.pellets:
                    cx,cy = self.tile_to_pixel_center(x,y)
                    pygame.draw.circle(self.screen, PELLET_COLOR, (cx,cy), max(2, self.TILE//8))
                if (x,y) in self.energizers:
                    cx,cy = self.tile_to_pixel_center(x,y)
                    pygame.draw.circle(self.screen, ENERGIZER_COLOR, (cx,cy), max(4, self.TILE//4))
                if (x,y) in self.powerups_on_map:
                    cx,cy = self.tile_to_pixel_center(x,y)
                    typ = self.powerups_on_map[(x,y)]
                    col = (100,255,100) if typ=='speed' else (180,180,255) if typ=='invincible' else (255,200,180)
                    pygame.draw.rect(self.screen, col, (cx-6, cy-6, 12, 12))
                # --- trap visuals (subtle) ---
                for trap in self.traps:
                    tx,ty = trap['tile']
                    if (x,y) == (tx,ty):
                        cx,cy = self.tile_to_pixel_center(x,y)
                        if trap.get('triggered'):
                            # show a brief spike ring if triggered
                            bt = trap.get('blocked_timer', 0)
                            if bt > 0:
                                # red ring while blocked
                                pygame.draw.circle(self.screen, (255,80,80), (cx,cy), max(6, self.TILE//3), 2)
                        else:
                            # subtle hint pulse if visible
                            if trap.get('visible'):
                                pulse = 40 + int(20 * math.sin(time.time()*4 + (tx+ty)))
                                surf = pygame.Surface((self.TILE, self.TILE), pygame.SRCALPHA)
                                pygame.draw.circle(surf, (255, 90, 90, pulse), (self.TILE//2, self.TILE//2), max(3, self.TILE//4))
                                self.screen.blit(surf, (cx - self.TILE//2, cy - self.TILE//2), special_flags=pygame.BLEND_PREMULTIPLIED)
                            else:
                                # sometimes a very faint spark (rare) to give an observant player a tiny clue
                                if random.random() < 0.007:
                                    cx,cy = self.tile_to_pixel_center(x,y)
                                    surf = pygame.Surface((6,6), pygame.SRCALPHA)
                                    pygame.draw.circle(surf, (255, 170, 170, 30), (3,3), 3)
                                    self.screen.blit(surf, (cx-3,cy-3), special_flags=pygame.BLEND_PREMULTIPLIED)

                # shadow ghost visuals
                for sg in self.shadow_ghosts:
                    if (x,y) == tuple(sg['tile']):
                        cx,cy = self.tile_to_pixel_center(x,y)
                        pulse = 90 + int(40 * math.sin(time.time() * 7 + (x+y)))
                        surf = pygame.Surface((self.TILE, self.TILE), pygame.SRCALPHA)
                        pygame.draw.circle(surf, (140,160,255,pulse), (self.TILE//2, self.TILE//2), self.TILE//3, 2)
                        self.screen.blit(surf, (cx - self.TILE//2, cy - self.TILE//2), special_flags=pygame.BLEND_ADD)

    # ---------- Core interactions ----------
    def unlock_achievement(self, name):
        if name not in self.achievements_unlocked:
            self.achievements_unlocked.add(name)
            self.save_badges()
        if name not in self.earned_current_run:
            self.earned_current_run.add(name)
            self.badge_pulse[name] = {'t':0.0, 'spark_emit': True}
            self.achievement_msg = f"Achievement Unlocked: {name}"
            self.achievement_timer = self.achievement_popup_total
            self.achievement_popup_elapsed = 0.0

    def consume_pellet_at(self, tile):
        if tile in self.pellets:
            self.pellets.remove(tile); self.player.score += 10
            for name,thr in ACHIEVEMENTS:
                if self.player.score >= thr and name not in self.earned_current_run:
                    self.unlock_achievement(name)
            return "pellet"
        if tile in self.energizers:
            self.energizers.remove(tile); self.player.score += 50
            for g in self.ghosts:
                g.state = "frightened"; g.frightened_timer = BUFF_DURATIONS['speed']
            for name,thr in ACHIEVEMENTS:
                if self.player.score >= thr and name not in self.earned_current_run:
                    self.unlock_achievement(name)
            return "energizer"
        if tile in self.powerups_on_map:
            typ = self.powerups_on_map.pop(tile); self.spawn_powerup_effect(typ)
            self.player.score += 100
            for name,thr in ACHIEVEMENTS:
                if self.player.score >= thr and name not in self.earned_current_run:
                    self.unlock_achievement(name)
            return "powerup"
        return None

    def spawn_powerup_effect(self, power_type):
        if power_type == 'speed':
            self.player.speed_boost_timer = BUFF_DURATIONS['speed']
        elif power_type == 'freeze':
            for g in self.ghosts: g.frozen_timer = BUFF_DURATIONS['freeze']; g.state = "frozen"
        elif power_type == 'invincible':
            self.player.invincible_timer = BUFF_DURATIONS['invincible']

    def check_collisions(self):
        for g in self.ghosts:
            if g.respawn_timer > 0 or g.state == "eaten" or g.state == "frozen": continue
            dist = (g.pos - self.player.pos).length()
            if dist < self.player.radius + g.radius - 6:
                if self.player.invincible_timer > 0: continue
                if g.state == "frightened":
                    g.state = "eaten"; g.respawn_timer = 4.0; g.frightened_timer = 0
                    g.tile = g.start_tile; g.target_tile = g.start_tile; g.pos = pygame.math.Vector2(self.tile_to_pixel_center(*g.start_tile))
                    self.player.score += 200
                else:
                    if self.player.invincible_timer <= 0:
                        self.player.lives -= 1
                        self.player.tile = (MAZE_COLS//2, MAZE_ROWS-3)
                        self.player.target_tile = self.player.tile
                        self.player.pos = pygame.math.Vector2(self.tile_to_pixel_center(*self.player.tile))
                        self.player.direction = (1,0); self.player.desired_direction = (0,0)
                        for g2 in self.ghosts:
                            g2.tile = g2.start_tile; g2.target_tile = g2.start_tile; g2.pos = pygame.math.Vector2(self.tile_to_pixel_center(*g2.start_tile))
                            g2.state = "scatter"; g2.frightened_timer = 0.0; g2.respawn_timer = 0.0
                        if self.player.lives <= 0: self.game_over_screen()
        # check shadow ghosts hits
        for sg in list(self.shadow_ghosts):
            if tuple(self.player.tile) == tuple(sg['tile']):
                self.player.slow_timer = max(self.player.slow_timer, 2.0)
                try: self.shadow_ghosts.remove(sg)
                except: pass

        if self.player.at_center():
            self.consume_pellet_at(self.player.tile)
            if len(self.pellets) + len(self.energizers) == 0:
                self.level += 1; self.init_game(hard_reset=False)

    # ---------- Game over screen (kept compact) ----------
    def game_over_screen(self):
        while True:
            self.draw_gradient_bg(self.screen)
            card_w = int(self.screen_w * 0.94)
            card_h = int(self.screen_h * 0.78)
            cx = (self.screen_w - card_w)//2
            cy = max(24, int(self.screen_h * 0.04))
            panel = pygame.Surface((card_w,card_h), pygame.SRCALPHA)
            shadow = pygame.Surface((card_w+12, card_h+12), pygame.SRCALPHA)
            pygame.draw.rect(shadow, (0,0,0,140), (0,0,card_w+12,card_h+12), border_radius=18)
            self.screen.blit(shadow, (cx-6, cy-6))
            pygame.draw.rect(panel, (6,6,14,250), (0,0,card_w,card_h), border_radius=16)
            title = self.font_large.render("GAME OVER", True, (240,90,90))
            panel.blit(title, (40, 36))
            score_t = self.font_big.render(f"Final Score: {self.player.score}", True, WHITE)
            panel.blit(score_t, (40, 36 + title.get_height() + 8))
            panel.blit(self.font_main.render("Badges Earned:", True, MUTED), (40, 36 + title.get_height() + 48))
            earned = list(self.earned_current_run)

            if not earned:
                note = self.font_main.render("No badges yet — keep playing to earn achievements!", True, MUTED)
                panel.blit(note, (40, 36 + title.get_height() + 88))
            else:
                count = len(earned)
                max_med_w = 80
                available_w = card_w - 160
                med_w = min(max_med_w, max(72, (available_w - (count-1)*28) // count))
                med_h = int(med_w * 0.78)
                cols = min(3, count)
                rows = (count + cols - 1) // cols
                grid_total_w = cols * med_w + (cols - 1) * 28
                start_x = (card_w - grid_total_w) // 2
                y_top = 150
                for i,name in enumerate(earned):
                    r = i // cols; c = i % cols
                    rect_x = start_x + c * (med_w + 28)
                    rect_y = y_top + r * (med_h + 110)
                    md_center = (rect_x + med_w//2, rect_y + med_h//2)
                    self.draw_gem_medallion(panel, md_center, med_w, name)
                    ribbon_h = 24
                    ribbon_w = int(med_w * 0.74)
                    rx = rect_x + (med_w - ribbon_w)//2
                    ry = rect_y + med_h - 12
                    pygame.draw.rect(panel, (18,18,20), (rx, ry, ribbon_w, ribbon_h), border_radius=8)
                    name_txt = self.font_big.render(name, True, WHITE)
                    panel.blit(name_txt, (rx + (ribbon_w - name_txt.get_width())//2, ry + (ribbon_h - name_txt.get_height())//2 - 1))
                    desc = BADGE_DESCRIPTIONS.get(name, "")
                    lines = wrap_text(desc, self.font_main, med_w + 10)
                    y_off = rect_y + med_h + 28
                    for ln in lines[:3]:
                        dt = self.font_main.render(ln, True, (235,235,235))
                        panel.blit(dt, (rect_x + (med_w - dt.get_width())//2, y_off))
                        y_off += dt.get_height() + 4

            btn_w = int(card_w * 0.22); btn_h = max(40, int(self.screen_h * 0.08))
            play_btn = pygame.Rect(cx + card_w - btn_w - 36, cy + card_h - btn_h - 36, btn_w, btn_h)
            quit_btn = pygame.Rect(cx + card_w - 2*btn_w - 72, cy + card_h - btn_h - 36, btn_w, btn_h)
            self.screen.blit(panel, (cx, cy))
            mp = pygame.mouse.get_pos()
            self.draw_button(self.screen, quit_btn, "Play Again", active=quit_btn.collidepoint(mp))
            self.draw_button(self.screen, play_btn, "Quit", active=play_btn.collidepoint(mp))
            pygame.display.flip()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if quit_btn.collidepoint(ev.pos):
                        self.level = 1
                        self.player = Player((MAZE_COLS//2, MAZE_ROWS//3), self)
                        self.init_game(hard_reset=True); return
                    if play_btn.collidepoint(ev.pos):
                        pygame.quit(); sys.exit()
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_r:
                        self.level = 1; self.player = Player((MAZE_COLS//2, MAZE_ROWS//3), self)
                        self.init_game(hard_reset=True); return
                    if ev.key == pygame.K_q or ev.key == pygame.K_ESCAPE:
                        pygame.quit(); sys.exit()
            self.clock.tick(FPS)

    # ---------- Input & Update ----------
    def handle_input(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_LEFT, pygame.K_a): self.player.set_desired_direction(-1,0)
                if ev.key in (pygame.K_RIGHT, pygame.K_d): self.player.set_desired_direction(1,0)
                if ev.key in (pygame.K_UP, pygame.K_w): self.player.set_desired_direction(0,-1)
                if ev.key in (pygame.K_DOWN, pygame.K_s): self.player.set_desired_direction(0,1)
                if ev.key == pygame.K_ESCAPE: pygame.quit(); sys.exit()

    def update(self, dt):
        # achievement popup timing
        if self.achievement_timer > 0:
            self.achievement_timer -= dt
            self.achievement_popup_elapsed += dt
            if self.achievement_timer <= 0:
                self.achievement_msg = None; self.achievement_timer = 0.0; self.achievement_popup_elapsed = 0.0

        # update player timers and movement
        self.player.update(dt)
        self.player.move_step()

        # update ghosts
        for g in self.ghosts:
            g.update(dt)
            g.speed = g.base_speed
            if g.state == "frightened": g.speed = g.base_speed * 0.85
            if g.frozen_timer > 0: g.speed = 0
            chase_chance = 0.5 + min(0.3, (self.level-1)*0.03)
            if self.difficulty == "Hard": chase_chance += 0.1
            if g.state not in ("frightened","frozen","eaten") and g.respawn_timer <= 0:
                g.state = "chase" if random.random() < chase_chance else "scatter"
            g.move_step(self.player.tile, self.player.direction, self.level)

        # update traps (strategic)
        self.handle_traps(dt)

        # collisions and pellet capture
        self.check_collisions()

    # ---------- Main run loop ----------
    def run(self):
        if not self.show_start_menu(): return
        self.show_story_controls()
        self.init_game(hard_reset=True)
        last = time.time()
        while True:
            now = time.time(); dt = now - last; last = now
            self.handle_input()
            self.update(dt)
            self.draw_gradient_bg(self.screen)
            maze_panel = pygame.Surface((self.MAZE_W + 8, self.MAZE_H + 8), pygame.SRCALPHA)
            pygame.draw.rect(maze_panel, (10,10,16,160), (0,0,self.MAZE_W+8,self.MAZE_H+8), border_radius=8)
            self.screen.blit(maze_panel, (self.MAZE_X-4, self.MAZE_Y-4))
            self.draw_maze()
            for g in self.ghosts: g.draw(self.screen)
            self.player.draw(self.screen)
            self.draw_ui_top()
            pygame.display.flip()
            self.clock.tick(FPS)

# ---------- Entities ----------
class Player:
    def __init__(self, start_tile, game: Game):
        self.tile = start_tile; self.target_tile = start_tile
        self.game = game
        self.pos = pygame.math.Vector2(self.game.tile_to_pixel_center(*start_tile))
        self.base_speed = max(2.2, self.game.TILE * 0.12)
        self.speed = self.base_speed
        self.lives = 3; self.score = 0
        self.direction = (1,0); self.desired_direction = (0,0)
        self.radius = max(8, self.game.TILE//2 - 2)
        self.invincible_timer = 0.0; self.speed_boost_timer = 0.0
        self.slow_timer = 0.0

    def update(self, dt):
        # invincible timer
        if self.invincible_timer > 0:
            self.invincible_timer -= dt
            if self.invincible_timer < 0: self.invincible_timer = 0.0
        # speed boost timer
        if self.speed_boost_timer > 0:
            self.speed_boost_timer -= dt
            if self.speed_boost_timer < 0: self.speed_boost_timer = 0.0
        # slow timer
        if self.slow_timer > 0:
            self.slow_timer -= dt
            if self.slow_timer < 0: self.slow_timer = 0.0
        # decide effective speed: slow > boost > base
        if self.slow_timer > 0:
            self.speed = self.base_speed * 0.55
        elif self.speed_boost_timer > 0:
            self.speed = self.base_speed * 1.75
        else:
            self.speed = self.base_speed

    def draw(self, surf):
        x,y = int(self.pos.x), int(self.pos.y); r = self.radius
        pygame.draw.circle(surf, NEON_YELLOW, (x,y), r+3, 2)
        pygame.draw.circle(surf, GOLD, (x,y), r)
        pygame.draw.circle(surf, NEON_YELLOW, (x,y), r-1, 2)
        dx,dy = self.direction
        if dx==0 and dy==0: dx,dy = (1,0)
        mouth_len = r + 2
        p1 = (x,y); p2 = (x + int(dx*mouth_len), y + int(dy*mouth_len))
        perp = (-dy, dx)
        p3 = (x + int(perp[0]*(r//2)), y + int(perp[1]*(r//2)))
        p4 = (x - int(perp[0]*(r//2)), y - int(perp[1]*(r//2)))
        pygame.draw.polygon(surf, DEEP_BG_B, [p1,p3,p2,p4])
        vis_w = max(6, r+2); vis_h = max(6, r//2)
        vis_x = x + int(dx*r*0.25) - vis_w//2
        vis_y = y + int(dy*r*0.15) - vis_h//2 - 3
        pygame.draw.ellipse(surf, (255,255,255), (vis_x,vis_y,vis_w,vis_h))
        if self.invincible_timer > 0:
            pygame.draw.circle(surf, NEON_GREEN, (x,y), r+6, 2)

    def at_center(self):
        tx,ty = self.tile
        cx,cy = self.game.tile_to_pixel_center(tx,ty)
        return abs(self.pos.x - cx) < 1 and abs(self.pos.y - cy) < 1

    def set_desired_direction(self, dx, dy):
        self.desired_direction = (dx,dy)

    def try_turn(self):
        if self.desired_direction == (0,0): return False
        dx,dy = self.desired_direction; tx,ty = self.tile
        nx,ny = tx+dx, ty+dy
        if not self.game.in_bounds(nx,ny): return False
        if self.game.is_wall_tile(nx,ny): return False
        self.direction = (dx,dy); self.target_tile = (nx,ny); return True

    def move_step(self):
        if self.at_center():
            self.pos.x, self.pos.y = self.game.tile_to_pixel_center(*self.tile)
            if self.try_turn(): pass
            else:
                dx,dy = self.direction
                if dx==0 and dy==0: return
                nx,ny = self.tile[0]+dx, self.tile[1]+dy
                if self.game.is_wall_tile(nx,ny):
                    self.direction = (0,0); return
                else:
                    self.target_tile = (nx,ny)
        tx,ty = self.target_tile; cx,cy = self.game.tile_to_pixel_center(tx,ty)
        dir_vec = pygame.math.Vector2(cx - self.pos.x, cy - self.pos.y)
        distance = dir_vec.length()
        if distance == 0:
            self.tile = self.target_tile; return
        step = min(self.speed, distance)
        if distance != 0:
            dir_vec.normalize_ip()
            self.pos += dir_vec * step
        if abs(self.pos.x - cx) < 1 and abs(self.pos.y - cy) < 1:
            self.pos.x, self.pos.y = cx, cy; self.tile = self.target_tile

class Ghost:
    def __init__(self, start_tile, color, game: Game):
        self.start_tile = start_tile; self.tile = start_tile; self.target_tile = start_tile
        self.game = game
        self.pos = pygame.math.Vector2(self.game.tile_to_pixel_center(*start_tile))
        self.radius = max(8, self.game.TILE//2 - 2)
        self.color = color; self.direction = (0,0)
        self.state = "scatter"; self.base_speed = max(1.6, self.game.TILE * 0.08); self.speed = self.base_speed
        self.frightened_timer = 0.0; self.frozen_timer = 0.0; self.respawn_timer = 0.0

    def update(self, dt):
        if self.frozen_timer > 0:
            self.frozen_timer -= dt
            if self.frozen_timer <= 0: self.frozen_timer = 0; self.state = "scatter"
        if self.frightened_timer > 0:
            self.frightened_timer -= dt
            if self.frightened_timer <= 0: self.frightened_timer = 0; self.state = "chase"
        if self.respawn_timer > 0:
            self.respawn_timer -= dt
            if self.respawn_timer <= 0:
                self.respawn_timer = 0; self.state = "scatter"
                self.tile = self.start_tile; self.target_tile = self.start_tile
                self.pos = pygame.math.Vector2(self.game.tile_to_pixel_center(*self.tile)); self.direction = (0,0)

    def draw(self, surf):
        x,y = int(self.pos.x), int(self.pos.y); r = self.radius
        color = self.color if self.state != "frightened" else (60,120,255)
        outline_color = tuple(min(255, c+80) for c in color)
        pygame.draw.circle(surf, outline_color, (x, y - r//6), r+3, 2)
        head_center = (x, y - r//6)
        pygame.draw.circle(surf, color, head_center, r)
        body_top = y; body_height = r + 6
        rect = pygame.Rect(x - r, body_top - 2, r*2, body_height)
        pygame.draw.rect(surf, color, rect)
        num_scalls = 5; sc_w = (r*2)//num_scalls
        for i in range(num_scalls):
            cx = x - r + sc_w//2 + i*sc_w
            cy = body_top + body_height - (sc_w//2)
            pygame.draw.circle(surf, color, (cx, cy), sc_w//2)
        vis_w = max(8, r+4); vis_h = max(6, r//2)
        vis_rect = pygame.Rect(x - vis_w//2, y - r//3, vis_w, vis_h)
        pygame.draw.ellipse(surf, (20,20,30), vis_rect)
        highlight = pygame.Rect(vis_rect.x+3, vis_rect.y+2, max(3, vis_rect.w-8), max(2, vis_rect.h//2))
        pygame.draw.ellipse(surf, (200,230,255), highlight)
        pupil_r = 2
        pygame.draw.circle(surf, WHITE if self.state=="frightened" else (30,30,30), (x - r//4, vis_rect.centery), pupil_r)
        pygame.draw.circle(surf, WHITE if self.state=="frightened" else (30,30,30), (x + r//4, vis_rect.centery), pupil_r)
        ant_x = x + r - 6; ant_y1 = y - r - 6; ant_y2 = y - r - 12
        pygame.draw.line(surf, NEON_PINK, (ant_x, ant_y1), (ant_x, ant_y2), 2)
        pygame.draw.circle(surf, NEON_PINK, (ant_x, ant_y2-4), 3)

    def at_center(self):
        tx,ty = self.tile; cx,cy = self.game.tile_to_pixel_center(tx,ty)
        return abs(self.pos.x - cx) < 1 and abs(self.pos.y - cy) < 1

    def move_step(self, player_tile, player_dir, level):
        if self.state == "frozen" or self.respawn_timer > 0 or self.state == "eaten":
            return
        if self.at_center():
            self.pos.x, self.pos.y = self.game.tile_to_pixel_center(*self.tile)
            tx, ty = self.tile
            choices = []
            for dx, dy, dname in [(1,0,"R"), (-1,0,"L"), (0,1,"D"), (0,-1,"U")]:
                nx, ny = tx + dx, ty + dy
                if not self.game.in_bounds(nx, ny):
                    continue
                if self.game.is_wall_tile(nx, ny):
                    continue
                choices.append(((dx,dy), dname))
            if not choices:
                self.direction = (0,0)
                self.target_tile = self.tile
                return
            reverse = None
            if self.direction == (1,0): reverse = "L"
            if self.direction == (-1,0): reverse = "R"
            if self.direction == (0,1): reverse = "U"
            if self.direction == (0,-1): reverse = "D"
            if self.state == "frightened":
                dist_map = bfs(self.tile, {player_tile}, self.game.is_wall_tile, self.game.in_bounds)
                maxd = -1
                choice = random.choice(choices)
                for (dx,dy), dname in choices:
                    nx, ny = tx + dx, ty + dy
                    d = dist_map.get((nx,ny), None)
                    dval = float('inf') if d is None else d
                    if dval > maxd and dname != reverse:
                        maxd = dval
                        choice = ((dx,dy), dname)
                self.direction = choice[0]
                self.target_tile = (tx + self.direction[0], ty + self.direction[1])
            elif self.state == "scatter":
                viable = [c for c in choices if c[1] != reverse]
                if viable and random.random() < 0.7:
                    choice = random.choice(viable)
                    self.direction = choice[0]
                else:
                    d,dname = choose_bfs_direction(self.tile, player_tile, self.game.is_wall_tile, self.game.in_bounds, forbidden_reverse=reverse)
                    if d == (0,0):
                        choice = random.choice(choices)
                        self.direction = choice[0]
                    else:
                        self.direction = d
                self.target_tile = (tx + self.direction[0], ty + self.direction[1])
            elif self.state == "chase":
                d,dname = choose_bfs_direction(self.tile, player_tile, self.game.is_wall_tile, self.game.in_bounds, forbidden_reverse=reverse)
                if d == (0,0):
                    viable = [c for c in choices if c[1] != reverse]
                    if viable:
                        choice = random.choice(viable)
                        self.direction = choice[0]
                    else:
                        self.direction = random.choice(choices)[0]
                else:
                    self.direction = d
                self.target_tile = (tx + self.direction[0], ty + self.direction[1])
        tx, ty = self.target_tile
        cx, cy = self.game.tile_to_pixel_center(tx, ty)
        dir_vec = pygame.math.Vector2(cx - self.pos.x, cy - self.pos.y)
        if dir_vec.length() == 0:
            self.pos.x, self.pos.y = cx, cy
            self.tile = self.target_tile
            return
        step = self.speed
        dir_vec.normalize_ip()
        self.pos += dir_vec * step
        if abs(self.pos.x - cx) < 1 and abs(self.pos.y - cy) < 1:
            self.pos.x, self.pos.y = cx, cy
            self.tile = self.target_tile

# ---------- Run ----------
if __name__ == "__main__":
    Game(SCREEN_W, SCREEN_H).run()
