"""Side-panel patterns (2026-11-20): colourful geometry that moves, turns a notch on every bass drum. Plus two video loops the user supplied.
Same interface as the games/screens: step(dt, kick, hit), draw() -> (h, w, 3) uint8, .px."""
import numpy as np, math, cv2, os
from screens import Scr

POP = [(255, 105, 180), (0, 200, 230), (255, 220, 0), (250, 250, 250), (150, 110, 235), (255, 120, 50), (120, 235, 180), (30, 30, 40)]

class Pat(Scr):
    W, H, px = 264, 540, 2; NCOL = 5
    def init(self):
        self.kc = 0; self.since = 9.0; self.Y, self.X = np.mgrid[0:self.H, 0:self.W].astype(np.float32)
        self.pal = np.array([POP[i] for i in self.r.permutation(len(POP))[:self.NCOL]], np.uint8); self.setup()
    def setup(self): pass
    def on_kick(self): pass
    def tick(self, dt, kick, hit):
        self.since += dt
        if kick > 0.6 and self.since > 0.18: self.kc += 1; self.since = 0.0; self.on_kick()
    def colour(self, idx): return self.pal[(idx.astype(np.int64) + self.kc) % len(self.pal)]
    def out(self, g):
        if self.since < 0.06: g = np.clip(g.astype(np.int16) + 40, 0, 255).astype(np.uint8)
        self.g = g; return g

class Stripes(Pat):
    def setup(self): self.s = float(self.r.choice([70, 95, 120])); self.dir = float(self.r.choice([-1, 1]))
    def draw(self): return self.out(self.colour(np.floor((self.X + self.dir * self.Y) / self.s + self.t * 1.6)))
class Rings(Pat):
    def setup(self): self.c = (self.W * self.r.uniform(.3, .7), self.H * self.r.uniform(.3, .7))
    def draw(self): return self.out(self.colour(np.floor(np.hypot(self.X - self.c[0], self.Y - self.c[1]) / 55 - self.t * 1.2)))
class Checker(Pat):
    NCOL = 4
    def draw(self):
        q = 88; x = self.X + self.t * 20; y = self.Y + self.t * 12
        return self.out(self.colour((np.floor(x / q) + np.floor(y / q)) % 2 + 2 * ((np.floor(x / (q * 2)) + np.floor(y / (q * 2))) % 2)))
class Truchet(Pat):
    NCOL = 4
    def setup(self): self.q = 132; self.o = self.r.integers(0, 2, (self.H // 132 + 2, self.W // 132 + 2))
    def on_kick(self): self.o = np.where(self.r.random(self.o.shape) < 0.35, 1 - self.o, self.o)
    def draw(self):
        q = self.q; ci = (self.X // q).astype(int); cj = (self.Y // q).astype(int); u = self.X - ci * q; v = self.Y - cj * q; o = self.o[cj, ci]
        d1 = np.where(o == 0, np.hypot(u, v), np.hypot(u - q, v)); d2 = np.where(o == 0, np.hypot(u - q, v - q), np.hypot(u, v - q))
        line = (np.abs(d1 - q / 2) < 15) | (np.abs(d2 - q / 2) < 15)
        return self.out(np.where(line[..., None], self.pal[(2 + self.kc) % 4], self.colour((ci + cj) % 2)))
class Dots(Pat):
    def draw(self):
        q = 66; m = np.hypot(self.X % q - q / 2, self.Y % q - q / 2) < 8 + 22 * (0.5 + 0.5 * np.sin(self.X / 120 + self.Y / 190 - self.t * 3))
        return self.out(np.where(m[..., None], self.colour(np.floor(self.Y / q / 2)), np.array((250, 244, 230), np.uint8)))
class Zigzag(Pat):
    def draw(self): return self.out(self.colour(np.floor((self.Y + np.abs(self.X % 132 - 66) * 1.2) / 60 + self.t * 0.8)))
class Sunburst(Pat):
    NCOL = 3
    def setup(self): self.c = (self.W / 2, self.H * self.r.uniform(.35, .65))
    def draw(self):
        g = self.colour(np.floor((np.arctan2(self.Y - self.c[1], self.X - self.c[0]) + self.t * 0.7) / (2 * np.pi) * 12)).copy()
        g[np.hypot(self.X - self.c[0], self.Y - self.c[1]) < 60 + 16 * math.exp(-self.since * 8)] = (250, 250, 250); return self.out(g)
class Waves(Pat):
    def draw(self): return self.out(self.colour(np.floor((self.Y + 50 * np.sin(self.X / 80 + self.t * 2.2 + self.Y / 240)) / 50)))
class Tris(Pat):
    NCOL = 6
    def draw(self):
        h = 110.0; w = 127.0; u = (self.X + self.t * 14) / w - 0.5 * self.Y / h; v = self.Y / h; fu, fv = np.floor(u), np.floor(v)
        return self.out(self.colour(fu * 2 + fv * 3 + ((u - fu) + (v - fv) > 1)))

def _memmap(path):
    """the clip at 960x540, as a file-backed array shared by every side that plays it"""
    npy = path[:-4] + '_side.npy'
    if not os.path.exists(npy):
        cap = cv2.VideoCapture(path); fr = []
        while True:
            ok, f = cap.read()
            if not ok: break
            fr.append(cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2RGB), (960, 540), interpolation=cv2.INTER_AREA))
        np.save(npy + '.tmp.npy', np.array(fr, np.uint8)); os.rename(npy + '.tmp.npy', npy)
    return np.load(npy, mmap_mode='r')
class ClipSide:
    """a strip of a video loop; it plays back and forth, runs faster on the bass drum, and jumps to another strip of the picture now and then"""
    W, H, px = 264, 540, 2
    def __init__(self, seed, path):
        self.r = np.random.default_rng(seed); self.a = _memmap(path); self.pos = float(self.r.integers(0, len(self.a))); self.dir = 1; self.x = int(self.r.integers(0, 960 - 264)); self.k = 0.0; self.since = 9.0; self.kc = 0
    def step(self, dt, kick, hit):
        self.k = max(self.k * (1 - 5 * dt), kick); self.since += dt; self.pos += self.dir * dt * 30 * (0.5 + 1.8 * self.k)
        if self.pos >= len(self.a) - 1: self.pos = len(self.a) - 1; self.dir = -1
        if self.pos <= 0: self.pos = 0; self.dir = 1
        if kick > 0.6 and self.since > 0.18:
            self.since = 0.0; self.kc += 1
            if self.kc % 2 == 0: self.x = int(self.r.integers(0, 960 - 264))
    def draw(self):
        g = np.array(self.a[int(self.pos)][:, self.x:self.x + 264])
        if self.since < 0.06: g = np.clip(g.astype(np.int16) + 40, 0, 255).astype(np.uint8)
        return g

PATTERNS = {'stripes': Stripes, 'rings': Rings, 'checker': Checker, 'truchet': Truchet, 'dots': Dots, 'zigzag': Zigzag, 'sunburst': Sunburst, 'waves': Waves, 'tris': Tris,
            'arcbeat': lambda s: ClipSide(s, 'clips/arcbeat.mp4'), 'prism': lambda s: ClipSide(s, 'clips/prism.mp4')}

if __name__ == '__main__':
    from PIL import Image
    ims = []
    for name, C in PATTERNS.items():
        for seed in (3, 8):
            o = C(seed)
            for k in range(100): o.step(1 / 30, float(k % 20 == 0), 0.0); fr = o.draw()
            ims.append(Image.fromarray(fr).resize((132, 270)))
    sh = Image.new('RGB', (132 * len(ims), 270)); [sh.paste(im, (k * 132, 0)) for k, im in enumerate(ims)]; sh.save('patterns.jpg', quality=88); print(len(ims))
