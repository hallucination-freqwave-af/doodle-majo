"""Cut-out protagonist dancing across the three zones, now and then. Jumps to a new spot on each bass drum."""
import numpy as np, cv2, glob
from PIL import Image
from render import KICKS

OW, OH = 1920, 1080
FIG_H = 860
SPOTS = [264, 528, 960, 1392, 1656]          # left zone, left border, centre, right border, right zone
P, S = 'pink', 'silver'
# duo = the two dancers as separate tracks, each taken from a different take, so they never do the same move
DUO = {'d1': (('sdA', 0), ('s2A', 1)), 'd2': (('s2A', 0), ('sdA', 1)), 'd3': (('s2B', 0), ('sdB', 0)), 'd4': (('sdB', 1), ('s2B', 1))}
WINDOWS_OLD = [(26.0, 31.0, 'sdA'), (47.0, 52.5, 'v1'), (67.5, 70.6, 'sdC'), (93.0, 98.0, 's2A'),
           (139.9, 143.0, 's2C'), (160.6, 165.5, 'sdB'), (176.0, 181.1, 's2B')]
WINDOWS_GREEN = [(26.0, 31.0, 'd1'), (47.0, 52.5, 'v1'), (67.5, 70.6, 'sdC'), (93.0, 98.0, 'd2'),
           (139.9, 143.0, 's2C'), (160.6, 165.5, 'd3'), (176.0, 181.1, 'd4')]   # the green-screen dancers, parked (2026-11-19)
WINDOWS_CUTOUT = [(47.0, 52.5, 'v1'), (93.0, 98.0, 'v2'), (176.0, 182.0, 'v1')]   # parked too
WINDOWS = []   # clean base: no cut-outs on top (2026-11-19)
# green-screen dance clips: name -> (folder, 12fps frame ranges, height on screen, where it may stand)
SRC = {'sdA': ('sd', [(1, 61)], 900, [640, 960, 1280]), 'sdC': ('sd', [(68, 113)], 1080, [860, 960, 1060]), 'sdB': ('sd', [(122, 181)], 900, [640, 960, 1280]),
       's2A': ('sd2', [(1, 61)], 900, [640, 960, 1280]), 's2C': ('sd2', [(68, 107)], 1080, [860, 960, 1060]), 's2B': ('sd2', [(116, 181)], 900, [640, 960, 1280])}

RANGES = {'v3': [(1, 5), (20, 29)]}   # hand-picked whole-body frames
_cache = {}
def frames_src(name):
    # one crop and one scale for the whole segment, so crouches and steps keep their real size
    folder, rngs, Ht, _ = SRC[name]; arrs = []
    for idx, f in enumerate(sorted(glob.glob(f'cut/{folder}/*.png')), 1):
        if not any(lo <= idx <= hi for lo, hi in rngs): continue
        a = np.array(Image.open(f).convert('RGBA')); m = (a[..., 3] > 150).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
        if n > 1:
            big = st[1:, cv2.CC_STAT_AREA].max()
            keep = np.isin(lab, [k for k in range(1, n) if st[k, cv2.CC_STAT_AREA] > big * 0.03])
            keep = cv2.dilate(keep.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool); a[..., 3] = np.where(keep, a[..., 3], 0)
        arrs.append(a)
    u = np.max([a[..., 3] for a in arrs], axis=0); ys, xs = np.where(u > 40)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1; s = Ht / (y1 - y0)
    return [cv2.resize(a[y0:y1, x0:x1], (int((x1 - x0) * s), Ht), interpolation=cv2.INTER_LANCZOS4) for a in arrs]

def frames(name):
    if name in SRC and name not in _cache: _cache[name] = frames_src(name)
    if name not in _cache:
        fs = []
        allf = sorted(glob.glob(f'cut/{name}/*.png')); rng_ = RANGES.get(name)
        for idx, f in enumerate(allf, 1):
            if rng_ and not any(lo <= idx <= hi for lo, hi in rng_): continue
            a = np.array(Image.open(f).convert('RGBA'))
            m = (a[..., 3] > 150).astype(np.uint8)
            n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
            if n <= 1: continue
            big = st[1:, cv2.CC_STAT_AREA].max()
            keep = np.isin(lab, [k for k in range(1, n) if st[k, cv2.CC_STAT_AREA] > big * 0.25])
            keep = cv2.dilate(keep.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
            a[..., 3] = np.where(keep, a[..., 3], 0)
            ys, xs = np.where(a[..., 3] > 0)
            im = Image.fromarray(a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]); s = FIG_H / im.height
            fs.append(np.array(im.resize((max(1, int(im.width * s)), FIG_H), Image.LANCZOS)))
        _cache[name] = fs
    return _cache[name]

def active(t):
    for a, b, n in WINDOWS:
        if a <= t < b: return a, b, n
    return None

def blit(out, fig, cx, tint=None):
    fh, fw = fig.shape[:2]; x0 = int(cx - fw / 2); y0 = OH - fh
    for dx, col, amt in ((18, (255, 80, 200), 0.55), (0, None, 1.0)):   # hard pink shadow, then the figure
        xa, xb = max(0, x0 + dx), min(OW, x0 + dx + fw)
        if xb <= xa: continue
        f = fig[:, xa - x0 - dx:xb - x0 - dx]; al = f[..., 3:4].astype(np.float32) / 255 * amt
        rgb = f[..., :3] if col is None and tint is None else np.broadcast_to(np.array(col if col is not None else tint, np.uint8), f[..., :3].shape)
        reg = out[y0:y0 + fh, xa:xb].astype(np.float32); out[y0:y0 + fh, xa:xb] = (reg * (1 - al) + rgb * al).astype(np.uint8)
    return out

def duo(out, t, a, b, name):
    import solo
    tracks = [solo.split(seg)[side] for seg, side in DUO[name]]
    hits = KICKS[(KICKS >= a) & (KICKS <= t)]; n = len(hits)
    pos = [1, 3]; moved_at = [a, a]
    for k in range(1, n + 1):   # they take turns: one bass drum moves the pink one, the next moves the silver one
        who = k % 2; r = np.random.default_rng(int(a) * 100 + k)
        opts = [i for i in range(len(SPOTS)) if abs(i - pos[1 - who]) >= 2 and i != pos[who]]
        pos[who] = int(r.choice(opts)); moved_at[who] = hits[k - 1]
    order = [0, 1] if moved_at[0] <= moved_at[1] else [1, 0]   # whoever moved last is in front
    for who in order:
        fs = tracks[who]; span = max(1, len(fs) - 1); k = int((t - a) * 12) + who * 7
        k = k % span if (k // span) % 2 == 0 else span - k % span
        tint = ((255, 80, 200), (255, 255, 255))[who] if (t - moved_at[who]) < 0.07 else None
        out = blit(out, fs[k], SPOTS[pos[who]], tint)
    return out

def overlay(out, t):
    w = active(t)
    if w is None: return out
    a, b, name = w
    if name in DUO: return duo(out, t, a, b, name)
    fs = frames(name)
    if not fs: return out
    src = name in SRC
    k = int((t - a) * (12 if src else 8)); n = len(fs); span = max(1, n - 1)
    k = k % span if (k // span) % 2 == 0 else span - k % span
    fig = fs[k]
    hits = KICKS[(KICKS >= a) & (KICKS <= t)]
    rng = np.random.default_rng(len(hits) * 31 + int(a))
    pop = False
    if src:   # a real dance: it keeps its own motion; the place changes on every second bass drum, with a one-frame pink pop
        spots = SRC[name][3]; step = len(hits) // 2; cx = spots[(step + int(a)) % len(spots)]
        changed = hits[step * 2 - 1] if step >= 1 else a
        pop = (t - changed) < 0.07
    elif len(hits) == 0: cx = -fig.shape[1] / 2 + (t - a) * 2200          # walk in from the left until the first drum
    elif t > b - 0.5: cx = SPOTS[-1] + (t - (b - 0.5)) * 2400            # run out to the right at the end
    else: cx = SPOTS[(len(hits) * 2 + rng.integers(0, 2)) % len(SPOTS)]
    if not src and len(hits) and rng.random() < 0.35: fig = fig[:, ::-1]
    since = t - hits[-1] if len(hits) else 9
    squash = 1.0 if src else 1 - 0.12 * np.exp(-since * 12)
    fh = int(fig.shape[0] * squash); fw = int(fig.shape[1] * (2 - squash))
    fig = cv2.resize(fig, (fw, fh), interpolation=cv2.INTER_AREA)
    x0 = int(cx - fw / 2); y0 = OH - fh
    xa, xb = max(0, x0), min(OW, x0 + fw)
    if xb <= xa: return out
    f = fig[:, xa - x0:xb - x0]; al = f[..., 3:4].astype(np.float32) / 255
    if pop: f = f.copy(); f[..., :3] = (255, 80, 200)
    # a hard pink shadow first, then the figure
    sh = np.zeros_like(f[..., :3]); sh[:] = (255, 80, 200)
    sx = 18
    sa, sb = max(0, xa + sx), min(OW, xb + sx)
    if sb > sa:
        reg = out[y0:y0 + fh, sa:sb].astype(np.float32); a2 = al[:, :sb - sa] * 0.55
        out[y0:y0 + fh, sa:sb] = (reg * (1 - a2) + sh[:, :sb - sa] * a2).astype(np.uint8)
    reg = out[y0:y0 + fh, xa:xb].astype(np.float32)
    out[y0:y0 + fh, xa:xb] = (reg * (1 - al) + f[..., :3] * al).astype(np.uint8)
    return out
