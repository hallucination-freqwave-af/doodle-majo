import numpy as np, cv2, sys, subprocess, os, math
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1350, 30
P = np.array(Image.open('poster.png').convert('RGB'))  # (H,W,3)
BLUE = np.array([0, 170, 230], np.uint8)
PINK = np.array([255, 120, 220], np.uint8)
BLACK = np.zeros(3, np.uint8)
WHITE = np.full(3, 255, np.uint8)

rms = np.load('rms.npy'); flux = np.load('flux.npy'); low = np.load('low.npy'); hi = np.load('hi.npy')
AFPS = 22050 / 512
rms = rms / rms.max()
BEAT = 60 / 89.1
def af(arr, t):
    i = min(int(t * AFPS), len(arr) - 1); return float(arr[max(i, 0)])
def kick(t):  # smoothed low energy peak
    i = int(t * AFPS); return float(low[max(0, i - 1):i + 2].max()) if i < len(low) else 0.0
def hit(t):   # onset strength
    return af(flux, t)
def beatphase(t): return (t / BEAT) % 1.0

FONT_JP = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
_fonts = {}
def font(sz):
    if sz not in _fonts: _fonts[sz] = ImageFont.truetype(FONT_JP, sz, index=0)
    return _fonts[sz]

rng = np.random.default_rng(7)
CARD = (240, 65, 830, 660)  # black square with girls
GIRLS = P[CARD[1]:CARD[3], CARD[0]:CARD[2]].copy()

# ---------- helpers ----------
def blank(color=BLUE):
    return np.ascontiguousarray(np.broadcast_to(color, (H, W, 3)).astype(np.uint8))

def strips(img, n, amp, t, seed=0, vertical=False):
    out = img.copy()
    r = np.random.default_rng(seed + int(t * 7))
    if vertical:
        edges = np.linspace(0, W, n + 1).astype(int)
        for a, b in zip(edges[:-1], edges[1:]):
            out[:, a:b] = np.roll(img[:, a:b], int(r.integers(-amp, amp + 1)), axis=0)
    else:
        edges = np.linspace(0, H, n + 1).astype(int)
        for a, b in zip(edges[:-1], edges[1:]):
            out[a:b] = np.roll(img[a:b], int(r.integers(-amp, amp + 1)), axis=1)
    return out

def invert(img): return 255 - img
def swap(img, order): return img[..., order]
def mosaic(img, block):
    block = max(1, int(block))
    s = cv2.resize(img, (max(1, W // block), max(1, H // block)), interpolation=cv2.INTER_AREA)
    return cv2.resize(s, (W, H), interpolation=cv2.INTER_NEAREST)
def place(bg, fg, x, y, scale=1.0):
    if scale != 1.0:
        fg = cv2.resize(fg, (max(1, int(fg.shape[1] * scale)), max(1, int(fg.shape[0] * scale))), interpolation=cv2.INTER_AREA)
    h, w = fg.shape[:2]
    x0, y0 = int(x), int(y)
    xa, ya = max(0, x0), max(0, y0); xb, yb = min(W, x0 + w), min(H, y0 + h)
    if xb <= xa or yb <= ya: return bg
    bg[ya:yb, xa:xb] = fg[ya - y0:yb - y0, xa - x0:xb - x0]
    return bg
def pil_over(img, draw_fn):
    im = Image.fromarray(img); d = ImageDraw.Draw(im, 'RGBA'); draw_fn(d, im); return np.array(im.convert('RGB'))
def text(img, s, size, xy, fill=(255, 255, 255), anchor='mm', stroke=0, sfill=(0, 0, 0), angle=0):
    f = font(size)
    if angle == 0:
        return pil_over(img, lambda d, im: d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=sfill))
    bbox = f.getbbox(s, stroke_width=stroke); tw, th = bbox[2] - bbox[0] + 20, bbox[3] - bbox[1] + 20
    layer = Image.new('RGBA', (tw, th), (0, 0, 0, 0)); ImageDraw.Draw(layer).text((10 - bbox[0], 10 - bbox[1]), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=sfill)
    layer = layer.rotate(angle, expand=True, resample=Image.BICUBIC)
    im = Image.fromarray(img); im.paste(layer, (int(xy[0] - layer.width / 2), int(xy[1] - layer.height / 2)), layer); return np.array(im)

def cat(d, x, y, s, color, flip=False, run=0.0):
    # procedural running cat: body, head, ears, tail, legs
    f = -1 if flip else 1
    d.ellipse([x - s * 1.0, y - s * 0.45, x + s * 1.0, y + s * 0.45], fill=color)
    hx = x + f * s * 1.0
    d.ellipse([hx - s * 0.5, y - s * 0.75, hx + s * 0.5, y + s * 0.15], fill=color)
    d.polygon([(hx - f * s * 0.42, y - s * 0.6), (hx - f * s * 0.5, y - s * 1.25), (hx - f * s * 0.05, y - s * 0.75)], fill=color)
    d.polygon([(hx + f * s * 0.05, y - s * 0.75), (hx + f * s * 0.45, y - s * 1.2), (hx + f * s * 0.42, y - s * 0.6)], fill=color)
    # tail
    tx = x - f * s * 1.0
    d.line([(tx, y), (tx - f * s * 0.7, y - s * 0.6 - s * 0.5 * math.sin(run * 6)), (tx - f * s * 0.3, y - s * 1.4)], fill=color, width=max(2, int(s * 0.18)))
    # legs
    ph = math.sin(run * 12)
    for i, lx in enumerate([x - s * 0.6, x - s * 0.2, x + s * 0.3, x + s * 0.7]):
        dy = s * 0.5 * abs(math.sin(run * 12 + i * 1.57))
        d.line([(lx, y + s * 0.2), (lx + f * s * 0.3 * ph * (1 if i % 2 else -1), y + s * 0.4 + dy)], fill=color, width=max(2, int(s * 0.2)))
    # eye
    ex = hx + f * s * 0.18
    d.ellipse([ex - s * 0.08, y - s * 0.4, ex + s * 0.08, y - s * 0.24], fill=(255, 120, 220))

def speedlines(img, n, t, color=(255, 255, 255), alpha=200):
    def fn(d, im):
        r = np.random.default_rng(int(t * 30))
        for _ in range(n):
            y = int(r.integers(0, H)); l = int(r.integers(80, 500)); x = int(r.integers(-200, W))
            d.line([(x, y), (x + l, y)], fill=color + (int(r.integers(80, alpha)),), width=int(r.integers(2, 7)))
    return pil_over(img, fn)

def sun(img, cx, cy, r, t, rays=24, col=(255, 230, 60)):
    def fn(d, im):
        for i in range(rays):
            a = t * 0.8 + i * 2 * math.pi / rays
            d.polygon([(cx + math.cos(a) * r * 0.9, cy + math.sin(a) * r * 0.9),
                       (cx + math.cos(a + 0.08) * r * 2.6, cy + math.sin(a + 0.08) * r * 2.6),
                       (cx + math.cos(a - 0.08) * r * 2.6, cy + math.sin(a - 0.08) * r * 2.6)], fill=col + (90,))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col + (255,))
        # smug face
        d.arc([cx - r * 0.5, cy - r * 0.2, cx + r * 0.5, cy + r * 0.5], 10, 170, fill=(0, 0, 0, 255), width=int(r * 0.08))
        for ex in (-0.3, 0.3):
            d.line([(cx + ex * r - r * 0.12, cy - r * 0.25), (cx + ex * r + r * 0.12, cy - r * 0.25)], fill=(0, 0, 0, 255), width=int(r * 0.08))
    return pil_over(img, fn)

def particles(img, n, t, seed, size=6, col=(255, 255, 255)):
    r = np.random.default_rng(seed)
    px = r.random(n); py = r.random(n); vx = r.normal(0, 0.05, n); vy = r.normal(0, 0.05, n)
    xs = ((px + vx * t) % 1.0 * W).astype(int); ys = ((py + vy * t) % 1.0 * H).astype(int)
    def fn(d, im):
        for x, y in zip(xs, ys): d.ellipse([x - size, y - size, x + size, y + size], fill=col)
    return pil_over(img, fn)

# ---------- scenes (each: f(t_local, t_global) -> frame) ----------
def sc_intro(tl, t):  # strips slide in on beats; 0-12s
    img = blank(BLACK)
    n = 18
    edges = np.linspace(0, H, n + 1).astype(int)
    order = np.random.default_rng(1).permutation(n)
    for k, i in enumerate(order):
        arrive = 0.4 + k * (11.0 / n)
        if t >= arrive:
            a, b = edges[i], edges[i + 1]
            prog = min(1, (t - arrive) / 0.25)
            off = int((1 - prog) ** 2 * W * (1 if i % 2 else -1))
            img[a:b] = np.roll(P[a:b], off, axis=1) if prog < 1 else P[a:b]
    if hit(t) > 0.5: img = strips(img, 30, 40, t)
    return img

def sc_bounce(tl, t):  # DVD-logo poster + speed lines; 12-42s
    img = blank(BLUE)
    img = speedlines(img, int(20 + 60 * kick(t)), t)
    sc = 0.45 + 0.08 * kick(t)
    w, h = int(W * sc), int(H * sc)
    vx, vy = 310, 230
    x = (tl * vx) % (2 * (W - w)); x = x if x < W - w else 2 * (W - w) - x
    y = (tl * vy) % (2 * (H - h)); y = y if y < H - h else 2 * (H - h) - y
    card = P
    phase = int(tl / 2.5) % 4
    if phase == 1: card = swap(P, [2, 0, 1])
    elif phase == 2: card = invert(P)
    elif phase == 3: card = swap(P, [1, 2, 0])
    img = place(img, card, x, y, sc)
    # ghost trail
    for k in (1, 2, 3):
        gx = x - k * 40; img = place(img, (card // (k + 1)).astype(np.uint8), gx, y + k * 10, sc) if hit(t) > 0.4 else img
    img = text(img, '風を切って走るスピード', 70, (W // 2, 120 + 20 * math.sin(tl * 3)), stroke=6, angle=-6)
    if kick(t) > 0.8: img = strips(img, 24, 60, t)
    return img

def sc_cats(tl, t):  # cats run, girls chase; 42-72s
    img = blank(PINK if int(tl * 2) % 8 == 0 else BLUE)
    img = speedlines(img, 15, t, color=(0, 0, 0), alpha=120)
    def fn(d, im):
        r = np.random.default_rng(3)
        for i in range(14):
            sp = 250 + r.integers(0, 400); s = 30 + r.integers(0, 60); y0 = r.integers(80, H - 80)
            flip = bool(r.integers(0, 2)); x = ((tl * sp + r.integers(0, W)) % (W + 300)) - 150
            if flip: x = W - x
            col = [(0, 0, 0), (255, 255, 255), (255, 120, 220)][i % 3]
            cat(d, x, y0 + 12 * math.sin(tl * 8 + i), s, col, flip=flip, run=tl)
    img = pil_over(img, fn)
    # girls card chasing, bobbing
    gx = (tl * 180) % (W + 600) - 300
    sc = 0.8 + 0.1 * kick(t)
    img = place(img, GIRLS, gx, 420 + 30 * math.sin(tl * 9), sc)
    img = text(img, '追いつけ 猫のスピリット', 64, (W // 2, 1180), stroke=6, angle=5)
    img = text(img, 'ニャ' * (1 + int(tl) % 3), 48, (W // 2, 90), fill=(0, 0, 0), angle=-3)
    if hit(t) > 0.55: img = strips(img, 40, 25, t, vertical=True)
    return img

def sc_flicker(tl, t):  # 明滅 chaos, heads swap; 72-102s
    k = kick(t); h = hit(t)
    base = P.copy()
    if int(tl * 6) % 2 == 0 and k > 0.5: base = invert(base)
    if h > 0.6: base = swap(base, [[2, 0, 1], [1, 2, 0], [0, 2, 1]][int(t * 13) % 3])
    base = strips(base, 12 + int(40 * k), int(10 + 150 * k), t)
    # head swap: mirror the girls card on alternate beats
    if int(t / BEAT) % 2 == 0:
        base[CARD[1]:CARD[3], CARD[0]:CARD[2]] = GIRLS[:, ::-1]
    # mosaic pulse
    if beatphase(t) < 0.15: base = mosaic(base, 8 + 40 * k)
    # random black frames = blink
    if h > 0.85 and int(t * 30) % 3 == 0: base = blank(BLACK)
    if int(tl) % 4 == 3: base = text(base, '明滅', 260, (W // 2, H // 2), fill=(255, 120, 220), stroke=10, angle=10 * math.sin(tl * 5))
    return base

def sc_sun(tl, t):  # 朝日は昇るが居場所はなし; 102-134s
    img = blank(BLUE)
    img = particles(img, 60, t, 11, size=4)
    rise = min(1, tl / 10)
    cy = H + 300 - rise * (H + 100); cx = W // 2
    img = sun(img, cx, cy, 170 + 20 * kick(t), tl)
    # poster gets shoved: slides up and out, bounces back, shoved again
    push = max(0, (tl - 6))
    oy = -int(1400 * (push / 6) ** 2) if push < 6 else int(-1400 + (push - 6) * 700) if push < 9 else int(400 * math.sin((push - 9) * 2))
    sc = 0.55; img = place(img, P, (W - W * sc) // 2 + 300 * math.sin(tl * 1.3), 150 + oy, sc)
    if tl > 14:
        lines = ['朝日は昇るが', '居場所はなし', 'Dawn breaks,', 'but I belong nowhere.']
        for i, s in enumerate(lines):
            if tl > 14 + i * 2.2:
                img = text(img, s, 80 if i < 2 else 60, (W // 2, 200 + i * 110), fill=(0, 0, 0) if i < 2 else (255, 255, 255), stroke=5, sfill=(255, 255, 255) if i < 2 else (0, 0, 0), angle=(-4, 4)[i % 2])
    if tl > 24:  # cat laughs at the sun
        img = pil_over(img, lambda d, im: cat(d, 200 + 60 * math.sin(tl * 4), H - 180, 60, (0, 0, 0), run=tl))
        img = text(img, 'ｗ' * (1 + int(tl * 3) % 5), 56, (330, H - 330), fill=(0, 0, 0), angle=15)
    if hit(t) > 0.7: img = strips(img, 20, 30, t)
    return img

def sc_cells(tl, t):  # 単細胞: noise -> mosaic resolves to poster, dissolves again; 134-166s
    cyc = 8.0; p = (tl % cyc) / cyc
    block = 2 + 120 * (1 - math.sin(p * math.pi)) ** 2
    img = mosaic(P, block)
    noise = np.random.default_rng(int(t * 30)).integers(0, 255, (H // 20, W // 20, 3), dtype=np.uint8)
    noise = cv2.resize(noise, (W, H), interpolation=cv2.INTER_NEAREST)
    a = (1 - math.sin(p * math.pi)) ** 3 * 0.9
    img = cv2.addWeighted(img, 1 - a, noise, a, 0)
    # cell blobs breathing
    def fn(d, im):
        r = np.random.default_rng(5)
        for i in range(25):
            x, y = r.integers(0, W), r.integers(0, H); rr = 20 + 60 * r.random() * (0.5 + 0.5 * math.sin(tl * 2 + i))
            col = [(255, 120, 220, 110), (0, 0, 0, 90), (255, 255, 255, 120)][i % 3]
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=col)
            d.ellipse([x - rr * 0.3, y - rr * 0.3, x + rr * 0.3, y + rr * 0.3], fill=(0, 170, 230, 200))
    img = pil_over(img, fn)
    if kick(t) > 0.75: img = strips(img, 16, 80, t, vertical=int(tl) % 2 == 0)
    img = text(img, '単細胞', 90, (W - 260, 110), fill=(255, 255, 255), stroke=6, angle=-8)
    return img

def sc_finale(tl, t):  # everything at once, faster; 166-190s
    k = kick(t); h = hit(t)
    img = sc_bounce(tl * 1.7, t) if int(tl * 2) % 3 != 1 else sc_cats(tl * 1.4, t)
    if int(tl * 4) % 5 == 0: img = invert(img)
    img = strips(img, 10 + int(60 * k), int(20 + 200 * k), t, vertical=int(tl * 3) % 2 == 0)
    if h > 0.6: img = mosaic(img, 6 + 30 * h)
    img = sun(img, 140 + 40 * math.sin(tl * 2), 160, 70, tl, rays=12)
    words = ['自由がモットー', 'Freedom', 'あまのじゃく', 'ニャー', '平均値はなし', '狂った周波数']
    img = text(img, words[int(tl * 1.5) % len(words)], 110, (W // 2, H // 2 + 200 * math.sin(tl * 2)), fill=(255, 120, 220) if int(tl * 6) % 2 else (255, 255, 255), stroke=8, angle=12 * math.sin(tl * 7))
    return img

def sc_outro(tl, t):  # 190-202: poster alone, blinks out
    e = af(rms, t)
    img = P.copy()
    if tl < 2: img = cv2.addWeighted(img, tl / 2, blank(BLACK), 1 - tl / 2, 0)
    if tl > 5:
        img = cv2.addWeighted(img, max(0, 1 - (tl - 5) / 4), blank(BLACK), min(1, (tl - 5) / 4), 0)
    if tl > 7: img = text(img, 'documented by Matashichi .', 44, (W // 2, H - 60), fill=(255, 120, 220))
    if tl > 10 and int(tl * 10) % 7 == 0: img = blank(BLACK)
    return img

SCENES = [(0, 12, sc_intro), (12, 42, sc_bounce), (42, 72, sc_cats), (72, 102, sc_flicker),
          (102, 134, sc_sun), (134, 166, sc_cells), (166, 190, sc_finale), (190, 201.9, sc_outro)]

def frame(t):
    for a, b, fn in SCENES:
        if a <= t < b:
            img = fn(t - a, t)
            # 0.4s crossfade into scene
            if t - a < 0.4 and a > 0:
                prev = [f for x, y, f in SCENES if y == a][0]
                pimg = prev(a - [x for x, y, f in SCENES if y == a][0] - 0.001, a - 0.001)
                w = (t - a) / 0.4; img = cv2.addWeighted(img, w, pimg, 1 - w, 0)
            return np.ascontiguousarray(img)
    return blank(BLACK)

if __name__ == '__main__':
    if sys.argv[1] == 'preview':
        os.makedirs('prev', exist_ok=True)
        for ts in sys.argv[2].split(','):
            Image.fromarray(frame(float(ts))).save(f'prev/{float(ts):06.1f}.jpg', quality=88)
    else:
        i = int(sys.argv[1]); a, b, fn = SCENES[i]
        out = f'scene{i:02d}.mp4'; tmp = f'tmp_scene{i:02d}.mp4'
        n = int(round((b - a) * FPS))
        p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                              '-c:v', 'libx264', '-crf', '18', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
        for k in range(n):
            p.stdin.write(frame(a + k / FPS).tobytes())
        p.stdin.close(); rc = p.wait()
        if rc == 0: os.rename(tmp, out); print('done', out, n)
        else: sys.exit(rc)
