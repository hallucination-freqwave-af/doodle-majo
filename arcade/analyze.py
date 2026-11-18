"""song.aif -> mono.f32 + rms/flux/low/hi .npy (render.py reads these). usage: python3 analyze.py song.aif"""
import sys, subprocess, numpy as np
from scipy import signal
src = sys.argv[1]; sr = 22050; hop = 512
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src, '-ac', '1', '-ar', str(sr), '-f', 'f32le', 'mono.f32'], check=True)
x = np.fromfile('mono.f32', dtype=np.float32); nfr = len(x) // hop
rms = np.sqrt(np.mean(x[:nfr * hop].reshape(nfr, hop) ** 2, axis=1))
f, t, S = signal.stft(x, sr, nperseg=2048, noverlap=2048 - hop); mag = np.abs(S)
flux = np.sum(np.maximum(mag[:, 1:] - mag[:, :-1], 0), axis=0); flux /= flux.max()
low = np.sum(mag[f < 150], axis=0); low /= low.max(); hi = np.sum(mag[f > 4000], axis=0); hi /= hi.max()
for n, a in [('rms', rms), ('flux', flux), ('low', low), ('hi', hi)]: np.save(n + '.npy', a)
fl = flux - flux.mean(); ac = np.correlate(fl, fl, 'full')[len(fl) - 1:]; lags = np.arange(len(ac)) / (sr / hop)
m = (lags > 0.3) & (lags < 1.0); print('duration', len(x) / sr, 'bpm', 60 / lags[m][np.argmax(ac[m])])
