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
    if d == 'P' and d not in _clip:               # one dancer cut out of the green-screen take, on flat pink
        import solo
        fig = solo.split('s2A')[0]; out = []
        for f in fig:
            bg = np.zeros((OH, OW, 3), np.uint8); bg[:] = (255, 105, 180); h, w = f.shape[:2]; s_ = 1000 / h; f = cv2.resize(f, (int(w * s_), 1000), interpolation=cv2.INTER_LANCZOS4); h, w = f.shape[:2]
            x0, y0 = OW // 2 - w // 2, OH - h - 30; cv2.ellipse(bg, (OW // 2, OH - 40), (230, 26), 0, 0, 360, (215, 70, 150), -1)
            al = f[..., 3:4].astype(np.float32) / 255; bg[y0:y0 + h, x0:x0 + w] = (bg[y0:y0 + h, x0:x0 + w] * (1 - al) + f[..., :3] * al).astype(np.uint8); out.append(bg)
        _clip[d] = out
    if d not in _clip:
        out = []
        for f in sorted(glob.glob(f'seq/{d}/*.png')):
            im = cv2.cvtColor(cv2.imread(f), cv2.COLOR_BGR2RGB); s = OW / im.shape[1]
            im = cv2.resize(im, (OW, int(round(im.shape[0] * s))), interpolation=cv2.INTER_LANCZOS4); y0 = (im.shape[0] - OH) // 2
            out.append(np.ascontiguousarray(im[y0:y0 + OH]))
        _clip[d] = out
    return _clip[d]

LAY = {'A': ['centre', 'full_chunky', 'tri_close', 'full_swap', 'tri_canon', 'centre'],
       'B': ['full_chunky', 'tri_canon', 'tri_close', 'full_swap', 'tri_canon', 'centre'],
       'P': ['full_chunky', 'tri_canon', 'tri_close', 'full_swap', 'tri_canon', 'centre']}
def chunky(img, n=8):
    h, w = img.shape[:2]; s = cv2.resize(cv2.resize(img, (w // n, h // n), interpolation=cv2.INTER_AREA), (w, h), interpolation=cv2.INTER_NEAREST).astype(np.int16)
    s[::4] -= 25; return np.clip(s, 0, 255).astype(np.uint8)

def takeover(base, t):
    TP = 37.27                                   # the pink-hoodie girl keeps the first two seconds, then on this bass drum the cut-out dancer takes over
    d = 'A' if t < 7 * SEG else ('B' if t < TP else 'P'); a = 6 * SEG if d == 'A' else (7 * SEG if d == 'B' else TP)
    if d == 'P': return dancer2(base, t)
    fs = clip(d); k = min(len(fs) - 1, int((t - a) * 12) + (10 if d == 'P' else 0)); f = fs[k]
    if d == 'P' and 'hy' not in _clip:           # where her head is, per frame (she crouches), for the close-up
        _clip['hy'] = [int(np.where((np.abs(x[:, 900:1020].astype(int) - (255, 105, 180)).sum(2) > 60).any(1))[0][0]) for x in fs]
    lay = (['full_chunky', 'tri_canon', 'full_swap', 'tri_close', 'centre'][min(len(kicks_in(a, t)) - 1, 4)] if d == 'P' else LAY[d][min(len(kicks_in(a, t)), 5)]); out = base.copy(); L, Rz = slice(0, SW), slice(OW - SW, OW); C = slice(SW, SW + CW)
    if d == 'P' and lay.startswith('full'):       # she is alone on flat pink: when she takes all three screens, she is in each of them
        xc = OW // 2 - SW // 2; f = f.copy(); f[:, L] = fs[max(0, k - 3)][:, xc:xc + SW]; f[:, Rz] = fs[min(len(fs) - 1, k + 3)][:, xc:xc + SW]
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
        out[:, C] = f[:, C]; cr = cv2.resize(f[60:600, 828:1092] if d != 'P' else f[max(0, _clip['hy'][k] - 40):max(0, _clip['hy'][k] - 40) + 400, 862:1058], (SW, OH), interpolation=cv2.INTER_CUBIC).astype(np.float32)
        out[:, L] = np.clip(cr * np.array([1.0, 0.55, 0.85]) + 20, 0, 255).astype(np.uint8)
        out[:, Rz] = np.clip(cr[:, ::-1] * np.array([0.55, 0.95, 1.0]) + 20, 0, 255).astype(np.uint8)
    out[:, SW - 3:SW + 3] = 0; out[:, SW + CW - 3:SW + CW + 3] = 0
    if d == 'P' and t - a < 0.08: out = np.clip(out.astype(np.int16) + 120, 0, 255).astype(np.uint8)
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
    if t < GEO_AT[16]: return fr                     # the scene before runs on until the bass drum
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

def _post(fr, t, i):
    if i == 0: return intro(fr, t)
    if i >= END_SC: return ending(fr, t)
    if i == 24: return gaan(fr, t)
    if i == 25: return thermal(fr, t)
    if i == 26: return flood(fr, t)
    if i in (6, 7): return takeover(fr, t)
    if i == 10: return fire(fr, t)
    if i in (16, 17): return juggle(fr, t)
    if i in UK: return ukiyo(fr, t, i)
    if i in WINK_SC: return wink(fr, t)
    if i == DZ_SC: return danzen(fr, t) if t < GEO_AT[30] else hands(fr, t)
    if i == 30: return hands(fr, t)
    return colourfly(bike(fr, t), t)

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

# ---------------------------------------------------------------- 0:46  the colour leaves the kiro-kiro poster with the sparkles, and flies off across all three screens
FLY_T = 9 * SEG; FLY_A, FLY_B = FLY_T - 1.2, FLY_T + 1.1
_fl = {}
def _fly_init():
    P = R.POSTERS[8]; r = np.random.default_rng(46); hsv = cv2.cvtColor(P, cv2.COLOR_RGB2HSV)
    ys, xs = np.where((hsv[..., 1] > 70) & (hsv[..., 2] > 90)); n = 900
    if len(ys) < n: ys, xs = np.where(hsv[..., 2] > 60)
    idx = r.choice(len(ys), n, replace=False); ys, xs = ys[idx], xs[idx]
    col = hsv[ys, xs].astype(np.float32); col[:, 1] = np.clip(col[:, 1] * 1.6 + 60, 0, 255); col[:, 2] = np.clip(col[:, 2] * 1.2 + 40, 0, 255)
    col = cv2.cvtColor(col.astype(np.uint8)[None], cv2.COLOR_HSV2RGB)[0]
    x0 = SW + xs * (CW / 1080.0); y0 = ys * (OH / 1350.0)
    ang = np.arctan2(y0 - OH * 0.55, x0 - OW / 2) + r.normal(0, 0.5, n); sp = r.uniform(250, 1000, n)
    _fl.update(x=x0, y=y0, vx=np.cos(ang) * sp * 1.5, vy=np.sin(ang) * sp - 250, col=col, born=FLY_A + (1 - y0 / OH) * 0.75 + r.uniform(0, 0.45, n),
               size=r.integers(4, 15, n), star=r.random(n) < 0.3, life=r.uniform(0.9, 1.7, n), tw=r.random(n) * 6.3)
def colourfly(fr, t):
    if not (FLY_A <= t < FLY_B): return fr
    if not _fl: _fly_init()
    out = fr
    if t < FLY_T:                               # as it leaves, the poster goes grey from the bottom up
        p = ease((t - FLY_A) / 1.1); c = out[:, SW:SW + CW]; g = cv2.cvtColor(c, cv2.COLOR_RGB2GRAY)[..., None].astype(np.float32)
        lim = OH * (1 - p * 1.15); w = np.clip((np.arange(OH)[:, None, None] - lim) / 90.0, 0, 1)
        out[:, SW:SW + CW] = (c * (1 - w) + g * w).astype(np.uint8)
    age = t - _fl['born']; m = (age > 0) & (age < _fl['life'])
    for k in np.where(m)[0]:
        a = float(age[k]); x = _fl['x'][k] + _fl['vx'][k] * a; y = _fl['y'][k] + _fl['vy'][k] * a - 300 * a * a
        if not (-40 < x < OW + 40 and -40 < y < OH + 40): continue
        fade = 1 - a / _fl['life'][k]; s = max(2, int(_fl['size'][k] * (0.5 + fade))); col = tuple(int(v) for v in _fl['col'][k])
        xb = _fl['x'][k] + _fl['vx'][k] * max(0, a - 0.05); yb = _fl['y'][k] + _fl['vy'][k] * max(0, a - 0.05) - 300 * max(0, a - 0.05) ** 2
        cv2.line(out, (int(xb), int(yb)), (int(x), int(y)), col, max(1, s // 3))
        if _fl['star'][k]:                        # a sparkle rides with the colour
            q = int(s * (1.6 + 0.8 * math.sin(t * 30 + _fl['tw'][k]))); xi, yi = int(x), int(y)
            cv2.fillPoly(out, [np.array([(xi, yi - q), (xi + q // 4, yi - q // 4), (xi + q, yi), (xi + q // 4, yi + q // 4), (xi, yi + q), (xi - q // 4, yi + q // 4), (xi - q, yi), (xi - q // 4, yi - q // 4)], np.int32)], (255, 255, 255))
            cv2.circle(out, (xi, yi), max(1, q // 4), col, -1)
        else: cv2.rectangle(out, (int(x) - s // 2, int(y) - s // 2), (int(x) + s // 2, int(y) + s // 2), col, -1)
    if abs(t - FLY_T) < 0.05: out = np.clip(out.astype(np.int16) + 80, 0, 255).astype(np.uint8)
    return out

# ---------------------------------------------------------------- 2:33  時空断線: the red line-diamond comes flying out of the poster until it fills all three screens
DZ_SC = 29; DZ_C = (SW + int(525 * 0.8), int(1045 * 0.8)); DZ_RED = (255, 72, 40)
_dz = {}
def danzen_poster():
    if 'p' not in _dz: _dz['p'] = cv2.resize(cv2.cvtColor(cv2.imread('extra/danzen.png'), cv2.COLOR_BGR2RGB), (1080, 1350), interpolation=cv2.INTER_AREA)
    return _dz['p']
def danzen(fr, t):
    a = DZ_SC * SEG; tl = t - a; out = fr; cx, cy = DZ_C; ks = kicks_in(a, t)
    births = [(a - 1.5 + k * 0.055, 1.0) for k in range(int((tl + 1.5) / 0.055) + 1)] + [(float(k), 3.0) for k in ks]      # a steady stream, and a heavy one on every bass drum
    rate = 1.3 + 0.9 * min(1.0, tl / 3.0)                                                                  # they come faster and faster
    for tb, wt in sorted(births):
        age = t - tb
        if age < 0: continue
        s = 26 * math.exp(age * rate)
        if s > 3200: continue
        pts = np.array([(cx, cy - s * 0.93), (cx + s, cy), (cx, cy + s * 0.93), (cx - s, cy)], np.int32)
        cv2.polylines(out, [pts], True, DZ_RED, max(1, int((1 + s / 260) * wt)), cv2.LINE_AA)
    L = min(2400, 300 * math.exp(tl * 1.1))                                                                # the cross through its middle keeps growing
    th = max(2, int(2 + tl * 2)); cv2.line(out, (int(cx - L), cy), (int(cx + L), cy), DZ_RED, th, cv2.LINE_AA); cv2.line(out, (cx, int(cy - L)), (cx, int(cy + L)), DZ_RED, th, cv2.LINE_AA)
    if len(ks) and t - ks[-1] < 0.06: out = np.clip(out.astype(np.int16) + 70, 0, 255).astype(np.uint8)
    return out


# ---------------------------------------------------------------- geometric cuts, here and there: tiles close over all three screens, then open onto the next scene
P_POP = [(255, 80, 200), (0, 200, 230), (255, 220, 0), (12, 12, 16), (245, 245, 245), (255, 72, 40)]
P_PRINT = [(236, 222, 196), (30, 52, 120), (196, 48, 40), (28, 30, 44), (236, 222, 196)]          # paper, indigo, beni, ink
P_RED = [(255, 72, 40), (12, 12, 16), (245, 245, 245), (255, 72, 40), (200, 30, 120)]
P_NIGHT = [(255, 220, 0), (12, 12, 16), (245, 245, 245), (120, 160, 255), (12, 12, 16)]
# scene the cut leads into -> (shape, palette, how it sweeps)
EARLY = {23: 116.87}      # this scene comes in early, on the bass drum after the held breath at 1:57
P_TITLE = [(255, 220, 0), (0, 200, 230), (245, 245, 245), (120, 160, 255), (255, 240, 120), (0, 200, 230)]
GEO_HOLD = {100: 26.63}    # 100 = the title card: tiles close on 25.15, hold under the title, open on 26.63
GEO_AT = {16: 83.55, 100: 25.15, 30: 152.53}      # this cut sits on the bass drum, not on the scene grid (the grid was 0.7 s early against the music)
GEOS = {100: ('hex', P_TITLE, 'in'), 16: ('diamond', P_POP, 'in'), 11: ('tri', P_POP, 'in'), 14: ('hex', P_POP, 'down'), 20: ('check', P_PRINT, 'diag'), 30: ('diamond', P_RED, 'out'), 35: ('check', P_NIGHT, 'in')}
_geo = {}
def _cells(shape):
    out = []
    if shape == 'tri':
        w, h = 120, 104
        for row in range(-1, OH // h + 2):
            for col in range(-2, OW // (w // 2) + 2):
                x = col * (w // 2); y = row * h; up = (row + col) % 2 == 0
                out.append(([(x, y + h), (x + w // 2, y), (x + w, y + h)] if up else [(x, y), (x + w, y), (x + w // 2, y + h)], x + w / 2, y + h / 2))
    elif shape == 'hex':
        rad = 74; dx = rad * math.sqrt(3); dy = rad * 1.5
        for row in range(-1, int(OH / dy) + 2):
            for col in range(-1, int(OW / dx) + 2):
                cx = col * dx + (dx / 2 if row % 2 else 0); cy = row * dy
                out.append(([(cx + rad * math.sin(k * math.pi / 3), cy - rad * math.cos(k * math.pi / 3)) for k in range(6)], cx, cy))
    elif shape == 'check':
        q = 120
        for row in range(OH // q + 1):
            for col in range(OW // q + 1): out.append(([(col * q, row * q), (col * q + q, row * q), (col * q + q, row * q + q), (col * q, row * q + q)], col * q + q / 2, row * q + q / 2))
    elif shape == 'diamond':
        w, h = 160, 148
        for row in range(-1, int(OH / (h / 2)) + 2):
            for col in range(-1, int(OW / (w / 2)) + 2):
                if (row + col) % 2: continue
                cx, cy = col * w / 2, row * h / 2; out.append(([(cx, cy - h / 2), (cx + w / 2, cy), (cx, cy + h / 2), (cx - w / 2, cy)], cx, cy))
    return out
def _geo_init(sc):
    shape, pal, sweep = GEOS[sc]; T = GEO_AT.get(sc, sc * SEG); r = np.random.default_rng(sc); tiles = []
    for pts, cx, cy in _cells(shape):
        rad = min(1.0, math.hypot((cx - OW / 2) / (OW / 2), (cy - OH / 2) / (OH / 2)) / 1.25)
        if sweep == 'in': c, o = 1 - rad, rad                      # closes from the edges, opens from the middle
        elif sweep == 'out': c, o = rad, rad                       # bursts from the middle, clears from the middle
        elif sweep == 'down': c = o = min(1.0, max(0.0, cy / OH))  # falls from the top, clears from the top
        else: c = o = min(1.0, max(0.0, (cx + cy) / (OW + OH)))    # sweeps corner to corner
        j = r.uniform(0, 0.09)
        ci = int(r.integers(0, len(pal))) if shape != 'check' or pal is P_NIGHT else (int(cx // 120 + cy // 120) % 2) * 1 + (2 if r.random() < 0.12 else 0)
        tiles.append((np.array(pts, np.int32), T - 0.52 + 0.40 * c + j, GEO_HOLD.get(sc, T) + 0.07 + 0.42 * o + j, pal[ci % len(pal)], ci, float(r.uniform(0, 10))))
    _geo[sc] = tiles
def geo(fr, t):
    for sc in GEOS:
        T = GEO_AT.get(sc, sc * SEG)
        if T - 0.55 <= t < GEO_HOLD.get(sc, T) + 0.65:
            if sc not in _geo: _geo_init(sc)
            pal = GEOS[sc][1]
            for pts, on, off, col, ci, ph in _geo[sc]:
                if on <= t < off:
                    if sc in GEO_HOLD: col = pal[(ci + int(t * 5 + ph)) % len(pal)]             # while it holds, the tiles keep changing colour
                    c = (255, 255, 255) if (t - on < 0.04 or off - t < 0.04) else col          # each one flashes white as it turns
                    cv2.fillPoly(fr, [pts], c); cv2.polylines(fr, [pts], True, (12, 12, 16), 2, cv2.LINE_AA)
    return fr

def post(fr, t, i): return title(geo(_post(fr, t, i), t), t)

# ---------------------------------------------------------------- 1:57  the centre picture cracks in the held breath, then bursts into pieces on the bass drum
_sh = {}
def _shards_geo():
    if 'tris' in _sh: return
    r = np.random.default_rng(117); nx, ny = 8, 10; gx = np.zeros((ny + 1, nx + 1, 2), np.float32)
    for j in range(ny + 1):
        for i in range(nx + 1):
            x = i * CW / nx + (r.uniform(-34, 34) if 0 < i < nx else 0); y = j * OH / ny + (r.uniform(-34, 34) if 0 < j < ny else 0); gx[j, i] = (x, y)
    tris = []
    for j in range(ny):
        for i in range(nx):
            a, b, c, d = gx[j, i], gx[j, i + 1], gx[j + 1, i + 1], gx[j + 1, i]
            tris += [(a, b, c), (a, c, d)] if (i + j) % 2 else [(a, b, d), (b, c, d)]
    _sh['tris'] = tris; sh = []
    for tri in tris:
        pts = np.array(tri); c = pts.mean(0); d = c - np.array([CW / 2, OH / 2]); dist = float(np.hypot(*d)) + 1e-3
        sp = r.uniform(1500, 3200); sh.append(dict(pts=pts, c=c, v=d / dist * sp + r.normal(0, 260, 2), w=r.uniform(-9, 9), delay=dist * 0.00012, grow=r.uniform(0.2, 1.3)))
    _sh['sh'] = sh
def cracks(fr, t, TC):                    # in the pause before the hit: fine white cracks spread over the picture
    _shards_geo(); p = (t - (TC - 0.75)) / 0.75
    if p <= 0: return fr
    n = int(len(_sh['tris']) * min(1.0, p) ** 1.5); order = sorted(range(len(_sh['sh'])), key=lambda k: _sh['sh'][k]['delay'])
    for k in order[:n]:
        pts = (_sh['sh'][k]['pts'] + (SW, 0)).astype(np.int32); cv2.polylines(fr, [pts], True, (255, 255, 255), 2, cv2.LINE_AA)
    return fr
def shatter_init(img):                    # img: the centre picture as it stood at the hit (864 x 1080)
    _shards_geo()
    for s in _sh['sh']:
        x0, y0 = np.floor(s['pts'].min(0)).astype(int); x1, y1 = np.ceil(s['pts'].max(0)).astype(int); x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(CW, x1), min(OH, y1)
        m = np.zeros((y1 - y0, x1 - x0), np.uint8); cv2.fillPoly(m, [(s['pts'] - (x0, y0)).astype(np.int32)], 255)
        s['patch'] = img[y0:y1, x0:x1].copy(); s['mask'] = m; s['off'] = s['c'] - (x0, y0)
    _sh['ready'] = True
def shatter(fr, t, TC):
    age = t - TC
    if not _sh.get('ready') or age > 1.3: return fr
    for s in _sh['sh']:
        a = max(0.0, age - s['delay']); sc = 1 + s['grow'] * a
        cx = SW + s['c'][0] + s['v'][0] * a; cy = s["c"][1] + s["v"][1] * a + 200 * a * a
        ph, pw = s['mask'].shape; S = int(math.hypot(pw, ph) * sc) + 4
        if not (-S < cx < OW + S and -S < cy < OH + S): continue
        M = cv2.getRotationMatrix2D((float(s['off'][0]), float(s['off'][1])), math.degrees(s['w'] * a), sc); M[0, 2] += S / 2 - s['off'][0]; M[1, 2] += S / 2 - s['off'][1]
        p = cv2.warpAffine(s['patch'], M, (S, S)); m = cv2.warpAffine(s['mask'], M, (S, S))
        x0, y0 = int(cx - S / 2), int(cy - S / 2); xa, xb, ya, yb = max(0, x0), min(OW, x0 + S), max(0, y0), min(OH, y0 + S)
        if xb <= xa or yb <= ya: continue
        mm = m[ya - y0:yb - y0, xa - x0:xb - x0] > 128; reg = fr[ya:yb, xa:xb]; reg[mm] = p[ya - y0:yb - y0, xa - x0:xb - x0][mm]
        edge = cv2.Canny(m, 50, 150)[ya - y0:yb - y0, xa - x0:xb - x0] > 0; reg[edge] = (255, 255, 255)      # a bright rim, like broken glass
    return fr

# ================================================================= 2026-11-19 late: go all the way — the opening, 2:04-2:20, and the ending
class Shards:
    """a picture cut into jittered triangles that fly; age 0 = whole. Run age downwards and it assembles instead."""
    def __init__(self, w, h, nx, ny, seed, ox=0, oy=0, speed=(1500, 3200), grav=200.0):
        r = np.random.default_rng(seed); self.w, self.h, self.ox, self.oy, self.grav = w, h, ox, oy, grav; g = np.zeros((ny + 1, nx + 1, 2), np.float32)
        for j in range(ny + 1):
            for i in range(nx + 1): g[j, i] = (i * w / nx + (r.uniform(-.3, .3) * w / nx if 0 < i < nx else 0), j * h / ny + (r.uniform(-.3, .3) * h / ny if 0 < j < ny else 0))
        self.s = []
        for j in range(ny):
            for i in range(nx):
                a, b, c, d = g[j, i], g[j, i + 1], g[j + 1, i + 1], g[j + 1, i]
                for tri in ([(a, b, c), (a, c, d)] if (i + j) % 2 else [(a, b, d), (b, c, d)]):
                    pts = np.array(tri); cen = pts.mean(0); dv = cen - np.array([w / 2, h / 2]); dist = float(np.hypot(*dv)) + 1e-3
                    self.s.append(dict(pts=pts, c=cen, v=dv / dist * r.uniform(*speed) + r.normal(0, 260, 2), w=r.uniform(-9, 9), delay=dist * 0.00012, grow=r.uniform(0.2, 1.3)))
    def init(self, img):
        for s in self.s:
            x0, y0 = np.floor(s['pts'].min(0)).astype(int); x1, y1 = np.ceil(s['pts'].max(0)).astype(int); x0, y0, x1, y1 = max(0, x0), max(0, y0), min(self.w, x1), min(self.h, y1)
            m = np.zeros((y1 - y0, x1 - x0), np.uint8); cv2.fillPoly(m, [(s['pts'] - (x0, y0)).astype(np.int32)], 255); s['patch'] = img[y0:y1, x0:x1].copy(); s['mask'] = m; s['off'] = s['c'] - (x0, y0)
        self.ready = True; return self
    def draw(self, fr, age, rim=True):
        for s in self.s:
            a = max(0.0, age - s['delay']); sc = 1 + s['grow'] * a
            cx = self.ox + s['c'][0] + s['v'][0] * a; cy = self.oy + s['c'][1] + s['v'][1] * a + self.grav * a * a
            ph, pw = s['mask'].shape; S = int(math.hypot(pw, ph) * sc) + 4
            if not (-S < cx < OW + S and -S < cy < OH + S): continue
            M = cv2.getRotationMatrix2D((float(s['off'][0]), float(s['off'][1])), math.degrees(s['w'] * a), sc); M[0, 2] += S / 2 - s['off'][0]; M[1, 2] += S / 2 - s['off'][1]
            p = cv2.warpAffine(s['patch'], M, (S, S)); m = cv2.warpAffine(s['mask'], M, (S, S))
            x0, y0 = int(cx - S / 2), int(cy - S / 2); xa, xb, ya, yb = max(0, x0), min(OW, x0 + S), max(0, y0), min(OH, y0 + S)
            if xb <= xa or yb <= ya: continue
            mm = m[ya - y0:yb - y0, xa - x0:xb - x0] > 128; reg = fr[ya:yb, xa:xb]; reg[mm] = p[ya - y0:yb - y0, xa - x0:xb - x0][mm]
            if rim and a > 0: reg[cv2.Canny(m, 50, 150)[ya - y0:yb - y0, xa - x0:xb - x0] > 0] = (255, 255, 255)
        return fr
def _snow(shape, t, k=6):
    n = np.random.default_rng(int(t * 60)).integers(0, 255, (shape[0] // k, shape[1] // k), dtype=np.uint8); return np.repeat(cv2.resize(n, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)[..., None], 3, 2)
def _lines(out): out[:, SW - 3:SW + 3] = 0; out[:, SW + CW - 3:SW + CW + 3] = 0; return out

# ---- before the music: the tube warms up, the "dreaming majo" card flies together out of pieces from all over the three screens, holds —
# ---- and on the first note of the song it bursts, and the song's own opening (the strips sliding in) is underneath
PRE = 2.0; PRE_WHOLE = 1.35; _in = {}
def _logo():
    if 'sh' not in _in:
        from PIL import Image as _I
        pim = _I.open('extra/logo.png').convert('RGBA'); bg = _I.new('RGBA', pim.size, (255, 255, 255, 255)); bg.alpha_composite(pim)      # the card is white
        im = cv2.resize(np.array(bg.convert('RGB')), (1080, 1920), interpolation=cv2.INTER_AREA)[285:1635]
        _in['sh'] = Shards(CW, OH, 8, 10, 1, ox=SW).init(cv2.resize(im, (CW, OH), interpolation=cv2.INTER_AREA))
    return _in['sh']
def pre_frame(tp):                                  # tp: 0 .. PRE, silent
    out = np.zeros((OH, OW, 3), np.uint8); out[:, :SW] = _snow((OH, SW), tp); out[:, OW - SW:] = _snow((OH, SW), tp + 9)
    out = _lines(out); out = _logo().draw(out, max(0.0, (PRE_WHOLE - tp) * 1.25 - 0.12), rim=tp < PRE_WHOLE)
    if tp < 0.42:                                   # the picture opens from a white line
        m = np.zeros((OH, OW), bool); w = int(OW / 2 * min(1.0, tp / 0.2)); h = 3 if tp < 0.2 else int(OH / 2 * ((tp - 0.2) / 0.22) ** 2) + 3
        m[OH // 2 - h:OH // 2 + h, OW // 2 - w:OW // 2 + w] = True; out[~m] = 0
        if tp < 0.24: out[m] = 255
    if 0 <= tp - PRE_WHOLE < 0.07: out = np.clip(out.astype(np.int16) + 110, 0, 255).astype(np.uint8)
    return out
def intro(fr, t):                                   # the song has started: the card bursts
    if t > 1.4: return fr
    out = _logo().draw(fr, t)
    if t < 0.09: out = np.clip(out.astype(np.int16) + 140, 0, 255).astype(np.uint8)
    return out

# ---- 2:04  ガーン: on every bass drum a side screen drops out of its frame and a fresh one slams in from above
def _drop_off(a):
    if a < 0.28: return OH * (a / 0.28) ** 2
    if a < 0.5: return -OH * (1 - (a - 0.28) / 0.22) ** 2
    return 46 * math.exp(-(a - 0.5) * 9) * abs(math.sin((a - 0.5) * 22))
def gaan(fr, t):
    a0 = 24 * SEG; ks = kicks_in(a0, t); out = fr
    for side in (0, 1):
        mine = [k for j, k in enumerate(ks) if j % 2 == side]
        if not mine: continue
        y = int(_drop_off(t - mine[-1]))
        if y == 0: continue
        sl = slice(0, SW) if side == 0 else slice(OW - SW, OW); pan = out[:, sl].copy(); out[:, sl] = (40, 12, 12)
        if y > 0: out[y:, sl] = pan[:OH - y] if y < OH else out[y:, sl]
        else: out[:OH + y, sl] = pan[-y:]
    if len(ks) and t - ks[-1] < 0.08: out = np.roll(out, 16, axis=0)
    return _lines(out)

# ---- 2:09  素直すぎて発火 (2): the whole wall seen through a heat camera, hotter with every bass drum
def thermal(fr, t):
    a0 = 25 * SEG; tl = t - a0; p = kickpulse(t, 5.0); heat = min(1.0, tl / (SEG * 0.6))
    g = np.clip(fr.astype(np.float32).mean(2) * (0.75 + 0.5 * heat + 0.7 * p), 0, 255).astype(np.uint8)
    th = cv2.cvtColor(cv2.applyColorMap(g, cv2.COLORMAP_INFERNO), cv2.COLOR_BGR2RGB); w = min(1.0, 0.25 + 0.75 * heat)
    out = cv2.addWeighted(fr, 1 - w, th, w, 0)
    if tl > SEG * 0.85: out = (out * max(0.0, 1 - (tl - SEG * 0.85) / (SEG * 0.15))).astype(np.uint8)
    return _lines(out)

# ---- 2:14  鼻血 (2): it rains red on all three screens and the red rises
def flood(fr, t):
    a0 = 26 * SEG; tl = t - a0; out = fr; r = np.random.default_rng(26); level = int(OH - OH * 0.5 * min(1.0, tl / SEG) ** 1.3); RED = (230, 0, 30)
    for k in range(70):
        x = int(r.integers(0, OW)); sp = 500 + r.integers(0, 700); y = int((r.integers(0, OH) + tl * sp) % (level + 80)) - 80; L = 50 + int(r.integers(0, 60))
        cv2.line(out, (x, y), (x, min(level, y + L)), RED, 9); cv2.circle(out, (x, min(level, y + L)), 9, RED, -1)
    reg = out[level:].astype(np.float32); out[level:] = (reg * 0.18 + np.array(RED) * 0.82).astype(np.uint8); out[level:level + 5] = (255, 120, 130)
    for kt in kicks_in(a0, t):
        age = t - kt
        if age < 0.5:
            rr = np.random.default_rng(int(kt * 100)); x = int(rr.integers(150, OW - 150)); w = int(40 + 500 * age)
            cv2.ellipse(out, (x, level), (w, max(3, int(26 * (1 - age / 0.5)))), 0, 180, 360, (255, 200, 205), 5)
    return _lines(out)

# ---- 3:06  the end: everything spins faster and faster, the last bass drum breaks all three screens, and what is left is a cat and a name
END_SC = 36; END_T0 = END_SC * SEG; END_TS = float(KICKS[-1]); END_OFF = 193.4; _en = {}
def _roul(t):
    tl = max(0.0, t - END_T0); idx = int(5 * tl + 10 * tl * tl); n = len(R.IMAGES); out = np.zeros((OH, OW, 3), np.uint8)
    out[:, SW:SW + CW] = cv2.resize(R.IMAGES[idx % n], (CW, OH), interpolation=cv2.INTER_AREA)
    for sl, k in ((slice(0, SW), idx + 7), (slice(OW - SW, OW), idx + 13)): out[:, sl] = chunky(cv2.resize(R.IMAGES[k % n][:, 276:804], (SW, OH), interpolation=cv2.INTER_AREA))
    if idx % 3 == 1: out = 255 - out
    return _lines(out)
def _after(t):
    out = np.zeros((OH, OW, 3), np.uint8)
    for x0, x1 in ((6, SW - 6), (SW + 6, SW + CW - 6), (OW - SW + 6, OW - 6)): cv2.rectangle(out, (x0, 6), (x1, OH - 7), (46, 46, 58), 2)
    cx, cy, r_ = OW // 2, 470, 92; W_ = (240, 240, 240)
    if t > END_TS + 0.9:
        cv2.circle(out, (cx, cy), r_, W_, -1)
        for s in (-1, 1): cv2.fillPoly(out, [np.array([(cx + s * r_, cy - 28), (cx + s * (r_ - 6), cy - r_ - 46), (cx + s * 22, cy - r_ + 8)], np.int32)], W_)
        if int(t * 1.4) % 5: 
            for s in (-1, 1): cv2.ellipse(out, (cx + s * 36, cy - 6), (9, 15), 0, 0, 360, (0, 0, 0), -1)
        else:
            for s in (-1, 1): cv2.line(out, (cx + s * 36 - 11, cy - 6), (cx + s * 36 + 11, cy - 6), (0, 0, 0), 4)
    if t > END_TS + 1.8:
        txt = 'documented by Matashichi .'; (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 1.1, 2); cv2.putText(out, txt, (cx - tw // 2, 690), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 120, 220), 2, cv2.LINE_AA)
    return out
def ending(fr, t):
    if t < END_TS: return _roul(t)
    if t >= END_OFF + 0.5: return np.zeros((OH, OW, 3), np.uint8)
    out = _after(t)
    if t > END_OFF:                                 # the tube switches off: a line, then a dot
        a = t - END_OFF; h = max(3, int(OH * (1 - min(1.0, a / 0.22)) ** 2)); w = OW if a < 0.22 else max(6, int(OW * (1 - (a - 0.22) / 0.28)))
        small = cv2.resize(out, (w, h), interpolation=cv2.INTER_AREA); out = np.zeros_like(out); y0, x0 = (OH - h) // 2, (OW - w) // 2
        out[y0:y0 + h, x0:x0 + w] = np.maximum(small, 255 if h <= 3 else 0); return out
    age = t - END_TS
    if age < 3.3:
        if 'sh' not in _en: _en['sh'] = Shards(OW, OH, 12, 8, 188, speed=(700, 2300), grav=1500.0).init(_roul(END_TS - 0.001))
        out = _en['sh'].draw(out, age)
    if age < 0.1: out = np.clip(out.astype(np.int16) + 150, 0, 255).astype(np.uint8)
    return out

# ---------------------------------------------------------------- the title, "ama no jako": a sticker slapped across all three screens on a bass drum
TI_IN, TI_OUT = 25.15, 26.63; _ti = {}
def _title_img():
    if 'im' not in _ti:
        im = cv2.cvtColor(cv2.imread('extra/title.png'), cv2.COLOR_BGR2RGB).astype(np.int32); r, g, b = im[..., 0], im[..., 1], im[..., 2]
        al = 1 - np.clip((g - np.maximum(r, b) - 40) / 60.0, 0, 1); im[..., 1] = np.minimum(g, np.maximum(r, b) + 10)               # key out the green, take the spill off
        w = 1780; h = int(im.shape[0] * w / im.shape[1]); rgb = cv2.resize(im.astype(np.uint8), (w, h), interpolation=cv2.INTER_AREA); al = cv2.resize(al.astype(np.float32), (w, h), interpolation=cv2.INTER_AREA)
        pad = 40; rgb = cv2.copyMakeBorder(rgb, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(255, 255, 255)); al = cv2.copyMakeBorder(al, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
        m = (al > 0.5).astype(np.uint8); rim = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (37, 37)))                # a white sticker edge so it reads on anything
        rim_a = cv2.GaussianBlur(rim.astype(np.float32), (0, 0), 1.2); rgb = (rgb * al[..., None] + 255 * (1 - al[..., None])).astype(np.uint8)
        _ti['im'] = np.dstack([rgb, (np.maximum(rim_a, al) * 255).astype(np.uint8)])
    return _ti['im']
def title(fr, t):
    if not (TI_IN <= t < TI_OUT + 0.25): return fr
    a = t - TI_IN; im = _title_img()
    sc = 1.0 + 0.05 * kickpulse(t, 8.0)
    if a < 0.2: sc = 0.2 + 1.0 * (a / 0.2) if a < 0.13 else 1.2 - 0.2 * ((a - 0.13) / 0.07)                                      # slapped on: overshoots, settles
    dy = 0
    if t > TI_OUT: dy = -int(1500 * ((t - TI_OUT) / 0.25) ** 2)                                                                   # and it is peeled off upwards
    out = fr
    h, w = im.shape[:2]; W2, H2 = max(2, int(w * sc)), max(2, int(h * sc)); p = cv2.resize(im, (W2, H2), interpolation=cv2.INTER_LINEAR)
    for ox, oy, shadow in ((22, 22, True), (0, 0, False)):
        x0, y0 = OW // 2 - W2 // 2 + ox, OH // 2 - H2 // 2 + oy + dy; xa, xb, ya, yb = max(0, x0), min(OW, x0 + W2), max(0, y0), min(OH, y0 + H2)
        if xb <= xa or yb <= ya: continue
        q = p[ya - y0:yb - y0, xa - x0:xb - x0]; al = q[..., 3:4].astype(np.float32) / 255
        src = np.array((20, 10, 30), np.float32) if shadow else q[..., :3].astype(np.float32)
        out[ya:yb, xa:xb] = (out[ya:yb, xa:xb] * (1 - al) + src * al).astype(np.uint8)
    if a < 0.06: out = np.clip(out.astype(np.int16) + 100, 0, 255).astype(np.uint8)
    return out


# ---------------------------------------------------------------- 1:25  the girl with the floating balls (replaces the 自由気ままん poster; runs two slots)
JG_A, JG_B = GEO_AT[16], 18 * SEG; JG_C = (905, 400)
JG_LOOK = ['wide4', 'sizes', 'echo', 'upstut', 'wide4', 'sizes', 'upstut', 'wide4', 'sizes', 'upstut', 'wide4', 'sizes', 'upstut', 'wide4']     # the afterimage only once
JG_HALF = 17 * SEG      # second half: the other take of her, with the glass shapes
class Clip:
    def __init__(self, path): self.cap = cv2.VideoCapture(path); self.n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)); self.c = {}; self.last = -9
    def get(self, k):
        k = int(min(max(k, 0), self.n - 2))
        if k not in self.c:
            if k != self.last + 1: self.cap.set(cv2.CAP_PROP_POS_FRAMES, k)
            ok, fr = self.cap.read(); self.last = k
            if not ok: return next(iter(self.c.values()))
            fr = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB); sc = OW / fr.shape[1]; fr = cv2.resize(fr, (OW, int(round(fr.shape[0] * sc))), interpolation=cv2.INTER_LANCZOS4); y0 = (fr.shape[0] - OH) // 2
            if len(self.c) > 40: self.c.pop(next(iter(self.c)))
            self.c[k] = np.ascontiguousarray(fr[y0:y0 + OH])
        return self.c[k]
def _zoomc(f, s, w=OW, h=OH):                         # crop round her, at scale s, to a w x h window
    cw, ch = w / s, h / s; x0 = int(min(max(JG_C[0] - cw / 2, 0), OW - cw)); y0 = int(min(max(JG_C[1] - ch * 0.45, 0), OH - ch))
    return cv2.resize(f[y0:y0 + int(ch), x0:x0 + int(cw)], (w, h), interpolation=cv2.INTER_CUBIC)
_jg = {}
def juggle(fr, t):
    if not (JG_A <= t < JG_B): return fr
    if 'c' not in _jg: _jg['c'] = Clip('clips/sd6.mp4'); _jg['d'] = Clip('clips/sd7.mp4')
    c = _jg['c'] if t < JG_HALF else _jg['d']; ks = kicks_in(JG_A - 0.05, t); n = max(0, len(ks) - 1); look = JG_LOOK[n % len(JG_LOOK)]; since = t - (ks[-1] if len(ks) else JG_A)
    src = (t - JG_A) / (JG_HALF - JG_A) * 7.0 if t < JG_HALF else 3.0 + (t - JG_HALF) / (JG_B - JG_HALF) * 9.5      # first half of one take, then the busiest stretch of the other
    slow = t >= JG_HALF                              # the second take is played slow, 5 frames a second, hands barely moving
    if slow: src = 5.0 + (t - JG_HALF) / (JG_B - JG_HALF) * 3.4
    F = (lambda sec: c.get(int(sec * 5) / 5.0 * 24)) if slow else (lambda sec: c.get(sec * 24))
    if look == 'wide4':                               # all three screens, 4 frames a second
        out = F(int(src * 4) / 4.0).copy()
    elif look == 'echo':                              # the balls and her hands leave themselves behind
        q = int(src * 12) / 12.0; acc = F(q).astype(np.float32) * 0.34
        for j, wgt in ((1, 0.26), (2, 0.22), (3, 0.18)): acc += F(q - j * 0.33).astype(np.float32) * wgt
        out = acc.astype(np.uint8)
    elif look == 'upstut':                            # big, small, bigger: the size stutters in and the picture goes forward, back, forward
        tick = int(since * 10); pos = tick // 3 + (1 if tick % 3 == 1 else 0); zs = [1.0, 1.5, 1.25, 2.0, 1.6, 2.7, 2.1, 3.3]
        out = _zoomc(F(src - since) if slow else F(src - since + pos * 0.12), zs[tick % len(zs)])
    else:                                             # three sizes of her at once, and they keep changing places
        f = F(int(src * 6) / 6.0); bg = cv2.resize(f[900:1000, 0:100], (SW, OH), interpolation=cv2.INTER_AREA); small = cv2.resize(f, (SW, int(SW * OH / OW)), interpolation=cv2.INTER_AREA)
        tile = bg.copy(); hh = small.shape[0]
        for row in range(3): tile[30 + row * 350:30 + row * 350 + hh] = small
        views = [tile, _zoomc(f, 1.35, SW, OH), _zoomc(f, 3.4, SW, OH)]; r_ = int(since * 5)
        out = np.zeros((OH, OW, 3), np.uint8); out[:, SW:SW + CW] = _zoomc(f, [1.9, 1.0, 2.6][r_ % 3], CW, OH)
        out[:, :SW] = views[r_ % 3]; out[:, OW - SW:] = views[(r_ + 1) % 3]
    if since < 0.05 and n > 0: out = np.clip(out.astype(np.int16) + 60, 0, 255).astype(np.uint8)
    return _lines(out)


# ---------------------------------------------------------------- 2:34  her hands and the glass shapes (replaces the rest of 時空断線 and the ギラギラ poster)
HD_A, HD_B = GEO_AT[30], 31 * SEG; HD_IRIS = 157.83
HD_LOOK = ['wide4', 'sizes', 'upstut', 'colour', 'three', 'echo', 'sizes', 'upstut', 'colour', 'three', 'wide4', 'sizes', 'upstut', 'colour']   # no back-and-forth: her hands barely move, the cutting does the moving
_hd = {}
def hands(fr, t):
    if not (HD_A <= t < HD_B): return fr
    if 'c' not in _hd: _hd['c'] = Clip('clips/sd8.mp4')
    c = _hd['c']; ks = kicks_in(HD_A - 0.05, t); n = max(0, len(ks) - 1); look = HD_LOOK[n % len(HD_LOOK)]; since = t - (ks[-1] if len(ks) else HD_A)
    half = HD_IRIS                                # slow motion, 5 frames a second: the arms-up stretch, then the hands with the shapes
    src = 2.0 + (t - HD_A) / (half - HD_A) * 2.4 if t < half else 10.0 + (t - half) / (HD_B - half) * 2.7
    F = lambda sec: c.get(int(sec * 5) / 5.0 * 24); cx0 = JG_C
    globals()['JG_C'] = (960, 430)
    try:
        if look == 'wide4': out = F(src).copy()
        elif look == 'three':                         # three of her: the outer two mirrored and a beat behind
            f = F(src); g = F(src - 0.4); x0 = OW // 2 - SW // 2; out = f.copy()
            out[:, :SW] = g[:, x0:x0 + SW][:, ::-1]; out[:, OW - SW:] = g[:, x0:x0 + SW][:, ::-1]
        elif look == 'colour':                        # every frame printed in different inks
            out = F(src)[..., [[0, 1, 2], [2, 0, 1], [1, 2, 0], [0, 2, 1]][int(src * 5) % 4]].copy()
        elif look == 'echo':                          # she trails herself, slowly
            acc = F(src).astype(np.float32) * 0.34
            for j, wgt in ((1, 0.26), (2, 0.22), (3, 0.18)): acc += F(src - j * 0.2).astype(np.float32) * wgt
            out = acc.astype(np.uint8)
        elif look == 'upstut':                        # one held frame; only the size jumps — big, small, bigger
            zs = [1.0, 1.5, 1.25, 2.0, 1.6, 2.7, 2.1, 3.3]; out = _zoomc(F(src - since), zs[int(since * 8) % len(zs)])
        else:
            f = F(src); r_ = int(since * 4); views = [_zoomc(f, 1.0, SW, OH), _zoomc(f, 1.6, SW, OH), _zoomc(f, 3.2, SW, OH)]
            out = np.zeros((OH, OW, 3), np.uint8); out[:, SW:SW + CW] = _zoomc(f, [1.9, 1.0, 2.6][r_ % 3], CW, OH); out[:, :SW] = views[r_ % 3]; out[:, OW - SW:] = views[(r_ + 1) % 3]
    finally: globals()['JG_C'] = cx0
    if t < HD_IRIS: _hd['last'] = out.copy()
    elif t < HD_IRIS + 0.5 and 'last' in _hd:         # the ring on her chest opens over all three screens; the hands are inside it
        p = ease((t - HD_IRIS) / 0.5); rad = int(40 + 1250 * p); m = np.zeros((OH, OW), np.uint8); cv2.circle(m, (960, 620), rad, 255, -1)
        out = np.where(m[..., None] > 0, out, _hd['last'])
        for dr, col, th in ((0, (255, 255, 255), 6), (16, (255, 90, 220), 10), (34, (0, 220, 255), 8), (54, (255, 90, 220), 4)): cv2.circle(out, (960, 620), rad + dr, col, th, cv2.LINE_AA)
    if since < 0.05 and n > 0: out = np.clip(out.astype(np.int16) + 60, 0, 255).astype(np.uint8)
    return _lines(out)


# ---------------------------------------------------------------- 0:39  from the green-screen take, seconds 7-15: the close-up as it is, then the right-hand dancer alone — never three in step
_d2 = {}
def _d2_init():
    from PIL import Image as _I
    import solo, glob
    PINK = np.array((255, 105, 180), np.float32); cu = []
    for f in sorted(glob.glob('cut/sd2/*.png'))[84:107]:                      # 7.0 s .. 8.9 s at 12 fps: the close-up
        a = np.array(_I.open(f).convert('RGBA')); a = cv2.resize(a, (OW, int(round(a.shape[0] * OW / a.shape[1]))), interpolation=cv2.INTER_LANCZOS4); y0 = (a.shape[0] - OH) // 2; a = a[y0:y0 + OH]
        al = a[..., 3:4].astype(np.float32) / 255; cu.append((PINK * (1 - al) + a[..., :3] * al).astype(np.uint8))
    wd, hy = [], []
    for f in solo.split('s2B')[1]:                                            # 9.6 s .. 15 s: the dancer on the right, by herself
        bg = np.zeros((OH, OW, 3), np.uint8); bg[:] = (255, 105, 180); h, w = f.shape[:2]; s_ = 1000 / h; f = cv2.resize(f, (int(w * s_), 1000), interpolation=cv2.INTER_LANCZOS4); h, w = f.shape[:2]
        x0, y0 = OW // 2 - w // 2, OH - h - 30; cv2.ellipse(bg, (OW // 2, OH - 40), (230, 26), 0, 0, 360, (215, 70, 150), -1)
        al = f[..., 3:4].astype(np.float32) / 255; bg[y0:y0 + h, x0:x0 + w] = (bg[y0:y0 + h, x0:x0 + w] * (1 - al) + f[..., :3] * al).astype(np.uint8)
        rows = np.where((f[..., 3] > 128).any(1))[0]; cols = np.where((f[:max(1, h // 4), :, 3] > 128).any(0))[0]
        wd.append(bg); hy.append((y0 + int(rows[0]), x0 + int(cols.mean()) if len(cols) else OW // 2))
    _d2.update(cu=cu, wd=wd, hy=hy)
def dancer2(base, t):
    if not _d2: _d2_init()
    TP, K1, END = 37.27, 38.59, 8 * SEG; cu, wd, hy = _d2['cu'], _d2['wd'], _d2['hy']; L, Rz, C = slice(0, SW), slice(OW - SW, OW), slice(SW, SW + CW)
    if t < K1:                                                                # the close-up, as it is, over all three screens
        out = cu[min(len(cu) - 1, int((t - TP) * 12))].copy()
        if t - TP < 0.08: out = np.clip(out.astype(np.int16) + 120, 0, 255).astype(np.uint8)
        return _lines(out)
    ks = kicks_in(K1 - 0.01, t); n = max(0, len(ks) - 1); k0 = float(ks[-1]) if len(ks) else K1; since = t - k0; N = len(wd)
    idx = lambda tt: int(min(N - 1, max(0, (tt - K1) / (END - K1) * (N - 1))))
    def crop(i, s, w, h, top=0.10):
        f = wd[i]; y_, x_ = hy[i]; cw, ch = w / s, h / s; x0 = int(min(max(x_ - cw / 2, 0), OW - cw)); y0 = int(min(max(y_ - top * ch, 0), OH - ch))
        return cv2.resize(f[y0:y0 + int(ch), x0:x0 + int(cw)], (w, h), interpolation=cv2.INTER_CUBIC)
    if n == 0:                                                                # she lands big: head to hips across the whole wall
        out = crop(idx(t), 1.7, OW, OH)
    elif n == 1:                                                              # one of her dancing, stuttering forward-back-forward; either side, only her face, held
        tick = int(since * 10); i = min(N - 1, idx(k0) + tick // 3 + (1 if tick % 3 == 1 else 0)); out = np.zeros((OH, OW, 3), np.uint8); out[:, C] = wd[i][:, C]
        h_ = min(N - 1, idx(k0) + int(since * 4) * 2)
        out[:, L] = np.clip(crop(h_, 3.4, SW, OH, 0.22).astype(np.float32) * (1.0, 0.75, 0.95) + 12, 0, 255).astype(np.uint8)
        out[:, Rz] = np.clip(crop(max(0, h_ - 3), 3.4, SW, OH, 0.22)[:, ::-1].astype(np.float32) * (0.7, 0.9, 1.0) + 12, 0, 255).astype(np.uint8)
    elif n == 2:                                                              # one frame held; only the size jumps — big, small, bigger
        zs = [1.0, 1.6, 1.25, 2.2, 1.7, 2.9, 2.2, 3.5]; out = crop(idx(k0), zs[int(since * 8) % len(zs)], OW, OH)
    else:                                                                     # back in her frame; the games return
        out = base.copy(); out[:, C] = wd[idx(t)][:, C]
    if since < 0.06: out = np.clip(out.astype(np.int16) + 90, 0, 255).astype(np.uint8)
    return _lines(out)
