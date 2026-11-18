"""green-screen clip -> RGBA frames: human-seg mask AND not-green, with green spill removed"""
import sys, glob, os, numpy as np, cv2
from PIL import Image
from rembg import new_session, remove
src, dst = sys.argv[1], sys.argv[2]; ses = new_session('u2net_human_seg')
for f in sorted(glob.glob(src + '/*.png')):
    im = Image.open(f).convert('RGB'); rgb = np.array(im).astype(np.int32)
    seg = np.array(remove(im, session=ses, only_mask=True)).astype(np.float32) / 255
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    green = np.clip((g - np.maximum(r, b) * 1.25 - 12) / 40.0, 0, 1)          # 1 = backdrop
    al = np.clip(np.maximum(seg, 0) * (1 - green), 0, 1)
    al = cv2.GaussianBlur(al, (0, 0), 0.8)
    g2 = np.minimum(g, np.maximum(r, b) + 6)                                    # despill
    out = np.dstack([r, g2, b, al * 255]).astype(np.uint8)
    Image.fromarray(out).save(os.path.join(dst, os.path.basename(f)))
print('CUTDONE')
