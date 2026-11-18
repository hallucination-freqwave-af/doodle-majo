"""Split the two dancers of a green-screen segment into separate tracks (left one / right one)."""
import numpy as np, cv2, glob
from PIL import Image

SEGS = {'sdA': ('sd', (1, 61)), 'sdB': ('sd', (122, 181)), 's2A': ('sd2', (1, 61)), 's2B': ('sd2', (116, 181))}
_c = {}
def split(seg):
    """-> (left_frames, right_frames, n_ok): RGBA arrays, one crop+scale per track, frames where the two touch are held from the last good one"""
    if seg in _c: return _c[seg]
    folder, (lo, hi) = SEGS[seg]; fs = sorted(glob.glob(f'cut/{folder}/*.png'))[lo - 1:hi]
    L, R, ok = [], [], 0; pair_h = []; okf = []
    for f in fs:
        a = np.array(Image.open(f).convert('RGBA')); m = (a[..., 3] > 150).astype(np.uint8)
        n, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
        order = sorted(range(1, n), key=lambda k: -st[k, cv2.CC_STAT_AREA])
        ys = np.where(m.any(1))[0]; pair_h.append((ys.min(), ys.max()) if len(ys) else (0, 1))
        if len(order) >= 2 and st[order[1], cv2.CC_STAT_AREA] > st[order[0], cv2.CC_STAT_AREA] * 0.35:
            b1, b2 = sorted(order[:2], key=lambda k: cen[k][0]); out = []
            for me, other in ((b1, b2), (b2, b1)):
                keep = lab == me
                for k in order[2:]:   # loose bits (a hand, hair) go to the nearer body
                    if st[k, cv2.CC_STAT_AREA] > 40 and abs(cen[k][0] - cen[me][0]) < abs(cen[k][0] - cen[other][0]): keep |= lab == k
                keep = cv2.dilate(keep.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~cv2.dilate((lab == other).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
                p = a.copy(); p[..., 3] = np.where(keep, p[..., 3], 0); out.append(p)
            L.append(out[0]); R.append(out[1]); ok += 1; okf.append(True)
        else:
            L.append(L[-1] if L else None); R.append(R[-1] if R else None); okf.append(False)
    if seg.endswith('B'): L = [x for x, o in zip(L, okf) if o]; R = [x for x, o in zip(R, okf) if o]   # where they overlap, drop the frame rather than freeze
    first = next(i for i, x in enumerate(L) if x is not None)
    L = [x if x is not None else L[first] for x in L]; R = [x if x is not None else R[first] for x in R]
    y0 = min(p[0] for p in pair_h); y1 = max(p[1] for p in pair_h) + 1; s = 900 / (y1 - y0)
    def pack(tr):
        u = np.max([x[..., 3] for x in tr], axis=0); xs = np.where((u > 40).any(0))[0]; x0, x1 = xs.min(), xs.max() + 1
        return [cv2.resize(x[y0:y1, x0:x1], (max(1, int((x1 - x0) * s)), 900), interpolation=cv2.INTER_LANCZOS4) for x in tr]
    _c[seg] = (pack(L), pack(R), ok, len(fs)); return _c[seg]

if __name__ == '__main__':
    ims = []
    for seg in SEGS:
        l, r, ok, n = split(seg); print(seg, 'separable', ok, '/', n, l[0].shape, r[0].shape)
        for tr in (l, r):
            for k in (5, len(tr) // 2, len(tr) - 5):
                f = tr[k]; bg = Image.new('RGB', (f.shape[1], f.shape[0]), (70, 40, 90)); bg.paste(Image.fromarray(f), (0, 0), Image.fromarray(f)); ims.append(bg.resize((int(f.shape[1] * 0.25), 225)))
    W = max(sum(i.width for i in ims[j:j + 6]) for j in range(0, len(ims), 6)); sh = Image.new('RGB', (W, 225 * 4))
    for j in range(0, len(ims), 6):
        x = 0
        for i in ims[j:j + 6]: sh.paste(i, (x, (j // 6) * 225)); x += i.width
    sh.save('solochk.jpg', quality=88)
