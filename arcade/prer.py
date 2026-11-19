"""the silent lead-in before the song: python3 prer.py -> v3_pre.mp4"""
import numpy as np, subprocess, os, special
OW, OH, FPS = 1920, 1080, 30
p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{OW}x{OH}', '-r', str(FPS), '-i', '-',
                      '-c:v', 'libx264', '-crf', '18', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', 'tmp_pre.mp4'], stdin=subprocess.PIPE)
n = int(round(special.PRE * FPS))
for k in range(n): p.stdin.write(np.ascontiguousarray(special.pre_frame(k / FPS)).tobytes())
p.stdin.close()
if p.wait() == 0: os.rename('tmp_pre.mp4', 'v3_pre.mp4'); print('done pre', n)
