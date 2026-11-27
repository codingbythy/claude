"""A fire made the way myNoise's noise machines make it, offline: a few frequency bands, each with two recorded stems (A and B)
that take turns, A every (durA + durB) / 2 * stretch seconds and B starting half an A-length (times stretch) after A, each
band at gain level ** 3, the whole at `master`. Because every band has its own period, the fire never comes round the same.
Used by the long-video build (copied into a scene's video-kit) and by make-kit.py to measure its loudness.

The stems are not in this repository: they belong to myNoise and are used with permission, so they stay in the channel's
Google Drive (Cozy Scenes / fire-stems) and the Colab notebook copies them next to the build.
"""
import subprocess
import numpy as np

SR = 48000


class StemFire:
    def __init__(self, cfg, folder):
        self.parts = []                     # (stem samples, first start in seconds, period in seconds, gain)
        rate = cfg.get('rate', 1.0)         # tape speed: below 1 is slower and deeper
        for band in cfg['bands']:
            a, b = (self._load(f"{folder}/{band[s]}.ogg", rate) for s in ('a', 'b'))
            da, db = round(len(a) / SR * 8) / 8, round(len(b) / SR * 8) / 8
            period = (da + db) / 2 * cfg.get('stretch', 1.85)
            half = round(len(a) / SR * 8) / 16 * cfg.get('stretch', 1.85)
            g = band['level'] ** 3 * cfg.get('master', 0.5)
            self.parts += [(a, 0.0, period, g), (b, half, period, g)]

    @staticmethod
    def _load(path, rate):
        af = f'aresample={SR},asetrate={SR * rate:.3f},aresample={SR}' if rate != 1 else f'aresample={SR}'
        out = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-af', af, '-ac', '2', '-f', 'f32le', '-'], capture_output=True, check=True).stdout
        return np.frombuffer(out, '<f4').reshape(-1, 2)

    def render(self, start, n):
        """n stereo samples of fire starting `start` samples into the video, as float32."""
        out = np.zeros((n, 2), np.float32); t0, t1 = start / SR, (start + n) / SR
        for stem, first, period, g in self.parts:
            k = int(np.floor((t0 - first - len(stem) / SR) / period))
            while True:
                at = first + k * period
                if at >= t1:
                    break
                s0 = int(round(at * SR)) - start; lo, hi = max(0, s0), min(n, s0 + len(stem))
                if hi > lo:
                    out[lo:hi] += g * stem[lo - s0:hi - s0]
                k += 1
        return out

