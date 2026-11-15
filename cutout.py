#!/usr/bin/env python3
"""連番PNGの人物を切り抜く（背景を透明にする）。

使い方: python3 cutout.py 元のフォルダ 出力フォルダ
壊れたPNGは飛ばす。すでに出力にあるものも飛ばす（途中から再開できる）。
"""
import glob, os, sys
from PIL import Image
from rembg import remove, new_session

src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
s = new_session("u2net_human_seg")
for f in sorted(glob.glob(os.path.join(src, "*.png"))):
    o = os.path.join(dst, os.path.basename(f))
    if os.path.exists(o):
        continue
    try:
        remove(Image.open(f).convert("RGB"), session=s).save(o)
    except Exception:
        print("skip", f, file=sys.stderr)
