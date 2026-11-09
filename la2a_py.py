"""Pure-Python port of la2a/la2a_core.h (LA-2A manual-faithful behavioral core, mono). Verified sample-for-sample
against the C++ in test_la2a_block.py. NOT hardware-equivalent; every constant is the repo's UNVERIFIED fit."""
import math
import numpy as np

class LA2ACore:
    def __init__(self, fs, gain_db=0.0, peak_reduction=0.07, compress=False):
        self.fs = float(fs); self.gainT = 10 ** (gain_db / 20.0); self.prT = float(peak_reduction); self.compress = bool(compress)
        self.reset(); self.smooth = 1.0 - math.exp(-1.0 / (0.010 * self.fs))
        c = lambda t: math.exp(-1.0 / (max(t, 1.0 / self.fs) * self.fs))
        self.fa = self.sa = c(10e-6); self.fr = c(0.030); self.sr = c(2.0); self.wf, self.ws = 0.56, 0.44
    def reset(self):
        self.gf = self.gs = 0.0; self.gain = self.gainT; self.pr = self.prT; self.gr_db = 0.0
    def process(self, x, return_gr=False):
        x = np.asarray(x, dtype=np.float64); out = np.empty_like(x); gr = np.empty_like(x) if return_gr else None
        gamma = 2.0 / 3.0 if self.compress else 1.0; gf, gs = self.gf, self.gs; gain, pr = self.gain, self.pr
        fa, fr, sa, sr, wf, ws, sm = self.fa, self.fr, self.sa, self.sr, self.wf, self.ws, self.smooth
        for i in range(len(x)):
            v = float(x[i])
            if not math.isfinite(v): v = 0.0
            gain += sm * (self.gainT - gain); pr += sm * (self.prT - pr)
            K = 400.0 * pr * pr + 1e-9; light = abs(v)
            t = 20.0 * math.log10(1.0 + K * (light ** gamma if self.compress else light))
            k = fa if t > gf else fr; gf = k * gf + (1 - k) * t
            k = sa if t > gs else sr; gs = k * gs + (1 - k) * t
            if gf < 1e-18: gf = 0.0
            if gs < 1e-18: gs = 0.0
            g = wf * gf + ws * gs
            out[i] = v * 10.0 ** (-g / 20.0) * gain
            if return_gr: gr[i] = g
        self.gf, self.gs, self.gain, self.pr, self.gr_db = gf, gs, gain, pr, (g if len(x) else 0.0)
        return (out, gr) if return_gr else out
