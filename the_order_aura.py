"""
the_order_aura.py - drop-in replacements for three stages of THE ORDER (CASE 22-EAR-4).

    chain = TheOrder(44100.0, custom=aura_stages(44100.0))

  saturation -> VantageSaturationBlock : biased tanh run at 4x (even + odd harmonics), DC-blocked wet path,
                                         unity small-signal gain, parallel mix like the stock block
  limiter    -> TruePeakLimiterBlock   : real look-ahead, 4x true-peak detection, two-pass safety, default -1.0 dBTP
  dither     -> ProDitherBlock         : TPDF + 5-tap Lipshitz error feedback (feedback subtracted), real 16-bit grid

Offline (whole-array) processing. Real-time latency to report to a host:
  Vantage 4x FIR 60 samples, limiter look-ahead N samples (see .latency_samples).
Grid note: ProDither quantises to k/32767 (matches x32767 export); a x32768 exporter should rescale.
"""
import numpy as np
from scipy import signal
from scipy.ndimage import minimum_filter1d, uniform_filter1d

import the_order_vocal_chain as O
from vantage_os import vantage
from prodither_fixed import ProDither, ProDitherConfig
from la2a_py import LA2ACore


class VantageSaturationBlock(O.DSPBlock):
    name = "saturation"; codec_key = "sat:Vulture"
    latency_samples = 60                                # 241-tap Kaiser up + down at 4x (offline: compensated)

    def __init__(self, fs, a=2.0, bias=0.3, mix=0.22, oversample=4, dc_hz=5.0):
        self.fs, self.a, self.bias, self.mix, self.L = float(fs), a, bias, mix, oversample
        self.R = 1.0 - 2.0 * np.pi * dc_hz / self.fs

    def process_block(self, x):
        x = np.asarray(x, dtype=np.float64)
        g = self.a * (1.0 - np.tanh(self.bias) ** 2)             # small-signal gain of the curve -> unity
        wet = vantage(x, self.a, self.bias, self.L) / g
        wet = signal.lfilter([1.0, -1.0], [1.0, -self.R], wet)    # DC blocker (curve is asymmetric)
        return (1.0 - self.mix) * x + self.mix * wet


class LA2ASlowCompBlock(O.DSPBlock):
    """LA-2A manual-faithful behavioral leveler (replaces the stock 'slow_comp', which only claimed LA-2A style).
    peak_reduction 0.04-0.10 gives about 1-6 dB of gain reduction at vocal peaks (-12..-6 dBFS); the core's PR taper is
    steep (0.5 is 30 dB of reduction), and its base gain is unity, so use gain_db for makeup. Offline, zero latency."""
    name = "slow_comp"; codec_key = "slowcomp:LA2A"; latency_samples = 0

    def __init__(self, fs, peak_reduction=0.07, gain_db=0.0, compress=False):
        self.core = LA2ACore(fs, gain_db, peak_reduction, compress)

    def process_block(self, x): return self.core.process(x)
    def reset(self): self.core.reset()


class TruePeakLimiterBlock(O.DSPBlock):
    name = "limiter"; codec_key = "lim:Weiss"

    def __init__(self, fs, ceiling_dbtp=-1.0, lookahead_ms=5.0, release_ms=80.0, oversample=4, margin_db=0.05):
        self.fs, self.os = float(fs), oversample
        self.target_lin = 10 ** (ceiling_dbtp / 20.0)
        self.ceiling = 10 ** ((ceiling_dbtp - margin_db) / 20.0)
        self.N = max(2, int(lookahead_ms * 1e-3 * fs))
        self.rel = np.exp(-1.0 / (release_ms * 1e-3 * self.fs))
        self.latency_samples = self.N

    def _gain(self, x):
        up = signal.resample_poly(x, self.os, 1)[: len(x) * self.os]
        pk = np.abs(up).reshape(len(x), self.os).max(axis=1)              # true-peak per host sample
        r = np.minimum(1.0, self.ceiling / np.maximum(pk, 1e-12))
        m = minimum_filter1d(r, size=2 * self.N - 1, mode="nearest")      # future AND past N samples
        g = uniform_filter1d(m, size=self.N, mode="nearest")             # smooth ramp, still <= r at every sample
        out = np.empty_like(g); cur = 1.0; rel = self.rel
        for i in range(len(g)):                                          # release only slows recovery
            cur = min(g[i], rel * cur + (1.0 - rel)); out[i] = cur
        return out

    def true_peak(self, y):
        return float(np.max(np.abs(signal.resample_poly(y, self.os, 1)))) if len(y) else 0.0

    def process_block(self, x):
        y = np.asarray(x, dtype=np.float64)
        for _ in range(3):                                               # safety passes
            if self.true_peak(y) <= self.target_lin:
                break
            y = y * self._gain(y)
        return y


class ProDitherBlock(O.DSPBlock):
    name = "dither"; codec_key = "dither"

    def __init__(self, fs, bits=16, shaping="lipshitz", seed=0):
        self.cfg = ProDitherConfig(bit_depth=bits, sample_rate_hz=float(fs), mode="clean", shaping=shaping, dither_seed=seed)

    def process_block(self, x):
        return ProDither(self.cfg).process(np.asarray(x, dtype=np.float64))


def aura_stages(fs, la2a=False, **kw):
    """custom={...} dict for TheOrder(...). la2a=True also swaps the slow compressor for the LA-2A core."""
    d = {"saturation": VantageSaturationBlock(fs, **kw.get("sat", {})),
         "limiter": TruePeakLimiterBlock(fs, **kw.get("lim", {})),
         "dither": ProDitherBlock(fs, **kw.get("dith", {}))}
    if la2a: d["slow_comp"] = LA2ASlowCompBlock(fs, **kw.get("la2a", {}))
    return d
