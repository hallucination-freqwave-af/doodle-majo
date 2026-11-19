"""Hand-made moments (2026-11-19): 0:31-0:41 takeover by two new clips, 0:52 the fire spreads past its frame, 1:24 the poster leaves its frame."""
import numpy as np, cv2, glob, math
import render2 as R
from render import KICKS, kickpulse

OW, OH, SW, CW = 1920, 1080, 528, 864
SEG = R.SEG
def ease(x): x = min(1.0, max(0.0, x)); return 0.5 - 0.5 * math.cos(x * math.pi)
def kicks_in(a, t): return KICKS[(KICKS >= a) & (KICKS <= t)]

# ---------------------------------------------------------------- 0:31-0:41  takeover
_clip = {}
def clip(d):
    if d not in _clip:
        out = []
        for f in sorted(glob.glob(f'seq/{d}/*.png')):
            im = cv2.cvtColor(cv2.imread(f), cv2.COLOR_BGR2RGB); s = OW / im.shape[1]
            im = cv2.resize(im, (OW, int(round(im.shape[0] * s))), interpolation=cv2.INTER_LANCZOS4); y0 = (im.shape[0] - OH) // 2
            out.append(np.ascontiguousarray(im[y0:y0 + OH]))
        _clip[d] = out
    return _clip[d]

LAY = {'A': ['centre', 'full_chunky', 'tri_close', 'full_swap', 'tri_canon', 'centre'],
       'B': ['full_chunky', 'tri_canon', 'tri_close', 'full_swap', 'tri_canon', 'centre']}
def chunky(img, n=8):
    h, w = img.shape[:2]; s = cv2.resize(cv2.resize(img, (w // n, h // n), interpolation=cv2.INTER_AREA), (w, h), interpolation=cv2.INTER_NEAREST).astype(np.int16)
    s[::4] -= 25; return np.clip(s, 0, 255).astype(np.uint8)

def takeover(base, t):
    d = 'A' if t < 7 * SEG else 'B'; a = (6 if d == 'A' else 7) * SEG
    fs = clip(d); k = min(len(fs) - 1, int((t - a) * 12)); f = fs[k]
    lay = LAY[d][min(len(kicks_in(a, t)), 5)]; out = base.copy(); L, Rz = slice(0, SW), slice(OW - SW, OW); C = slice(SW, SW + CW)
    if lay == 'centre':            # she arrives in the middle; the games keep running either side
        out[:, C] = f[:, C]
    elif lay == 'full_chunky':     # she takes all three screens; the game screens show her in their own fat pixels
        out = f.copy(); out[:, L] = chunky(f[:, L]); out[:, Rz] = chunky(f[:, Rz])
    elif lay == 'full_swap':       # all three, the side screens in the wrong colours
        out = f.copy(); out[:, L] = f[:, L][..., [2, 0, 1]]; out[:, Rz] = f[:, Rz][..., [1, 2, 0]]
    elif lay == 'tri_canon':       # three of her, each a few frames apart
        x0 = OW // 2 - SW // 2; out[:, C] = f[:, C]
        out[:, L] = fs[max(0, k - 5)][:, x0:x0 + SW]; out[:, Rz] = fs[min(len(fs) - 1, k + 5)][:, x0:x0 + SW]
    elif lay == 'tri_close':       # the side screens push in on her
        out[:, C] = f[:, C]; cr = cv2.resize(f[60:600, 828:1092], (SW, OH), interpolation=cv2.INTER_CUBIC).astype(np.float32)
        out[:, L] = np.clip(cr * np.array([1.0, 0.55, 0.85]) + 20, 0, 255).astype(np.uint8)
        out[:, Rz] = np.clip(cr[:, ::-1] * np.array([0.55, 0.95, 1.0]) + 20, 0, 255).astype(np.uint8)
    out[:, SW - 3:SW + 3] = 0; out[:, SW + CW - 3:SW + CW + 3] = 0
    p = kickpulse(t, 12.0) if len(kicks_in(a - 0.3, t)) else 0
    if p > 0.03: out = np.clip(out.astype(np.int16) + int(120 * p), 0, 255).astype(np.uint8)
    return out

# ---------------------------------------------------------------- 0:52  fire past the frame
_F = {'grid': None, 'rng': np.random.default_rng(52)}
def fire(fr, t):
    a = 10 * SEG; tl = t - a; q = (tl - 0.7 * SEG) / (0.3 * SEG); ks = kicks_in(a, t)
    heat = min(1.0, tl / (SEG * 0.55)) * (1.0 if q < 0.45 else max(0.0, 1 - (q - 0.45) * 3)); p = kickpulse(t, 5.0) if len(ks) else 0.0
    gh, gw = 135, 240
    if _F['grid'] is None: _F['grid'] = np.zeros((gh + 2, gw), np.float32)
    F = _F['grid']; rng = _F['rng']
    F[-2:] = rng.random((2, gw)).astype(np.float32) * (0.35 + 0.9 * heat + 0.6 * p) * (heat > 0.02)
    div = 4.3 - 0.27 * min(1.0, 0.25 + 0.75 * heat + 0.5 * p)
    below = F[1:-1]; F[:-2] = (np.roll(below, 1, 1) + below + np.roll(below, -1, 1) + F[2:]) / div
    v = np.clip(F[:gh], 0, 1.4); col = np.stack([np.clip(v * 3, 0, 1), np.clip(v * 3 - 1, 0, 1), np.clip(v * 3 - 2, 0, 1)], -1) * 255
    al = np.clip(v * 2.6, 0, 1)[..., None]
    col = cv2.resize(col, (OW, OH), interpolation=cv2.INTER_NEAREST); al = cv2.resize(al, (OW, OH), interpolation=cv2.INTER_NEAREST)[..., None]
    out = fr.astype(np.float32)
    for sl in (slice(0, SW), slice(OW - SW, OW)):       # the game screens heat up too
        out[:, sl, 0] += 110 * heat; out[:, sl, 2] -= 60 * heat
    out = out * (1 - al) + col * al
    for kt in ks:                                        # every bass drum: a ring of heat from the middle, across all three screens
        age = t - kt
        if age < 0.55:
            ring = np.zeros((OH // 2, OW // 2, 3), np.uint8); r = int(60 + age / 0.55 * 1150)
            cv2.circle(ring, (OW // 4, OH // 4), r // 2, (255, 235, 170), max(2, int(26 * (1 - age / 0.55))))
            out += cv2.resize(ring, (OW, OH), interpolation=cv2.INTER_LINEAR).astype(np.float32) * (1 - age / 0.55) * 1.2
    if p > 0.5 and len(ks): out += 150 * (p - 0.5) * 2 * (1 if len(ks) == 1 else 0.5)   # the first one whites out harder
    if q > 0:                                            # then everything burns white and falls to ash, sides included
        e = ease(q); tgt = 255.0 if q < 0.5 else 28.0
        for sl in (slice(0, SW), slice(OW - SW, OW)): out[:, sl] = out[:, sl] * (1 - e) + tgt * e
    out = np.clip(out, 0, 255).astype(np.uint8)
    if p > 0.35: out = np.roll(np.roll(out, int(rng.integers(-14, 15) * p), 1), int(rng.integers(-10, 11) * p), 0)
    return out

# ---------------------------------------------------------------- 1:24  the poster leaves its frame
_P = {}
def free_bg():
    if 'bg' not in _P:
        P = R.POSTERS[16]; g = cv2.GaussianBlur(P, (0, 0), 60).astype(np.float32)
        _P['bg'] = np.clip(g * 0.55 + 105, 0, 255).astype(np.uint8)      # only its glow is left where it used to hang
    return _P['bg']

def _targets():
    if 'tg' not in _P:
        a = 16 * SEG; ks = [float(x) for x in KICKS[(KICKS >= a) & (KICKS < 17 * SEG)]]; r = np.random.default_rng(84)
        xs = [264, 1656, 700, 1392, 300, 1200]; tg = [(a, 960.0, 540.0, 0.8)]
        for j, kt in enumerate(ks): tg.append((kt, float(xs[j % len(xs)]), float(r.integers(330, 760)), float(r.choice([0.42, 0.5, 0.58, 0.46]))))
        tg[-1] = (tg[-1][0], 2500.0, 420.0, 0.4)          # the last drum: gone, off the right edge
        _P['tg'] = tg
    return _P['tg']

def _state(t):
    tg = _targets(); j = max(i for i, g in enumerate(tg) if g[0] <= t) if t >= tg[0][0] else 0
    cur = tg[j]; prev = tg[j - 1] if j else cur; e = ease((t - cur[0]) / (0.22 if j < len(tg) - 1 else 0.5))
    x = prev[1] + (cur[1] - prev[1]) * e; y = prev[2] + (cur[2] - prev[2]) * e; s = prev[3] + (cur[3] - prev[3]) * e
    if j: x += 26 * math.sin(t * 1.9); y += 18 * math.sin(t * 2.7 + 1)
    return x, y, s

def _paste(out, card, x, y, alpha=1.0, shadow=False):
    h, w = card.shape[:2]; x0, y0 = int(x - w / 2), int(y - h / 2)
    for dx, dy, col in (((16, 16, (255, 80, 200)),) if shadow else ()) + ((0, 0, None),):
        xa, xb, ya, yb = max(0, x0 + dx), min(OW, x0 + dx + w), max(0, y0 + dy), min(OH, y0 + dy + h)
        if xb <= xa or yb <= ya: continue
        src = card[ya - y0 - dy:yb - y0 - dy, xa - x0 - dx:xb - x0 - dx] if col is None else np.array(col, np.uint8)
        out[ya:yb, xa:xb] = (out[ya:yb, xa:xb] * (1 - alpha) + src * alpha).astype(np.uint8) if alpha < 1 else src
    return out

def free(fr, t):
    a = 16 * SEG; tl = t - a; P = R.POSTERS[16]; out = fr
    # the empty place: a dashed outline in the centre screen
    for k in range(0, 2 * (CW + OH), 60):
        ph = (k + int(t * 60)) % (2 * (CW + OH)); m = 40
        if ph < CW: cv2.line(out, (SW + ph, m), (SW + min(CW, ph + 30), m), (255, 255, 255), 5)
        elif ph < CW + OH: cv2.line(out, (SW + CW - m, ph - CW), (SW + CW - m, min(OH, ph - CW + 30)), (255, 255, 255), 5)
        elif ph < 2 * CW + OH: cv2.line(out, (SW + CW - (ph - CW - OH), OH - m), (SW + CW - min(CW, ph - CW - OH + 30), OH - m), (255, 255, 255), 5)
        else: cv2.line(out, (SW + m, OH - (ph - 2 * CW - OH)), (SW + m, OH - min(OH, ph - 2 * CW - OH + 30)), (255, 255, 255), 5)
    for back, al in ((0.20, 0.18), (0.10, 0.32)):       # where it just was
        x, y, s = _state(max(a, t - back)); card = cv2.resize(P, (max(2, int(1080 * s)), max(2, int(1350 * s))), interpolation=cv2.INTER_AREA); out = _paste(out, card, x, y, al)
    x, y, s = _state(t); card = cv2.resize(P, (max(2, int(1080 * s)), max(2, int(1350 * s))), interpolation=cv2.INTER_AREA)
    out = _paste(out, card, x, y, 1.0, shadow=True)
    rr = 1350 * s * 0.42 + 30 * kickpulse(t, 6.0)       # the brush ring travels with it
    for k in range(40):
        an = t * 4 + k * 0.15; w = int(4 + 18 * (k / 40))
        cv2.line(out, (int(x + rr * math.cos(an)), int(y + rr * math.sin(an))), (int(x + rr * math.cos(an + 0.15)), int(y + rr * math.sin(an + 0.15))), (255, 210, 0), w)
    for i in range(22):                                   # the cranes cross all three screens
        bx = (tl * (260 + i * 35) + i * 190) % (OW + 300) - 150; by = 70 + (i * 97) % (OH - 140) + 25 * math.sin(tl * 3 + i); fl = 24 * math.sin(tl * 10 + i)
        col = (0, 200, 230) if i % 2 else (255, 255, 255)
        cv2.line(out, (int(bx - 44), int(by - fl)), (int(bx), int(by)), col, 7); cv2.line(out, (int(bx), int(by)), (int(bx + 44), int(by - fl)), col, 7)
    return out

def post(fr, t, i):
    if i in (6, 7): return takeover(fr, t)
    if i == 10: return fire(fr, t)
    if i == 16: return free(fr, t)
    if i in UK: return ukiyo(fr, t, i)
    if i in WINK_SC: return wink(fr, t)
    return bike(fr, t)

# ---------------------------------------------------------------- ukiyo-e clip (1:43 and 2:51): print plates, detail cuts, cat seals
PAPER = np.array([236, 222, 196], np.float32); INK = np.array([28, 30, 44], np.float32); INDIGO = np.array([30, 52, 120], np.float32); BENI = np.array([196, 48, 40], np.float32)
UK = {20: (0.0, 7.8), 33: (8.0, 15.0)}                 # scene -> the stretch of the clip it plays (sped up to fit: the clip barely moves)
UK_LAY = {20: ['games', 'plates', 'details', 'plates2', 'details', 'full'], 33: ['full', 'details', 'plates', 'details', 'plates2', 'games']}
UK_DET = {20: [(1150, 60), (1480, 40), (330, 80), (1250, 380), (60, 330), (1560, 360)],     # wave, Fuji, tower and pines, the crowd, the hill, the far street
          33: [(40, 230), (1220, 250), (420, 380), (1480, 200), (620, 40), (900, 330)]}      # the laughing faces, the suitcase, her face, the hands
SEAL_AT = [(130, 130), (1790, 950), (400, 950), (1520, 130), (1790, 130), (130, 950), (1520, 950), (400, 130)]   # corners of the side screens only: never on a face
_uk = {'cap': None, 'idx': -1, 'frame': None, 'grain': None}
def _uk_frame(src_t):
    if _uk['cap'] is None: _uk['cap'] = cv2.VideoCapture('clips/sd3.mp4')
    cap = _uk['cap']; k = int(src_t * 24)
    if k != _uk['idx']:
        if k != _uk['idx'] + 1: cap.set(cv2.CAP_PROP_POS_FRAMES, k)
        ok, fr = cap.read()
        while ok and _uk['idx'] + 1 < k and False: pass
        if ok:
            fr = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB); s = OW / fr.shape[1]; fr = cv2.resize(fr, (OW, int(round(fr.shape[0] * s))), interpolation=cv2.INTER_LANCZOS4)
            y0 = (fr.shape[0] - OH) // 2; _uk['frame'] = np.ascontiguousarray(fr[y0:y0 + OH])
        _uk['idx'] = k
    return _uk['frame']

def key_plate(img):      # the black key block: lines only, on paper
    g = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY); m = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 15, 9) > 0
    m |= g < 60; return np.where(m[..., None], INK, PAPER).astype(np.uint8)
def colour_plate(img, which):   # the colour blocks without the key lines: flat, a few inks, lines blurred away
    m = cv2.medianBlur(img, 21); m = (m // 52) * 52 + 26
    if which == 'beni': m = m[..., [0, 2, 1]]                   # the second pull, with the inks swapped
    return np.clip(m.astype(np.float32) * 0.85 + PAPER * 0.15, 0, 255).astype(np.uint8)
def ink_game(img):        # the games, printed in indigo on paper
    lum = img.astype(np.float32).mean(2, keepdims=True) / 255; return (PAPER + (INDIGO - PAPER) * np.clip(lum * 1.5, 0, 1)).astype(np.uint8)

def _seal(size=170):
    if 'seal' not in _uk:
        s = np.zeros((size, size, 4), np.uint8); cv2.rectangle(s, (6, 6), (size - 7, size - 7), (196, 40, 36, 235), -1, cv2.LINE_AA)
        c = size // 2; hole = np.zeros((size, size), np.uint8)
        cv2.circle(hole, (c, c + 12), 46, 255, -1, cv2.LINE_AA)                                   # a cat's head, cut out of the red
        cv2.fillPoly(hole, [np.array([(c - 46, c - 4), (c - 40, c - 62), (c - 8, c - 30)], np.int32)], 255, cv2.LINE_AA)
        cv2.fillPoly(hole, [np.array([(c + 46, c - 4), (c + 40, c - 62), (c + 8, c - 30)], np.int32)], 255, cv2.LINE_AA)
        s[..., 3] = np.where(hole > 0, 0, s[..., 3])
        for ex in (-18, 18): cv2.ellipse(s, (c + ex, c + 6), (6, 10), 0, 0, 360, (196, 40, 36, 235), -1, cv2.LINE_AA)
        for sx in (-1, 1):
            for dy in (-6, 6): cv2.line(s, (c + sx * 14, c + 28), (c + sx * 44, c + 28 + dy), (196, 40, 36, 235), 2, cv2.LINE_AA)
        _uk['seal'] = s
    return _uk['seal']

def ukiyo(base, t, i):
    a = i * SEG; tl = t - a; s0, s1 = UK[i]
    tick = int(tl * 4); pos = tick // 3 + (1 if tick % 3 == 1 else 0)        # 4 frames a second, and it stutters: forward, forward, back
    f = _uk_frame(min(s1, s0 + pos * (s1 - s0) / (int(SEG * 4) // 3 + 1)))
    ks = kicks_in(a, t); n = len(ks); lay = UK_LAY[i][min(n, 5)]; L, Rz, C = slice(0, SW), slice(OW - SW, OW), slice(SW, SW + CW)
    out = f.copy()
    if lay == 'games':        # she stands in the middle; the games either side are printed in indigo
        out[:, L] = ink_game(base[:, L]); out[:, Rz] = ink_game(base[:, Rz])
    elif lay in ('plates', 'plates2'):   # the print pulled apart across the screens: key lines one side, one colour block the other
        kl, cp = key_plate(f), colour_plate(f, 'indigo' if lay == 'plates' else 'beni')
        a_, b_ = (L, Rz) if lay == 'plates' else (Rz, L); out[:, a_] = kl[:, a_]; out[:, b_] = cp[:, b_]
    elif lay == 'details':    # the picture hardly moves, so the cutting does: each side screen jumps to a corner of the print
        det = UK_DET[i]
        for sl, j in ((L, n), (Rz, n + 3)):
            x0, y0 = det[j % len(det)]; x0 = min(x0, OW - 342); y0 = min(y0, OH - 700)
            out[:, sl] = cv2.resize(f[y0:y0 + 700, x0:x0 + 342], (SW, OH), interpolation=cv2.INTER_CUBIC)
    if _uk['grain'] is None: _uk['grain'] = (np.random.default_rng(3).normal(0, 7, (OH // 2, OW // 2)).astype(np.float32))
    out = np.clip(out.astype(np.float32) + cv2.resize(_uk['grain'], (OW, OH), interpolation=cv2.INTER_NEAREST)[..., None], 0, 255).astype(np.uint8)
    out[:, SW - 3:SW + 3] = (28, 30, 44); out[:, SW + CW - 3:SW + CW + 3] = (28, 30, 44)
    seal = _seal(); off = 0 if i == 20 else 3
    for j, kt in enumerate(ks):   # every bass drum stamps a red cat seal, and they stay
        age = t - kt; sc = 1.0 + max(0.0, 0.09 - age) * 9; sz = int(170 * sc); sl_ = cv2.resize(seal, (sz, sz), interpolation=cv2.INTER_AREA)
        M = cv2.getRotationMatrix2D((sz / 2, sz / 2), (-9, 6, -4, 11, 3, -12)[(j + off) % 6], 1.0); sl_ = cv2.warpAffine(sl_, M, (sz, sz))
        cx, cy = SEAL_AT[(j + off) % len(SEAL_AT)]; x0, y0 = cx - sz // 2, cy - sz // 2
        xa, xb, ya, yb = max(0, x0), min(OW, x0 + sz), max(0, y0), min(OH, y0 + sz); p = sl_[ya - y0:yb - y0, xa - x0:xb - x0]; al = p[..., 3:4].astype(np.float32) / 255
        out[ya:yb, xa:xb] = (out[ya:yb, xa:xb] * (1 - al) + p[..., :3] * al).astype(np.uint8)
    if n and (t - ks[-1]) < 0.07: out = np.roll(out, 10, axis=0)       # the stamp lands
    return out

# ---------------------------------------------------------------- the motorbike, scattered through the whole song (short cut-ins on a bass drum)
class Reader:
    def __init__(self, path): self.cap = cv2.VideoCapture(path); self.idx = -1; self.frame = None
    def get(self, src_t):
        k = int(src_t * 24)
        if k != self.idx:
            if k != self.idx + 1: self.cap.set(cv2.CAP_PROP_POS_FRAMES, k)
            ok, fr = self.cap.read()
            if ok:
                fr = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB); s = OW / fr.shape[1]; fr = cv2.resize(fr, (OW, int(round(fr.shape[0] * s))), interpolation=cv2.INTER_LANCZOS4)
                y0 = (fr.shape[0] - OH) // 2; self.frame = np.ascontiguousarray(fr[y0:y0 + OH])
            self.idx = k
        return self.frame

BIKE_SCENES = [1, 4, 8, 11, 13, 17, 19, 21, 24, 26, 28, 30, 32, 34, 36, 37]
BIKE_TYPES = ['both', 'left', 'both', 'right']   # 2026-11-19: only ever in the side screens (that reads best); which side varies
def _bike_plan():
    plan = []
    for j, sc in enumerate(BIKE_SCENES):
        a, b = sc * SEG, (sc + 1) * SEG; ks = [float(k) for k in KICKS if a + 0.6 <= k <= b - 1.2]
        if not ks: continue
        t0 = min(ks, key=lambda k: abs(k - (a + b) / 2 + (0.8 if j % 2 else -0.8)))       # not always the same place in the scene
        nxt = [float(k) for k in KICKS if k > t0 + 0.3]; t1 = min(t0 + 1.1, max(t0 + 0.5, nxt[0] if nxt else t0 + 0.8), b - 0.1)
        plan.append((t0, t1, j * 15.0 / len(BIKE_SCENES), BIKE_TYPES[j % len(BIKE_TYPES)]))
    return plan
BIKE_PLAN = _bike_plan()   # parked 2026-11-19: real-light footage kills the strange mood
BIKE = []
_bk = {}
def bike(fr, t):
    for t0, t1, s0, typ in BIKE:
        if t0 <= t < t1: break
    else: return fr
    if 'a' not in _bk: _bk['a'] = Reader('clips/sd4.mp4'); _bk['b'] = Reader('clips/sd4.mp4')
    src = min(14.9, s0 + (t - t0)); f = _bk['a'].get(src); cx = 1000 if src < 8.0 else 800; out = fr
    g = _bk['b'].get(min(14.9, src + 0.45)); x0 = min(max(0, cx - SW // 2), OW - SW)   # she rides into the game screens, in their fat pixels; the poster stays
    if typ in ('both', 'left'): out[:, :SW] = chunky(f[:, x0:x0 + SW])
    if typ in ('both', 'right'): out[:, OW - SW:] = chunky((g if typ == 'both' else f)[:, x0:x0 + SW])
    out[:, SW - 3:SW + 3] = 0; out[:, SW + CW - 3:SW + CW + 3] = 0
    if t - t0 < 0.07: out = np.clip(out.astype(np.int16) + 70, 0, 255).astype(np.uint8)
    return out

# ---------------------------------------------------------------- 2:20  the sailor girl: 4 fps walking up (cuts and colours on the drum), the wink at 10 fps stuttering, 4 fps out
WINK_SC = (27, 28); WINK_EYE = (9.6, 11.3)      # where the eyelid moves in the clip
WINK_LOOK = ['plain', 'close', 'swapA', 'close', 'swapB', 'plain', 'closeA', 'plain']
_wk = {}
def wink(fr, t):
    if 'r' not in _wk:
        _wk['r'] = Reader('clips/sd5.mp4'); T0 = WINK_SC[0] * SEG; T1 = (WINK_SC[-1] + 1) * SEG
        ks = [float(k) for k in KICKS if k >= T0 + SEG + 0.9]; _wk['t'] = (T0, ks[0], T1)       # the wink starts on a bass drum
    T0, TW, T1 = _wk['t']; e0, e1 = WINK_EYE; out = fr; WL = 3.0; C = slice(SW, SW + CW)
    if t < TW:                                   # 4 fps, centre only; every bass drum changes how she is shown
        n = int((TW - T0) * 4) + 1; f = _wk['r'].get(int((t - T0) * 4) * 9.3 / n); look = WINK_LOOK[len(kicks_in(T0, t)) % len(WINK_LOOK)]
        c = f[:, C]
        if look.startswith('close'): c = cv2.resize(f[40:580, 744:1176], (CW, OH), interpolation=cv2.INTER_CUBIC)
        if look in ('swapA', 'closeA'): c = c[..., [2, 0, 1]]
        elif look == 'swapB': c = c[..., [1, 2, 0]]
        out[:, C] = c
    elif t < TW + WL:                            # 10 ticks a second, and the eyelid stutters: forward, back, forward — all three screens
        tick = int((t - TW) * 10); pos = tick // 3 + (1 if tick % 3 == 1 else 0)
        f = _wk['r'].get(min(e1, e0 + pos * (e1 - e0) / 10.0)); out = f.copy()
        if t - TW < 0.07: out = np.clip(out.astype(np.int16) + 90, 0, 255).astype(np.uint8)
    else:                                        # 4 fps again, back in her frame
        f = _wk['r'].get(min(14.9, 11.6 + int((t - TW - WL) * 4) * 0.3)); out[:, C] = f[:, C]
    out[:, SW - 3:SW + 3] = 0; out[:, SW + CW - 3:SW + CW + 3] = 0
    return out
