"""16:9 version: centre = render2 frame scaled to 864x1080, sides = retro games (528px each)."""
import numpy as np, cv2, sys, subprocess, os
import render2 as R
from games import GAMES as OLD, GW as OGW, GH as OGH
from games16 import Shooter16, TetrisSpin, Racer, Blobs, Vector, Climber, GW, GH
from races import RACES
from render import kick, hit
import dance

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
SCHED = []; prev = ()
for _i in range(60):
    roll = _r.random()
    if roll < 0.45: a, b = _next_race(prev), None; b = _next_race(prev + (a,))       # car + car
    elif roll < 0.85:                                                                  # car + something else
        a = _next_race(prev); b = str(_r.choice([o for o in OTHERS if o not in prev]))
        if _r.random() < 0.5: a, b = b, a
    else: a = str(_r.choice(OTHERS)); b = str(_r.choice([o for o in OTHERS if o != a]))
    mode = MODES[_r.integers(0, len(MODES))]
    if mode == 'chunky' and (a.startswith(('ps1', 'rain')) or b.startswith(('ps1', 'rain'))): mode = 'plain'
    SCHED.append((a, b, mode, int(_r.integers(0, 3)))); prev = (a, b)

def make(kind, seed, scene, left):
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
    CFR = 30 if i in (3, 23, 15, 35) else (15 if i in R.BLUR_SCENES else [8, 4, 15, 6, 12, 4, 10, 8, 5][i % 9])  # 30 where the 裏 blur lives, else low; centre frame rate for this scene; sides stay at 30
    last_q, cen = None, None
    # warm the games up a little so they don't start empty
    for _ in range(60): L.game.step(1 / 30, 0, 0); Rr.game.step(1 / 30, 0, 0)
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-crf', '18', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
    for k in range(n0, n1):
        t = k / FPS
        q = int(t * CFR)
        if q != last_q: cen = R.frame(q / CFR); last_q = q
        fr = dance.overlay(compose(cen, L.frame(t, 1 / FPS), Rr.frame(t, 1 / FPS)), t)
        if t > R.DUR - 2.5: fr = (fr * max(0, (R.DUR - t) / 2.5)).astype(np.uint8)
        p.stdin.write(np.ascontiguousarray(fr).tobytes())
    p.stdin.close(); rc = p.wait()
    if rc == 0: os.rename(tmp, out); print('done', out, n1 - n0)
    else: sys.exit(rc)
