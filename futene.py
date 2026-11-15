#!/usr/bin/env python3
"""ふて寝の型 — 初期パラグルビート（キブンヤのmajo ふて寝4）から取り出した型。

芯は「圧と抜きの落差」。
  圧 : 二枚（A=枠に入った錨 / B=別のもの）を1〜3コマで行き来させる
  抜き: フレームそのものを縮める・動かす・傾ける・黒帯で狭める。浮遊感と溜め
  錨 : 最初の連番フォルダ（または --anchor）が何度も戻ってくる
どこで抜くか、どれくらい詰めるかはシードまかせ。何本か出して偶然を拾う。

使い方:
  python3 futene.py --people materials/people --bgvideo materials/bgv \
      --audio 曲 --title タイトル --out 出力.mp4 --seed 1 [--anchor フォルダ名]
  --seeds 1,2,3 で何本かまとめて出す（出力名に _s番号 が付く）
"""
import argparse, glob, math, os, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageChops, ImageFilter
import doodle_majo as dm

W, H, FPS = dm.W, dm.H, dm.FPS


# ---------- 柄 ----------
def zigzag(rnd):
    a, b = rnd.sample(["#111111", "#e8f000", "#5ad1c8", "#ff3d8b", "#2a3fd0", "#ffffff"], 2)
    im = Image.new("RGB", (W, H), a); d = ImageDraw.Draw(im)
    amp, step, th = rnd.choice([(80, 120, 70), (50, 80, 45), (120, 180, 100)])
    for y0 in range(-amp, H + 2 * amp, th * 2 + amp):
        d.line([(x, y0 + (amp if (x // step) % 2 else 0)) for x in range(-step, W + step, step)], fill=b, width=th)
    return im


def dots(rnd):
    bg, fg = rnd.sample(["#f6d6d6", "#e8e2d8", "#111111", "#2a3fd0", "#ffd400"], 2)
    im = Image.new("RGB", (W, H), bg); d = ImageDraw.Draw(im); s = rnd.choice([16, 22, 30])
    for y in range(0, H, s):
        for x in range(0, W, s): d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=fg)
    return im


def lines(rnd):
    im = Image.new("RGB", (W, H), "#ffffff"); d = ImageDraw.Draw(im)
    for k in range(-40, 80):
        y = k * 28
        d.line([(x, y + 60 * math.sin(x / 260 + k * .1)) for x in range(0, W + 40, 40)], fill="#111111", width=4)
    return im


def swirl_bg(video, rnd):
    """背景: 動画か柄"""
    if video and rnd.random() < .6: return None
    return rnd.choice([zigzag, dots, lines, lambda r: dm.graphic_full(r)])(rnd)


# ---------- 静止画（切り抜かず、パラグルっぽく使う） ----------
def load_stills(folder, size=(1280, 720)):
    fs = sorted(f for f in glob.glob(os.path.join(folder, "**", "*"), recursive=True)
                if f.lower().endswith((".png", ".jpg", ".jpeg")) and "__MACOSX" not in f)
    out = []
    for f in fs:
        try: out.append(Image.open(f).convert("RGB").resize(size))
        except Exception: pass
    print(f"静止画 {len(out)}枚", file=sys.stderr)
    return out


class StillRun:
    """静止画を区間ごとに秒数を変えて点滅させる（1コマずつ／3コマずつ／溜め）"""
    def __init__(s, stills, rnd):
        s.st, s.r = stills, rnd
        s.i = rnd.randrange(len(stills)); s.hold = 1; s.left = 0; s.run = 0

    def frame(s):
        r = s.r
        if s.run <= 0:                       # 区間が替わると刻みも替わる
            s.hold = r.choice([1, 1, 2, 3, 5, 12]); s.run = r.randint(6, 30)
            if r.random() < .3: s.i = r.randrange(len(s.st))
        if s.left <= 0:
            s.i = (s.i + (1 if r.random() < .8 else r.randint(2, 20))) % len(s.st)
            s.left = s.hold
        s.left -= 1; s.run -= 1
        return s.st[s.i].resize((W, H))


# ---------- 枠 ----------
def rounded_mask(w, h, r):
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255)
    return m.filter(ImageFilter.GaussianBlur(r * .25))


def framed(content, rnd, kind=None):
    """content(W×H)を枠に入れて返す（RGBA、枠の外は透明）"""
    kind = kind or rnd.choice(["round", "bars", "rect", "round"])
    sc = rnd.uniform(.62, .85)
    w, h = int(W * sc), int(H * sc)
    c = content.resize((w, h)).convert("RGBA")
    if kind == "round":
        c.putalpha(rounded_mask(w, h, int(h * .28)))
    elif kind == "bars":
        d = ImageDraw.Draw(c); bh = int(h * rnd.uniform(.08, .18))
        d.rectangle([0, h - bh, w, h], fill="#000000")
        if rnd.random() < .5: d.rectangle([0, 0, w, bh // 2], fill="#000000")
    return c


# ---------- 中身 ----------
class Cast:
    def __init__(s, seqs, anchor_i, video, bgs, rnd):
        s.seqs, s.ai, s.video, s.bgs, s.r = seqs, anchor_i, video, bgs, rnd
        s.others = [q for i, q in enumerate(seqs) if i != anchor_i] or seqs

    def anchor_scene(s, t, actor, bg=None):
        """錨の場面: 白っぽい地に錨（二人並べることもある）"""
        im = bg.copy() if bg is not None else Image.new("RGB", (W, H), "#e9e4dc")
        put = dm.put
        if actor.get("pair"):
            put(im, actor["a"].img(t), H * .9, W * .36, H); put(im, actor["b"].img(t), H * .9, W * .64, H)
        else:
            put(im, actor["a"].img(t), H * .95, W * .5, H)
        return im

    def b_scene(s, t, st):
        """B: 別のキャラを図形の面に、または柄そのもの、または背景動画"""
        r = s.r
        if st["kind"] == "pattern": return st["pat"]
        if st["kind"] == "video" and s.video: return s.video.frame().copy()
        im = st["panel"].copy()
        dm.put(im, st["actor"].img(t), H * st["h"], W * st["x"], H)
        return im

    def new_b(s, t):
        r = s.r
        k = r.random()
        if k < .3: return {"kind": "pattern", "pat": zigzag(r) if r.random() < .6 else dots(r)}
        if k < .45 and s.video: return {"kind": "video"}
        return {"kind": "char", "panel": dm.graphic_full(r), "actor": dm.Actor(s.others, r, t),
                "h": r.uniform(.8, 1.1), "x": r.uniform(.35, .65)}

    def new_anchor(s, t):
        r = s.r; aseq = [s.seqs[s.ai]]
        a = dm.Actor(aseq, r, t)
        if r.random() < .5:
            return {"a": a, "b": dm.Actor(aseq, r, t), "pair": True}
        return {"a": a}


# ---------- 段の並び（毎回ちがう） ----------
def plan(total, rnd):
    segs = [("intro", total * rnd.uniform(.07, .1))]
    outro = total * rnd.uniform(.05, .08)
    left = total - segs[0][1] - outro
    while left > 0.5:
        if segs[-1][0] in ("press",):
            L = rnd.uniform(1.0, 6.0); kind = "release" if rnd.random() < .55 else "burst"
        else:
            L = rnd.uniform(3.0, 13.0); kind = "press"
            if rnd.random() < .25: kind = "anchor"; L = rnd.uniform(1.5, 4)
        L = min(L, left)
        if kind == "press" and L > 4 and rnd.random() < .4:     # 山の途中にいきなり抜く
            cut = rnd.uniform(1.5, L - 1.5); short = rnd.uniform(.4, 1.2)
            segs += [("press", cut), ("release", short), ("press", L - cut)]
            left -= L + short
            continue
        segs.append((kind, L)); left -= L
    segs.append(("outro", outro))
    return segs


# ---------- 抜き（フレームそのものを動かす） ----------
class Release:
    def __init__(s, rnd, nf, video):
        s.r, s.nf, s.video = rnd, nf, video
        s.mode = rnd.choice(["shrink", "float", "rotate", "bars", "shrink", "tilt"])
        s.bg = rnd.choice([None, "black", "dots"]) if video else rnd.choice(["black", "dots"])
        s.dots = dots(rnd)
        s.angles = [rnd.choice([0, 90, -90, 180, 25, -30, 12]) for _ in range(64)]
        s.min_s = rnd.uniform(.03, .35)
        s.ease = rnd.choice([.3, .6, 1, 2.5, 4])

    def apply(s, im, f):
        r = s.r; p = f / max(1, s.nf - 1)
        base = (s.video.frame().copy() if s.bg is None else
                Image.new("RGB", (W, H), "#000000") if s.bg == "black" else s.dots.copy())
        if s.bg is None: base = base.point(lambda v: v * .45)
        if s.mode == "shrink":       # 点まで縮んで戻る
            q = abs(math.cos(math.pi * p)); q = q ** s.r.choice([1, 1]) if not hasattr(s, "ease") else q ** s.ease
            sc = s.min_s + (1 - s.min_s) * q
            return paste_scaled(base, im, sc, 0, 0, 0)
        if s.mode == "float":        # ふわっと漂う
            sc = .55 + .1 * math.sin(p * math.pi * 2)
            return paste_scaled(base, im, sc, W * .18 * math.sin(p * 5), H * .12 * math.cos(p * 3.3), 3 * math.sin(p * 4))
        if s.mode == "rotate":       # コマごとに角度が変わる
            return paste_scaled(base, im, .8, 0, 0, s.angles[(f // 3) % len(s.angles)])
        if s.mode == "tilt":         # 斜めに切って下を見せる
            sc = .85; ang = s.angles[(f // 4) % len(s.angles)]
            out = paste_scaled(base, im, sc, r.uniform(-40, 40), 0, ang)
            d = ImageDraw.Draw(out)
            d.polygon([(W * .55, H), (W, H * .25), (W, H)], fill="#3a9a5c")
            return out
        # bars: 黒帯が上下から締める
        bh = int(H * .45 * math.sin(math.pi * p))
        out = im.copy(); d = ImageDraw.Draw(out)
        d.rectangle([0, 0, W, bh], fill="#000000"); d.rectangle([0, H - bh, W, H], fill="#000000")
        return out


def paste_scaled(base, im, sc, dx, dy, ang):
    w, h = max(2, int(W * sc)), max(2, int(H * sc))
    c = im.resize((w, h)).convert("RGBA")
    if ang: c = c.rotate(ang, expand=True, resample=Image.BILINEAR)
    base.paste(c, (int((W - c.width) / 2 + dx), int((H - c.height) / 2 + dy)), c)
    return base


class Burst:
    """発信（小さく溜める）→ ぱーーーん（一気に寄る）。何枚も連なる"""
    def __init__(s, rnd, nf, video, stills):
        s.r, s.video, s.stills = rnd, video, stills
        s.bg = rnd.choice(["black", "black", "video", "still"])
        s.trains = []; f = 0
        while f < nf:
            charge = rnd.choice([2, 4, 8, 14, 22])          # 発信の長さ
            boom = rnd.choice([3, 4, 6, 9])                  # ぱーーーんの速さ
            src = rnd.choice(["still", "still", "A"]) if stills else "A"
            pic = rnd.choice(stills) if src == "still" and stills else None
            pos = (rnd.uniform(-.25, .25) * W, rnd.uniform(-.2, .2) * H) if rnd.random() < .5 else (0, 0)
            ang = rnd.choice([0, 0, 0, 8, -12, 90])
            s.trains.append((f, charge, boom, pic, pos, ang))
            f += max(1, int((charge + boom) * rnd.choice([.35, .5, .7, 1.0])))   # 連なり（重なる）

    def apply(s, A, f):
        r = s.r
        if s.bg == "video" and s.video: base = s.video.frame().copy().point(lambda v: v * .35)
        elif s.bg == "still" and s.stills: base = s.stills[(f // 2) % len(s.stills)].resize((W, H)).point(lambda v: v * .3)
        else: base = Image.new("RGB", (W, H), "#000000")
        for st, charge, boom, pic, pos, ang in s.trains:
            k = f - st
            if k < 0 or k >= charge + boom + 2: continue
            if k < charge:                                   # 発信: 小さく震える・明滅
                if (k // 2) % 3 == 2: continue
                sc = .04 + .03 * (k / max(1, charge)) + r.uniform(-.008, .008)
            else:                                            # ぱーーーん: 加速して画面を突き抜ける
                p = (k - charge) / boom
                sc = .07 + 1.6 * (p ** 2.4)
            im = pic.resize((W, H)) if pic is not None else A
            dx, dy = pos[0] * (1 - min(1, sc)), pos[1] * (1 - min(1, sc))
            base = paste_scaled(base, im, sc, dx, dy, ang * (1 - min(1, sc)))
        return base


# ---------- 組む ----------
def render(a, seed, out):
    rnd = random.Random(seed)
    seqs = dm.load_seqs(a.people)
    names = sorted(d for d in os.listdir(a.people) if os.path.isdir(os.path.join(a.people, d)))
    ai = names.index(a.anchor) if a.anchor in names else 0
    video = dm.BgVideo(a.bgvideo, random.Random(seed + 7)) if a.bgvideo else None
    cast = Cast(seqs, ai, video, [], rnd)
    stills = load_stills(a.stills) if a.stills else []
    total = dm.duration(a.audio)
    segs = plan(total, rnd)
    print(f"seed {seed}: " + " ".join(f"{k}{L:.1f}" for k, L in segs), file=sys.stderr)

    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", a.audio, "-shortest", "-c:a", "aac", "-b:a", "256k",
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", out],
                          stdin=subprocess.PIPE)
    fj = ImageFont.truetype(dm.FONT_JP, 220); fe = ImageFont.truetype(dm.FONT, 150)
    t = 0
    for kind, L in segs:
        nf = int(round(L * FPS))
        anc = cast.new_anchor(t)
        bgA = swirl_bg(video, rnd)
        frameA = rnd.choice(["round", "bars", "rect", "round"])
        bst = cast.new_b(t)
        period = rnd.choice([1, 2, 2, 3])          # 二枚の行き来の刻み
        bswap = rnd.choice([3, 3, 4, 6])           # Bの中身が替わる刻み
        rel = Release(rnd, nf, video) if kind == "release" else None
        bur = Burst(rnd, nf, video, stills) if kind == "burst" else None
        srun = StillRun(stills, rnd) if stills else None
        use_still = stills and rnd.random() < .5
        glitchy = rnd.random() < .25
        for f in range(nf):
            if video:
                if f % 9 == 0: video.step()
            # A: 枠に入った錨
            scene = cast.anchor_scene(t, anc)
            if kind in ("press", "release", "burst"):
                base = (video.frame().copy() if bgA is None and video else (bgA or zigzag(rnd)).copy())
                fr = framed(scene, random.Random(seed * 1000 + int(t / 30)), frameA)
                base.paste(fr, ((W - fr.width) // 2, (H - fr.height) // 2), fr)
                A = base
            else:
                A = scene
            if kind == "press":
                if f % bswap == 0 and rnd.random() < .7: bst = cast.new_b(t)
                if (f // period) % 2 == 0: im = A
                elif use_still and rnd.random() < .6: im = srun.frame()
                else: im = cast.b_scene(t, bst)
                if f % 15 == 0 and rnd.random() < .3:
                    anc = cast.new_anchor(t)
                for x in anc.values():
                    if isinstance(x, dm.Actor) and rnd.random() < .02: x.maybe_stutter(t)
            elif kind == "release":
                im = rel.apply(A, f)
            elif kind == "burst":
                im = bur.apply(A, f)
            elif kind == "intro":
                im = A.copy(); d = ImageDraw.Draw(im)
                if f > nf * .15:
                    txt = "dreaming majo" if f < nf * .55 else (a.title or "")
                    font = fe if f < nf * .55 else fj
                    tw = d.textlength(txt, font=font)
                    d.text(((W - tw) / 2, H * .38), txt, font=font,
                           fill="#e0242b" if f < nf * .55 else "#5ad1f0", stroke_width=6, stroke_fill="#ffffff")
            else:  # anchor / outro: 錨に戻る
                im = A
            if glitchy and kind == "press" and (t // 2) % 3 == 0: im = dm.glitch(im, rnd)
            ff.stdin.write(im.convert("RGB").tobytes()); t += 1
    ff.stdin.close(); ff.wait()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--people", required=True); ap.add_argument("--bgvideo", default="")
    ap.add_argument("--audio", required=True); ap.add_argument("--title", default="")
    ap.add_argument("--anchor", default=""); ap.add_argument("--stills", default=""); ap.add_argument("--out", default="futene.mp4")
    ap.add_argument("--seed", type=int, default=1); ap.add_argument("--seeds", default="")
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(",")] if a.seeds else [a.seed]
    for s in seeds:
        out = a.out if len(seeds) == 1 else a.out.replace(".mp4", f"_s{s}.mp4")
        render(a, s, out)


if __name__ == "__main__":
    main()
