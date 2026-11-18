"""16-bit (c.1990) side-panel games on a 132x270 grid (4px pixels): a vertical shooter with stages, and a Tetris that spins."""
import numpy as np, math, cv2

GW, GH = 132, 270

class Base:
    def __init__(self, seed): self.r = np.random.default_rng(seed); self.g = np.zeros((GH, GW, 3), np.uint8); self.t = 0.0; self.shake = 0.0
    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, int(x)), max(0, int(y)); x1, y1 = min(GW, int(x + w)), min(GH, int(y + h))
        if x1 > x0 and y1 > y0: self.g[y0:y1, x0:x1] = c
    def px(self, x, y, c):
        if 0 <= x < GW and 0 <= y < GH: self.g[int(y), int(x)] = c
    def sprite(self, x, y, pat, pal, sc=2):
        for j, row in enumerate(pat):
            for i, ch in enumerate(row):
                if ch != '.': self.rect(x + i * sc, y + j * sc, sc, sc, pal[ch])
    def circle(self, cx, cy, r, c, fill=True, w=1):
        cv2.circle(self.g, (int(cx), int(cy)), int(r), c, -1 if fill else w)
    def finish(self):
        if self.shake > 0:
            dx, dy = self.r.integers(-3, 4, 2); self.g = np.roll(np.roll(self.g, int(dx), 1), int(dy), 0)
        return self.g

# ---- sprites (original) ----
SHIP = ["......1......", ".....121.....", ".....121.....", "....12321....", "....12321....", "...1233321...", "..123333321..", ".12334443321.", "1233344443321", "1223311133221", "11.1.....1.11"]
SHIP_PAL = {'1': (40, 60, 120), '2': (90, 140, 230), '3': (200, 230, 255), '4': (255, 120, 60)}
OPTION = ["..11..", ".1221.", "122221", "122221", ".1221.", "..11.."]
OPT_PAL = {'1': (200, 120, 0), '2': (255, 230, 120)}
EN1 = [".1...1.", "12...21", ".12221.", "1233321", "1232321", ".12221.", "..1.1.."]
EN1_PAL = {'1': (120, 20, 60), '2': (230, 60, 140), '3': (255, 200, 230)}
EN2 = ["...11...", "..1221..", ".123321.", "12344321", ".123321.", "..1221..", "...11..."]
EN2_PAL = {'1': (20, 80, 60), '2': (60, 200, 120), '3': (180, 255, 200), '4': (255, 255, 255)}
BOSS = [
    "......11111111......", "....112222222211....", "..11223333333322211.", ".1223334444444333221", "12233344455544433322", "12233444555554443322",
    "12233444556554443322", "12233444555554443322", "12233344455544433322", ".1223334444444333221", "..11223333333322211.", "..1.1122222222211.1.",
    ".11...11111111...11.", "122...........122...", "122...........122..."]
BOSS_PAL = {'1': (60, 20, 80), '2': (120, 60, 160), '3': (190, 120, 230), '4': (240, 200, 255), '5': (255, 80, 120)}

class Shooter16(Base):
    STAGES = ['space', 'cave', 'city']
    def __init__(self, seed, stage=None):
        super().__init__(seed); self.stage = stage or self.STAGES[seed % 3]
        self.px_, self.py_ = GW / 2, GH - 30; self.vx = 0
        self.bullets = []; self.ebullets = []; self.enemies = []; self.booms = []; self.debris = []
        self.laser = 0.0; self.boss = None; self.bosstimer = 14 + self.r.random() * 6; self.wave = 0; self.spawn = 0; self.score = 0
        self.stars = [(self.r.random() * GW, self.r.random() * GH, 0.3 + self.r.random()) for _ in range(90)]
        self.scroll = 0.0; self.power = 1
        self.cave = [self._cavecol() for _ in range(GH // 6 + 3)]
        self.city = [(self.r.integers(0, GW), self.r.integers(10, 40), self.r.integers(14, 50)) for _ in range(26)]
    def _cavecol(self): return (int(self.r.integers(12, 34)), int(self.r.integers(12, 34)))
    def step(self, dt, kick, hit):
        self.t += dt; self.scroll += dt * 40; self.shake = max(0, self.shake - dt); self.laser = max(0, self.laser - dt)
        self.px_ = GW / 2 + 34 * math.sin(self.t * 0.9) + 10 * math.sin(self.t * 3.1); self.py_ = GH - 36 + 8 * math.sin(self.t * 1.7)
        if kick > 0.45:
            self.bullets += [[self.px_ - 4, self.py_ - 10, 0], [self.px_ + 4, self.py_ - 10, 0]]
            if self.power > 1: self.bullets += [[self.px_ - 12, self.py_ + 4, -0.4], [self.px_ + 12, self.py_ + 4, 0.4]]
        if hit > 0.85 and self.laser <= 0: self.laser = 0.35
        self.spawn += dt
        if self.spawn > 1.6 and self.boss is None:
            self.spawn = 0; self.wave += 1; kind = self.wave % 3; base = self.r.integers(20, GW - 20)
            for k in range(6): self.enemies.append({'x': base, 'y': -10 - k * 12, 'k': kind, 'ph': k * 0.6, 'hp': 2, 'fl': 0})
        self.bosstimer -= dt
        if self.bosstimer < 0 and self.boss is None: self.boss = {'x': GW / 2, 'y': -20, 'hp': 60, 'fl': 0, 'ph': 0}
        for e in self.enemies:
            e['y'] += 32 * dt
            if e['k'] == 0: e['x'] += math.sin(self.t * 2.5 + e['ph']) * 60 * dt
            elif e['k'] == 1: e['x'] += (self.px_ - e['x']) * 0.8 * dt
            else: e['x'] += math.cos(self.t * 4 + e['ph']) * 90 * dt
            e['fl'] = max(0, e['fl'] - dt)
            if self.r.random() < 0.35 * dt: self.ebullets.append([e['x'], e['y'] + 4, (self.px_ - e['x']) * 0.5, 55])
        if self.boss is not None:
            b = self.boss; b['ph'] += dt
            b['y'] += (40 - b['y']) * 1.5 * dt; b['x'] = GW / 2 + 40 * math.sin(b['ph'] * 0.8); b['fl'] = max(0, b['fl'] - dt)
            if int(b['ph'] * 6) % 6 == 0 and self.r.random() < 0.5:
                for a in range(-2, 3): self.ebullets.append([b['x'], b['y'] + 14, a * 18, 60])
            if hit > 0.7:
                for a in range(12): self.ebullets.append([b['x'], b['y'] + 10, 60 * math.cos(a * math.pi / 6), 60 * math.sin(a * math.pi / 6)])
        for bl in self.bullets: bl[1] -= 220 * dt; bl[0] += bl[2] * 220 * dt
        for eb in self.ebullets: eb[0] += eb[2] * dt; eb[1] += eb[3] * dt
        # hits
        for bl in self.bullets:
            for e in self.enemies:
                if abs(e['x'] - bl[0]) < 8 and abs(e['y'] - bl[1]) < 8 and e['hp'] > 0:
                    e['hp'] -= 1; e['fl'] = 0.08; bl[1] = -99
                    if e['hp'] <= 0: self.boom(e['x'], e['y'], 1); self.score += 100
            if self.boss is not None and abs(self.boss['x'] - bl[0]) < 20 and abs(self.boss['y'] - bl[1]) < 15:
                self.boss['hp'] -= 1; self.boss['fl'] = 0.06; bl[1] = -99
        if self.laser > 0:
            for e in self.enemies:
                if abs(e['x'] - self.px_) < 8: e['hp'] = 0; self.boom(e['x'], e['y'], 1)
            if self.boss is not None and abs(self.boss['x'] - self.px_) < 12: self.boss['hp'] -= 25 * dt; self.boss['fl'] = 0.05
        if self.boss is not None and self.boss['hp'] <= 0:
            for k in range(7): self.booms.append([self.boss['x'] + self.r.integers(-14, 14), self.boss['y'] + self.r.integers(-8, 8), -k * 0.12, 2.2])
            self.shake = 0.8; self.boss = None; self.bosstimer = 16 + self.r.random() * 8; self.power = 2; self.score += 5000
        self.enemies = [e for e in self.enemies if e['y'] < GH + 10 and e['hp'] > 0]
        self.bullets = [b for b in self.bullets if b[1] > -5]; self.ebullets = [b for b in self.ebullets if -5 < b[1] < GH + 5 and -5 < b[0] < GW + 5]
        for bm in self.booms: bm[2] += dt
        self.booms = [b for b in self.booms if b[2] < 0.6]
        for d in self.debris: d[0] += d[2] * dt; d[1] += d[3] * dt; d[3] += 80 * dt; d[4] -= dt
        self.debris = [d for d in self.debris if d[4] > 0]
    def boom(self, x, y, size):
        self.booms.append([x, y, 0, size]); self.shake = max(self.shake, 0.15)
        for _ in range(8):
            a = self.r.random() * 6.3; s = 30 + self.r.random() * 60
            self.debris.append([x, y, math.cos(a) * s, math.sin(a) * s - 30, 0.5 + self.r.random() * 0.4])
    def background(self):
        if self.stage == 'space':
            yy = np.linspace(0, 1, GH)[:, None]
            self.g[:] = (np.stack([8 + 20 * yy, 4 + 10 * yy, 30 + 50 * yy], -1) * np.ones((GH, GW, 1))).astype(np.uint8)
            for x, y, s in self.stars:
                yy2 = (y + self.scroll * s) % GH; c = min(230, int(90 + 110 * s))
                self.px(x, yy2, (c, c, min(255, c + 40)))
                if s > 1.1: self.px(x, yy2 + 1, (c // 2, c // 2, c // 2))
            # a slow planet
            self.circle(GW * 0.8, (self.scroll * 0.15) % (GH + 120) - 60, 26, (60, 40, 110)); self.circle(GW * 0.8 - 8, (self.scroll * 0.15) % (GH + 120) - 68, 18, (110, 80, 170))
        elif self.stage == 'cave':
            self.g[:] = (40, 20, 50)
            off = int(self.scroll / 6) ; sub = int(self.scroll % 6)
            while len(self.cave) < GH // 6 + 4 + off - getattr(self, 'cave0', 0): self.cave.append(self._cavecol())
            for j in range(GH // 6 + 2):
                k = off + j; L, Rr = self.cave[k % len(self.cave)]
                y = j * 6 - sub
                self.rect(0, y, L, 6, (120, 60, 140)); self.rect(0, y, L - 4, 6, (80, 30, 100)); self.rect(GW - Rr, y, Rr, 6, (120, 60, 140)); self.rect(GW - Rr + 4, y, Rr, 6, (80, 30, 100))
                if k % 5 == 0: self.rect(L, y + 2, 3, 2, (255, 120, 180)); self.rect(GW - Rr - 3, y + 2, 3, 2, (255, 120, 180))
        else:  # city at night
            yy = np.linspace(0, 1, GH)[:, None]
            self.g[:] = (np.stack([10 + 30 * yy, 10 + 10 * yy, 40 + 40 * yy], -1) * np.ones((GH, GW, 1))).astype(np.uint8)
            for k, (x, w, h) in enumerate(self.city):
                y = (k * 37 + self.scroll * (0.5 + (k % 3) * 0.3)) % (GH + 60) - 50
                shade = 30 + (k % 3) * 25
                self.rect(x, y, w, h, (shade, shade, shade + 30))
                for wy in range(2, h - 2, 4):
                    for wx in range(2, w - 2, 4):
                        if (k * 7 + wy * 3 + wx) % 5 < 2: self.rect(x + wx, y + wy, 2, 2, (255, 230, 120))
            for i in range(4): self.rect(0, (i * 70 + self.scroll * 1.6) % (GH + 20) - 10, GW, 1, (90, 60, 120))
    def draw(self):
        self.background()
        # ebullets / enemies
        for eb in self.ebullets: self.circle(eb[0], eb[1], 1.5, (255, 220, 120)); self.px(eb[0], eb[1], (255, 255, 255))
        for e in self.enemies:
            pal = EN1_PAL if e['k'] != 1 else EN2_PAL; pat = EN1 if e['k'] != 1 else EN2
            if e['fl'] > 0: pal = {k: (255, 255, 255) for k in pal}
            self.sprite(e['x'] - 7, e['y'] - 7, pat, pal)
        if self.boss is not None:
            b = self.boss; pal = BOSS_PAL if b['fl'] <= 0 else {k: (255, 255, 255) for k in BOSS_PAL}
            self.sprite(b['x'] - 20, b['y'] - 15, BOSS, pal)
            self.rect(20, 4, 92, 3, (60, 0, 0)); self.rect(20, 4, 92 * max(0, b['hp']) / 60, 3, (255, 60, 80))
        # player
        if self.laser > 0:
            self.rect(self.px_ - 3, 0, 6, self.py_, (120, 200, 255)); self.rect(self.px_ - 1, 0, 2, self.py_, (255, 255, 255))
        for bl in self.bullets: self.rect(bl[0] - 1, bl[1], 2, 7, (255, 240, 160)); self.px(bl[0], bl[1], (255, 255, 255))
        self.sprite(self.px_ - 13, self.py_ - 11, SHIP, SHIP_PAL)
        self.rect(self.px_ - 2, self.py_ + 11, 4, 4 + int(5 * abs(math.sin(self.t * 30))), (255, 160, 60))
        if self.power > 1:
            for s in (-1, 1): self.sprite(self.px_ + s * 22 - 6 + 2 * math.sin(self.t * 5 + s), self.py_ - 4 + 2 * math.cos(self.t * 5 + s), OPTION, OPT_PAL)
        for bm in self.booms:
            if bm[2] < 0: continue
            p = bm[2] / 0.6; rr = (4 + 22 * p) * bm[3]
            self.circle(bm[0], bm[1], rr, (255, 90, 30) if p < 0.5 else (120, 40, 20), fill=False, w=max(1, int(4 * (1 - p))))
            if p < 0.3: self.circle(bm[0], bm[1], rr * 0.5, (255, 240, 180))
        for d in self.debris: self.px(d[0], d[1], (255, 200, 80))
        # HUD
        self.rect(0, GH - 6, GW, 6, (0, 0, 0)); self.rect(2, GH - 4, min(GW - 4, self.score // 200), 2, (255, 230, 120))
        return self.finish()

TETROMINOES = [[(0, 0), (1, 0), (2, 0), (3, 0)], [(0, 0), (1, 0), (0, 1), (1, 1)], [(0, 0), (1, 0), (2, 0), (1, 1)],
               [(0, 0), (1, 0), (2, 0), (2, 1)], [(0, 0), (1, 0), (2, 0), (0, 1)], [(1, 0), (2, 0), (0, 1), (1, 1)], [(0, 0), (1, 0), (1, 1), (2, 1)]]
TCOL = [(0, 240, 240), (240, 240, 0), (160, 0, 240), (240, 160, 0), (0, 0, 240), (0, 240, 0), (240, 0, 0)]

class TetrisSpin(Base):
    """Tetris, arranged: a cleared line makes the whole board spin; gravity flips now and then; blocks drift in colour."""
    def __init__(self, seed):
        super().__init__(seed); self.cw, self.ch = 10, 20; self.cell = 11
        self.board = np.zeros((self.ch, self.cw), int); self.spawn(); self.tick = 0; self.angle = 0.0; self.spin = 0.0
        self.flip = 1; self.fliptimer = 7 + self.r.random() * 4; self.parts = []; self.hue = 0.0
    def spawn(self):
        self.k = int(self.r.integers(0, 7)); self.shape = list(TETROMINOES[self.k]); self.x = int(self.r.integers(0, self.cw - 3)); self.y = 0
    def fits(self, shape, x, y):
        for dx, dy in shape:
            X, Y = x + dx, y + dy
            if X < 0 or X >= self.cw or Y >= self.ch or (Y >= 0 and self.board[Y, X]): return False
        return True
    def step(self, dt, kick, hit):
        self.t += dt; self.tick += dt; self.hue += dt * 0.3; self.fliptimer -= dt
        if self.spin > 0: self.spin -= dt; self.angle += 720 * dt; return
        self.angle = (self.angle % 360); self.angle += (0 - self.angle) * min(1, 6 * dt) if self.angle < 180 else (360 - self.angle) * min(1, 6 * dt)
        if self.fliptimer < 0:  # gravity flips: board turns upside down, stack falls to the other side
            self.fliptimer = 7 + self.r.random() * 5; self.flip *= -1
            self.board = self.board[::-1]; self.spin = 0.25; self.angle = 0
            # re-settle: drop columns
            for i in range(self.cw):
                col = self.board[:, i]; vals = col[col > 0]; col[:] = 0; col[self.ch - len(vals):] = vals
            self.spawn(); return
        if kick > 0.7:
            rot = [(-dy, dx) for dx, dy in self.shape]
            if self.fits(rot, self.x, self.y): self.shape = rot
        if hit > 0.6 and self.fits(self.shape, self.x + 1, self.y): self.x += 1
        if self.tick > 0.11:
            self.tick = 0
            if self.fits(self.shape, self.x, self.y + 1): self.y += 1
            else:
                for dx, dy in self.shape:
                    if 0 <= self.y + dy < self.ch: self.board[self.y + dy, self.x + dx] = self.k + 1
                full = [i for i in range(self.ch) if self.board[i].all()]
                if full:
                    for j in full:
                        for i in range(self.cw):
                            a = self.r.random() * 6.3; s = 40 + self.r.random() * 80
                            self.parts.append([i, j, math.cos(a) * s, math.sin(a) * s, 0.8, TCOL[self.board[j, i] - 1]])
                    self.board = np.vstack([np.zeros((len(full), self.cw), int), np.delete(self.board, full, axis=0)])
                    self.spin = 0.5; self.shake = 0.3
                if self.board[:2].any(): self.board[:] = 0; self.spin = 0.5
                self.spawn()
        for p in self.parts: p[0] += p[2] * dt / self.cell; p[1] += p[3] * dt / self.cell; p[4] -= dt
        self.parts = [p for p in self.parts if p[4] > 0]
    def draw(self):
        c = self.cell; bw, bh = self.cw * c, self.ch * c
        board = np.zeros((bh + 8, bw + 8, 3), np.uint8); board[:] = (12, 10, 30)
        board[2:-2, 2:-2] = (70, 60, 120); board[4:-4, 4:-4] = (0, 0, 0)
        def cellcol(k, i, j):
            r, g, b = TCOL[k]; m = 0.75 + 0.25 * math.sin(self.hue + i * 0.4 + j * 0.3)
            return (int(r * m), int(g * m), int(b * m))
        def cell(i, j, k, bright=False):
            x0, y0 = 4 + i * c, 4 + j * c; col = (255, 255, 255) if bright else cellcol(k, i, j)
            board[y0 + 1:y0 + c - 1, x0 + 1:x0 + c - 1] = col; board[y0 + 1:y0 + 3, x0 + 1:x0 + c - 1] = tuple(min(255, v + 70) for v in col)
        for j in range(self.ch):
            for i in range(self.cw):
                if self.board[j, i]: cell(i, j, self.board[j, i] - 1)
        if self.spin <= 0:
            for dx, dy in self.shape:
                if self.y + dy >= 0: cell(self.x + dx, self.y + dy, self.k, bright=int(self.t * 10) % 5 == 0)
        for p in self.parts:
            x0, y0 = int(4 + p[0] * c), int(4 + p[1] * c)
            if 0 <= x0 < bw and 0 <= y0 < bh: board[max(0, y0):y0 + 4, max(0, x0):x0 + 4] = p[5]
        ang = self.angle * (1 if self.flip > 0 else -1) + (180 if self.flip < 0 else 0)
        M = cv2.getRotationMatrix2D(((bw + 8) / 2, (bh + 8) / 2), ang, 1.0)
        rot = cv2.warpAffine(board, M, (bw + 8, bh + 8), borderValue=(12, 10, 30))
        self.g[:] = (12, 10, 30)
        # starry backdrop so the spin reads
        for k in range(40):
            x = (k * 37 + self.t * 10) % GW; y = (k * 53 + self.t * (20 + k % 5 * 7)) % GH; self.px(x, y, (60, 50, 110))
        ox, oy = (GW - bw - 8) // 2, (GH - bh - 8) // 2
        self.g[oy:oy + bh + 8, ox:ox + bw + 8] = rot
        return self.finish()


# ---------------- more side games (variety) ----------------
CAR = ["..1111..", ".122221.", ".133331.", "12222221", "12444421", ".122221.", ".133331.", "12222221", "11....11"]

class Racer(Base):
    """top-down neon road; kick = boost (lines rush), hit = a car spins out in sparks"""
    def __init__(self, seed):
        super().__init__(seed); self.scroll = 0; self.boost = 0; self.cars = []; self.px_ = GW / 2; self.spark = []; self.spawn = 0
        self.pal = [(255, 60, 140), (0, 220, 255), (255, 200, 0), (120, 255, 120)]
    def step(self, dt, kick, hit):
        self.t += dt; self.boost = max(self.boost * (1 - 3 * dt), kick); sp = 90 + 260 * self.boost
        self.scroll += sp * dt; self.spawn += dt; self.shake = max(0, self.shake - dt)
        if self.spawn > 0.7: self.spawn = 0; self.cars.append([30 + self.r.integers(0, 4) * 20, -20, self.r.integers(0, 4), 0])
        for c in self.cars: c[1] += (sp - 60) * dt; c[3] = max(0, c[3] - dt)
        if hit > 0.8 and self.cars:
            c = self.cars[self.r.integers(0, len(self.cars))]; c[3] = 0.6; self.shake = 0.2
            for _ in range(10): a = self.r.random() * 6.3; self.spark.append([c[0] + 8, c[1] + 9, math.cos(a) * 70, math.sin(a) * 70, 0.4])
        self.cars = [c for c in self.cars if c[1] < GH + 20]
        tgt = min(self.cars, key=lambda c: abs(c[1] - (GH - 40)))[0] if self.cars else GW / 2
        self.px_ += ((GW - tgt) * 0.9 - self.px_ + 10 * math.sin(self.t * 3)) * min(1, 2 * dt); self.px_ = min(max(self.px_, 26), GW - 42)
        for s in self.spark: s[0] += s[2] * dt; s[1] += s[3] * dt; s[4] -= dt
        self.spark = [s for s in self.spark if s[4] > 0]
    def draw(self):
        yy = np.linspace(0, 1, GH)[:, None]
        self.g[:] = (np.stack([30 + 40 * yy, 10 + 10 * yy, 60 + 40 * yy], -1) * np.ones((GH, GW, 1))).astype(np.uint8)
        self.rect(18, 0, GW - 36, GH, (25, 25, 35))
        for y in range(-40, GH + 40, 40):
            yy2 = (y + self.scroll) % (GH + 40) - 20
            for lx in (38, 58, 78): self.rect(lx + 10, yy2, 2, 18, (230, 230, 230) if self.boost < 0.6 else (255, 120, 220))
            self.rect(14, yy2, 4, 20, (255, 60, 60)); self.rect(14, yy2 + 20, 4, 20, (255, 255, 255))
            self.rect(GW - 18, yy2, 4, 20, (255, 60, 60)); self.rect(GW - 18, yy2 + 20, 4, 20, (255, 255, 255))
        if self.boost > 0.6:
            for k in range(20): x = self.r.integers(20, GW - 20); y = self.r.integers(0, GH); self.rect(x, y, 1, 14, (255, 255, 255))
        for c in self.cars:
            col = self.pal[c[2]]; pal = {'1': (20, 20, 20), '2': col, '3': (180, 230, 255), '4': (255, 255, 255)}
            if c[3] > 0 and int(self.t * 20) % 2: pal = {k: (255, 255, 255) for k in pal}
            self.sprite(c[0], c[1], CAR, pal)
        self.sprite(self.px_, GH - 40, CAR, {'1': (20, 20, 20), '2': (255, 255, 255), '3': (120, 200, 255), '4': (255, 80, 80)})
        self.rect(self.px_ + 4, GH - 20, 2, 4 + int(8 * self.boost), (255, 160, 60)); self.rect(self.px_ + 10, GH - 20, 2, 4 + int(8 * self.boost), (255, 160, 60))
        for s in self.spark: self.rect(s[0], s[1], 2, 2, (255, 220, 80))
        return self.finish()

class Blobs(Base):
    """falling-blob puzzle: pairs drop; on each strong kick every group of 3+ pops in a flash and the rest fall (chains)"""
    COLS = [(255, 70, 120), (60, 220, 255), (255, 220, 60), (120, 255, 120), (190, 110, 255)]
    def __init__(self, seed):
        super().__init__(seed); self.cw, self.ch = 6, 13; self.c = 18; self.b = np.full((self.ch, self.cw), -1)
        self.new(); self.tick = 0; self.pop = []; self.pt = 0; self.combo = 0
        for j in range(self.ch - 4, self.ch):
            for i in range(self.cw): self.b[j, i] = self.r.integers(0, 5)
    def new(self): self.x = int(self.r.integers(0, self.cw - 1)); self.y = 0; self.pair = (int(self.r.integers(0, 5)), int(self.r.integers(0, 5)))
    def free(self, x, y): return 0 <= x < self.cw and y < self.ch and (y < 0 or self.b[y, x] < 0)
    def settle(self):
        for i in range(self.cw):
            col = [v for v in self.b[:, i] if v >= 0]; self.b[:, i] = -1
            if col: self.b[self.ch - len(col):, i] = col
    def groups(self):
        seen = np.zeros_like(self.b, bool); out = []
        for j in range(self.ch):
            for i in range(self.cw):
                if self.b[j, i] < 0 or seen[j, i]: continue
                st = [(i, j)]; g = []; seen[j, i] = True
                while st:
                    x, y = st.pop(); g.append((x, y))
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        X, Y = x + dx, y + dy
                        if 0 <= X < self.cw and 0 <= Y < self.ch and not seen[Y, X] and self.b[Y, X] == self.b[j, i]: seen[Y, X] = True; st.append((X, Y))
                if len(g) >= 3: out.append(g)
        return out
    def step(self, dt, kick, hit):
        self.t += dt; self.tick += dt; self.pt = max(0, self.pt - dt); self.shake = max(0, self.shake - dt)
        if kick > 0.75 and self.pt <= 0:
            gs = self.groups()
            if gs:
                self.pop = [p for g in gs for p in g]; self.pt = 0.25; self.combo += 1; self.shake = 0.12
                for x, y in self.pop: self.b[y, x] = -1
                self.settle()
            else: self.combo = 0
        if hit > 0.6 and self.free(self.x + 2, self.y) and self.free(self.x + 2, self.y + 1): self.x += 1
        if self.tick > 0.09:
            self.tick = 0
            if self.free(self.x, self.y + 2) and self.free(self.x + 1, self.y + 2): self.y += 1
            else:
                for k, (x, y) in enumerate([(self.x, self.y + 1), (self.x + 1, self.y + 1)]):
                    if 0 <= y < self.ch: self.b[y, x] = self.pair[k]
                self.settle()
                if (self.b[:3] >= 0).sum() > 6: self.b[:6] = -1; self.settle()
                self.new()
    def blob(self, x, y, col, flash=False):
        cx, cy = x + self.c / 2, y + self.c / 2
        self.circle(cx, cy, self.c / 2 - 1, (255, 255, 255) if flash else col)
        if not flash: self.circle(cx - 3, cy - 3, 2, (255, 255, 255))
    def draw(self):
        self.g[:] = (20, 10, 40); ox, oy = (GW - self.cw * self.c) // 2, GH - self.ch * self.c - 10
        self.rect(ox - 3, oy - 3, self.cw * self.c + 6, self.ch * self.c + 6, (120, 80, 200)); self.rect(ox, oy, self.cw * self.c, self.ch * self.c, (0, 0, 0))
        for j in range(self.ch):
            for i in range(self.cw):
                if self.b[j, i] >= 0: self.blob(ox + i * self.c, oy + j * self.c, self.COLS[self.b[j, i]])
        for k, (x, y) in enumerate([(self.x, self.y), (self.x + 1, self.y)]):
            if 0 <= y < self.ch: self.blob(ox + x * self.c, oy + y * self.c, self.COLS[self.pair[k]])
        if self.pt > 0:
            for x, y in self.pop: self.circle(ox + x * self.c + self.c / 2, oy + y * self.c + self.c / 2, self.c * (0.9 - self.pt * 2), (255, 255, 255), fill=False, w=2)
        for k in range(min(self.combo, 8)): self.circle(10 + k * 14, 14, 5, self.COLS[k % 5])
        return self.finish()

class Vector(Base):
    """green-phosphor vector rocks; kick = the ship fires, rocks split; lines only"""
    def __init__(self, seed):
        super().__init__(seed); self.rocks = [self.rock(3) for _ in range(5)]; self.shots = []; self.ang = 0
    def rock(self, size, x=None, y=None):
        n = 9; rad = [size * 7 * (0.7 + 0.3 * self.r.random()) for _ in range(n)]
        return {'x': self.r.random() * GW if x is None else x, 'y': self.r.random() * GH if y is None else y, 'vx': self.r.normal(0, 12), 'vy': self.r.normal(0, 12),
                'a': 0, 'va': self.r.normal(0, 1), 's': size, 'rad': rad}
    def step(self, dt, kick, hit):
        self.t += dt; self.ang += dt * 1.4
        for r in self.rocks: r['x'] = (r['x'] + r['vx'] * dt) % GW; r['y'] = (r['y'] + r['vy'] * dt) % GH; r['a'] += r['va'] * dt
        if kick > 0.55: self.shots.append([GW / 2, GH / 2, math.cos(self.ang) * 160, math.sin(self.ang) * 160, 0.8])
        for s in self.shots: s[0] += s[2] * dt; s[1] += s[3] * dt; s[4] -= dt
        new = []
        for r in self.rocks:
            hitr = False
            for s in self.shots:
                if (s[0] - r['x']) ** 2 + (s[1] - r['y']) ** 2 < (r['s'] * 7) ** 2: s[4] = 0; hitr = True
            if hitr and r['s'] > 1: new += [self.rock(r['s'] - 1, r['x'], r['y']) for _ in range(2)]
            elif not hitr: new.append(r)
        self.rocks = new if new else [self.rock(3) for _ in range(5)]
        self.shots = [s for s in self.shots if s[4] > 0]
    def draw(self):
        self.g[:] = (0, 8, 0); G = (90, 255, 140)
        for r in self.rocks:
            n = len(r['rad']); pts = np.array([[r['x'] + r['rad'][k] * math.cos(r['a'] + k * 6.283 / n), r['y'] + r['rad'][k] * math.sin(r['a'] + k * 6.283 / n)] for k in range(n)], np.int32)
            cv2.polylines(self.g, [pts], True, G, 1)
        c, s_ = math.cos(self.ang), math.sin(self.ang); cx, cy = GW / 2, GH / 2
        ship = np.array([[cx + c * 9, cy + s_ * 9], [cx - c * 6 - s_ * 5, cy - s_ * 6 + c * 5], [cx - c * 3, cy - s_ * 3], [cx - c * 6 + s_ * 5, cy - s_ * 6 - c * 5]], np.int32)
        cv2.polylines(self.g, [ship], True, (220, 255, 220), 1)
        for s in self.shots: self.px(s[0], s[1], (220, 255, 220))
        glow = cv2.GaussianBlur(self.g, (0, 0), 2); self.g = np.clip(self.g.astype(int) + glow.astype(int), 0, 255).astype(np.uint8)
        return self.finish()

class Climber(Base):
    """a tiny figure hopping up through floating platforms; each kick is a jump; the world scrolls down"""
    FIG = [".11.", "1221", ".33.", "3333", ".33.", "3..3"]
    def __init__(self, seed):
        super().__init__(seed); self.cam = 0; self.plats = [(self.r.integers(10, GW - 40), GH - 20 - k * 34, self.r.integers(0, 3)) for k in range(30)]
        self.x, self.y, self.vy = GW / 2, GH - 40, 0; self.best = 0
    def step(self, dt, kick, hit):
        self.t += dt; self.vy += 260 * dt; self.y += self.vy * dt
        tgt = min(self.plats, key=lambda p: abs(p[1] - self.cam - (self.y - 50))); self.x += (tgt[0] + 12 - self.x) * min(1, 2.5 * dt)
        for px, py, k in self.plats:
            sy = py - self.cam
            if self.vy > 0 and px - 4 < self.x < px + 34 and sy - 2 < self.y < sy + 6: self.y = sy; self.vy = 0
        if kick > 0.6 and self.vy == 0: self.vy = -190
        if self.y < GH * 0.45: d = GH * 0.45 - self.y; self.cam -= d; self.y += d
        if self.y > GH + 30: self.y, self.vy = GH * 0.4, 0
        top = min(p[1] for p in self.plats)
        self.plats = [p for p in self.plats if p[1] - self.cam < GH + 20]
        while len(self.plats) < 30: top -= 34; self.plats.append((self.r.integers(10, GW - 40), top, self.r.integers(0, 3)))
    def draw(self):
        yy = np.linspace(0, 1, GH)[:, None]; h = (self.cam * -0.001) % 1
        self.g[:] = (np.stack([20 + 60 * yy, 30 + 50 * (1 - yy), 80 + 40 * yy], -1) * np.ones((GH, GW, 1))).astype(np.uint8)
        for k in range(30): self.px((k * 41) % GW, (k * 67 - self.cam * 0.3) % GH, (200, 200, 255))
        for px, py, k in self.plats:
            sy = py - self.cam; col = [(255, 120, 200), (120, 220, 255), (255, 230, 120)][k]
            self.rect(px, sy, 30, 4, col); self.rect(px, sy + 4, 30, 2, tuple(v // 2 for v in col))
        self.sprite(self.x - 4, self.y - 12, self.FIG, {'1': (40, 40, 40), '2': (255, 220, 200), '3': (255, 80, 160)})
        return self.finish()
