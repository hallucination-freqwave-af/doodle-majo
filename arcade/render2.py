import numpy as np, cv2, sys, subprocess, os, math, glob
from PIL import Image, ImageDraw
from render import (W, H, FPS, kick, hit, beatphase, kickpulse, offpulse, af, rms, BEAT, strips, invert, swap, mosaic, place, pil_over,
                    text, cat, speedlines, sun, particles, blank, BLUE, PINK, BLACK, WHITE)

_text = text
def text(img, s, *a, **k):
    # no captions: keep only the countdown digits and the credit line
    if s.replace(':','').isdigit() or s.startswith('documented'): return _text(img, s, *a, **k)
    return img

IMAGES = [np.array(Image.open(f).convert('RGB')) for f in sorted(glob.glob('posters/*.png'))]

class VideoSource:
    """a clip, cover-cropped to 1080x1350; frame(tl) plays it (ping-pong when shorter than the slot)"""
    def __init__(self, path):
        self.cap = cv2.VideoCapture(path); self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)); self.cache = {}; self.last = -1
    def frame(self, tl):
        k = int(tl * self.fps); span = max(1, self.n - 1)
        cyc = k // span; k = k % span if cyc % 2 == 0 else span - k % span   # ping-pong
        if k in self.cache: return self.cache[k]
        if k != self.last + 1: self.cap.set(cv2.CAP_PROP_POS_FRAMES, k)
        ok, fr = self.cap.read(); self.last = k
        if not ok: return self.cache.get(self.last - 1, blank(BLACK))
        fr = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB); h, w = fr.shape[:2]; s = max(W / w, H / h)
        fr = cv2.resize(fr, (int(w * s) + 1, int(h * s) + 1)); y0 = (fr.shape[0] - H) // 2; x0 = (fr.shape[1] - W) // 2
        out = np.ascontiguousarray(fr[y0:y0 + H, x0:x0 + W]); self.cache = {k: out}; return out

CLIPS = {7: 'clips/v1.mp4', 20: 'clips/v2.mp4', 33: 'clips/v3.mp4'}   # where the moving fragments sit
POSTERS = list(IMAGES)
for pos in sorted(CLIPS): POSTERS.insert(pos, VideoSource(CLIPS[pos]))
DUR = 201.9
NS = len(POSTERS)
SEG = DUR / NS  # ~13.46s each

def ease(x): return 0.5 - 0.5 * math.cos(min(1, max(0, x)) * math.pi)

def wave(img, amp, freq, t, axis=1):
    # sinusoidal row/col shift (swimming)
    ys = np.arange(H if axis == 1 else W)
    off = (amp * np.sin(ys / freq + t * 4)).astype(int)
    out = np.empty_like(img)
    if axis == 1:
        for y in range(H): out[y] = np.roll(img[y], off[y], axis=0)
    else:
        for x in range(W): out[:, x] = np.roll(img[:, x], off[x], axis=0)
    return out

def shake(img, amp, t):
    r = np.random.default_rng(int(t * 60)); dx, dy = r.integers(-amp, amp + 1, 2)
    return np.roll(np.roll(img, int(dx), axis=1), int(dy), axis=0)

def zoom(img, s, cx=0.5, cy=0.5):
    w, h = int(W / s), int(H / s); x0 = int(W * cx - w / 2); y0 = int(H * cy - h / 2)
    x0 = min(max(0, x0), W - w); y0 = min(max(0, y0), H - h)
    return cv2.resize(img[y0:y0 + h, x0:x0 + w], (W, H), interpolation=cv2.INTER_LINEAR)

def rotate(img, deg, s=1.0, bg=(0, 0, 0)):
    M = cv2.getRotationMatrix2D((W / 2, H / 2), deg, s)
    return cv2.warpAffine(img, M, (W, H), borderValue=bg)

def scanlines(img, t, strength=0.5):
    out = img.astype(np.int16)
    out[(np.arange(H) + int(t * 200)) % 4 < 2] -= int(90 * strength)
    return np.clip(out, 0, 255).astype(np.uint8)

def blur(img, k): k = max(1, int(k) | 1); return cv2.GaussianBlur(img, (k, k), 0)

def glitch_common(img, t):  # the thread through everything: strong onset -> channel swap (colour only)
    h = hit(t)
    if h > 0.8: img = swap(img, [[2, 0, 1], [1, 2, 0], [0, 2, 1]][int(t * 13) % 3])
    return img

def e01_intro(P, tl, t):  # strips slide in
    img = blank(BLACK); n = 18; edges = np.linspace(0, H, n + 1).astype(int)
    order = np.random.default_rng(1).permutation(n)
    for k, i in enumerate(order):
        arrive = 0.3 + k * (SEG*0.65 / n)
        if tl >= arrive:
            a, b = edges[i], edges[i + 1]; prog = min(1, (tl - arrive) / 0.25)
            img[a:b] = np.roll(P[a:b], int((1 - prog) ** 2 * W * (1 if i % 2 else -1)), axis=1)
    if tl > SEG*0.75: img = e_bounce(P, tl - SEG*0.75, t)
    return img

def e_bounce(P, tl, t):
    img = blank(BLUE); img = speedlines(img, int(20 + 60 * kick(t)), t)
    sc = 0.45 + 0.08 * kick(t); w, h = int(W * sc), int(H * sc); vx, vy = 310, 230
    x = (tl * vx) % (2 * (W - w)); x = x if x < W - w else 2 * (W - w) - x
    y = (tl * vy) % (2 * (H - h)); y = y if y < H - h else 2 * (H - h) - y
    card = [P, swap(P, [2, 0, 1]), invert(P), swap(P, [1, 2, 0])][int(tl / 2.5) % 4]
    return place(img, card, x, y, sc)

def e02_castout(P, tl, t):  # 幸福圏外: a circle (圏) is drawn; the poster shrinks and is pushed outside it
    img = blank((255, 40, 150))
    cx, cy = W // 2, H // 2; R = 480
    p = ease((tl - SEG * 0.25) / (SEG * 0.5))
    sc = 1.0 - 0.6 * p; ox = int(540 * p)
    card = cv2.resize(P, (int(W * sc), int(H * sc)))
    img = place(img, card, cx - card.shape[1] // 2 + ox, cy - card.shape[0] // 2)
    def fn(d, im):
        prog = min(1, tl / (SEG * 0.25)) * 360
        d.arc([cx - R, cy - R, cx + R, cy + R], -90, -90 + prog, fill=(255, 255, 255), width=14)
        if p > 0.95 and int(tl * 4) % 2: d.ellipse([cx - 30, cy - 30, cx + 30, cy + 30], fill=(255, 255, 255))
    img = pil_over(img, fn)
    return glitch_common(img, t)

def e03_sever(P, tl, t):  # 時空断線: horizontal tear with time offset; scanlines; diamond rotates
    img = P.copy()
    n = 9; edges = np.linspace(0, H, n + 1).astype(int)
    for i, (a, b) in enumerate(zip(edges[:-1], edges[1:])):
        img[a:b] = np.roll(P[a:b], int(300 * math.sin(tl * (1.5 + i * 0.4) + i)), axis=1)
    img = scanlines(img, t, 0.6)
    if beatphase(t) < 0.2: img = invert(img)
    img = rotate(img, 15 * math.sin(tl * 1.2), 1.0 + 0.15 * kick(t), bg=(200, 230, 200))
    if hit(t) > 0.6: img = mosaic(img, 10 + 30 * hit(t))
    return text(img, '断　線', 140, (W // 2, 200 + 40 * math.sin(tl * 6)), fill=(230, 255, 180), stroke=8, sfill=(40, 40, 80))

def e04_fateline(P, tl, t):  # ギリギリの運命線: every bass drum (ドン・ドンドン) slams the poster small; it swells back between hits
    p = kickpulse(t, 6.0)
    sc = 1.0 - 0.45 * p
    img = blank((20, 20, 20) if p < 0.9 else (255, 40, 60)); card = cv2.resize(P, (int(W * sc), int(H * sc)))
    img = place(img, card, (W - card.shape[1]) // 2, (H - card.shape[0]) // 2)
    def fn(d, im):
        amp = 60 + 120 * p
        pts = [(x, H * 0.75 + amp * math.sin(x / 90 + t * 5) + 40 * math.sin(x / 23 - t * 9)) for x in range(0, W + 20, 20)]
        d.line(pts, fill=(255, 40, 60), width=int(10 + 14 * p))
    return pil_over(img, fn)

def e05_denpa(P, tl, t):  # 電波: concentric waves + static; 呪詛 rain
    img = P.copy()
    noise = np.random.default_rng(int(t * 30)).integers(0, 255, (H // 6, W // 6), dtype=np.uint8)
    noise = cv2.resize(noise, (W, H), interpolation=cv2.INTER_NEAREST)[..., None]
    a = 0.25 + 0.5 * hit(t)
    img = cv2.addWeighted(img, 1 - a, np.repeat(noise, 3, 2), a, 0)
    def fn(d, im):
        cx, cy = 820, 1000
        for i in range(12):
            r = ((tl * 350 + i * 110) % 1300)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, int(220 * (1 - r / 1300))), width=6)
        rr = np.random.default_rng(4)
        for i in range(30):
            x = rr.integers(0, W); y = (rr.integers(0, H) + tl * (400 + rr.integers(0, 500))) % H
            d.text((x, y), '呪', font=__import__('render').font(50 + int(rr.integers(0, 40))), fill=(255, 0, 90, 230))
    img = pil_over(img, fn)
    if beatphase(t) < 0.1: img = invert(img)
    return img

def e06_battery(P, tl, t):  # 残り25%: battery drains 25->15, colour drains with it, then 無音 freeze
    p25 = 25 - 10 * min(1, tl / (SEG*0.68))
    img = P.copy()
    if tl > SEG*0.7:  # 無音: grey, still
        return (cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)[..., None].repeat(3, 2) * 0.6).astype(np.uint8)
    g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)[..., None].repeat(3, 2); a = (25 - p25) / 10
    img = cv2.addWeighted(img, 1 - a * 0.8, g, a * 0.8, 0)
    def fn(d, im):
        x0, y0, w, h = W // 2 - 300, 60, 600, 140
        d.rounded_rectangle([x0, y0, x0 + w, y0 + h], 25, outline=(255, 255, 255), width=10, fill=(0, 0, 0, 180))
        d.rectangle([x0 + w, y0 + 45, x0 + w + 30, y0 + h - 45], fill=(255, 255, 255))
        fw = int((w - 30) * p25 / 100)
        col = (255, 60, 90) if int(tl * 6) % 2 or p25 > 18 else (255, 255, 255)
        d.rectangle([x0 + 15, y0 + 15, x0 + 15 + fw, y0 + h - 15], fill=col)
        d.text((W // 2, y0 + h // 2), f'{p25:.0f}%', font=__import__('render').font(90), fill=(255, 255, 255), anchor='mm', stroke_width=5, stroke_fill=(0, 0, 0))
    return pil_over(img, fn)

def e07_swim(P, tl, t):  # 君と共に泳ぐブルー: the water rises from the bottom and they go under
    img = P.copy()
    level = int(H - H * ease(tl / (SEG * 0.8)))
    blue = np.array([0, 90, 200], np.uint8)
    under = (img.astype(np.float32) * 0.45 + blue * 0.55).astype(np.uint8)
    img[level:] = under[level:]
    if level > 0: img[max(0, level - 6):level] = (200, 230, 255)
    def fn(d, im):
        r = np.random.default_rng(6)
        for i in range(40):
            x = r.integers(0, W) + 25 * math.sin(tl * 2 + i); y = H - ((r.integers(0, H) + tl * (120 + r.integers(0, 250))) % (H + 100))
            if y > level: s = 6 + r.integers(0, 20); d.ellipse([x - s, y - s, x + s, y + s], outline=(255, 255, 255, 180), width=3)
    img = pil_over(img, fn)
    if kick(t) > 0.8: img = (np.clip(img.astype(int) + 40, 0, 255)).astype(np.uint8)
    return img

def e08_kirakira(P, tl, t):  # kiro kiro: sparkle bursts, blink-out frames, zoom pulse
    img = zoom(P, 1.0 + 0.25 * kick(t), 0.5, 0.4)
    def fn(d, im):
        r = np.random.default_rng(int(t * 30))
        for i in range(int(8 + 60 * hit(t))):
            x, y = r.integers(0, W), r.integers(0, H); s = r.integers(8, 50)
            col = [(255, 255, 255), (255, 170, 230), (170, 230, 255)][i % 3]
            d.polygon([(x, y - s), (x + s * 0.25, y - s * 0.25), (x + s, y), (x + s * 0.25, y + s * 0.25), (x, y + s), (x - s * 0.25, y + s * 0.25), (x - s, y), (x - s * 0.25, y - s * 0.25)], fill=col)
    img = pil_over(img, fn)
    if hit(t) > 0.85 and int(t * 30) % 2 == 0: img = blank(WHITE)
    if int(tl * 1.5) % 4 == 3: img = text(img, '笑いすぎて', 120, (W // 2, H // 2 - 100), fill=(0, 0, 0), stroke=8, sfill=(255, 255, 255), angle=10 * math.sin(tl * 8))
    if int(tl * 1.5) % 4 == 3: img = text(img, '飛んだ', 160, (W // 2 + 60 * math.sin(tl * 7), H // 2 + 100 - 150 * ((tl * 1.5) % 1)), fill=(120, 230, 255), stroke=8)
    return img

def e09_nosebleed(P, tl, t):  # 鼻血: a drip grows, pools; she goes pale as it drains
    img = P.copy()
    a = min(1, tl / SEG) * 0.6
    g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)[..., None].repeat(3, 2); img = cv2.addWeighted(img, 1 - a, g, a, 0)
    def fn(d, im):
        nx, ny = 945, 700
        L = min(H - ny, int(tl * 150)) + 30 * abs(math.sin(tl * 9)) * (hit(t) > 0.5)
        d.line([(nx, ny), (nx + 8 * math.sin(tl * 3), ny + L)], fill=(230, 0, 30), width=18)
        d.ellipse([nx - 14, ny + L - 20, nx + 14, ny + L + 10], fill=(230, 0, 30))
        if tl > SEG*0.45:
            pw = (tl - SEG*0.45) * 160
            d.ellipse([W // 2 - pw, H - 120 - pw * 0.25, W // 2 + pw, H - 60 + pw * 0.1], fill=(230, 0, 30))
    return pil_over(img, fn)

def e10_fire(P, tl, t):  # 発火: it heats up (red climbs), sparks, then burns white and goes to ash
    img = P.astype(np.int16)
    heat = min(1, tl / (SEG * 0.7))
    img[..., 0] += int(120 * heat); img[..., 2] -= int(80 * heat)
    img = np.clip(img, 0, 255).astype(np.uint8)
    img = shake(img, int(2 + 20 * kick(t) * heat), t)
    def fn(d, im):
        r = np.random.default_rng(8)
        for i in range(int(120 * heat)):
            x = r.integers(0, W) + 40 * math.sin(tl * 5 + i); y = H - ((r.integers(0, H) + tl * (300 + r.integers(0, 600))) % H)
            l = r.integers(10, 50); a = tl * 10 + i
            d.line([(x, y), (x + l * math.cos(a), y + l * math.sin(a))], fill=[(255, 220, 0), (255, 120, 0), (255, 40, 0)][i % 3], width=int(r.integers(3, 9)))
    img = pil_over(img, fn)
    if tl > SEG * 0.7:
        p = ease((tl - SEG * 0.7) / (SEG * 0.3))
        img = cv2.addWeighted(img, 1 - p, blank(WHITE) if p < 0.5 else blank((30, 30, 30)), p, 0)
    return img

def e11_dream(P, tl, t):  # 夢感覚移動 (1): slow drift, soft blur, double exposure, sparkle; then it falls asleep (tilts, closes)
    img = zoom(P, 1.12 + 0.08 * math.sin(tl * 0.5), 0.5 + 0.08 * math.sin(tl * 0.7), 0.5 + 0.08 * math.cos(tl * 0.6))
    img = cv2.addWeighted(img, 0.6, blur(np.roll(img, int(60 * math.sin(tl * 1.5)), axis=1), 31), 0.4, 0)
    if kick(t) > 0.7: img = cv2.addWeighted(img, 0.5, invert(img), 0.5, 0)
    def fn(d, im):
        r = np.random.default_rng(9)
        for i in range(30):
            x, y = r.integers(0, W), r.integers(0, H); s = 10 + 15 * abs(math.sin(tl * 3 + i))
            d.polygon([(x, y - s), (x + s * 0.2, y - s * 0.2), (x + s, y), (x + s * 0.2, y + s * 0.2), (x, y + s), (x - s * 0.2, y + s * 0.2), (x - s, y), (x - s * 0.2, y - s * 0.2)], fill=(255, 255, 255, 200))
    img = pil_over(img, fn)
    if tl > SEG*0.6:  # sleeping: tilt and dim
        img = rotate(img, -25 * ease((tl - SEG*0.6) / 3), 0.8, bg=(20, 20, 60))
        pass
        img = text(img, 'zzz' + '.' * (int(tl * 2) % 4), 100, (W - 250, 200), fill=(255, 255, 255), stroke=6)
    return img

def e12_dream2(P, tl, t):  # 夢感覚移動 (2): 4-panel shuffle / galaxy rain / birds
    img = P.copy()
    # quadrant shuffle on beat
    hw, hh = W // 2, H // 2
    quads = [img[:hh, :hw].copy(), img[:hh, hw:].copy(), img[hh:, :hw].copy(), img[hh:, hw:].copy()]
    perm = np.random.default_rng(int(t / BEAT)).permutation(4)
    out = img.copy()
    for i, q in enumerate(perm):
        yy, xx = [(0, 0), (0, hw), (hh, 0), (hh, hw)][i]
        out[yy:yy + hh, xx:xx + hw] = quads[q]
    img = out if beatphase(t) < 0.5 else P.copy()
    def fn(d, im):
        r = np.random.default_rng(10)
        for i in range(60):
            x = (r.integers(0, W) - tl * 80) % W; y = (r.integers(0, H) + tl * (200 + r.integers(0, 300))) % H
            d.line([(x, y), (x - 8, y - 40)], fill=[(255, 120, 220), (120, 200, 255), (255, 255, 255)][i % 3], width=3)
        for i in range(6):  # birds
            bx = (tl * (150 + i * 40) + i * 200) % (W + 200) - 100; by = 150 + i * 90 + 20 * math.sin(tl * 4 + i)
            fl = 15 * math.sin(tl * 12 + i)
            d.line([(bx - 30, by - fl), (bx, by), (bx + 30, by - fl)], fill=(0, 0, 0), width=5)
    img = pil_over(img, fn)
    if kick(t) > 0.8: img = mosaic(img, 20)
    return img

def e13_car(P, tl, t):  # baby in car: no glitch — the poster itself drives. Pink sky, clouds going by, a road under it; it changes lane on every bass drum
    from render import KICKS
    img = blank((255, 150, 210)); a0 = t - tl; ks = KICKS[(KICKS >= a0) & (KICKS <= t)]; n = len(ks)
    lanes = [W * 0.5, W * 0.36, W * 0.64, W * 0.5, W * 0.3, W * 0.7]; cur = lanes[n % len(lanes)]; prev = lanes[(n - 1) % len(lanes)] if n else cur
    e = min(1.0, (t - ks[-1]) / 0.18) if n else 1.0; e = 0.5 - 0.5 * math.cos(e * math.pi); cx = prev + (cur - prev) * e
    sp = 700 + 1500 * kickpulse(t, 3.0)
    def scene(d, im):
        r = np.random.default_rng(13)
        for k in range(9):                                  # clouds and little hearts drift past behind it
            x = (r.integers(0, W + 400) - tl * (120 + k * 40)) % (W + 400) - 200; y = 90 + k * 95; s_ = 40 + r.integers(0, 50)
            if k % 3: 
                for dx, rr in ((0, 1.0), (s_ * 0.9, 0.75), (-s_ * 0.9, 0.7)): d.ellipse([x + dx - s_ * rr, y - s_ * rr * 0.6, x + dx + s_ * rr, y + s_ * rr * 0.6], fill=(255, 255, 255))
            else: d.polygon([(x, y + s_ * 0.6), (x - s_ * 0.6, y - s_ * 0.1), (x - s_ * 0.3, y - s_ * 0.5), (x, y - s_ * 0.2), (x + s_ * 0.3, y - s_ * 0.5), (x + s_ * 0.6, y - s_ * 0.1)], fill=(255, 90, 170))
        d.rectangle([0, H - 210, W, H], fill=(60, 50, 70)); d.rectangle([0, H - 216, W, H - 206], fill=(255, 255, 255))
        for k in range(8):                                  # the centre line rushes by
            x = (k * 260 - tl * sp) % (W + 260) - 130; d.rectangle([x, H - 112, x + 150, H - 96], fill=(255, 230, 90))
        for k in range(14):                                 # thin wind lines
            y = 60 + (k * 83) % (H - 320); x = (k * 311 - tl * sp * 1.3) % (W + 500) - 250; d.line([(x, y), (x + 180 + k * 12, y)], fill=(255, 255, 255, 170), width=3)
    img = pil_over(img, scene)
    sc = 0.78; card = cv2.resize(P, (int(W * sc), int(H * sc)), interpolation=cv2.INTER_AREA); bob = int(10 * abs(math.sin(t * 9))) + int(26 * kickpulse(t, 9.0))
    x0 = int(cx - card.shape[1] / 2); y0 = H - 150 - card.shape[0] - bob
    def under(d, im):                                       # shadow and wheels, so it sits on the road
        d.ellipse([x0 + 40, H - 175, x0 + card.shape[1] - 40, H - 125], fill=(30, 25, 40))
        for wx in (x0 + 150, x0 + card.shape[1] - 150): d.ellipse([wx - 62, H - 205 - bob // 2, wx + 62, H - 81 - bob // 2], fill=(20, 20, 26)); d.ellipse([wx - 22, H - 165 - bob // 2, wx + 22, H - 121 - bob // 2], fill=(230, 230, 235))
    img = pil_over(img, under)
    return place(img, card, x0, y0)

def e14_map(P, tl, t):  # 未来の地図: rainbow rays; the card brightens from dark as the path gets drawn
    img = blank((90, 170, 230))
    def rays(d, im):
        cols = [(0, 160, 255), (255, 0, 140), (255, 230, 0), (0, 230, 90)]
        for i in range(24):
            a = tl * 1.2 + i * math.pi / 12
            d.polygon([(W / 2, H / 2), (W / 2 + 2000 * math.cos(a), H / 2 + 2000 * math.sin(a)), (W / 2 + 2000 * math.cos(a + 0.13), H / 2 + 2000 * math.sin(a + 0.13))], fill=cols[i % 4])
    img = pil_over(img, rays)
    lit = ease(tl / SEG); card = (P * (0.15 + 0.85 * lit)).astype(np.uint8)
    img = place(img, card, int(W * 0.15), 100, 0.7)
    def path(d, im):
        pts = [(W * 0.1 + i * 12, H * 0.9 + 80 * math.sin(i / 7 + tl)) for i in range(int(min(W * 0.8 / 12, tl * 14)))]
        if len(pts) > 1: d.line(pts, fill=(0, 0, 0), width=10)
        if pts: cat(d, pts[-1][0], pts[-1][1] - 40, 40, (0, 0, 0), run=tl)
    return pil_over(img, path)

def e15_pika(P, tl, t):  # ピカッと狂う夜: every bass drum is a flash of lightning — white, bolts, the poster blazing, then it settles
    p = kickpulse(t, 9.0)
    img = np.clip(P.astype(np.float32) * (0.85 + 1.3 * p) + 60 * p, 0, 255).astype(np.uint8)
    if p > 0.8: img = blank(WHITE) if int(t * 30) % 2 else invert(img)
    def bolt(d, im):
        if p > 0.25:
            r = np.random.default_rng(int(t * 30))
            for _ in range(2 + int(3 * p)):
                x = r.integers(100, W - 100); pts = [(x, 0)]
                for y in range(0, H, 80): x += r.integers(-90, 90); pts.append((x, y))
                d.line(pts, fill=(255, 220, 0), width=int(6 + 14 * p)); d.line(pts, fill=(255, 255, 255), width=int(2 + 5 * p))
    img = pil_over(img, bolt)
    return shake(img, int(30 * p), t) if p > 0.3 else img

def e16_free(P, tl, t):  # 自由気ままん: cranes fly; the poster drifts wherever it likes (position only), brush ring spins
    img = blank((255, 170, 220) if int(tl * 2) % 2 else (120, 230, 240))
    img = place(img, P, int(200 * math.sin(tl * 1.3)), int(150 * math.sin(tl * 0.9)), 0.8)
    def fn(d, im):
        for i in range(14):
            bx = (tl * (200 + i * 30) + i * 160) % (W + 300) - 150; by = 100 + (i * 97) % (H - 200) + 25 * math.sin(tl * 3 + i)
            fl = 22 * math.sin(tl * 10 + i)
            d.line([(bx - 40, by - fl), (bx, by), (bx + 40, by - fl)], fill=(0, 200, 230) if i % 2 else (255, 255, 255), width=7)
        cx, cy, r = 760, 300, 180 + 30 * kick(t)
        for k in range(40):
            a = tl * 4 + k * 0.15; w = int(4 + 20 * (k / 40))
            d.line([(cx + r * math.cos(a), cy + r * math.sin(a)), (cx + r * math.cos(a + 0.15), cy + r * math.sin(a + 0.15))], fill=(255, 210, 0), width=w)
    return pil_over(img, fn)

def e17_crayon(P, tl, t):  # どん曇り: scribbles cloud it over, then the heart lights (glow pulse)
    img = P.copy()
    grey = (cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)[..., None].repeat(3, 2) * 0.7).astype(np.uint8)
    cloud = min(1, tl / (SEG * 0.5)); img = cv2.addWeighted(img, 1 - cloud, grey, cloud, 0)
    def fn(d, im):
        r = np.random.default_rng(17); n = int(tl * 25)
        for i in range(n):
            x, y = r.integers(0, W), r.integers(0, H); col = [(230, 90, 20), (120, 40, 160), (40, 40, 40), (30, 120, 220)][i % 4]
            pts = [(x + r.integers(-120, 120), y + r.integers(-120, 120)) for _ in range(5)]
            d.line(pts, fill=col + (160,), width=int(r.integers(6, 18)))
    img = pil_over(img, fn)
    if tl > SEG * 0.5:
        g = 0.5 + 0.5 * math.sin(tl * 8) * (0.5 + kick(t))
        def heart(d, im):
            cx, cy, s = W // 2, H // 2 + 50, 160 + 60 * g
            for rr, a in [(2.2, 40), (1.6, 80), (1.0, 255)]:
                S = s * rr
                d.polygon([(cx, cy + S), (cx - S, cy - S * 0.1), (cx - S * 0.5, cy - S * 0.8), (cx, cy - S * 0.4), (cx + S * 0.5, cy - S * 0.8), (cx + S, cy - S * 0.1)], fill=(255, 240, 60, a))
        img = pil_over(img, heart)
    return img

def e18_launch(P, tl, t):  # ハニカミ宇宙服: starfield rush, poster shrinks away to Kepler, UFO beam
    img = blank((5, 5, 30))
    def stars(d, im):
        r = np.random.default_rng(18)
        for i in range(140):
            ang = r.random() * 2 * math.pi; sp = 0.3 + r.random(); z = ((r.random() + tl * sp * 0.4) % 1.0)
            x = W / 2 + math.cos(ang) * z * 1200; y = H / 2 + math.sin(ang) * z * 1400; l = z * 60
            d.line([(x, y), (x + math.cos(ang) * l, y + math.sin(ang) * l)], fill=(255, 255, 255), width=int(1 + z * 5))
    img = pil_over(img, stars)
    sc = max(0.04, 1.0 - ease(tl / (SEG * 0.8)) * 0.96)
    card = rotate(P, 25 * math.sin(tl * 1.5) * (1 - sc), 1.0, bg=(5, 5, 30))
    img = place(img, card, W / 2 - W * sc / 2 + 150 * math.sin(tl) * (1 - sc), H / 2 - H * sc / 2 - 200 * (1 - sc), sc)
    def ufo(d, im):
        ux, uy = 180 + 60 * math.sin(tl * 2), 220 + 20 * math.sin(tl * 5)
        d.polygon([(ux, uy + 20), (W / 2 - 100, H), (W / 2 + 100, H)], fill=(120, 255, 200, 70 + int(80 * kick(t))))
        d.ellipse([ux - 90, uy - 25, ux + 90, uy + 25], fill=(200, 200, 220)); d.ellipse([ux - 40, uy - 55, ux + 40, uy], fill=(255, 120, 60))
    img = pil_over(img, ufo)
    img = text(img, 'さよなら、地球' if int(tl) % 2 else 'ケプラー452b へ', 80, (W // 2, H - 160), fill=(255, 120, 220), stroke=6)
    if hit(t) > 0.8: img = invert(img)
    return img

def e19_alarm(P, tl, t):  # あと2分で覚める夢: countdown 2:00 -> 0:00 way too fast, alarm shakes, white-out
    frac = min(1, tl / (SEG * 0.8)); secs = int(120 * (1 - frac))
    img = P.copy()
    if frac < 1:
        img = cv2.addWeighted(img, 1, blur(img, 21 + 2 * int(20 * (1 - frac))), 0.0, 0) if False else blur(img, 1 + 2 * int(15 * (1 - frac)))
        if secs < 30: img = shake(img, int(10 + 40 * (1 - secs / 30)), t)
        img = text(img, f'{secs // 60}:{secs % 60:02d}', 260, (W // 2, 300), fill=(255, 60, 60), stroke=12, sfill=(255, 255, 255))
        if secs < 30 and int(tl * 8) % 2: img = text(img, 'ジリリリリ', 110, (W // 2, H // 2 + 200), fill=(0, 0, 0), stroke=8, sfill=(255, 255, 0), angle=15 * math.sin(tl * 30))
    else:
        img = blank(WHITE); img = text(img, '覚めた', 180, (W // 2, H // 2), fill=(0, 0, 0))
        if int(tl * 4) % 2: img = text(img, '（まだ夢）', 70, (W // 2, H // 2 + 170), fill=(255, 120, 220))
    return img

def e20_kaleido(P, tl, t):  # halftone twins: 4-way mirror kaleidoscope rotating, zoom, then it folds shut
    img = rotate(P, tl * 30, 1.2 + 0.3 * kick(t), bg=(240, 170, 230))
    hw, hh = W // 2, H // 2
    q = img[:hh, :hw] if int(tl * 2) % 2 else img[hh:, hw:]
    k = np.empty_like(img)
    k[:hh, :hw] = q; k[:hh, hw:] = q[:, ::-1]; k[hh:, :hw] = q[::-1]; k[hh:, hw:] = q[::-1, ::-1]
    if beatphase(t) < 0.25: k = swap(k, [1, 2, 0])
    if tl > SEG * 0.8:  # fold shut
        p = ease((tl - SEG * 0.8) / (SEG * 0.2)); k = rotate(k, 0, max(0.02, 1 - p), bg=(0, 0, 0))
        k = text(k, 'documented by Matashichi .', 50, (W // 2, H - 90), fill=(255, 120, 220))
    return k

TRICKS = [e01_intro, e02_castout, e03_sever, e04_fateline, e05_denpa, e06_battery, e07_swim, e08_kirakira,
          e09_nosebleed, e10_fire, e11_dream, e12_dream2, e13_car, e14_map, e15_pika, e16_free, e17_crayon, e18_launch, e19_alarm, e20_kaleido]

def e21_wink(P, tl, t):  # eyelid closes/opens over the poster; dotted line runs
    img = P.copy()
    ph = (tl * 1.6) % 1.0; close = max(0, 1 - abs(ph - 0.5) * 8)  # quick blink
    lid = int(H * 0.55 * close)
    img[:lid] = 0; img[H - lid // 2:] = 0
    if hit(t) > 0.6: img = np.roll(img, int(80 * hit(t)), axis=1)
    def fn(d, im):
        for i in range(14):
            x = (i * 90 + tl * 500) % (W + 90) - 45
            d.rectangle([x, 590, x + 50, 630], fill=(255, 150, 220))
    return glitch_common(pil_over(img, fn), t)

def e22_skew(P, tl, t):  # mute_wink (pink): on the bass drum it snaps to full colour, on the 裏 it goes soft (blur)
    g = cv2.cvtColor(P, cv2.COLOR_RGB2GRAY)[..., None].repeat(3, 2)
    p = kickpulse(t, 5.0); o = offpulse(t, 8.0)
    img = cv2.addWeighted(P, p, g, 1 - p, 0)
    if o > 0.05: img = blur(img, 1 + 2 * int(14 * o))
    return img

def e23_melt(P, tl, t):  # ガーン: it drops from the top, hits the floor, shrinks on impact, bounces smaller each time
    sc0 = 0.75; card_h = int(H * sc0); floor = H - card_h
    y, v, dt, g, e = -card_h, 0.0, 1 / 120, 4200.0, 0.5; impact = 0.0; n = int(tl / dt)
    for _ in range(n):
        v += g * dt; y += v * dt
        if y > floor: y = floor; v = -v * e; impact = 1.0
        impact *= 0.9
    sc = sc0 - 0.12 * impact
    img = blank((60, 20, 20) if impact > 0.6 and int(t * 30) % 2 else (235, 215, 185))
    card = cv2.resize(P, (int(W * sc), int(H * sc)))
    return place(img, card, (W - card.shape[1]) // 2, int(y + card_h - card.shape[0]))

def e24_blinds(P, tl, t):  # 素直すぎて発火 (2): every honest beat makes it glow hotter, then it goes to black ash
    heat = min(1, tl / (SEG * 0.75))
    img = P.astype(np.int16)
    img[..., 0] += int(140 * heat * (0.6 + 0.4 * kick(t))); img[..., 1] += int(40 * heat); img[..., 2] -= int(120 * heat)
    img = np.clip(img, 0, 255).astype(np.uint8)
    if tl > SEG * 0.75:
        p = ease((tl - SEG * 0.75) / (SEG * 0.25)); img = (img * (1 - p)).astype(np.uint8)
    return img

def e25_spin_drip(P, tl, t):  # 鼻血 (2): a red rain of drops; the poster tints redder with every drop
    img = P.astype(np.int16); img[..., 0] += int(60 * min(1, tl / SEG)); img[..., 1] -= int(40 * min(1, tl / SEG))
    img = np.clip(img, 0, 255).astype(np.uint8)
    def fn(d, im):
        for k in range(16):
            x = 100 + k * 60 + 30 * math.sin(tl * 2 + k); y0 = (tl * (300 + k * 40) + k * 200) % (H + 200) - 100
            d.line([(x, y0), (x, y0 + 60)], fill=(230, 0, 30), width=12); d.ellipse([x - 12, y0 + 50, x + 12, y0 + 74], fill=(230, 0, 30))
        d.line([(170, 520), (170 + 4 * math.sin(tl * 3), 520 + min(800, tl * 120))], fill=(230, 0, 30), width=16)
    return pil_over(img, fn)

def e26_eq(P, tl, t):  # はみ出し者の変拍子: it grows past the frame (はみ出す), and pulses off the beat on purpose
    off = (beatphase(t) + 0.5) % 1.0
    sc = 1.0 + 0.45 * min(1, tl / SEG) + 0.12 * (1 - off) ** 3
    img = zoom(P, sc, 0.5, 0.45)
    if int(tl * 3) % 7 == 6: img = swap(img, [1, 0, 2])
    return img

def e27_ribbon(P, tl, t):  # rainbow ribbon sweeps; hue rotates per beat
    img = swap(P, [[0, 1, 2], [2, 0, 1], [1, 2, 0]][int(t / BEAT) % 3])
    def fn(d, im):
        cols = [(255, 0, 80), (255, 160, 0), (255, 255, 0), (0, 230, 120), (0, 160, 255), (180, 0, 255)]
        for j, c in enumerate(cols):
            pts = [(x, H / 2 + 300 * math.sin(x / 150 + tl * 3) + j * 22 - 60 + 200 * math.sin(tl * 0.8)) for x in range(-20, W + 40, 20)]
            d.line(pts, fill=c + (230,), width=22)
    img = pil_over(img, fn)
    return img

def e28_parallel(P, tl, t):  # パラレル: copies multiply, 1 -> 2 -> 4 -> 9 -> 16, each a different colour world
    n = [1, 2, 2, 3, 3, 4][min(5, int(tl / (SEG / 6)))]
    tw, th = W // n, H // n; img = np.zeros_like(P)
    small = cv2.resize(P, (tw, th), interpolation=cv2.INTER_AREA)
    for i in range(n):
        for j in range(n):
            k = i * n + j
            tile = [small, swap(small, [2, 0, 1]), swap(small, [1, 2, 0]), invert(small)][k % 4] if n > 1 else small
            img[j * th:(j + 1) * th, i * tw:(i + 1) * tw] = tile
    return img

def e29_strobe(P, tl, t):  # ギラギラ: strobe between normal / inverted / threshold-binarized
    m = int(t * 12) % 4
    if m == 1: return invert(P)
    if m == 2:
        g = cv2.cvtColor(P, cv2.COLOR_RGB2GRAY); b = (g > 120 + 60 * math.sin(tl * 7)).astype(np.uint8) * 255
        out = np.stack([b, b // 2 + 100, b], -1) if kick(t) > 0.6 else np.stack([b, b, b], -1)
        return out.astype(np.uint8)
    if m == 3: return zoom(P, 1.3, 0.3 + 0.4 * (int(tl) % 2), 0.4)
    return P

def e30_lens(P, tl, t):  # dreaming: slow colour drift and gentle breathing (scale only)
    a = 0.5 + 0.5 * math.sin(tl * 1.1)
    img = cv2.addWeighted(P, 1 - a * 0.6, swap(P, [2, 0, 1]), a * 0.6, 0)
    img = zoom(img, 1.04 + 0.06 * math.sin(tl * 0.8), 0.5, 0.5)
    img = blur(img, 1 + 2 * int(6 * (0.5 + 0.5 * math.sin(tl * 1.3))))
    return img

def e31_blocks(P, tl, t):  # datamosh-ish: random rectangles displaced, channel-split, glitter
    img = P.copy(); r = np.random.default_rng(int(t * 15))
    for _ in range(int(4 + 30 * hit(t))):
        w, h = int(r.integers(60, 400)), int(r.integers(20, 160)); x, y = int(r.integers(0, W - w)), int(r.integers(0, H - h))
        dx, dy = r.integers(-150, 150), r.integers(-60, 60)
        src = P[y:y + h, x:x + w]; ty, tx = min(max(0, y + dy), H - h), min(max(0, x + dx), W - w)
        img[ty:ty + h, tx:tx + w] = src if r.random() > 0.3 else src[..., [2, 0, 1]]
    return img

def e32_static(P, tl, t):  # 静電気中毒: every hit is a バチッ — white flash, hair-raising jump upward, arcs
    img = P.copy(); h = hit(t)
    if h > 0.6: img = np.roll(img, -int(60 * h), axis=0); img[-int(60 * h):] = 255
    def fn(d, im):
        r = np.random.default_rng(int(t * 30)); cx, cy = 545, 700
        for _ in range(int(4 + 24 * h)):
            a = r.random() * 2 * math.pi; x, y = cx, cy; pts = [(x, y)]
            for k in range(12):
                x += math.cos(a) * 45 + r.integers(-35, 35); y += math.sin(a) * 45 + r.integers(-35, 35); pts.append((x, y))
            d.line(pts, fill=(255, 255, 255), width=4); d.line(pts, fill=(200, 120, 255), width=1)
    img = pil_over(img, fn)
    if h > 0.85: img = blank(WHITE) if int(t * 30) % 2 else invert(img)
    return img

def e33_shutter(P, tl, t):  # ピカッと狂う夜 (2): the night lit by the drum — each hit blazes, colour zigzags crackle down
    p = kickpulse(t, 8.0)
    img = np.clip(P.astype(np.float32) * (0.55 + 1.1 * p) + 40 * p, 0, 255).astype(np.uint8)
    if p > 0.85 and int(t * 30) % 2: img = blank(WHITE)
    def fn(d, im):
        r = np.random.default_rng(33)
        for i in range(5):
            x = 150 + i * 200; pts = [(x + (60 if k % 2 else -60), (k * 110 + t * 300) % (H + 200) - 100) for k in range(14)]
            d.line(pts, fill=[(255, 120, 0), (0, 200, 120), (230, 60, 200), (255, 220, 0), (120, 160, 255)][i], width=int(4 + 12 * p))
        if p > 0.3:
            rr = np.random.default_rng(int(t * 30))
            for _ in range(3):
                x = rr.integers(100, W - 100); q = [(x, 0)]
                for y in range(0, H, 90): x += rr.integers(-80, 80); q.append((x, y))
                d.line(q, fill=(255, 255, 255), width=int(3 + 8 * p))
    return pil_over(img, fn)

def e34_spotlight(P, tl, t):  # headlight sweep over a dark poster
    dark = (P * 0.12).astype(np.uint8)
    cx = int(W / 2 + 500 * math.sin(tl * 1.7)); cy = int(H / 2 + 400 * math.sin(tl * 1.1)); r = int(260 + 200 * kick(t))
    yy, xx = np.ogrid[:H, :W]; dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    m = np.clip(1 - dist / r, 0, 1)[..., None]
    img = (dark + (P.astype(np.float32) - dark) * m).astype(np.uint8)
    if hit(t) > 0.8: img = P.copy()  # flash: everything lit for one frame
    return img

def e35_jelly(P, tl, t):  # 悲しみの指数: an index meter climbs with the tears; at 100 it releases — colour blooms
    p = min(1, tl / (SEG * 0.7)); img = P.copy()
    if p < 1:
        g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)[..., None].repeat(3, 2); img = cv2.addWeighted(img, 0.35, g, 0.65, 0)
    else:
        q = ease((tl - SEG * 0.7) / (SEG * 0.3)); img = np.clip(img.astype(int) + int(70 * q) + int(40 * kick(t)), 0, 255).astype(np.uint8)
    def fn(d, im):
        r = np.random.default_rng(35)
        for i in range(25):
            x = r.integers(0, W) + 20 * math.sin(tl + i); y = (r.integers(0, H) + tl * (60 + r.integers(0, 120))) % H; s = 14 + r.integers(0, 20)
            d.polygon([(x, y - s * 1.4), (x + s * 0.9, y + s * 0.3), (x, y + s), (x - s * 0.9, y + s * 0.3)], fill=(255, 150, 220, 220))
        x0, y0, w, hh = 80, H - 160, W - 160, 50
        d.rectangle([x0, y0, x0 + w, y0 + hh], outline=(255, 255, 255), width=5)
        d.rectangle([x0, y0, x0 + w * p, y0 + hh], fill=(255, 150, 220))
        d.text((W // 2, y0 - 50), f'{int(p * 100)}', font=__import__('render').font(70), fill=(255, 255, 255), anchor='mm', stroke_width=4, stroke_fill=(0, 0, 0))
    return pil_over(img, fn)

def e36_roulette(P, tl, t):  # finale: every poster flickers past on the beat, slows, lands on this one
    n = len(IMAGES); rate = 24 * max(0.08, 1 - tl / (SEG * 0.85))
    if tl < SEG * 0.85:
        idx = int(tl * rate) % n; img = IMAGES[idx]
        return invert(img) if hit(t) > 0.85 else img
    img = P.copy()
    if hit(t) > 0.7: img = invert(img)
    return img

TRICKS += [e21_wink, e22_skew, e23_melt, e24_blinds, e25_spin_drip, e26_eq, e27_ribbon, e28_parallel, e29_strobe, e30_lens,
           e31_blocks, e32_static, e33_shutter, e34_spotlight, e35_jelly, e36_roulette]

def e_video(V, tl, t):  # a fragment that already moves: play it, let the colour thread touch it, blink white on the hardest hits
    img = V.frame(tl)
    if hit(t) > 0.8: img = swap(img, [[2, 0, 1], [1, 2, 0], [0, 2, 1]][int(t * 13) % 3])
    if kick(t) > 0.92 and int(t * 30) % 2: img = np.clip(img.astype(int) + 90, 0, 255).astype(np.uint8)
    return img

REMAP = {18: 17, 19: 18, 21: 19}      # 2026-11-19: a clip took slots 16-17, so these posters moved one place later (the kaleidoscope poster dropped out)
def scene_frame(i, tl, t):
    i = REMAP.get(i, i)
    src = POSTERS[i]
    if isinstance(src, VideoSource): return np.ascontiguousarray(e_video(src, tl, t))
    j = i - sum(1 for p in CLIPS if p < i)   # index among the still posters
    return np.ascontiguousarray(TRICKS[j](src, tl, t))

# the 裏 blur, dropped on top of whatever a scene is already doing: about a third of the scenes, and inside them only some bars
_br = np.random.default_rng(22)
BLUR_SCENES = {3, 22}  # ベイビーの聖戦 and the first 無言のウィンク (the second has its own)
def ura_blur(img, i, t):
    if i not in BLUR_SCENES or int(t / BEAT / 2) % 3 == 0: return img
    o = offpulse(t, 8.0)
    return blur(img, 1 + 2 * int(14 * o)) if o > 0.05 else img

def frame(t):
    i = min(NS - 1, int(t / SEG)); a = i * SEG; tl = t - a
    img = ura_blur(scene_frame(i, tl, t), i, t)
    if i > 0 and tl < 0.35:  # 0.35s crossfade from previous
        pimg = scene_frame(i - 1, SEG - 0.001, a - 0.001); w = tl / 0.35
        img = cv2.addWeighted(img, w, pimg, 1 - w, 0)
    if t > DUR - 2.5: img = (img * max(0, (DUR - t) / 2.5)).astype(np.uint8)
    return np.ascontiguousarray(img)

if __name__ == '__main__':
    if sys.argv[1] == 'preview':
        os.makedirs('prev2', exist_ok=True)
        for ts in sys.argv[2].split(','):
            Image.fromarray(frame(float(ts))).save(f'prev2/{float(ts):06.1f}.jpg', quality=88)
    else:
        i = int(sys.argv[1]); a = i * SEG; b = min(DUR, (i + 1) * SEG)
        out = f'v2_scene{i:02d}.mp4'; tmp = f'tmp_v2_{i:02d}.mp4'
        n0 = int(round(a * FPS)); n1 = int(round(b * FPS))
        p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                              '-c:v', 'libx264', '-crf', '18', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
        for k in range(n0, n1): p.stdin.write(frame(k / FPS).tobytes())
        p.stdin.close(); rc = p.wait()
        if rc == 0: os.rename(tmp, out); print('done', out, n1 - n0)
        else: sys.exit(rc)
