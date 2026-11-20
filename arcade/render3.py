"""16:9 version: centre = render2 frame scaled to 864x1080, sides = retro games (528px each)."""
import numpy as np, cv2, sys, subprocess, os
import render2 as R
from games import GAMES as OLD, GW as OGW, GH as OGH
from games16 import Shooter16, TetrisSpin, Racer, Blobs, Vector, Climber, GW, GH
from races import RACES
from screens import SCREENS, Shapes
from patterns import PATTERNS
from render import kick, hit
import math
import dance
import special

OW, OH, FPS = 1920, 1080, 30
CW = 864; SW = (OW - CW) // 2  # 528
PX = SW // GW  # 4

RACE_KEYS = list(RACES)
OTHERS = ['shoot', 'tetris', 'blobs', 'vector', 'climber', 'old']
MODES = ['plain', 'plain', 'plain', 'mirror', 'tint', 'chunky', 'mirror']
TINTS = [np.array([0.35, 1.0, 0.45]), np.array([1.0, 0.7, 0.25]), np.array([1.0, 0.35, 0.9])]
_r = np.random.default_rng(11)
_races = []
def _next_race(avoid):
    global _races
    for _ in range(40):
        if not _races: _races = list(_r.permutation(RACE_KEYS))
        k = str(_races.pop())
        if k not in avoid: return k
    return k
# 2026-11-19: the side screens are no longer only games. Cars stay the backbone; next to them, screens nobody is playing.
SCREEN_KEYS = list(SCREENS); _scr = []
def _next_screen(avoid):
    global _scr
    for _ in range(40):
        if not _scr: _scr = list(_r.permutation(SCREEN_KEYS))
        k = str(_scr.pop())
        if k not in avoid: return k
    return k
SCHED = []; prev = ()
for _i in range(60):
    roll = _r.random()
    if roll < 0.42: a, b = _next_race(prev), _next_screen(prev)                              # a car and a screen left on
    elif roll < 0.60: a, b = str(_r.choice([o for o in OTHERS if o not in prev])), _next_screen(prev)   # a game and a screen
    elif roll < 0.78: a = _next_screen(prev); b = _next_screen(prev + (a,))                 # two screens, nobody home
    elif roll < 0.90: a = _next_race(prev); b = _next_race(prev + (a,))                     # car + car
    else: a, b = _next_race(prev), str(_r.choice([o for o in OTHERS if o not in prev]))      # car + game
    if _r.random() < 0.5: a, b = b, a
    mode = 'plain'
    if a not in SCREENS and b not in SCREENS: mode = MODES[_r.integers(0, len(MODES))]
    elif a not in SCREENS and _r.random() < 0.15: mode = 'mirror'                            # mirror = the left one twice, its own run each side
    if mode == 'chunky' and (a.startswith(('ps1', 'rain')) or b.startswith(('ps1', 'rain'))): mode = 'plain'
    SCHED.append((a, b, mode, int(_r.integers(0, 3)))); prev = (a, b)

SCHED[30] = ('tank', 'ecg', 'plain', 0)
SCHED[12] = ('shapes', 'shapes', 'plain', 0)
SCHED[13] = (SCHED[13][0], SCHED[13][1], 'tint', 2)      # 1:10: both side screens in pink   # 1:04-1:10: grey paper with small geometric figures, both sides (each its own scatter)   # 21 already has bars + ecg

# 2026-11-20: cars and games only now and then. Mostly patterns; some of the screens nobody is watching. The ball-game scenes, the grey shapes and the pink one stay.
KEEP = {2, 9, 31, 12, 13}
_r2 = np.random.default_rng(20); _deck = []
def _pat(avoid):
    global _deck
    for _ in range(60):
        if not _deck: _deck = list(_r2.permutation([k for k in PATTERNS if k not in ('arcbeat', 'prism')] * 4 + ['arcbeat'] * 4 + ['prism'] * 2 + ['shapes'] * 2))
        k = str(_deck.pop())
        if k not in avoid: return k
    return k
_prev = ()
for _i in range(60):
    if _i in KEEP: _prev = SCHED[_i][:2]; continue
    roll = _r2.random(); mode = 'plain'
    if roll < 0.45:
        a = _pat(_prev); b = _pat(_prev + (a,))
        if _r2.random() < 0.35: mode = 'mirror'            # the same pattern both sides, each its own run
    elif roll < 0.75: a, b = _pat(_prev), _next_screen(_prev)
    elif roll < 0.85: a = _next_screen(_prev); b = _next_screen(_prev + (a,))
    else: a, b = (_next_race(_prev) if _r2.random() < 0.7 else str(_r2.choice(OTHERS))), _pat(_prev)
    if mode != 'mirror' and _r2.random() < 0.5: a, b = b, a
    SCHED[_i] = (a, b, mode, 0); _prev = (a, b)

SCHED[0] = ('ps1_97', 'tank', 'plain', 0); SCHED[1] = ('ecg', 'tetris', 'plain', 0)      # the opening, through the second picture, stays as it was

def make(kind, seed, scene, left):
    if kind in PATTERNS: g = PATTERNS[kind](seed); return g, g.px
    if kind == 'shapes': g = Shapes(seed); return g, g.px
    if kind in SCREENS: g = SCREENS[kind](seed); return g, g.px
    if kind in RACES: g = RACES[kind](seed); return g, g.px
    if kind == 'shoot': return Shooter16(seed, stage=Shooter16.STAGES[(scene + (0 if left else 1)) % 3]), PX
    if kind == 'tetris': return TetrisSpin(seed), PX
    if kind == 'racer': return Racer(seed), PX
    if kind == 'blobs': return Blobs(seed), PX
    if kind == 'vector': return Vector(seed), PX
    if kind == 'climber': return Climber(seed), PX
    return OLD[[0, 2, 4][scene % 3]](seed), SW // OGW

class Side:
    def __init__(self, scene, left, partner=None):
        a, b, self.mode, ti = SCHED[scene % len(SCHED)]; self.left = left; self.tint = TINTS[ti]
        self.flip = False
        if self.mode == 'mirror' and not left:   # same game and look as the left, flipped — but its own run, so the motion differs
            self.game, self.px = make(a, scene * 7 + 101, scene, True); self.flip = True
            for _ in range(int(30 * (1.7 + (scene % 5) * 0.6))): self.game.step(1 / 30, 0, 0)
        else:
            self.game, self.px = make(a if left else b, scene * 7 + (1 if left else 2), scene, left)
        self.t0 = scene * R.SEG
    def frame(self, t, dt):
        if hasattr(self.game, 'set_time'): self.game.set_time(t)
        self.game.step(dt, kick(t), hit(t))
        g = self.game.draw()
        if self.mode == 'chunky': g = cv2.resize(cv2.resize(g, (g.shape[1] // 2, g.shape[0] // 2), interpolation=cv2.INTER_AREA), (g.shape[1], g.shape[0]), interpolation=cv2.INTER_NEAREST)
        img = cv2.resize(g, (g.shape[1] * self.px, g.shape[0] * self.px), interpolation=cv2.INTER_NEAREST)
        if img.shape[1] != SW or img.shape[0] != OH: img = cv2.resize(img, (SW, OH), interpolation=cv2.INTER_NEAREST)
        if self.flip: img = img[:, ::-1]
        if self.mode == 'tint':
            lum = img.mean(axis=2, keepdims=True); img = np.clip(lum * self.tint * 1.3, 0, 255).astype(np.uint8)
        img = img.astype(np.int16); img[::4] -= 25; img = np.clip(img, 0, 255).astype(np.uint8)
        tl = t - self.t0
        if tl < 0.18:  # channel-change static at the head of each scene
            n = np.random.default_rng(int(t * 60)).integers(0, 255, (OH // 6, SW // 6), dtype=np.uint8)
            img = np.repeat(cv2.resize(n, (SW, OH), interpolation=cv2.INTER_NEAREST)[..., None], 3, 2)
        self.last = img
        return img

def compose(centre, L, Rr):
    out = np.zeros((OH, OW, 3), np.uint8)
    out[:, :SW] = L; out[:, OW - SW:] = Rr
    c = cv2.resize(centre, (CW, OH), interpolation=cv2.INTER_AREA)
    out[:, SW:SW + CW] = c
    return out

if __name__ == '__main__':
    i = int(sys.argv[1]); a = i * R.SEG; b = min(R.DUR, (i + 1) * R.SEG)
    n0, n1 = int(round(a * FPS)), int(round(b * FPS))
    out = f'v3_scene{i:02d}.mp4'; tmp = f'tmp_v3_{i:02d}.mp4'
    L = Side(i, True); Rr = Side(i, False, partner=L)
    CFR = 30 if i in (3, 23, 15, 35, 10) else (15 if i in R.BLUR_SCENES else [8, 4, 15, 6, 12, 4, 10, 8, 5][i % 9])  # 30 where the 裏 blur lives, else low; centre frame rate for this scene; sides stay at 30
    last_q, cen = None, None
    # warm the games up a little so they don't start empty
    if i not in special.EARLY:
        for _ in range(60): L.game.step(1 / 30, 0, 0); Rr.game.step(1 / 30, 0, 0)
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-crf', '18', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
    EARLY_NEXT = special.EARLY.get(i + 1)   # the next scene cuts in before this one's slot is over
    if EARLY_NEXT:
        Ln = Side(i + 1, True); Rn = Side(i + 1, False, partner=Ln); Ln.t0 = Rn.t0 = EARLY_NEXT
        for _ in range(60): Ln.game.step(1 / 30, 0, 0); Rn.game.step(1 / 30, 0, 0)
    if i in special.EARLY:                  # ...and here it is already under way: bring its side screens up to where they were
        L.t0 = Rr.t0 = special.EARLY[i]
        for _ in range(60): L.game.step(1 / 30, 0, 0); Rr.game.step(1 / 30, 0, 0)
        for kk in range(int(math.ceil(special.EARLY[i] * FPS)), n0): L.frame(kk / FPS, 1 / FPS); Rr.frame(kk / FPS, 1 / FPS)
    HOLD = special.GEO_AT.get(i) if i == 16 else None          # this scene starts late, on a bass drum: until then the previous scene keeps running
    if HOLD:
        Lp = Side(i - 1, True); Rp = Side(i - 1, False, partner=Lp)
        for _ in range(60): Lp.game.step(1 / 30, 0, 0); Rp.game.step(1 / 30, 0, 0)
        for kk in range(int(round((i - 1) * R.SEG * FPS)), n0): Lp.frame(kk / FPS, 1 / FPS); Rp.frame(kk / FPS, 1 / FPS)
    for k in range(n0, n1):
        t = k / FPS
        if EARLY_NEXT and t >= EARLY_NEXT:
            fr = special.geo(compose(R.scene_frame(i + 1, t - EARLY_NEXT, t), Ln.frame(t, 1 / FPS), Rn.frame(t, 1 / FPS)), t)
            if not special._sh.get('ready'): special.shatter_init(cv2.resize(cen, (CW, OH), interpolation=cv2.INTER_AREA))
            fr = special.shatter(fr, t, EARLY_NEXT)
            if t - EARLY_NEXT < 0.06: fr = np.clip(fr.astype(np.int16) + 90, 0, 255).astype(np.uint8)
            p.stdin.write(np.ascontiguousarray(fr).tobytes()); continue
        if HOLD and t < HOLD:
            fr = special.geo(compose(R.scene_frame(i - 1, t - (i - 1) * R.SEG, t), Lp.frame(t, 1 / FPS), Rp.frame(t, 1 / FPS)), t)
            L.game.step(1 / FPS, 0, 0); Rr.game.step(1 / FPS, 0, 0)
            p.stdin.write(np.ascontiguousarray(fr).tobytes()); continue
        q = int(t * CFR)
        if q != last_q:
            if i in (6, 7, 20, 33, 27, 28, 36, 37, 38, 30): cen = np.zeros((1350, 1080, 3), np.uint8)          # taken over (special.takeover)
            elif i in (16, 17): cen = np.zeros((1350, 1080, 3), np.uint8)
            elif i == 29: cen = special.danzen_poster()                        # 時空断線 (special.danzen)                              # the poster has left (special.free)
            elif i in (8, 21, 34, 31, 9, 11, 14, 35, 23, 18) and q / CFR - a < 0.4: cen = R.scene_frame(i, max(0, q / CFR - a), q / CFR)   # hard cut in: what came before is gone
            else: cen = R.frame(q / CFR)
            last_q = q
        fr = special.post(compose(cen, L.frame(t, 1 / FPS), Rr.frame(t, 1 / FPS)), t, i)
        if EARLY_NEXT: fr = special.cracks(fr, t, EARLY_NEXT)
        fr = dance.overlay(fr, t)
        if t > R.DUR - 2.5: fr = (fr * max(0, (R.DUR - t) / 2.5)).astype(np.uint8)
        p.stdin.write(np.ascontiguousarray(fr).tobytes())
    p.stdin.close(); rc = p.wait()
    if rc == 0: os.rename(tmp, out); print('done', out, n1 - n0)
    else: sys.exit(rc)
