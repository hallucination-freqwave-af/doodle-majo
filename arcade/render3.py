"""16:9 version: centre = render2 frame scaled to 864x1080, sides = retro games (528px each)."""
import numpy as np, cv2, sys, subprocess, os
import render2 as R
from games import GAMES as OLD, GW as OGW, GH as OGH
from games16 import Shooter16, TetrisSpin, GW, GH
from render import kick, hit

OW, OH, FPS = 1920, 1080, 30
CW = 864; SW = (OW - CW) // 2  # 528
PX = SW // GW  # 4

class Side:
    def __init__(self, scene, left):
        seed = scene * 7 + (1 if left else 2); slot = (scene + (0 if left else 2)) % 9
        if slot in (3, 7): self.game = TetrisSpin(seed); self.px = PX
        elif slot == 5: self.game = OLD[[0, 2, 4][scene % 3]](seed); self.px = SW // OGW  # a rare 8-bit guest
        else: self.game = Shooter16(seed, stage=Shooter16.STAGES[(scene // 2 + (0 if left else 1)) % 3]); self.px = PX
        self.left = left
    def frame(self, t, dt):
        self.game.step(dt, kick(t), hit(t))
        g = self.game.draw()
        img = cv2.resize(g, (g.shape[1] * self.px, g.shape[0] * self.px), interpolation=cv2.INTER_NEAREST)
        # CRT scanlines
        img = img.astype(np.int16); img[::4] -= 25; img = np.clip(img, 0, 255).astype(np.uint8)
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
    L, Rr = Side(i, True), Side(i, False)
    CFR = [8, 4, 15, 6, 12, 4, 10, 8, 5][i % 9]  # centre frame rate for this scene; sides stay at 30
    last_q, cen = None, None
    # warm the games up a little so they don't start empty
    for _ in range(60): L.game.step(1 / 30, 0, 0); Rr.game.step(1 / 30, 0, 0)
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-crf', '18', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', tmp], stdin=subprocess.PIPE)
    for k in range(n0, n1):
        t = k / FPS
        q = int(t * CFR)
        if q != last_q: cen = R.frame(q / CFR); last_q = q
        fr = compose(cen, L.frame(t, 1 / FPS), Rr.frame(t, 1 / FPS))
        if t > R.DUR - 2.5: fr = (fr * max(0, (R.DUR - t) / 2.5)).astype(np.uint8)
        p.stdin.write(np.ascontiguousarray(fr).tobytes())
    p.stdin.close(); rc = p.wait()
    if rc == 0: os.rename(tmp, out); print('done', out, n1 - n0)
    else: sys.exit(rc)
