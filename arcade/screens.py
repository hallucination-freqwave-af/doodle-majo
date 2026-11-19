"""Side-panel screens that nobody is playing (2026-11-19): instruments, off-air television, screensavers, a fish tank, things growing, plates from an unknown field guide.
Same interface as the games: step(dt, kick, hit), draw() -> (h, w, 3) uint8, .px = enlargement to reach 528x1080. Optional set_time(t)."""
import numpy as np, math, cv2

class Scr:
    W, H, px = 132, 270, 4
    def __init__(self, seed): self.r = np.random.default_rng(seed); self.t = 0.0; self.g = np.zeros((self.H, self.W, 3), np.uint8); self.k = 0.0; self.init()
    def init(self): pass
    def step(self, dt, kick, hit): self.t += dt; self.k = max(self.k * (1 - 6 * dt), kick); self.tick(dt, kick, hit)
    def tick(self, dt, kick, hit): pass
    def glow(self, amt=1.0, s=1.5): self.g = np.clip(self.g.astype(np.int32) + (cv2.GaussianBlur(self.g, (0, 0), s).astype(np.int32) * amt).astype(np.int32), 0, 255).astype(np.uint8)

SEG7 = {'0': 'abcdef', '1': 'bc', '2': 'abged', '3': 'abgcd', '4': 'fgbc', '5': 'afgcd', '6': 'afgedc', '7': 'abc', '8': 'abcdefg', '9': 'abcdfg'}
def seg7(g, x, y, w, h, th, ch, col):
    if ch == ':':
        cv2.rectangle(g, (x + w // 2 - th // 2, y + h // 3 - th // 2), (x + w // 2 + th // 2, y + h // 3 + th // 2), col, -1)
        cv2.rectangle(g, (x + w // 2 - th // 2, y + 2 * h // 3 - th // 2), (x + w // 2 + th // 2, y + 2 * h // 3 + th // 2), col, -1); return
    m = h // 2; boxes = {'a': (x + th, y, x + w - th, y + th), 'g': (x + th, y + m - th // 2, x + w - th, y + m + th // 2), 'd': (x + th, y + h - th, x + w - th, y + h),
                         'f': (x, y + th, x + th, y + m - 1), 'b': (x + w - th, y + th, x + w, y + m - 1), 'e': (x, y + m + 1, x + th, y + h - th), 'c': (x + w - th, y + m + 1, x + w, y + h - th)}
    for s in SEG7.get(ch, ''): cv2.rectangle(g, boxes[s][:2], boxes[s][2:], col, -1)

# ------------------------------------------------------------------ instruments
_audio = {}
def audio():
    if 'x' not in _audio: _audio['x'] = np.fromfile('mono.f32', dtype=np.float32)
    return _audio['x']

class Scope(Scr):
    """oscilloscope: the song's real waveform on top, the same signal against itself below"""
    W, H, px = 264, 540, 2
    def init(self): self.now = 0.0
    def set_time(self, t): self.now = t
    def draw(self):
        g = self.g; g[:] = (0, 12, 5); W, H = self.W, self.H
        for x in range(0, W, 33): g[:, x] = (0, 40, 18)
        for y in range(0, H, 33): g[y, :] = (0, 40, 18)
        x = audio(); i0 = int(self.now * 22050); s = x[i0:i0 + W * 5:5]
        if len(s) >= W:
            pts = np.stack([np.arange(W), 135 - s[:W] * 230], 1).astype(np.int32); cv2.polylines(g, [pts], False, (120, 255, 160), 1, cv2.LINE_AA)
        a = x[i0:i0 + 900]; b = x[i0 + 37:i0 + 937]
        if len(b) == 900:
            pts = np.stack([W / 2 + a * 220, 400 + b * 220], 1).astype(np.int32); cv2.polylines(g, [pts], False, (90, 255, 140), 1, cv2.LINE_AA)
        self.glow(1.0 + self.k, 2.0); return self.g

class ECG(Scr):
    """heart monitor: every bass drum is a beat"""
    def init(self): self.buf = np.full(self.W, 70.0); self.buf2 = np.full(self.W, 150.0); self.x = 0.0; self.since = 9.0; self.last = None; self.bpm = 89
    def tick(self, dt, kick, hit):
        self.since += dt
        if kick > 0.6 and self.since > 0.18:
            if self.last is not None: self.bpm = int(min(199, max(40, 60 / max(0.3, self.t - self.last))))
            self.last = self.t; self.since = 0.0
        x0 = int(self.x); self.x = (self.x + 46 * dt) % self.W
        for xx in range(x0, int(self.x) + 1 if self.x >= x0 else x0 + 1):
            s = self.since; v = 0.0
            if s < 0.05: v = -45 * (s / 0.05)
            elif s < 0.09: v = -45 + 65 * ((s - 0.05) / 0.04)
            elif s < 0.13: v = 20 * (1 - (s - 0.09) / 0.04)
            elif 0.25 < s < 0.4: v = -8 * math.sin((s - 0.25) / 0.15 * math.pi)
            self.buf[xx % self.W] = 70 + v; self.buf2[xx % self.W] = 150 + 14 * math.sin(self.t * 1.6)
    def draw(self):
        g = self.g; g[:] = (0, 0, 0); W = self.W
        for buf, col in ((self.buf, (60, 255, 90)), (self.buf2, (80, 200, 255))):
            for x in range(W - 1):
                if (x - int(self.x)) % W < 10: continue
                cv2.line(g, (x, int(buf[x])), (x + 1, int(buf[x + 1])), col, 1)
        col = (60, 255, 90) if self.since > 0.12 else (255, 255, 255)
        for j, ch in enumerate(f'{self.bpm:3d}'.replace(' ', '')): seg7(g, 30 + j * 28, 200, 20, 40, 4, ch, col)
        if self.since < 0.15: cv2.circle(g, (112, 215), 6, (255, 60, 80), -1)
        self.glow(0.8); return self.g

class Radar(Scr):
    """a sweep going round; things show up on the loud hits and fade"""
    def init(self): self.a = 0.0; self.blips = []; self.trail = np.zeros((self.H, self.W), np.float32)
    def tick(self, dt, kick, hit):
        self.a += 2.4 * dt
        if hit > 0.7 and self.r.random() < 0.6: self.blips.append([self.r.uniform(12, 58), self.r.uniform(0, 6.283), 6.0])
        for b in self.blips: b[2] -= dt
        self.blips = [b for b in self.blips if b[2] > 0][-12:]
        self.trail *= 0.90; cx, cy = 66, 120
        cv2.line(self.trail, (cx, cy), (int(cx + 60 * math.cos(self.a)), int(cy + 60 * math.sin(self.a))), 1.0, 2)
    def draw(self):
        g = self.g; g[:] = (0, 10, 4); cx, cy = 66, 120
        for rr in (20, 40, 60): cv2.circle(g, (cx, cy), rr, (0, 70, 30), 1)
        cv2.line(g, (cx - 60, cy), (cx + 60, cy), (0, 70, 30), 1); cv2.line(g, (cx, cy - 60), (cx, cy + 60), (0, 70, 30), 1)
        g[..., 1] = np.clip(g[..., 1] + self.trail * 200, 0, 255).astype(np.uint8); g[..., 0] = np.clip(g[..., 0] + self.trail * 60, 0, 255).astype(np.uint8)
        for rr, an, life in self.blips:
            d = (self.a - an) % 6.283; br = math.exp(-d * 0.9); x, y = int(cx + rr * math.cos(an)), int(cy + rr * math.sin(an))
            cv2.circle(g, (x, y), 2, (int(120 * br), int(255 * br), int(140 * br)), -1)
        for j in range(8): cv2.rectangle(g, (12 + j * 14, 215), (20 + j * 14, 215 + int(6 + 30 * abs(math.sin(self.t * 1.3 + j)) * (0.3 + self.k))), (0, 150, 60), -1)
        self.glow(0.7); return self.g

# ------------------------------------------------------------------ off-air
class Bars(Scr):
    """colour bars after the station has signed off; a bass drum knocks it into snow for a moment"""
    def init(self): self.noise = 0.0
    def tick(self, dt, kick, hit):
        self.noise = max(0, self.noise - dt)
        if kick > 0.8: self.noise = 0.13
    def draw(self):
        g = self.g; W, H = self.W, self.H
        if self.noise > 0:
            n = self.r.integers(0, 255, (H // 2, W // 2), dtype=np.uint8); g[:] = cv2.resize(n, (W, H), interpolation=cv2.INTER_NEAREST)[..., None]; return g
        cols = [(192, 192, 192), (192, 192, 0), (0, 192, 192), (0, 192, 0), (192, 0, 192), (192, 0, 0), (0, 0, 192)]; bw = W / 7
        for i, c in enumerate(cols):
            g[:180, int(i * bw):int((i + 1) * bw)] = c; g[180:200, int(i * bw):int((i + 1) * bw)] = cols[6 - i] if i % 2 == 0 else (16, 16, 16)
        g[200:] = (16, 16, 16); g[200:, :22] = (0, 33, 76); g[200:, 22:44] = (235, 235, 235); g[200:, 44:66] = (50, 0, 106)
        y = int((self.t * 60) % (H + 40)) - 40; g[max(0, y):max(0, y + 26)] = (g[max(0, y):max(0, y + 26)] * 0.6).astype(np.uint8)
        return g

class Weather(Scr):
    """the late-night weather chart: isobars drifting, no forecaster"""
    def init(self):
        self.c = [(self.r.random() * self.W, self.r.random() * self.H, self.r.uniform(-6, 6), self.r.uniform(-4, 4), self.r.choice([-1, 1]) * self.r.uniform(0.6, 1.2), self.r.uniform(30, 55)) for _ in range(5)]
        self.yy, self.xx = np.mgrid[0:self.H, 0:self.W].astype(np.float32)
    def draw(self):
        g = self.g; g[:] = (14, 30, 84); f = np.zeros((self.H, self.W), np.float32); marks = []
        for x, y, vx, vy, amp, sg in self.c:
            cx = (x + vx * self.t) % self.W; cy = (y + vy * self.t) % self.H; f += amp * np.exp(-((self.xx - cx) ** 2 + (self.yy - cy) ** 2) / (2 * sg * sg)); marks.append((int(cx), int(cy), amp))
        f += 0.12 * self.k
        for lv in np.arange(-1.0, 1.21, 0.2):
            cs, _ = cv2.findContours((f > lv).astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE); cv2.drawContours(g, cs, -1, (235, 235, 245), 1)
        for cx, cy, amp in marks:
            col = (255, 90, 90) if amp > 0 else (120, 200, 255); cv2.circle(g, (cx, cy), 4, col, 1); cv2.line(g, (cx - 2, cy), (cx + 2, cy), col, 1)
            if amp > 0: cv2.line(g, (cx, cy - 2), (cx, cy + 2), col, 1)
        return g

class VCR(Scr):
    """the video recorder nobody ever set: 12:00, blinking on the bass drum"""
    def init(self): self.on = True; self.since = 9.0; self.roll = 0.0
    def tick(self, dt, kick, hit):
        self.since += dt
        if kick > 0.6 and self.since > 0.2: self.on = not self.on; self.since = 0.0
        if hit > 0.75: self.roll = self.r.uniform(60, 220)
    def draw(self):
        g = self.g; g[:] = (12, 22, 190)
        if self.on:
            x = 12
            for ch in '12:00': w = 10 if ch == ':' else 22; seg7(g, x, 105, w, 46, 5, ch, (245, 245, 245)); x += w + 5
        cv2.fillPoly(g, [np.array([(12, 18), (12, 34), (24, 26)], np.int32)], (245, 245, 245))
        y0 = int(self.roll + 6 * math.sin(self.t * 3)) % (self.H - 20)
        for k in range(14):
            y = y0 + int(self.r.integers(0, 18)); x = int(self.r.integers(0, self.W - 30)); g[y % self.H, x:x + int(self.r.integers(8, 60))] = (230, 230, 240)
        g[::2] = (g[::2] * 0.88).astype(np.uint8); return g

# ------------------------------------------------------------------ screensavers
class Warp(Scr):
    def init(self): self.s = self.r.uniform(-1, 1, (260, 3)); self.s[:, 2] = self.r.uniform(0.05, 1, 260); self.prev = None
    def tick(self, dt, kick, hit):
        self.prev = self.s.copy(); self.s[:, 2] -= dt * (0.25 + 1.4 * self.k); m = self.s[:, 2] <= 0.03
        self.s[m] = np.stack([self.r.uniform(-1, 1, m.sum()), self.r.uniform(-1, 1, m.sum()), np.ones(m.sum())], 1); self.prev[m] = self.s[m]
    def draw(self):
        g = self.g; g[:] = (0, 0, 6)
        for (x, y, z), (px_, py_, pz) in zip(self.s, self.prev if self.prev is not None else self.s):
            a = (int(66 + x / z * 50), int(135 + y / z * 100)); b = (int(66 + px_ / pz * 50), int(135 + py_ / pz * 100)); c = int(255 * (1 - z) ** 0.5)
            cv2.line(g, b, a, (c, c, min(255, c + 30)), 1)
        return g

class Pipes(Scr):
    def init(self): self.heads = []; self.acc = 0.0; self.life = 0.0; self.g[:] = (4, 4, 10); self.new()
    def new(self):
        col = [(255, 120, 200), (120, 220, 255), (255, 230, 120), (150, 255, 170), (190, 140, 255)][int(self.r.integers(0, 5))]
        self.heads.append([int(self.r.integers(2, 20)) * 6, int(self.r.integers(2, 43)) * 6, int(self.r.integers(0, 4)), col]); self.heads = self.heads[-4:]
    def tick(self, dt, kick, hit):
        self.acc += dt; self.life += dt
        if kick > 0.8 and self.r.random() < 0.6: self.new()
        if self.life > 9: self.g[:] = (4, 4, 10); self.life = 0; self.heads = []; self.new()
        while self.acc > 0.055:
            self.acc -= 0.055
            for h in self.heads:
                if self.r.random() < 0.22: h[2] = (h[2] + int(self.r.choice([1, 3]))) % 4; cv2.circle(self.g, (h[0], h[1]), 4, h[3], -1); cv2.circle(self.g, (h[0] - 1, h[1] - 1), 1, (255, 255, 255), -1)
                dx, dy = [(1, 0), (0, 1), (-1, 0), (0, -1)][h[2]]; nx, ny = h[0] + dx * 6, h[1] + dy * 6
                if not (6 <= nx < self.W - 6 and 6 <= ny < self.H - 6): h[2] = (h[2] + 2) % 4; continue
                cv2.line(self.g, (h[0], h[1]), (nx, ny), h[3], 5); cv2.line(self.g, (h[0] - (dy != 0), h[1] - (dx != 0)), (nx - (dy != 0), ny - (dx != 0)), tuple(min(255, c + 70) for c in h[3]), 1)
                h[0], h[1] = nx, ny
    def draw(self): return self.g

CAT = [["..#....#....", ".###..###...", ".########...", ".#.####.#..#", ".########.##", "..#########.", "..########..", "..#.#..#.#.."],
       ["..#....#....", ".###..###...", ".########...", ".#.####.#.#.", ".########.#.", "..########..", "..########..", "...#.##.#..."]]
class Cats(Scr):
    """night roofs; cats cross, one after another, and jump on the bass drum"""
    def init(self):
        self.cats = [[self.r.random() * self.W, lvl, self.r.choice([-1, 1]) * self.r.uniform(14, 34), 0.0] for lvl in (158, 204, 244) for _ in range(2)]
        self.roofs = [(int(self.r.integers(0, self.W)), int(self.r.integers(14, 40)), lvl) for lvl in (158, 204, 244) for _ in range(5)]
        self.stars = [(int(self.r.integers(0, self.W)), int(self.r.integers(0, 130))) for _ in range(40)]
    def tick(self, dt, kick, hit):
        for c in self.cats:
            c[0] = (c[0] + c[2] * dt) % (self.W + 24) ; c[3] = max(c[3] * (1 - 5 * dt), 1.0 if kick > 0.7 else 0)
    def draw(self):
        g = self.g; yy = np.linspace(0, 1, self.H)[:, None]; g[:] = (np.stack([18 + 30 * yy, 14 + 20 * yy, 50 + 50 * yy], -1) * np.ones((self.H, self.W, 1))).astype(np.uint8)
        for x, y in self.stars: g[y, x] = (220, 220, 255) if (x + int(self.t * 3)) % 7 else (90, 90, 140)
        cv2.circle(g, (98, 46), 22, (250, 240, 200), -1); cv2.circle(g, (90, 40), 5, (232, 220, 180), -1); cv2.circle(g, (104, 54), 3, (232, 220, 180), -1)
        for lvl, shade in ((158, 86), (204, 62), (244, 40)):
            g[lvl:] = (shade, shade, shade + 14)
            for x, w, l in self.roofs:
                if l == lvl: cv2.fillPoly(g, [np.array([(x - w, lvl), (x, lvl - w // 2), (x + w, lvl)], np.int32)], (shade, shade, shade + 14))
            shade = shade
        for x, lvl, v, j in self.cats:
            pat = CAT[int(self.t * 6 + lvl) % 2]; y0 = int(lvl - 8 - 18 * j)
            y0 -= 8
            for r_, row in enumerate(pat):
                for c_, ch in enumerate(row if v > 0 else row[::-1]):
                    xx = int(x) - 24 + c_ * 2
                    if ch == '#' and 0 <= xx < self.W - 1 and 0 <= y0 + r_ * 2 < self.H - 1: g[y0 + r_ * 2:y0 + r_ * 2 + 2, xx:xx + 2] = (0, 0, 0)
            ex = int(x) - 24 + (9 if v > 0 else 2) * 2
            if 0 <= ex < self.W - 1: g[y0 + 6:y0 + 8, ex:ex + 2] = (255, 220, 60)
        return g

# ------------------------------------------------------------------ the tank
class Tank(Scr):
    """a fish tank left on; a bass drum drops food"""
    def init(self):
        self.fish = [[self.r.random() * self.W, self.r.uniform(40, 190), self.r.choice([-1, 1]) * self.r.uniform(8, 22), int(self.r.integers(0, 4)), self.r.random() * 6] for _ in range(8)]
        self.cory = [[self.r.random() * self.W, self.r.uniform(232, 246), 0.0, self.r.choice([-1, 1])] for _ in range(6)]
        self.food = []; self.bub = [[40, 250.0]]; self.plants = [(int(self.r.integers(6, self.W - 6)), int(self.r.integers(30, 90))) for _ in range(7)]
    def tick(self, dt, kick, hit):
        if kick > 0.75 and len(self.food) < 12: self.food += [[self.r.uniform(15, self.W - 15), 22.0] for _ in range(3)]
        for f in self.food: f[1] += 14 * dt
        for fi in self.fish:
            tgt = min(self.food, key=lambda f: abs(f[0] - fi[0]) + abs(f[1] - fi[1])) if self.food else None
            if tgt is not None and abs(tgt[0] - fi[0]) + abs(tgt[1] - fi[1]) < 90:
                fi[2] = math.copysign(26, tgt[0] - fi[0]) if abs(tgt[0] - fi[0]) > 2 else fi[2]; fi[1] += max(-20, min(20, tgt[1] - fi[1])) * dt * 2
                if abs(tgt[0] - fi[0]) < 4 and abs(tgt[1] - fi[1]) < 4 and tgt in self.food: self.food.remove(tgt)
            else: fi[1] += 5 * math.sin(self.t * 1.2 + fi[4]) * dt
            fi[0] += fi[2] * dt
            if fi[0] < 6 or fi[0] > self.W - 6: fi[2] *= -1; fi[0] = min(max(fi[0], 6), self.W - 6)
        for c in self.cory:
            if c[2] <= 0 and self.r.random() < 0.02: c[2] = self.r.uniform(0.3, 0.9); c[3] = self.r.choice([-1, 1])
            if c[2] > 0: c[0] = min(max(c[0] + c[3] * 34 * dt, 4), self.W - 4); c[2] -= dt
        self.food = [f for f in self.food if f[1] < 240]
        if self.r.random() < 0.15: self.bub.append([40 + self.r.uniform(-3, 3), 248.0])
        for b in self.bub: b[1] -= 40 * dt; b[0] += math.sin(self.t * 6 + b[1]) * 0.3
        self.bub = [b for b in self.bub if b[1] > 16]
    def draw(self):
        g = self.g; yy = np.linspace(0, 1, self.H)[:, None]; g[:] = (np.stack([10 + 20 * yy, 110 - 50 * yy, 130 - 40 * yy], -1) * np.ones((self.H, self.W, 1))).astype(np.uint8)
        g[:14] = (20, 20, 26); g[14:17] = (200, 240, 250); g[248:] = (196, 170, 120); g[248:250] = (220, 200, 150)
        for x, h in self.plants:
            pts = [(int(x + 5 * math.sin(self.t * 1.3 + k * 0.5 + x) * k / 6), 248 - int(h * k / 6)) for k in range(7)]; cv2.polylines(g, [np.array(pts, np.int32)], False, (40, 150, 70), 2)
        for x, y in self.food: g[int(y):int(y) + 2, int(x):int(x) + 2] = (255, 210, 90)
        for x, y, v, kind, ph in self.fish:
            col = [(255, 120, 60), (250, 230, 90), (120, 200, 255), (255, 130, 200)][kind]; d = 1 if v > 0 else -1; x, y = int(x), int(y)
            cv2.ellipse(g, (x, y), (6, 3), 0, 0, 360, col, -1); cv2.fillPoly(g, [np.array([(x - d * 5, y), (x - d * 10, y - 3), (x - d * 10, y + 3)], np.int32)], col); g[y - 1, min(self.W - 1, max(0, x + d * 3))] = (0, 0, 0)
        for x, y, mv, d in self.cory:
            x, y = int(x), int(y); cv2.ellipse(g, (x, y), (4, 2), 0, 0, 360, (150, 150, 140), -1); g[y, max(0, x - 4):x + 4] = (60, 60, 60); g[y - 1, min(self.W - 1, max(0, x + int(d) * 2))] = (0, 0, 0)
        for x, y in self.bub: cv2.circle(g, (int(x), int(y)), 1, (220, 245, 255), 1)
        return g

# ------------------------------------------------------------------ growing
class Life(Scr):
    """cells that keep to their own rules; a bass drum throws in a handful more"""
    W, H, px = 66, 135, 8
    def init(self): self.c = (self.r.random((self.H, self.W)) < 0.14); self.age = np.zeros((self.H, self.W), np.int32); self.acc = 0.0
    def tick(self, dt, kick, hit):
        self.acc += dt
        if kick > 0.75:
            y, x = int(self.r.integers(0, self.H - 10)), int(self.r.integers(0, self.W - 10)); self.c[y:y + 10, x:x + 10] |= self.r.random((10, 10)) < 0.5
        while self.acc > 0.13:
            self.acc -= 0.13; n = sum(np.roll(np.roll(self.c, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0))
            new = (n == 3) | (self.c & (n == 2)); self.age = np.where(new, self.age + 1, 0); self.c = new
            if self.c.sum() < 60: self.c |= self.r.random((self.H, self.W)) < 0.12
    def draw(self):
        a = np.clip(self.age, 0, 12)[..., None] / 12.0; col = np.array([255, 255, 255]) * (1 - a) + np.array([200, 70, 230]) * a
        self.g = np.where(self.c[..., None], col, (10, 4, 20)).astype(np.uint8); return self.g

class Pet(Scr):
    """a small grey screen where something is growing on its own; it hops on the bass drum"""
    W, H, px = 66, 135, 8
    def init(self): self.hop = 0.0; self.hearts = []
    def tick(self, dt, kick, hit):
        self.hop = max(self.hop * (1 - 7 * dt), 1.0 if kick > 0.7 else 0)
        if hit > 0.8: self.hearts.append([33 + self.r.uniform(-14, 14), 70.0])
        for h in self.hearts: h[1] -= 16 * dt
        self.hearts = [h for h in self.hearts if h[1] > 8][-5:]
    def draw(self):
        g = self.g; bg, ink = (168, 186, 150), (38, 48, 40); g[:] = bg; cv2.rectangle(g, (3, 3), (62, 131), ink, 1)
        r = int(7 + min(9, self.t * 1.8)); cx, cy = 33, int(104 - r - 8 * self.hop)
        cv2.circle(g, (cx, cy), r, ink, -1)
        for s in (-1, 1): cv2.fillPoly(g, [np.array([(cx + s * r, cy - r // 3), (cx + s * (r - 1), cy - r - r // 2), (cx + s * (r // 4), cy - r + 1)], np.int32)], ink)
        ey = cy - r // 5; blink = int(self.t * 2) % 7 == 0
        for s in (-1, 1): g[ey:ey + (1 if blink else 2), cx + s * (r // 2) - 1:cx + s * (r // 2) + 1] = bg
        g[105, 8:58] = ink
        for x, y in self.hearts:
            x, y = int(x), int(y); g[y, x - 2:x] = ink; g[y, x + 1:x + 3] = ink; g[y + 1, x - 2:x + 3] = ink; g[y + 2, x - 1:x + 2] = ink; g[y + 3, x] = ink
        for j in range(3): cv2.rectangle(g, (12 + j * 16, 116), (20 + j * 16, 124), ink, 1 if j != int(self.t) % 3 else -1)
        return g

# ------------------------------------------------------------------ the field guide
class Plates(Scr):
    """plates from a field guide to nothing in particular: fine lines, one red mark, a page turned every other bass drum"""
    W, H, px = 264, 540, 2
    def init(self): self.page = 0; self.kc = 0; self.since = 9.0; self.cur = self.render(0); self.old = self.cur; self.turn = 1.0
    def render(self, n):
        r = np.random.default_rng(1000 + n * 7 + int(self.r.integers(0, 1)) ); g = np.zeros((self.H, self.W, 3), np.uint8); g[:] = (236, 226, 204); ink = (60, 46, 40)
        for k in range(3): self.scribble(g, r, 24, 30 + k * 9, int(r.integers(60, 200)), ink)
        cx, cy = 132 + int(r.integers(-20, 20)), 250; m = int(r.integers(5, 9)); ph = r.random(m) * 6.283; am = r.random(m) * 0.22; asp = r.uniform(0.6, 1.5)
        def outline(scale):
            pts = []
            for a in np.linspace(0, 6.283, 90, endpoint=False):
                rad = 80 * scale * (1 + sum(am[j] * math.sin((j + 1) * a + ph[j]) for j in range(m)) * 0.6); pts.append((cx + rad * math.cos(a) * min(1.2, asp), cy + rad * math.sin(a) / max(0.8, asp) * 1.3))
            return np.array(pts, np.int32)
        cv2.polylines(g, [outline(1.0)], True, ink, 1, cv2.LINE_AA)
        for sc in (0.72, 0.45): cv2.polylines(g, [outline(sc)], True, (150, 130, 115), 1, cv2.LINE_AA)
        o = outline(1.0)
        for k in range(int(r.integers(3, 6))):
            p = o[int(r.integers(0, 90))]; side = 1 if p[0] > cx else -1; q = (int(p[0] + side * r.integers(20, 50)), int(p[1] + r.integers(-30, 30)))
            cv2.line(g, tuple(int(v) for v in p), q, ink, 1, cv2.LINE_AA); cv2.circle(g, tuple(int(v) for v in p), 2, ink, -1); self.scribble(g, r, q[0] + (4 if side > 0 else -44), q[1], 40, ink)
        p = o[int(r.integers(0, 90))]; cv2.circle(g, (int((p[0] + cx) / 2), int((p[1] + cy) / 2)), 5, (214, 40, 40), -1)   # the one red mark
        for x in range(40, 225, 4): g[cy, x] = (150, 130, 115)
        cv2.line(g, (40, 430), (150, 430), ink, 1)
        for k in range(6): cv2.line(g, (40 + k * 22, 426), (40 + k * 22, 434), ink, 1)
        for k in range(int(r.integers(3, 7))): self.scribble(g, r, 24, 460 + k * 10, int(r.integers(80, 215)), ink)
        for k in range(n % 6 + 1): cv2.circle(g, (244 - k * 8, 520), 2, ink, -1)
        return g
    @staticmethod
    def scribble(g, r, x, y, length, ink):
        pts = [(x + k, y + int(r.integers(-2, 3)) * (r.random() > 0.2)) for k in range(0, length, 3)]
        if len(pts) > 1: cv2.polylines(g, [np.array(pts, np.int32)], False, ink, 1)
    def tick(self, dt, kick, hit):
        self.since += dt; self.turn = min(1.0, self.turn + dt / 0.22)
        if kick > 0.6 and self.since > 0.2:
            self.since = 0.0; self.kc += 1
            if self.kc % 2 == 0: self.page += 1; self.old = self.cur; self.cur = self.render(self.page); self.turn = 0.0
    def draw(self):
        if self.turn >= 1.0: self.g = self.cur; return self.g
        x = int(self.W * (1 - self.turn)); g = self.old.copy(); g[:, x:] = self.cur[:, :self.W - x]; g[:, max(0, x - 6):x] = (g[:, max(0, x - 6):x] * 0.7).astype(np.uint8); self.g = g; return g

SCREENS = {'scope': Scope, 'ecg': ECG, 'radar': Radar, 'bars': Bars, 'weather': Weather, 'vcr': VCR, 'warp': Warp, 'pipes': Pipes, 'cats': Cats,
           'tank': Tank, 'life': Life, 'pet': Pet, 'plates': Plates}

if __name__ == '__main__':
    from PIL import Image
    ims = []
    for name, C in SCREENS.items():
        o = C(5)
        for k in range(210):
            if hasattr(o, 'set_time'): o.set_time(60 + k / 30)
            o.step(1 / 30, float(k % 20 == 0), float(k % 31 == 0)); fr = o.draw()
        assert fr.shape[1] * o.px == 528 and fr.shape[0] * o.px == 1080, (name, fr.shape)
        ims.append(Image.fromarray(cv2.resize(fr, (264, 540), interpolation=cv2.INTER_NEAREST if o.px > 2 else cv2.INTER_AREA)))
    sh = Image.new('RGB', (264 * 7, 540 * 2)); [sh.paste(im, ((k % 7) * 264, (k // 7) * 540)) for k, im in enumerate(ims)]; sh.save('screens.jpg', quality=88); print(len(ims), 'ok')
