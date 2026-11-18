"""Racing variations for the side panels, 1983-2000.
Pseudo-3D (behind the car) styles share one road renderer; top-down styles are their own classes.
Every game: step(dt, kick, hit), draw() -> (h, w, 3) uint8.  .px tells the panel how much to enlarge."""
import numpy as np, math, cv2

PANEL_W, PANEL_H = 528, 1080

def lerp(a, b, t): return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

# ---------------------------------------------------------------- pseudo-3D road
STYLES = {
    'vector83': dict(res=1, sky=((0, 0, 0), (0, 0, 0)), ground=((0, 0, 0), (0, 0, 0)), road=((0, 0, 0), (0, 0, 0)), rumble=((0, 0, 0), (0, 0, 0)),
                     line=(80, 255, 120), hor=0.42, roadw=1.5, curve=0.9, hill=0.6, objs='pylon', wire=True, fog=None, spd=1.0),
    'coast86': dict(res=1, sky=((40, 120, 255), (255, 170, 120)), ground=((60, 200, 90), (40, 170, 70)), road=((110, 110, 120), (100, 100, 110)),
                    rumble=((255, 255, 255), (230, 30, 30)), line=(255, 255, 255), hor=0.40, roadw=1.6, curve=1.0, hill=0.5, objs='palm', sun=(255, 230, 120),
                    sea=(30, 90, 220), fog=None, spd=1.1),
    'neon89': dict(res=1, sky=((20, 0, 50), (150, 30, 140)), ground=((25, 10, 40), (35, 15, 55)), road=((30, 30, 45), (40, 40, 60)),
                   rumble=((255, 40, 200), (40, 220, 255)), line=(255, 230, 120), hor=0.38, roadw=1.5, curve=1.1, hill=0.3, objs='lamp', skyline=True, fog=None, spd=1.2),
    'snow93': dict(res=1, sky=((150, 160, 180), (220, 225, 235)), ground=((240, 245, 255), (215, 225, 240)), road=((90, 95, 110), (80, 85, 100)),
                   rumble=((255, 255, 255), (40, 90, 220)), line=(255, 255, 255), hor=0.36, roadw=1.4, curve=1.3, hill=0.9, objs='pine', mountains=(120, 130, 160),
                   fog=((225, 230, 240), 0.6), spd=1.0),
    'ps1_97': dict(res=2, sky=((90, 140, 200), (200, 210, 220)), ground=((70, 110, 60), (60, 95, 52)), road=((95, 95, 100), (88, 88, 94)),
                   rumble=((200, 200, 60), (60, 60, 60)), line=(230, 230, 230), hor=0.40, roadw=1.5, curve=0.9, hill=0.6, objs='block',
                   fog=((190, 200, 210), 1.0), dither=True, wobble=True, spd=1.2),
    'rainbow99': dict(res=2, sky=((0, 0, 10), (10, 0, 40)), ground=None, road=None, rumble=((255, 255, 255), (255, 255, 255)), line=None,
                      hor=0.35, roadw=1.3, curve=1.2, hill=1.0, objs='star', rainbow=True, fog=None, spd=1.3),
    'rain00': dict(res=2, sky=((5, 5, 15), (30, 25, 50)), ground=((15, 15, 25), (18, 18, 30)), road=((25, 25, 35), (30, 30, 42)),
                   rumble=((180, 180, 190), (60, 60, 70)), line=(220, 220, 160), hor=0.40, roadw=1.6, curve=0.8, hill=0.3, objs='lamp', skyline=True,
                   rain=True, wet=True, fog=((20, 18, 35), 0.7), trail=True, spd=1.3),
}

class PseudoRoad:
    def __init__(self, seed, style):
        self.st = st = STYLES[style]; self.r = np.random.default_rng(seed)
        self.W, self.H = 132 * st['res'], 270 * st['res']; self.px = PANEL_W // self.W
        self.t = 0.0; self.pos = 0.0; self.boost = 0.0; self.curve = 0.0; self.hill = 0.0; self.skyx = 0.0; self.flash = 0.0; self.shake = 0.0
        self.ph = self.r.random() * 6.3; self.F = 6.0; self.K = 7.0
        self.objs = [[k * 2.2 + self.r.random(), int(self.r.integers(0, 2)), self.r.random()] for k in range(1, 40)]
        self.cars = [[3 + k * 7 + self.r.random() * 3, self.r.choice([-0.45, 0.0, 0.45]), int(self.r.integers(0, 5))] for k in range(4)]
        self.steer = 0.0; self.prev = None
        self.drops = [(self.r.random() * self.W, self.r.random() * self.H) for _ in range(160)]
        self.stars = [(self.r.random() * self.W, self.r.random() * self.H, self.r.random()) for _ in range(120)]
    def step(self, dt, kick, hit):
        st = self.st; self.t += dt
        self.boost = max(self.boost * (1 - 2.5 * dt), kick); sp = st['spd'] * (1.0 + 2.0 * self.boost)
        self.pos += dt * sp
        self.curve = st['curve'] * (0.8 * math.sin(self.t * 0.33 + self.ph) + 0.4 * math.sin(self.t * 0.81 + 2 * self.ph))
        self.hill = st['hill'] * math.sin(self.t * 0.47 + self.ph)
        self.skyx += self.curve * sp * dt * 18
        self.steer += (-self.curve * 0.35 - self.steer) * min(1, 2 * dt)
        self.flash = max(0, self.flash - dt); self.shake = max(0, self.shake - dt)
        if hit > 0.85: self.flash = 0.12
        if kick > 0.8: self.shake = 0.08
        base = self.pos * self.F
        for o in self.objs:
            if o[0] < base + 0.2: o[0] += 40 * 2.2; o[1] = int(self.r.integers(0, 2)); o[2] = self.r.random()
        for c in self.cars:
            c[0] += dt * self.F * st['spd'] * 0.55
            if c[0] < base + self.K * 1.35 or c[0] > base + 60: c[0] = base + 25 + self.r.random() * 20; c[1] = float(self.r.choice([-0.45, 0.0, 0.45])); c[2] = int(self.r.integers(0, 5))
    # projection helpers
    def hor(self): return int(self.H * (self.st['hor'] + 0.04 * self.hill))
    def proj(self, n):
        d = n - self.pos * self.F
        if d <= self.K * 1.0: return None
        p = self.K / d; return p
    def row(self, p): return self.hor() + p * (self.H - self.hor())
    def cx(self, p): return self.W / 2 + self.curve * self.W * (1 - p) ** 2 * 0.9 + self.steer * self.W * 0.25 * p
    def half(self, p): return self.st['roadw'] * self.W * p * 0.5
    def draw(self):
        st = self.st; W, H = self.W, self.H; g = np.zeros((H, W, 3), np.uint8); hz = self.hor()
        # sky
        top, bot = st['sky']; yy = np.linspace(0, 1, max(1, hz))[:, None, None]
        g[:hz] = (np.array(top) * (1 - yy) + np.array(bot) * yy).astype(np.uint8)
        if st.get('rainbow') or st.get('wire'):
            for x, y, b in self.stars:
                X = int((x - self.skyx * 0.2 * b) % W); Y = int(y)
                if 0 <= Y < H: g[Y, X] = (int(120 + 135 * b),) * 3
        if st.get('sun'):
            sx = int((W * 0.5 - self.skyx * 0.3) % (W * 1.6) - W * 0.3); sy = int(hz * 0.62)
            cv2.circle(g, (sx, sy), int(W * 0.17), st['sun'], -1)
            for k in range(4): g[sy + 4 + k * 4: sy + 6 + k * 4, max(0, sx - W // 5):sx + W // 5] = bot
        if st.get('mountains'):
            pts = [(x, int(hz - (0.18 + 0.1 * math.sin((x + self.skyx * 0.5) / 9) + 0.06 * math.sin((x + self.skyx * 0.5) / 4.1)) * hz * 0.5)) for x in range(-2, W + 3, 3)]
            cv2.fillPoly(g, [np.array(pts + [(W + 2, hz), (-2, hz)], np.int32)], st['mountains'])
            cv2.fillPoly(g, [np.array([(x, min(hz, y + 4)) for x, y in pts] + [(W + 2, hz), (-2, hz)], np.int32)], tuple(int(v * 0.8) for v in st['mountains']))
        if st.get('skyline'):
            r = np.random.default_rng(7)
            for k in range(40):
                bx = int((k * 13 - self.skyx * 0.6) % (W + 40)) - 20; bw = int(r.integers(6, 16)); bh = int(r.integers(int(hz * 0.15), int(hz * 0.6)))
                cv2.rectangle(g, (bx, hz - bh), (bx + bw, hz), (15, 10, 30) if not st.get('rain') else (10, 10, 20), -1)
                for wy in range(hz - bh + 2, hz - 1, 3):
                    for wx in range(bx + 1, bx + bw - 1, 3):
                        if (k * 7 + wy + wx) % 4 == 0 and 0 <= wx < W: g[wy, wx] = (255, 220, 120) if k % 3 else (120, 220, 255)
        if st.get('wire'):
            pts = [(x, int(hz - (8 + 6 * abs(math.sin((x + self.skyx * 0.5) / 11)) + 4 * abs(math.sin((x + self.skyx) / 5))) * st['res'])) for x in range(0, W + 1, 4)]
            cv2.polylines(g, [np.array(pts, np.int32)], False, st['line'], 1)
        # road, row by row
        prev_alt = None; edgesL = []; edgesR = []
        for y in range(hz, H):
            p = (y - hz + 1) / (H - hz); n = self.pos * self.F + self.K / p; alt = int(n) % 2
            c = self.cx(p); h = self.half(p); rb = max(1, h * 0.12)
            xl, xr = int(c - h), int(c + h)
            if st.get('wire'):
                edgesL.append((xl, y)); edgesR.append((xr, y))
                if prev_alt is not None and alt != prev_alt: g[y, max(0, xl):max(0, min(W, xr))] = st['line']
                prev_alt = alt; continue
            if st['ground'] is not None: g[y] = st['ground'][alt]
            if st.get('sea') and y < hz + (H - hz) * 0.25: g[y, :max(0, int(c - h * 2.6))] = st['sea'] if (y + int(self.t * 10)) % 5 else (220, 240, 255)
            if st.get('rainbow'):
                rc = [(255, 50, 80), (255, 150, 0), (255, 240, 0), (60, 230, 90), (0, 170, 255), (90, 80, 255), (200, 70, 255)][int(n) % 7]
                g[y, max(0, xl):max(0, min(W, xr))] = tuple(int(v * (0.45 + 0.55 * p)) for v in rc)
            else:
                g[y, max(0, xl):max(0, min(W, xr))] = st['road'][alt]
            g[y, max(0, int(xl - rb)):max(0, min(W, xl))] = st['rumble'][alt]
            g[y, max(0, xr):max(0, min(W, int(xr + rb)))] = st['rumble'][alt]
            if st.get('line') and alt == 0:
                lw = max(1, int(h * 0.03))
                for f in (-1 / 3, 1 / 3):
                    lx = int(c + f * h); g[y, max(0, lx - lw):max(0, min(W, lx + lw))] = st['line']
            if st.get('wet') and alt == 1:
                for f in (-1.25, 1.25):  # reflections of the lamps on the wet road
                    lx = int(c + f * h * 0.75); g[y, max(0, lx - 1):max(0, min(W, lx + 1))] = (200, 170, 90)
        if st.get('wire'):
            cv2.polylines(g, [np.array(edgesL, np.int32)], False, st['line'], 1); cv2.polylines(g, [np.array(edgesR, np.int32)], False, st['line'], 1)
            cv2.polylines(g, [np.array([(int(self.cx((y - hz + 1) / (H - hz))), y) for y in range(hz, H, 2)], np.int32)], False, tuple(v // 2 for v in st['line']), 1)
        # sprites far -> near
        items = [(o[0], 'obj', o) for o in self.objs] + [(c[0], 'car', c) for c in self.cars]
        for n, kind, o in sorted(items, key=lambda x: -x[0]):
            p = self.proj(n)
            if p is None or p > 1.2: continue
            y = int(self.row(p)); c = self.cx(p); h = self.half(p)
            if kind == 'obj': self.obj(g, int(c + (1 if o[1] else -1) * h * 1.45), y, p, o[2])
            else: self.car(g, int(c + o[1] * h), y, p, o[2])
        # player
        bob = int(2 * self.st['res'] * abs(math.sin(self.t * 18)) * (0.3 + self.boost))
        self.car(g, int(W / 2 + self.steer * W * 0.1), H - 6 * st['res'] - bob, 0.95, -1, player=True)
        # finish
        if st.get('rain'):
            for k, (x, y) in enumerate(self.drops):
                yy = (y + self.t * 600) % H; xx = (x - self.t * 120) % W
                cv2.line(g, (int(xx), int(yy)), (int(xx - 3), int(yy + 10)), (150, 160, 200), 1)
        if st.get('fog'):
            fc, amt = st['fog']; ys = np.arange(H); depth = np.clip(1 - (ys - hz) / (H - hz), 0, 1) ** 2.2 * amt; depth[:hz] = 0
            g = (g * (1 - depth[:, None, None]) + np.array(fc) * depth[:, None, None]).astype(np.uint8)
        if st.get('wire'): g = np.clip(g.astype(int) + cv2.GaussianBlur(g, (0, 0), 1.5).astype(int), 0, 255).astype(np.uint8)
        if st.get('wobble'):
            jit = (np.sin(np.arange(H) * 0.7 + self.t * 40) * 1.2).astype(int)
            for y in range(hz, H, 2): g[y] = np.roll(g[y], jit[y], axis=0)
        if st.get('dither'):
            bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16 - 0.5
            th = np.tile(bayer, (H // 4 + 1, W // 4 + 1))[:H, :W, None] * 24
            g = (np.clip((g + th) // 24 * 24, 0, 255)).astype(np.uint8)
        if st.get('trail'):
            if self.prev is not None: g = cv2.addWeighted(g, 0.6, self.prev, 0.4, 0)
            self.prev = g.copy()
            g = np.clip(g.astype(int) + cv2.GaussianBlur(g, (0, 0), 4).astype(int) // 2, 0, 255).astype(np.uint8)
        if self.flash > 0: g = np.clip(g.astype(int) + 110, 0, 255).astype(np.uint8)
        if self.shake > 0: g = np.roll(g, int(self.r.integers(-2, 3)) * st['res'], axis=0)
        return g
    # --- sprites
    def obj(self, g, x, y, p, v):
        st = self.st; s = max(1, p * self.W * 0.5); kind = st['objs']; W, H = self.W, self.H
        if kind == 'palm':
            cv2.line(g, (x, y), (int(x + s * 0.15), int(y - s * 1.3)), (120, 80, 40), max(1, int(s * 0.08)))
            tx, ty = int(x + s * 0.15), int(y - s * 1.3)
            for a in range(6): an = a * 1.05 + 0.3; cv2.line(g, (tx, ty), (int(tx + math.cos(an) * s * 0.6), int(ty + math.sin(an) * s * 0.25 + s * 0.15)), (30, 150, 60), max(1, int(s * 0.07)))
        elif kind == 'lamp':
            cv2.line(g, (x, y), (x, int(y - s * 1.4)), (90, 90, 110), max(1, int(s * 0.05)))
            cv2.circle(g, (x, int(y - s * 1.4)), max(1, int(s * 0.12)), (255, 230, 150), -1)
            if st.get('wet'): cv2.line(g, (x, y), (x, min(H - 1, int(y + s * 0.9))), (120, 100, 60), max(1, int(s * 0.06)))
        elif kind == 'pine':
            for k in range(3):
                w = s * (0.45 - k * 0.1); yb = y - s * (0.2 + k * 0.35)
                cv2.fillPoly(g, [np.array([(int(x - w), int(yb)), (int(x + w), int(yb)), (x, int(yb - s * 0.5))], np.int32)], (30, 90 + k * 15, 60))
            cv2.fillPoly(g, [np.array([(int(x - s * 0.12), int(y - s * 1.05)), (int(x + s * 0.12), int(y - s * 1.05)), (x, int(y - s * 1.3))], np.int32)], (245, 250, 255))
        elif kind == 'pylon':
            cv2.polylines(g, [np.array([(int(x - s * 0.2), y), (x, int(y - s * 0.8)), (int(x + s * 0.2), y)], np.int32)], False, st['line'], 1)
        elif kind == 'block':
            bw, bh = int(s * (0.6 + v)), int(s * (1.2 + 1.5 * v)); col = [(170, 120, 100), (120, 140, 170), (190, 180, 150)][int(v * 3) % 3]
            cv2.rectangle(g, (x - bw // 2, y - bh), (x + bw // 2, y), col, -1)
            side = int(bw * 0.35) * (1 if x > W / 2 else -1)
            cv2.fillPoly(g, [np.array([(x + (bw // 2 if side > 0 else -bw // 2), y - bh), (x + (bw // 2 if side > 0 else -bw // 2) + side, y - bh - abs(side) // 2), (x + (bw // 2 if side > 0 else -bw // 2) + side, y - abs(side) // 2), (x + (bw // 2 if side > 0 else -bw // 2), y)], np.int32)], tuple(int(c * 0.65) for c in col))
        elif kind == 'star':
            r_ = max(1, int(s * 0.25)); cv2.circle(g, (x, int(y - s * 0.6)), r_, (255, 255, 200), -1); cv2.circle(g, (x, int(y - s * 0.6)), r_ * 2, (140, 120, 255), 1)
    def car(self, g, x, y, p, k, player=False):
        st = self.st; s = max(2, p * self.W * 0.34)
        if st.get('wire'):
            col = (220, 255, 220) if player else st['line']
            cv2.rectangle(g, (int(x - s / 2), int(y - s * 0.55)), (int(x + s / 2), y), col, 1)
            cv2.line(g, (int(x - s * 0.3), int(y - s * 0.55)), (int(x - s * 0.2), int(y - s * 0.8)), col, 1); cv2.line(g, (int(x + s * 0.3), int(y - s * 0.55)), (int(x + s * 0.2), int(y - s * 0.8)), col, 1)
            cv2.line(g, (int(x - s * 0.2), int(y - s * 0.8)), (int(x + s * 0.2), int(y - s * 0.8)), col, 1); return
        body = (230, 30, 40) if player else [(255, 200, 0), (40, 140, 255), (255, 255, 255), (60, 200, 90), (220, 80, 220)][k % 5]
        x0, x1 = int(x - s / 2), int(x + s / 2); y0 = int(y - s * 0.5)
        cv2.rectangle(g, (x0, y0), (x1, y), body, -1)
        cv2.rectangle(g, (int(x - s * 0.32), int(y - s * 0.78)), (int(x + s * 0.32), y0), tuple(int(c * 0.8) for c in body), -1)
        cv2.rectangle(g, (int(x - s * 0.25), int(y - s * 0.72)), (int(x + s * 0.25), y0), (40, 60, 90), -1)
        lt = (255, 60, 60) if not st.get('rain') else (255, 40, 40)
        cv2.rectangle(g, (x0 + 1, int(y - s * 0.32)), (int(x0 + s * 0.22), int(y - s * 0.2)), lt, -1); cv2.rectangle(g, (int(x1 - s * 0.22), int(y - s * 0.32)), (x1 - 1, int(y - s * 0.2)), lt, -1)
        cv2.rectangle(g, (int(x0 - s * 0.05), int(y - s * 0.12)), (int(x0 + s * 0.2), y), (20, 20, 20), -1); cv2.rectangle(g, (int(x1 - s * 0.2), int(y - s * 0.12)), (int(x1 + s * 0.05), y), (20, 20, 20), -1)
        if player and self.boost > 0.4:
            for f in (-0.3, 0.3): cv2.circle(g, (int(x + f * s), y + 1), max(1, int(s * 0.1 * (1 + self.boost))), (255, 160, 60), -1)
        if st.get('rain'):  # tail-light streak on the wet road
            cv2.line(g, (int(x0 + s * 0.1), y), (int(x0 + s * 0.1), min(self.H - 1, int(y + s * 0.8))), (140, 30, 30), max(1, int(s * 0.06)))
            cv2.line(g, (int(x1 - s * 0.1), y), (int(x1 - s * 0.1), min(self.H - 1, int(y + s * 0.8))), (140, 30, 30), max(1, int(s * 0.06)))

# ---------------------------------------------------------------- top-down
class Spy83:
    """8-bit top-down: the road snakes and narrows, grass both sides, blocky cars; kick = speed, hit = a car bursts"""
    def __init__(self, seed):
        self.r = np.random.default_rng(seed); self.W, self.H = 66, 135; self.px = PANEL_W // self.W
        self.t = 0.0; self.scroll = 0.0; self.boost = 0.0; self.cars = []; self.boom = []; self.spawn = 0; self.ph = self.r.random() * 6
        self.x = self.W / 2
    def road(self, y):
        s = (self.scroll - y) * 0.035 + self.ph
        c = self.W / 2 + 14 * math.sin(s) + 5 * math.sin(s * 2.3); w = 15 + 5 * math.sin(s * 0.7)
        return c, w
    def step(self, dt, kick, hit):
        self.t += dt; self.boost = max(self.boost * (1 - 3 * dt), kick); sp = 45 + 120 * self.boost; self.scroll += sp * dt; self.spawn += dt
        if self.spawn > 1.0: self.spawn = 0; c, w = self.road(-10); self.cars.append([c + self.r.uniform(-w * 0.5, w * 0.5), -10.0, int(self.r.integers(0, 3)), 0.0])
        for c in self.cars: c[1] += (sp - 25) * dt; rc, rw = self.road(c[1]); c[0] += (rc - c[0]) * 0.5 * dt * 3
        if hit > 0.8 and self.cars: c = self.cars.pop(int(self.r.integers(0, len(self.cars)))); self.boom.append([c[0], c[1], 0.0])
        self.cars = [c for c in self.cars if c[1] < self.H + 10]
        for b in self.boom: b[2] += dt
        self.boom = [b for b in self.boom if b[2] < 0.5]
        rc, _ = self.road(self.H - 16); self.x += (rc - self.x) * min(1, 3 * dt)
    def draw(self):
        g = np.zeros((self.H, self.W, 3), np.uint8)
        for y in range(self.H):
            c, w = self.road(y); stripe = int((y - self.scroll) / 4) % 2
            g[y] = (0, 150, 0) if stripe else (0, 120, 0)
            g[y, max(0, int(c - w)):int(c + w)] = (90, 90, 90)
            g[y, max(0, int(c - w) - 1):max(0, int(c - w))] = (255, 255, 255); g[y, int(c + w):int(c + w) + 1] = (255, 255, 255)
            if int((y - self.scroll) / 5) % 2: g[y, int(c)] = (255, 255, 0)
        for c in self.cars:
            col = [(0, 120, 255), (255, 255, 255), (255, 0, 120)][c[2]]
            g[max(0, int(c[1]) - 4):max(0, int(c[1]) + 4), max(0, int(c[0]) - 2):int(c[0]) + 2] = col
            g[max(0, int(c[1]) - 3):max(0, int(c[1]) - 1), max(0, int(c[0]) - 1):int(c[0]) + 1] = (0, 0, 0)
        y = self.H - 16; g[y - 4:y + 4, int(self.x) - 2:int(self.x) + 2] = (255, 40, 40); g[y - 3:y - 1, int(self.x) - 1:int(self.x) + 1] = (0, 0, 0)
        if self.boost > 0.5: g[y + 4:y + 6, int(self.x) - 1:int(self.x) + 1] = (255, 200, 0)
        for b in self.boom:
            rr = int(1 + b[2] * 14); cv2.circle(g, (int(b[0]), int(b[1])), rr, (255, 200, 0) if b[2] < 0.25 else (255, 80, 0), 1)
        return g

class Rally91:
    """16-bit top-down rally: winding dirt track, trees, the car drifts and lays skid marks; kick = throttle + dust"""
    def __init__(self, seed):
        self.r = np.random.default_rng(seed); self.W, self.H = 132, 270; self.px = PANEL_W // self.W
        self.t = 0.0; self.scroll = 0.0; self.boost = 0.0; self.ph = self.r.random() * 6; self.skids = []; self.dust = []; self.ang = 0.0; self.x = 66.0
        self.trees = [(self.r.random() * self.W, self.r.random() * 400) for _ in range(40)]
        tex = self.r.integers(0, 30, (64, 64)); self.tex = cv2.resize(tex.astype(np.uint8), (64, 64))
    def road(self, wy):
        s = wy * 0.012 + self.ph; return self.W / 2 + 32 * math.sin(s) + 10 * math.sin(s * 2.7), 22
    def step(self, dt, kick, hit):
        self.t += dt; self.boost = max(self.boost * (1 - 2.5 * dt), kick); sp = 70 + 150 * self.boost; self.scroll += sp * dt
        py = self.H - 50; wy = self.scroll + (self.H - py)
        rc, _ = self.road(wy); rc2, _ = self.road(wy + 20)
        tgt_ang = math.atan2(rc2 - rc, 20); self.ang += (tgt_ang * 1.6 - self.ang) * min(1, 4 * dt)
        self.x += (rc - self.x) * min(1, 2.2 * dt)
        if abs(self.ang) > 0.25 or self.boost > 0.5: self.skids.append([self.x, self.scroll])
        self.skids = self.skids[-200:]
        if kick > 0.6:
            for _ in range(6): self.dust.append([self.x + self.r.normal(0, 3), py + 10, self.r.normal(0, 25), self.r.uniform(20, 60), 0.6])
        for d in self.dust: d[0] += d[2] * dt; d[1] += d[3] * dt; d[4] -= dt
        self.dust = [d for d in self.dust if d[4] > 0]
    def draw(self):
        W, H = self.W, self.H; g = np.zeros((H, W, 3), np.uint8)
        for y in range(H):
            wy = self.scroll + (H - y); c, w = self.road(wy)
            ty = int(wy) % 64; row = self.tex[ty]
            grass = 70 + (row[np.arange(W) % 64] // 2)
            g[y, :, 0] = grass * 0.45; g[y, :, 1] = grass; g[y, :, 2] = grass * 0.35
            xs = slice(max(0, int(c - w)), min(W, int(c + w))); dirt = 120 + row[np.arange(xs.start, xs.stop) % 64]
            g[y, xs, 0] = np.clip(dirt + 40, 0, 255); g[y, xs, 1] = np.clip(dirt * 0.75 + 10, 0, 255); g[y, xs, 2] = np.clip(dirt * 0.45, 0, 255)
            g[y, max(0, int(c - w) - 2):max(0, int(c - w))] = (200, 40, 40) if int(wy / 6) % 2 else (240, 240, 240)
            g[y, min(W, int(c + w)):min(W, int(c + w) + 2)] = (200, 40, 40) if int(wy / 6) % 2 else (240, 240, 240)
        for sx, sw in self.skids:
            y = int(H - (sw - self.scroll) - 50)
            if 0 <= y < H: cv2.circle(g, (int(sx) - 4, y), 1, (60, 40, 30), -1); cv2.circle(g, (int(sx) + 4, y), 1, (60, 40, 30), -1)
        for tx, ty in self.trees:
            wy = ty + (self.scroll // 400) * 400; y = int(H - ((wy - self.scroll) % 400) - 0)
            c, w = self.road(self.scroll + (H - y))
            if abs(tx - c) < w + 8: continue
            cv2.circle(g, (int(tx) + 2, y + 2), 7, (20, 50, 20), -1); cv2.circle(g, (int(tx), y), 7, (40, 120, 40), -1); cv2.circle(g, (int(tx) - 2, y - 2), 3, (90, 170, 80), -1)
        car = np.zeros((22, 12, 3), np.uint8); car[:] = (230, 230, 40); car[3:8, 2:10] = (40, 60, 100); car[15:19, 2:10] = (40, 60, 100); car[0:2, :] = (255, 255, 200)
        car[:, 0] = car[:, -1] = (30, 30, 30)
        M = cv2.getRotationMatrix2D((6, 11), -math.degrees(self.ang), 1.0)
        canvas = np.zeros((30, 30, 3), np.uint8); canvas[4:26, 9:21] = car
        M = cv2.getRotationMatrix2D((15, 15), -math.degrees(self.ang), 1.0); rot = cv2.warpAffine(canvas, M, (30, 30))
        x0, y0 = int(self.x) - 15, H - 50 - 15; m = rot.sum(2) > 0
        reg = g[max(0, y0):y0 + 30, max(0, x0):x0 + 30]; mm = m[:reg.shape[0], :reg.shape[1]]; reg[mm] = rot[:reg.shape[0], :reg.shape[1]][mm]
        for d in self.dust: cv2.circle(g, (int(d[0]), int(d[1])), int(3 + (0.6 - d[4]) * 10), (170, 140, 100), -1)
        return g

class Neon90:
    """thin wrapper around the original neon top-down racer so it fits this module's interface"""
    def __init__(self, seed):
        from games16 import Racer
        self.g_ = Racer(seed); self.px = PANEL_W // 132
    def step(self, dt, kick, hit): self.g_.step(dt, kick, hit)
    def draw(self): return self.g_.draw()

RACES = {
    'vector83': lambda s: PseudoRoad(s, 'vector83'), 'spy83': Spy83, 'coast86': lambda s: PseudoRoad(s, 'coast86'),
    'neon89': lambda s: PseudoRoad(s, 'neon89'), 'neon90': Neon90, 'rally91': Rally91, 'snow93': lambda s: PseudoRoad(s, 'snow93'),
    'ps1_97': lambda s: PseudoRoad(s, 'ps1_97'), 'rainbow99': lambda s: PseudoRoad(s, 'rainbow99'), 'rain00': lambda s: PseudoRoad(s, 'rain00'),
}
