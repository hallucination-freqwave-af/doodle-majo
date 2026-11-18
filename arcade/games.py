"""Tiny procedural retro games drawn on a low-res pixel grid. Each: reset(seed), step(dt, kick, hit), draw() -> (GH,GW,3) uint8."""
import numpy as np, math

GW, GH = 66, 135  # cells; panel 528x1080 at 8px
BLACK = (0, 0, 0)

class Game:
    def __init__(self, seed): self.r = np.random.default_rng(seed); self.g = np.zeros((GH, GW, 3), np.uint8); self.t = 0.0
    def px(self, x, y, c):
        if 0 <= x < GW and 0 <= y < GH: self.g[int(y), int(x)] = c
    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, int(x)), max(0, int(y)); x1, y1 = min(GW, int(x + w)), min(GH, int(y + h))
        if x1 > x0 and y1 > y0: self.g[y0:y1, x0:x1] = c
    def sprite(self, x, y, pat, c):
        for j, row in enumerate(pat):
            for i, ch in enumerate(row):
                if ch == '#': self.px(x + i, y + j, c)
    def clear(self, c=BLACK): self.g[:] = c

ALIEN = ["..#...#..", "...#.#...", "..#####..", ".##.#.##.", "#########", "#.#####.#", "#.#...#.#", "...#.#..."]
ALIEN2 = ["..##..", ".####.", "######", "#.##.#", "######", ".#..#.", "#....#"]
SHIP = ["....#....", "...###...", "..#####..", "#########", "#########"]

class Invaders(Game):
    def __init__(self, seed):
        super().__init__(seed); self.alive = np.ones((5, 5), bool); self.ox = 4; self.dir = 1; self.oy = 8
        self.bullets = []; self.bombs = []; self.px_ = GW // 2; self.boom = []; self.tick = 0.0; self.score = 0
    def step(self, dt, kick, hit):
        self.t += dt; self.tick += dt
        if self.tick > 0.35:
            self.tick = 0; self.ox += self.dir * 2
            if self.ox > 14 or self.ox < 2: self.dir *= -1; self.oy += 3
            if self.oy > 90: self.oy = 8; self.alive[:] = True
        self.px_ += 30 * dt * math.sin(self.t * 1.7)
        if kick > 0.6 and (not self.bullets or self.bullets[-1][1] < GH - 20): self.bullets.append([self.px_ + 4, GH - 14])
        if hit > 0.7 and self.r.random() < 0.5:
            c = self.r.integers(0, 5); self.bombs.append([self.ox + c * 11 + 4, self.oy + 40])
        for b in self.bullets: b[1] -= 120 * dt
        for b in self.bombs: b[1] += 60 * dt
        self.bullets = [b for b in self.bullets if b[1] > 0]; self.bombs = [b for b in self.bombs if b[1] < GH]
        for b in self.bullets:
            for i in range(5):
                for j in range(5):
                    if self.alive[j, i]:
                        ax, ay = self.ox + i * 11, self.oy + j * 10
                        if ax <= b[0] < ax + 9 and ay <= b[1] < ay + 8:
                            self.alive[j, i] = False; self.boom.append([ax + 4, ay + 4, 0.4]); b[1] = -10; self.score += 10
        if not self.alive.any(): self.alive[:] = True; self.oy = 8
        for e in self.boom: e[2] -= dt
        self.boom = [e for e in self.boom if e[2] > 0]
    def draw(self):
        self.clear()
        for i in range(5):
            for j in range(5):
                if self.alive[j, i]:
                    c = [(120, 255, 120), (255, 120, 220), (120, 220, 255)][j % 3]
                    self.sprite(self.ox + i * 11, self.oy + j * 10, ALIEN if int(self.t * 3) % 2 else ALIEN2, c)
        self.sprite(self.px_, GH - 12, SHIP, (255, 255, 255))
        for b in self.bullets: self.rect(b[0], b[1], 1, 3, (255, 255, 0))
        for b in self.bombs: self.rect(b[0], b[1], 1, 3, (255, 80, 80))
        for e in self.boom:
            s = int(6 * (0.4 - e[2]) / 0.4) + 1
            for k in range(8):
                a = k * math.pi / 4; self.px(e[0] + math.cos(a) * s, e[1] + math.sin(a) * s, (255, 200, 0))
        for k in range(4): self.rect(6 + k * 15, GH - 24, 9, 4, (120, 255, 120))
        self.rect(0, 2, min(GW, self.score // 10), 1, (255, 255, 255))
        return self.g

TETROMINOES = [[(0, 0), (1, 0), (2, 0), (3, 0)], [(0, 0), (1, 0), (0, 1), (1, 1)], [(0, 0), (1, 0), (2, 0), (1, 1)],
               [(0, 0), (1, 0), (2, 0), (2, 1)], [(0, 0), (1, 0), (2, 0), (0, 1)], [(1, 0), (2, 0), (0, 1), (1, 1)], [(0, 0), (1, 0), (1, 1), (2, 1)]]
TCOL = [(0, 240, 240), (240, 240, 0), (160, 0, 240), (240, 160, 0), (0, 0, 240), (0, 240, 0), (240, 0, 0)]

class Tetris(Game):
    def __init__(self, seed):
        super().__init__(seed); self.cw, self.ch = 10, 20; self.cell = 6
        self.board = np.zeros((self.ch, self.cw), int); self.spawn(); self.tick = 0; self.flash = []; self.ft = 0
    def spawn(self):
        self.k = int(self.r.integers(0, 7)); self.shape = list(TETROMINOES[self.k]); self.x = int(self.r.integers(0, self.cw - 3)); self.y = 0
    def fits(self, shape, x, y):
        for dx, dy in shape:
            X, Y = x + dx, y + dy
            if X < 0 or X >= self.cw or Y >= self.ch or (Y >= 0 and self.board[Y, X]): return False
        return True
    def step(self, dt, kick, hit):
        self.t += dt; self.tick += dt; self.ft -= dt
        if kick > 0.7:  # rotate on kick
            rot = [(-dy, dx) for dx, dy in self.shape]
            if self.fits(rot, self.x, self.y): self.shape = rot
        if hit > 0.6: self.x += 1 if self.fits(self.shape, self.x + 1, self.y) else 0
        if self.tick > 0.12:
            self.tick = 0
            if self.fits(self.shape, self.x, self.y + 1): self.y += 1
            else:
                for dx, dy in self.shape:
                    if 0 <= self.y + dy < self.ch: self.board[self.y + dy, self.x + dx] = self.k + 1
                full = [i for i in range(self.ch) if self.board[i].all()]
                if full:
                    self.flash = full; self.ft = 0.3
                    self.board = np.vstack([np.zeros((len(full), self.cw), int), np.delete(self.board, full, axis=0)])
                if self.board[:2].any(): self.board[:] = 0
                self.spawn()
    def draw(self):
        self.clear((10, 10, 30)); ox, oy = 8, 7; c = self.cell
        self.rect(ox - 1, oy - 1, self.cw * c + 2, self.ch * c + 2, (80, 80, 120)); self.rect(ox, oy, self.cw * c, self.ch * c, (0, 0, 0))
        for j in range(self.ch):
            for i in range(self.cw):
                if self.board[j, i]: self.rect(ox + i * c, oy + j * c, c - 1, c - 1, TCOL[self.board[j, i] - 1])
        for dx, dy in self.shape:
            if self.y + dy >= 0: self.rect(ox + (self.x + dx) * c, oy + (self.y + dy) * c, c - 1, c - 1, TCOL[self.k])
        if self.ft > 0:
            for j in self.flash: self.rect(ox, oy + j * c, self.cw * c, c - 1, (255, 255, 255))
        return self.g

class Pong(Game):
    def __init__(self, seed):
        super().__init__(seed); self.bx, self.by = GW / 2, GH / 2; self.vx, self.vy = 40, 55; self.p1 = self.p2 = GH / 2; self.s1 = self.s2 = 0; self.flash = 0
    def step(self, dt, kick, hit):
        self.t += dt; self.flash = max(0, self.flash - dt)
        sp = 1 + kick
        self.bx += self.vx * dt * sp; self.by += self.vy * dt * sp
        if self.bx < 3 and abs(self.by - self.p1) < 9: self.vx = abs(self.vx) * 1.02; self.flash = 0.1
        if self.bx > GW - 4 and abs(self.by - self.p2) < 9: self.vx = -abs(self.vx) * 1.02; self.flash = 0.1
        if self.bx < 0: self.s2 += 1; self.bx, self.by = GW / 2, GH / 2; self.vx = 40
        if self.bx > GW: self.s1 += 1; self.bx, self.by = GW / 2, GH / 2; self.vx = -40
        if self.by < 0 or self.by > GH: self.vy *= -1
        self.p1 += (self.by - self.p1) * min(1, 3 * dt); self.p2 += (self.by - self.p2) * min(1, 2.2 * dt)
        if hit > 0.8: self.vy = -self.vy
    def draw(self):
        self.clear((20, 20, 20) if self.flash > 0 else BLACK)
        for y in range(0, GH, 6): self.rect(GW // 2, y, 1, 3, (90, 90, 90))
        self.rect(1, self.p1 - 8, 2, 16, (255, 255, 255)); self.rect(GW - 3, self.p2 - 8, 2, 16, (255, 255, 255))
        self.rect(self.bx - 1, self.by - 1, 2, 2, (255, 255, 255))
        for k in range(min(20, self.s1)): self.rect(4 + k * 3, 3, 2, 2, (255, 120, 220))
        for k in range(min(20, self.s2)): self.rect(GW - 6 - k * 3, 3, 2, 2, (120, 220, 255))
        return self.g

class Snake(Game):
    def __init__(self, seed):
        super().__init__(seed); self.c = 3; self.cw, self.ch = GW // self.c, GH // self.c
        self.body = [(self.cw // 2, self.ch // 2 + i) for i in range(6)]; self.dir = (0, -1); self.food = self.newfood(); self.tick = 0; self.dead = 0
    def newfood(self): return (int(self.r.integers(1, self.cw - 1)), int(self.r.integers(1, self.ch - 1)))
    def step(self, dt, kick, hit):
        self.t += dt; self.tick += dt
        if self.dead > 0: self.dead -= dt; return
        if self.tick > 0.07:
            self.tick = 0; hx, hy = self.body[0]; fx, fy = self.food
            # steer toward food, avoid reversing
            opts = [(1, 0), (-1, 0), (0, 1), (0, -1)]; opts = [d for d in opts if d != (-self.dir[0], -self.dir[1])]
            best = min(opts, key=lambda d: abs(hx + d[0] - fx) + abs(hy + d[1] - fy) + (100 if (hx + d[0], hy + d[1]) in self.body else 0))
            if kick > 0.85: best = opts[int(self.r.integers(0, len(opts)))]  # a kick makes it flinch
            self.dir = best; nh = (hx + best[0], hy + best[1])
            if nh in self.body or not (0 <= nh[0] < self.cw and 0 <= nh[1] < self.ch):
                self.dead = 0.6; self.body = [(self.cw // 2, self.ch // 2 + i) for i in range(6)]; self.dir = (0, -1); return
            self.body.insert(0, nh)
            if nh == self.food: self.food = self.newfood()
            else: self.body.pop()
    def draw(self):
        self.clear((0, 15, 0) if self.dead <= 0 else (60, 0, 0))
        for k, (x, y) in enumerate(self.body):
            self.rect(x * self.c, y * self.c, self.c - 1, self.c - 1, (120, 255, 120) if k else (255, 255, 255))
        fx, fy = self.food; self.rect(fx * self.c, fy * self.c, self.c - 1, self.c - 1, (255, 80, 120) if int(self.t * 6) % 2 else (255, 200, 0))
        return self.g

class Breakout(Game):
    def __init__(self, seed):
        super().__init__(seed); self.bricks = np.ones((8, 8), bool); self.bx, self.by = GW / 2, GH * 0.6; self.vx, self.vy = 35, -60; self.p = GW / 2; self.flash = []
    def step(self, dt, kick, hit):
        self.t += dt; sp = 1 + 0.5 * kick
        self.bx += self.vx * dt * sp; self.by += self.vy * dt * sp
        if self.bx < 0 or self.bx > GW - 1: self.vx *= -1
        if self.by < 0: self.vy *= -1
        if self.by > GH - 5 and abs(self.bx - self.p) < 8: self.vy = -abs(self.vy); self.vx += (self.bx - self.p) * 4
        if self.by > GH: self.bx, self.by = GW / 2, GH * 0.6; self.vy = -60
        self.p += (self.bx - self.p) * min(1, 4 * dt)
        i, j = int((self.bx - 1) // 8), int((self.by - 12) // 5)
        if 0 <= i < 8 and 0 <= j < 8 and self.bricks[j, i]:
            self.bricks[j, i] = False; self.vy *= -1; self.flash.append([i, j, 0.2])
        if hit > 0.8 and self.r.random() < 0.3:
            i, j = self.r.integers(0, 8), self.r.integers(0, 8)
            if self.bricks[j, i]: self.bricks[j, i] = False; self.flash.append([i, j, 0.2])
        if not self.bricks.any(): self.bricks[:] = True
        for f in self.flash: f[2] -= dt
        self.flash = [f for f in self.flash if f[2] > 0]
    def draw(self):
        self.clear()
        for j in range(8):
            for i in range(8):
                if self.bricks[j, i]: self.rect(1 + i * 8, 12 + j * 5, 7, 4, [(255, 60, 60), (255, 160, 0), (255, 240, 0), (0, 230, 90), (0, 160, 255), (160, 0, 240), (255, 120, 220), (255, 255, 255)][j])
        for f in self.flash: self.rect(1 + f[0] * 8 - 1, 12 + f[1] * 5 - 1, 9, 6, (255, 255, 255))
        self.rect(self.p - 7, GH - 4, 14, 2, (255, 255, 255)); self.rect(self.bx - 1, self.by - 1, 2, 2, (255, 255, 255))
        return self.g

class Shooter(Game):
    def __init__(self, seed):
        super().__init__(seed); self.stars = [(int(self.r.integers(0, GW)), self.r.random() * GH, 20 + self.r.random() * 60) for _ in range(40)]
        self.px_ = GW / 2; self.enemies = []; self.bullets = []; self.boom = []; self.spawn = 0
    def step(self, dt, kick, hit):
        self.t += dt; self.spawn += dt
        self.stars = [(x, (y + s * dt) % GH, s) for x, y, s in self.stars]
        self.px_ = GW / 2 + 22 * math.sin(self.t * 1.3)
        if self.spawn > 0.6: self.spawn = 0; self.enemies.append([self.r.integers(4, GW - 4), -6, self.r.random() * 2])
        if kick > 0.5: self.bullets.append([self.px_ - 2, GH - 12]); self.bullets.append([self.px_ + 2, GH - 12])
        for e in self.enemies: e[1] += 25 * dt; e[0] += math.sin(self.t * 3 + e[2]) * 10 * dt
        for b in self.bullets: b[1] -= 150 * dt
        for e in self.enemies:
            for b in self.bullets:
                if abs(e[0] - b[0]) < 4 and abs(e[1] - b[1]) < 4: e[1] = GH + 99; b[1] = -99; self.boom.append([e[0], e[1] - 99 - GH, 0.35])
        self.enemies = [e for e in self.enemies if e[1] < GH]; self.bullets = [b for b in self.bullets if b[1] > 0]
        for e in self.boom: e[2] -= dt
        self.boom = [e for e in self.boom if e[2] > 0]
        if hit > 0.85: self.boom.append([self.r.integers(5, GW - 5), self.r.integers(5, GH - 20), 0.3])
    def draw(self):
        self.clear((0, 0, 15))
        for x, y, s in self.stars: self.px(x, y, (90, 90, 140) if s < 50 else (200, 200, 255))
        self.sprite(self.px_ - 4, GH - 12, SHIP, (120, 220, 255))
        for e in self.enemies: self.sprite(e[0] - 3, e[1], ALIEN2, (255, 120, 220))
        for b in self.bullets: self.rect(b[0], b[1], 1, 3, (255, 255, 120))
        for e in self.boom:
            s = int(7 * (0.35 - e[2]) / 0.35) + 1
            for k in range(12):
                a = k * math.pi / 6; self.px(e[0] + math.cos(a) * s, e[1] + math.sin(a) * s, (255, 160, 0))
        return self.g

GAMES = [Invaders, Tetris, Pong, Snake, Breakout, Shooter]
