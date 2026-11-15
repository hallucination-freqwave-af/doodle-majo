#!/usr/bin/env python3
"""Doodle of Majo テンプレ — 五段の骨組みで動画を組む。

使い方:
  python3 doodle_majo.py --people 人物フォルダ --bg 背景フォルダ --audio 曲 \
      --out 出力.mp4 [--title タイトル] [--text 物語.txt] [--beat 秒] [--seed 1]

--people の中は、連番PNG（切り抜き済み）のフォルダを1つ以上。フォルダ1つ＝1本の動き。
--beat を省くと曲から拍を測る（測れなければ0.37秒）。
--text を省くと文字の段は文字なしで、人物を全面に出す段になる。

五段: 三枚並び → モザイク → 三枚並び → 全面（＋文字） → 締め
"""
import argparse, glob, math, os, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageChops

W, H, FPS = 1920, 1080, 30
PAL = ["#2a3fd0", "#ff3d8b", "#e8f000", "#b8f000", "#ff7a6b", "#18b4e8",
       "#111111", "#ffffff", "#ff5a1f"]
FONT = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
FONT_JP = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
SECTIONS = [("tri", 29), ("mosaic", 12), ("tri", 5), ("full", 10), ("end", 3)]
ADV = 5          # 人物の連番を何コマごとに進めるか（30fps÷5＝6fps のカクカク）


# ---------- 素材 ----------
def load_seqs(root, max_h=720):
    dirs = [d for d in sorted(glob.glob(os.path.join(root, "*"))) if os.path.isdir(d)] or [root]
    seqs = []
    for d in dirs:
        fs = sorted(f for f in glob.glob(os.path.join(d, "*")) if f.lower().endswith(".png"))
        if not fs: continue
        ims = [Image.open(f).convert("RGBA") for f in fs]
        box = None
        for im in ims:
            b = im.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()
            if b: box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
        if box is None: continue
        out = []
        for im in ims:
            c = im.crop(box)
            if c.height > max_h:
                c = c.resize((int(c.width * max_h / c.height), max_h), Image.LANCZOS)
            out.append(c)
        seqs.append(out)
        print(f"人物 {os.path.basename(d)}: {len(out)}枚", file=sys.stderr)
    return seqs


def load_bgs(root):
    out = []
    for f in sorted(glob.glob(os.path.join(root, "*"))):
        try: out.append(ImageOps.fit(Image.open(f).convert("RGB"), (W, H), Image.LANCZOS))
        except Exception: pass
    return out


def fit_cover(im, w, h):
    return ImageOps.fit(im, (w, h), Image.LANCZOS)


# ---------- 人物の動き（連番＋小刻みリピート） ----------
class Actor:
    def __init__(s, seqs, rnd, t):
        s.r = rnd
        s.seq = rnd.choice(seqs)
        s.i0 = rnd.randrange(len(s.seq))
        s.t0 = t
        s.stut = None  # (始まり, 長さ, 刻み, 基準コマ)

    def maybe_stutter(s, t):
        if s.stut is None and s.r.random() < .25:
            s.stut = (t, s.r.choice([6, 8, 10, 12]), s.r.choice([1, 2]), s.idx(t))

    def idx(s, t):
        if s.stut:
            st, n, k, base = s.stut
            if t < st + n:
                return (base + ((t - st) // k) % 2) % len(s.seq)
            s.t0 -= n          # リピート中は進まなかったことにする
            s.stut = None
        return (s.i0 + (t - s.t0) // ADV) % len(s.seq)

    def img(s, t):
        return s.seq[s.idx(t)]


def put(canvas, p, h, cx, by):
    h = int(h); w = max(1, int(p.width * h / p.height))
    pp = p.resize((w, max(h, 1)), Image.BILINEAR)
    canvas.paste(pp, (int(cx - w / 2), int(by - h)), pp)


# ---------- 図形の面 ----------
def halftone(d, w, h, col, rnd):
    step = rnd.choice([18, 22, 26])
    for y in range(0, h, step):
        for x in range(0, w, step):
            r = step * 0.42 * (0.4 + 0.6 * abs(math.sin(x / 140 + y / 210)))
            d.ellipse([x - r, y - r, x + r, y + r], fill=col)


def star(d, cx, cy, ro, ri, n, col, rot=0):
    d.polygon([(cx + (ro if i % 2 == 0 else ri) * math.cos(rot + math.pi * i / n),
                cy + (ro if i % 2 == 0 else ri) * math.sin(rot + math.pi * i / n)) for i in range(n * 2)], fill=col)


def panel_left(w, h, rnd):
    bg, fg, ac = rnd.sample(PAL, 3)
    im = Image.new("RGB", (w, h), bg); d = ImageDraw.Draw(im)
    kind = rnd.choice(["star", "dot", "stripe", "star"])
    if kind == "star":
        if rnd.random() < .6: halftone(d, w, h, fg, rnd)
        cx, cy, n = w / 2, h * rnd.uniform(.3, .6), rnd.choice([8, 12, 16])
        star(d, cx, cy, w * .42, w * .12, n, ac, rnd.random())
        star(d, cx, cy, w * .18, w * .07, n, rnd.choice(PAL))
        d.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], fill="#111111")
    elif kind == "dot":
        r = w * .2; d.ellipse([w / 2 - r, h / 2 - r, w / 2 + r, h / 2 + r], fill=fg)
    else:
        sw = rnd.choice([40, 60, 80])
        for i in range(-h, w + h, sw * 2):
            d.polygon([(i, 0), (i + sw, 0), (i + sw - h, h), (i - h, h)], fill=fg)
    return im


def panel_right(w, h, rnd):
    cols = rnd.sample(PAL, 6)
    im = Image.new("RGB", (w, h), cols[0]); d = ImageDraw.Draw(im)
    kind = rnd.choice(["target", "target", "thin", "zig"])
    cx, cy = w / 2, h / 2
    if kind == "target":
        r, k = h * .55, 0
        while r > 10:
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=cols[k % 6]); r -= rnd.choice([35, 45, 55]); k += 1
        d.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill="#111111")
        if rnd.random() < .7:
            d.rectangle([0, 0, w, 90], fill=cols[1])
            d.line([(x, 50 + (25 if (x // 40) % 2 else -25)) for x in range(0, w + 40, 40)], fill="#111111", width=10)
    elif kind == "thin":
        for r in range(40, int(h * .5), 34):
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=cols[2], width=3)
    else:
        d.line([(x, 150 + (40 if (x // 50) % 2 else -40)) for x in range(-50, w + 50, 50)], fill="#111111", width=14)
    for _ in range(rnd.randint(1, 3)):
        x, y, s = rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(12, 30)
        d.polygon([(x, y - s), (x - s, y + s), (x + s, y + s)], fill=rnd.choice(PAL))
    return im


def shape_tile(s, rnd):
    bg, fg = rnd.sample(PAL, 2)
    im = Image.new("RGB", (s, s), bg); d = ImageDraw.Draw(im); m = s * .1
    k = rnd.choice(["circle", "tri", "star", "flat"])
    if k == "circle": d.ellipse([m, m, s - m, s - m], fill=fg)
    elif k == "tri": d.polygon([(s / 2, m), (m, s - m), (s - m, s - m)], fill=fg)
    elif k == "star": star(d, s / 2, s / 2, s * .45, s * .18, rnd.choice([5, 6, 8]), fg, -math.pi / 2)
    return im


def glitch(im, rnd):
    im = ImageOps.posterize(im, 3)
    R, G, B = im.split()
    o = rnd.choice([8, 12, 18])
    return Image.merge("RGB", (ImageChops.offset(R, o, 0), G, ImageChops.offset(B, -o, 0)))


# ---------- 背景の動画（止まったり、そのまま再開したり） ----------
class BgVideo:
    def __init__(s, folder, rnd, src_fps=15):
        s.fs = sorted(glob.glob(os.path.join(folder, "*.jpg")) + glob.glob(os.path.join(folder, "*.png")))
        s.r, s.rate, s.pos, s.frozen = rnd, src_fps / FPS, 0.0, False
        s.cache = (None, None)

    def step(s):
        k = s.r.random()
        if s.frozen: s.frozen = k < .35            # 止まってたら大体は再開
        elif k < .2: s.frozen = True               # 止まる
        elif k < .27: s.pos = s.r.uniform(0, len(s.fs))  # たまに飛ぶ

    def frame(s):
        i = int(s.pos) % len(s.fs)
        if not s.frozen: s.pos += s.rate
        if s.cache[0] != i:
            s.cache = (i, Image.open(s.fs[i]).convert("RGB").resize((W, H)))
        return s.cache[1]


def graphic_full(rnd):
    """全面の図形（左右の面を一枚に広げたもの）"""
    return panel_left(W, H, rnd) if rnd.random() < .5 else panel_right(W, H, rnd)


# ---------- 段 ----------
class Wide:
    """全面: 背景の動画と図形を切り替えながら、人物を乗せる"""
    def __init__(s, rnd, seqs, bgs, t, video=None):
        s.r, s.seqs, s.bgs, s.video = rnd, seqs, bgs, video
        s.g = None; s.pick(t); s.switch()

    def switch(s):
        r = s.r
        if s.video and r.random() < .65: s.g = None
        elif s.bgs and r.random() < .3: s.g = r.choice(s.bgs)
        else: s.g = graphic_full(r)

    def pick(s, t):
        r = s.r
        s.big = Actor(s.seqs, r, t) if s.seqs else None
        s.small = Actor(s.seqs, r, t) if s.seqs and r.random() < .5 else None
        s.big_x, s.big_h = W * r.uniform(.3, .7), H * r.uniform(.75, 1.05)
        s.small_x = W * r.choice([.15, .85])

    def step(s, t):
        r = s.r
        if s.video: s.video.step()
        if r.random() < .55: s.switch()
        if r.random() < .45: s.pick(t)
        for a in (s.big, s.small):
            if a: a.maybe_stutter(t)

    def frame(s, t):
        im = (s.video.frame() if s.g is None else s.g).copy()
        if s.small: put(im, s.small.img(t), H * .35, s.small_x, H * .9)
        if s.big: put(im, s.big.img(t), s.big_h, s.big_x, H)
        return im


class Tri:
    def __init__(s, rnd, seqs, bgs, t):
        s.r, s.seqs, s.bgs = rnd, seqs, bgs
        s.wl, s.wc = int(W * .275), int(W * .45); s.wr = W - s.wl - s.wc
        s.L, s.C, s.R = panel_left(s.wl, H, rnd), s.center(), panel_right(s.wr, H, rnd)
        s.pick(t)

    def center(s):
        return fit_cover(s.r.choice(s.bgs), s.wc, H) if s.bgs else panel_left(s.wc, H, s.r)

    def pick(s, t):
        r = s.r
        s.big = Actor(s.seqs, r, t) if s.seqs else None
        s.small = Actor(s.seqs, r, t) if s.seqs and r.random() < .6 else None
        s.big_x, s.big_h = W * r.uniform(.4, .6), H * r.uniform(.75, 1.0)

    def step(s, t):
        r, k = s.r, s.r.random()
        if k < .35: s.L = panel_left(s.wl, H, r)
        elif k < .65: s.C = s.center()
        else: s.R = panel_right(s.wr, H, r)
        if r.random() < .45: s.pick(t)
        for a in (s.big, s.small):
            if a: a.maybe_stutter(t)

    def frame(s, t):
        im = Image.new("RGB", (W, H))
        im.paste(s.L, (0, 0)); im.paste(s.C, (s.wl, 0)); im.paste(s.R, (s.wl + s.wc, 0))
        if s.small: put(im, s.small.img(t), H * .32, s.wl * .5, H * .85)
        if s.big: put(im, s.big.img(t), s.big_h, s.big_x, H)
        return im


class Mosaic:
    def __init__(s, rnd, seqs, bgs, t):
        s.r, s.seqs, s.bgs = rnd, seqs, bgs; s.step(t)

    def step(s, t):
        r = s.r; cell = r.choice([135, 180, 216, 270])
        base = Image.new("RGB", (W, H)); s.cells = []
        for j in range(math.ceil(H / cell)):
            for i in range(math.ceil(W / cell)):
                x = r.random()
                if x < .5 or not (s.seqs or s.bgs): tile = shape_tile(cell, r)
                elif x < .72 and s.bgs: tile = fit_cover(r.choice(s.bgs), cell, cell)
                else:
                    tile = shape_tile(cell, r)
                    if s.seqs: s.cells.append((Actor(s.seqs, r, t), i * cell + cell / 2, j * cell + cell, cell))
                base.paste(tile, (i * cell, j * cell))
        s.base = base
        for a, *_ in s.cells: a.maybe_stutter(t)

    def frame(s, t):
        im = s.base.copy()
        for a, cx, by, c in s.cells: put(im, a.img(t), c * .95, cx, by)
        return im


class Full:
    def __init__(s, rnd, seqs, bgs, t, words=None, n_beats=1, video=None):
        s.r, s.seqs, s.bgs, s.video = rnd, seqs, bgs, video
        s.words, s.wi = words or [], 0
        s.per = max(1, math.ceil(len(s.words) / max(n_beats - 4, 1))) if s.words else 0
        s.placed = []; s.newbase(t)

    def newbase(s, t):
        r = s.r
        if s.video and r.random() < .6: s.bg = None
        else: s.bg = r.choice(s.bgs) if s.bgs and r.random() < .6 else Image.new("RGB", (W, H), r.choice(PAL))
        s.actor = Actor(s.seqs, r, t) if s.seqs else None
        s.h = H * r.uniform(.95, 1.25)

    def step(s, t):
        r = s.r
        if s.video: s.video.step()
        if r.random() < .4: s.newbase(t)
        elif s.actor: s.actor.maybe_stutter(t)
        if r.random() < .3: s.placed = s.placed[-3:]
        for _ in range(s.per):
            if s.wi < len(s.words):
                w = s.words[s.wi]; s.wi += 1
                s.placed.append((w, r.uniform(.05, .7) * W, r.uniform(.1, .8) * H,
                                 r.choice([70, 90, 120, 160]) if len(w) < 7 else r.choice([60, 80]),
                                 r.choice(["#18b4e8", "#ff3d8b", "#e8f000", "#ffffff"])))

    def frame(s, t):
        im = (s.video.frame() if s.bg is None else s.bg).copy()
        if s.actor: put(im, s.actor.img(t), s.h, W / 2, H)
        im = glitch(im, s.r) if (t // 3) % 4 else im
        d = ImageDraw.Draw(im)
        for w, x, y, size, col in s.placed:
            d.text((x, y), w, font=ImageFont.truetype(FONT, size), fill=col,
                   stroke_width=max(4, size // 18), stroke_fill="#111111")
        return im


class End:
    def __init__(s, rnd, seqs, bgs, t, title=""):
        im = Image.new("RGB", (W, H), "#000000"); d = ImageDraw.Draw(im)
        y = H / 2 - 150
        if title:
            f = ImageFont.truetype(FONT_JP, 64); tw = d.textlength(title, font=f)
            d.text(((W - tw) / 2, y - 90), title, font=f, fill="#e8f000"); y += 40
        f = ImageFont.truetype(FONT, 110)
        for k, line in enumerate(["dreaming", "majo"]):
            tw = d.textlength(line, font=f)
            d.text(((W - tw) / 2, y + k * 120), line, font=f, fill="#ff3d8b", stroke_width=5, stroke_fill="#7a3fd0")
        s.im = im
    def step(s, t): pass
    def frame(s, t): return s.im


# ---------- 拍と長さ ----------
def duration(audio):
    if not audio: return 59.0
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", audio],
                         capture_output=True, text=True).stdout
    return float(out.strip() or 59)


def detect_beat(audio):
    try:
        import librosa, numpy as np
        y, sr = librosa.load(audio, sr=22050)
        _, b = librosa.beat.beat_track(y=y, sr=sr)
        bt = librosa.frames_to_time(b, sr=sr)
        return float(np.median(np.diff(bt)))
    except Exception:
        return 0.37


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--people", default=""); ap.add_argument("--bg", default="")
    ap.add_argument("--audio", default=""); ap.add_argument("--text", default="")
    ap.add_argument("--title", default=""); ap.add_argument("--out", default="doodle.mp4")
    ap.add_argument("--beat", type=float, default=0); ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--bgvideo", default="", help="背景の動画を連番JPGにしたフォルダ（15fps）")
    ap.add_argument("--layout", default="wide", choices=["wide", "tri"], help="wide=全面 / tri=三枚並び")
    a = ap.parse_args()
    video = BgVideo(a.bgvideo, random.Random(a.seed + 1)) if a.bgvideo else None

    rnd = random.Random(a.seed)
    seqs = load_seqs(a.people) if a.people else []
    bgs = load_bgs(a.bg) if a.bg else []
    words = open(a.text, encoding="utf-8").read().split() if a.text else []
    beat = a.beat or (detect_beat(a.audio) if a.audio else 0.37)
    print(f"拍 {beat:.3f}秒", file=sys.stderr)

    total = duration(a.audio)
    unit = total / sum(x for _, x in SECTIONS)
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"] +
                          (["-i", a.audio, "-shortest", "-c:a", "aac", "-b:a", "256k"] if a.audio else []) +
                          ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", a.out],
                          stdin=subprocess.PIPE)
    beat_f = max(1, round(beat * FPS))
    t = 0
    for name, length in SECTIONS:
        nf = int(round(length * unit * FPS))
        if name == "full": obj = Full(rnd, seqs, bgs, t, words, max(1, nf // beat_f), video)
        elif name == "end": obj = End(rnd, seqs, bgs, t, a.title)
        elif name == "tri" and a.layout == "wide": obj = Wide(rnd, seqs, bgs, t, video)
        else: obj = {"tri": Tri, "mosaic": Mosaic}[name](rnd, seqs, bgs, t)
        f = 0
        while f < nf:
            r = rnd.random()
            if name in ("tri", "mosaic") and r < .05: hold = round(1.4 * FPS)   # 溜め
            elif name in ("tri", "mosaic") and r < .12: hold = 1                # 一瞬
            elif r < .3: hold = max(1, beat_f // 2)                            # 半拍
            else: hold = beat_f
            for _ in range(min(hold, nf - f)):
                ff.stdin.write(obj.frame(t).tobytes()); t += 1; f += 1
            obj.step(t)
        print(name, "done", file=sys.stderr)
    ff.stdin.close(); ff.wait()


if __name__ == "__main__":
    main()
