#!/usr/bin/env python3
"""
CASE FILE 22-EAR-4 — THE ORDER (UPGRADED)
Eargle-Informed Vocal Processing Chain — Modular Block Architecture

"The voice is already a synthesizer. You are not fixing it.
You are preserving a patch made of flesh and breath."

IMMUTABLE ORDER:
  SOURCE → CORRECTION → CONTROL → CHARACTER → SPACE → AUTOMATION → GLUE

CODEC STRING (canonical hardware → software keys):
  pre:U47>1073>Lavry>Genesys|hp|subeq:550A|fastcomp:1176|slowcomp:LA2A|
  deess:902|addeq:Pultec|sat:Vulture|delay:Echoplex|rev:EMT140|bus:SSL|lim:Weiss

Each processing stage carries both a stage name and a codec_key.
To inject your own custom DSP:
  1. Subclass DSPBlock (implement process_block + optionally set codec_key)
  2. Pass the instance into TheOrder(...) at construction time
  3. Or replace via chain.replace_stage("name", your_obj)

Dependencies: numpy  (scipy optional for higher-order filters)
"""

from __future__ import annotations
import numpy as np
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod


# =============================================================================
# CANONICAL CODEC KEYS  (must match Hardware_Codec_Mapping.md)
# =============================================================================

CODEC_STRING = (
    "pre:U47>1073>Lavry>Genesys|"
    "hp|"
    "subeq:550A|"
    "gate|"
    "fastcomp:1176|"
    "slowcomp:LA2A|"
    "deess:902|"
    "dyneq|"
    "addeq:Pultec|"
    "sat:Vulture|"
    "delay:Echoplex|"
    "rev:EMT140|"
    "bus:SSL|"
    "lim:Weiss|"
    "dither"
)

# stage name → codec key
CODEC_KEYS: Dict[str, str] = {
    "pre_chain":      "pre:U47>1073>Lavry>Genesys",
    "highpass":       "hp",
    "subtractive_eq": "subeq:550A",
    "noise_gate":     "gate",
    "fast_comp":      "fastcomp:1176",
    "slow_comp":      "slowcomp:LA2A",
    "parallel_comp":  "parallel",
    "deesser":        "deess:902",
    "dynamic_eq":     "dyneq",
    "additive_eq":    "addeq:Pultec",
    "saturation":     "sat:Vulture",
    "delay":          "delay:Echoplex",
    "reverb":         "rev:EMT140",
    "bus":            "bus:SSL",
    "limiter":        "lim:Weiss",
    "dither":         "dither",
}


# =============================================================================
# BASE INTERFACE — every custom DSP must satisfy this
# =============================================================================

class DSPBlock(ABC):
    """Minimal contract for any stage in The Order."""
    name: str = "unnamed"
    codec_key: str = ""          # e.g. "fastcomp:1176"

    @abstractmethod
    def process_block(self, x: np.ndarray) -> np.ndarray:
        """Process a mono float array in [-1, 1] (or beyond) and return same shape."""
        ...

    def reset(self) -> None:
        """Optional: clear internal state (delay lines, envelopes, etc.)."""
        pass


# =============================================================================
# I. CORRECTION BLOCKS  (Subtractive EQ + High-pass)
# =============================================================================
#
# ADVICE FOR CUSTOM DSP:
#   Replace HighPassBlock / SubtractiveEQBlock with any of:
#     - Your own biquad cascade / FIR / IIR bank
#     - Spectral subtraction or neural denoiser that preserves formants
#     - Dynamic EQ that only cuts when energy is present in the band
#   Keep the philosophy: REMOVE what masks the core. Do not add yet.
#   Target frequencies remain: HPF 80–100 Hz, mud 200–400, harsh 1–3 k,
#   sibilance region 5–8 k (pre-deess cut is mild).
# =============================================================================

class BiquadFilter:
    """Direct-Form I biquad — stable building block."""
    def __init__(self, b0, b1, b2, a1, a2):
        self.b0, self.b1, self.b2 = float(b0), float(b1), float(b2)
        self.a1, self.a2 = float(a1), float(a2)
        self.x1 = self.x2 = 0.0
        self.y1 = self.y2 = 0.0

    def process(self, x: float) -> float:
        y = (self.b0 * x + self.b1 * self.x1 + self.b2 * self.x2
             - self.a1 * self.y1 - self.a2 * self.y2)
        self.x2, self.x1 = self.x1, x
        self.y2, self.y1 = self.y1, y
        return y

    def process_block(self, x: np.ndarray) -> np.ndarray:
        y = np.empty_like(x, dtype=np.float64)
        for i, s in enumerate(x):
            y[i] = self.process(float(s))
        return y

    def reset(self):
        self.x1 = self.x2 = self.y1 = self.y2 = 0.0


def _peaking(fs, f0, gain_db, Q):
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * np.pi * f0 / fs
    alpha = np.sin(w0) / (2 * Q)
    c = np.cos(w0)
    b0 = 1 + alpha * A
    b1 = -2 * c
    b2 = 1 - alpha * A
    a0 = 1 + alpha / A
    a1 = -2 * c
    a2 = 1 - alpha / A
    return BiquadFilter(b0/a0, b1/a0, b2/a0, a1/a0, a2/a0)


def _highpass(fs, f0, Q=0.707):
    w0 = 2 * np.pi * f0 / fs
    alpha = np.sin(w0) / (2 * Q)
    c = np.cos(w0)
    b0 = (1 + c) / 2
    b1 = -(1 + c)
    b2 = (1 + c) / 2
    a0 = 1 + alpha
    a1 = -2 * c
    a2 = 1 - alpha
    return BiquadFilter(b0/a0, b1/a0, b2/a0, a1/a0, a2/a0)


def _lowshelf(fs, f0, gain_db, Q=0.707):
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * np.pi * f0 / fs
    alpha = np.sin(w0) / (2 * Q)
    c = np.cos(w0)
    two = 2 * np.sqrt(A) * alpha
    b0 = A * ((A+1) - (A-1)*c + two)
    b1 = 2*A * ((A-1) - (A+1)*c)
    b2 = A * ((A+1) - (A-1)*c - two)
    a0 = (A+1) + (A-1)*c + two
    a1 = -2 * ((A-1) + (A+1)*c)
    a2 = (A+1) + (A-1)*c - two
    return BiquadFilter(b0/a0, b1/a0, b2/a0, a1/a0, a2/a0)


def _highshelf(fs, f0, gain_db, Q=0.707):
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * np.pi * f0 / fs
    alpha = np.sin(w0) / (2 * Q)
    c = np.cos(w0)
    two = 2 * np.sqrt(A) * alpha
    b0 = A * ((A+1) + (A-1)*c + two)
    b1 = -2*A * ((A-1) + (A+1)*c)
    b2 = A * ((A+1) + (A-1)*c - two)
    a0 = (A+1) - (A-1)*c + two
    a1 = 2 * ((A-1) - (A+1)*c)
    a2 = (A+1) - (A-1)*c - two
    return BiquadFilter(b0/a0, b1/a0, b2/a0, a1/a0, a2/a0)


def _lowpass(fs, f0, Q=0.707):
    """Second-order Butterworth-style low-pass biquad."""
    w0 = 2 * np.pi * f0 / fs
    alpha = np.sin(w0) / (2 * Q)
    c = np.cos(w0)
    b0 = (1 - c) / 2
    b1 = 1 - c
    b2 = (1 - c) / 2
    a0 = 1 + alpha
    a1 = -2 * c
    a2 = 1 - alpha
    return BiquadFilter(b0/a0, b1/a0, b2/a0, a1/a0, a2/a0)



class HighPassBlock(DSPBlock):
    name = "highpass"
    codec_key = "hp"
    def __init__(self, sample_rate: float, cutoff: float = 85.0, Q: float = 0.707):
        self.filt = _highpass(sample_rate, cutoff, Q)
    def process_block(self, x): return self.filt.process_block(x)
    def reset(self): self.filt.reset()


class SubtractiveEQBlock(DSPBlock):
    """Classic corrective cuts: mud / harsh / pre-sibilance. Codec: subeq:550A"""
    name = "subtractive_eq"
    codec_key = "subeq:550A"
    def __init__(self, sample_rate: float):
        self.mud   = _peaking(sample_rate, 280.0, -3.5, 1.4)
        self.harsh = _peaking(sample_rate, 2200.0, -2.5, 1.8)
        self.sib   = _peaking(sample_rate, 6500.0, -2.0, 2.5)
    def process_block(self, x):
        x = self.mud.process_block(x)
        x = self.harsh.process_block(x)
        x = self.sib.process_block(x)
        return x
    def reset(self):
        self.mud.reset(); self.harsh.reset(); self.sib.reset()


# =============================================================================
# II. CONTROL BLOCKS  (Compression + De-ess)
# =============================================================================
#
# ADVICE FOR CUSTOM DSP:
#   FastCompBlock  → replace with your 1176 / FET / VCA model
#                    (keep attack ≤ 1 ms, ratio 3–8, GR 2–4 dB typical)
#   SlowCompBlock  → replace with LA-2A / opto / Fairchild model
#                    (program-dependent release, GR 2–3 dB)
#   DeEsserBlock   → replace with split-band, dynamic EQ, or neural de-esser
#                    (target 6–9 kHz, act only on sibilant peaks)
#   Parallel path is available via ParallelCompressorBlock if you want density
#   without destroying the main dynamic range.
# =============================================================================

class CompressorCore:
    """Shared feed-forward peak detector + gain computer."""
    def __init__(self, threshold_db=-18.0, ratio=4.0,
                 attack_ms=10.0, release_ms=100.0,
                 sample_rate=44100.0, makeup_db=0.0):
        self.threshold = 10 ** (threshold_db / 20.0)
        self.ratio = ratio
        self.atk = np.exp(-1.0 / (attack_ms * 0.001 * sample_rate))
        self.rel = np.exp(-1.0 / (release_ms * 0.001 * sample_rate))
        self.makeup = 10 ** (makeup_db / 20.0)
        self.env = 0.0

    def process(self, x: float) -> float:
        r = abs(x)
        if r > self.env:
            self.env = self.atk * self.env + (1 - self.atk) * r
        else:
            self.env = self.rel * self.env + (1 - self.rel) * r
        if self.env > self.threshold:
            g = (self.threshold / self.env) ** (1.0 - 1.0 / self.ratio)
        else:
            g = 1.0
        return x * g * self.makeup

    def process_block(self, x: np.ndarray) -> np.ndarray:
        return np.array([self.process(float(s)) for s in x], dtype=np.float64)

    def reset(self):
        self.env = 0.0


class FastCompBlock(DSPBlock):
    """1176-style fast peak control. Codec: fastcomp:1176"""
    name = "fast_comp"
    codec_key = "fastcomp:1176"
    def __init__(self, sample_rate: float,
                 threshold_db: float = -16.0, ratio: float = 4.0,
                 attack_ms: float = 0.4, release_ms: float = 80.0):
        self.core = CompressorCore(threshold_db, ratio, attack_ms, release_ms, sample_rate)
    def process_block(self, x): return self.core.process_block(x)
    def reset(self): self.core.reset()


class SlowCompBlock(DSPBlock):
    """LA-2A-style smoother level consistency. Codec: slowcomp:LA2A"""
    name = "slow_comp"
    codec_key = "slowcomp:LA2A"
    def __init__(self, sample_rate: float,
                 threshold_db: float = -18.0, ratio: float = 2.5,
                 attack_ms: float = 15.0, release_ms: float = 280.0,
                 makeup_db: float = 1.5):
        self.core = CompressorCore(threshold_db, ratio, attack_ms, release_ms,
                                   sample_rate, makeup_db)
    def process_block(self, x): return self.core.process_block(x)
    def reset(self): self.core.reset()


class ParallelCompressorBlock(DSPBlock):
    """
    Heavy parallel compression for density.
    Custom DSP tip: feed your own aggressive compressor into the wet path.
    """
    name = "parallel_comp"
    codec_key = "parallel"
    def __init__(self, sample_rate: float, mix: float = 0.25,
                 threshold_db: float = -28.0, ratio: float = 12.0,
                 attack_ms: float = 0.3, release_ms: float = 60.0):
        self.mix = mix
        self.wet = CompressorCore(threshold_db, ratio, attack_ms, release_ms, sample_rate, makeup_db=6.0)
    def process_block(self, x):
        wet = self.wet.process_block(x)
        return (1.0 - self.mix) * x + self.mix * wet
    def reset(self): self.wet.reset()


class DeEsserBlock(DSPBlock):
    """
    Simple side-chain style de-esser. Codec: deess:902
    For production: replace with true split-band or your custom dynamic EQ.
    """
    name = "deesser"
    codec_key = "deess:902"
    def __init__(self, sample_rate: float, freq: float = 7200.0,
                 threshold_db: float = -22.0, ratio: float = 5.0,
                 attack_ms: float = 0.8, release_ms: float = 45.0):
        self.comp = CompressorCore(threshold_db, ratio, attack_ms, release_ms, sample_rate)
        self.det = _peaking(sample_rate, freq, 6.0, 1.8)
    def process_block(self, x):
        return self.comp.process_block(x)
    def reset(self):
        self.comp.reset()
        self.det.reset()


# =============================================================================
# III. CHARACTER BLOCKS  (Additive EQ + Saturation)
# =============================================================================
#
# ADVICE FOR CUSTOM DSP:
#   AdditiveEQBlock → your Pultec / Neve / API emulation or linear-phase shelves
#   SaturationBlock → tape (Studer, Ampex), tube (Culture Vulture), console,
#                     waveshaper, or neural saturation models.
#   Keep moves small (1–3 dB) and harmonic generation subtle unless density is desired.
# =============================================================================

class AdditiveEQBlock(DSPBlock):
    """Codec: addeq:Pultec"""
    name = "additive_eq"
    codec_key = "addeq:Pultec"
    def __init__(self, sample_rate: float):
        self.warmth   = _lowshelf(sample_rate, 160.0, 1.8)
        self.presence = _peaking(sample_rate, 3200.0, 2.2, 0.9)
        self.air      = _highshelf(sample_rate, 11000.0, 1.5)
    def process_block(self, x):
        x = self.warmth.process_block(x)
        x = self.presence.process_block(x)
        x = self.air.process_block(x)
        return x
    def reset(self):
        self.warmth.reset(); self.presence.reset(); self.air.reset()


class SaturationBlock(DSPBlock):
    """Codec: sat:Vulture"""
    name = "saturation"
    codec_key = "sat:Vulture"
    def __init__(self, drive: float = 1.4, mix: float = 0.22, mode: str = "tape"):
        self.drive = drive
        self.mix = mix
        self.mode = mode
    def process_block(self, x):
        if self.mode == "tape":
            driven = x * self.drive
            sat = np.tanh(driven) / np.tanh(self.drive)
        else:  # tube-ish asymmetric
            driven = x * self.drive
            pos = np.tanh(driven)
            neg = np.tanh(driven * 0.88)
            sat = np.where(driven > 0, pos, neg)
            sat /= (np.max(np.abs(sat)) + 1e-12)
        return (1.0 - self.mix) * x + self.mix * sat
    def reset(self): pass


# =============================================================================
# IV. SPACE BLOCKS  (Delay + Reverb)
# =============================================================================
#
# ADVICE FOR CUSTOM DSP:
#   DelayBlock  → your tape echo, digital delay, or granular delay
#                 (keep HP ~200–300 Hz and LP ~4–6 kHz on the return)
#   ReverbBlock → plate, chamber, hall, or your FDN / convolution / neural reverb
#                 Prefer send/return topology conceptually; pre-delay 20–40 ms
# =============================================================================

class DelayBlock(DSPBlock):
    """Codec: delay:Echoplex"""
    name = "delay"
    codec_key = "delay:Echoplex"
    def __init__(self, sample_rate: float, delay_ms: float = 95.0,
                 feedback: float = 0.22, mix: float = 0.15,
                 hp_freq: float = 250.0, lp_freq: float = 5000.0):
        self.n = max(1, int(delay_ms * 0.001 * sample_rate))
        self.buf = np.zeros(self.n, dtype=np.float64)
        self.w = 0
        self.fb = feedback
        self.mix = mix
        self.hp = _highpass(sample_rate, hp_freq)
        self.lp = _lowpass(sample_rate, lp_freq)
    def process_block(self, x):
        out = np.empty_like(x, dtype=np.float64)
        for i, s in enumerate(x):
            d = self.buf[self.w]
            d = self.hp.process(d)
            d = self.lp.process(d)
            self.buf[self.w] = s + d * self.fb
            self.w = (self.w + 1) % self.n
            out[i] = (1.0 - self.mix) * s + self.mix * d
        return out
    def reset(self):
        self.buf[:] = 0.0
        self.w = 0
        self.hp.reset(); self.lp.reset()


class ReverbBlock(DSPBlock):
    """Simplified Dattorro-style FDN. Codec: rev:EMT140"""
    name = "reverb"
    codec_key = "rev:EMT140"
    def __init__(self, sample_rate: float = 44100.0, decay: float = 0.62,
                 damping: float = 0.45, mix: float = 0.16, predelay_ms: float = 28.0):
        self.mix = mix
        self.decay = decay
        self.damping = damping
        self.pre_n = max(1, int(predelay_ms * 0.001 * sample_rate))
        self.pre_buf = np.zeros(self.pre_n)
        self.pre_i = 0
        lengths = [0.0297, 0.0371, 0.0411, 0.0437, 0.013, 0.019]
        self.delays = [max(1, int(l * sample_rate)) for l in lengths]
        self.bufs = [np.zeros(d) for d in self.delays]
        self.idx = [0] * 6
        self.lp = [0.0] * 4

    def _ap(self, x, buf, i, coeff=0.7):
        delayed = buf[i]
        y = -x + delayed
        buf[i] = x + delayed * coeff
        return y, (i + 1) % len(buf)

    def process_block(self, x):
        out = np.zeros_like(x, dtype=np.float64)
        for i, s in enumerate(x):
            pred = self.pre_buf[self.pre_i]
            self.pre_buf[self.pre_i] = s
            self.pre_i = (self.pre_i + 1) % self.pre_n

            d0, self.idx[4] = self._ap(pred, self.bufs[4], self.idx[4])
            d1, self.idx[5] = self._ap(d0,   self.bufs[5], self.idx[5])

            tank = d1
            for k in range(4):
                delayed = self.bufs[k][self.idx[k]]
                self.lp[k] = (1 - self.damping) * delayed + self.damping * self.lp[k]
                delayed = self.lp[k]
                y = tank + delayed * self.decay
                self.bufs[k][self.idx[k]] = y
                self.idx[k] = (self.idx[k] + 1) % self.delays[k]
                tank = y * 0.5

            wet = sum(self.bufs[k][self.idx[k]] for k in range(4)) * 0.25
            out[i] = (1.0 - self.mix) * s + self.mix * wet
        return out

    def reset(self):
        self.pre_buf[:] = 0; self.pre_i = 0
        for b in self.bufs: b[:] = 0
        self.idx = [0] * 6
        self.lp = [0.0] * 4



# =============================================================================
# V-MOTION. MOTION & NOISE BLOCKS  (from SUPPLEMENTAL ADDENDUM)
# =============================================================================
#
# Dynamic EQ, Noise Gate, Dither — the two missing dimensions.
# The voice moves. The filter must move. The noise is the breath.
# =============================================================================

class DynamicEQBlock(DSPBlock):
    """
    Dynamic EQ with sidechain detection.
    Each band has its own envelope follower and gain computer.
    Codec: dyneq
    """
    name = "dynamic_eq"
    codec_key = "dyneq"

    def __init__(self, sample_rate: float, bands: list = None):
        self.fs = sample_rate
        if bands is None:
            # Default vocal dynamic bands (mud / harsh / presence)
            bands = [
                {"freq": 280.0,  "gain_db": -3.5, "Q": 1.4, "threshold_db": -28.0,
                 "ratio": 3.0, "attack_ms": 5.0, "release_ms": 80.0},
                {"freq": 2200.0, "gain_db": -2.5, "Q": 1.8, "threshold_db": -24.0,
                 "ratio": 4.0, "attack_ms": 2.0, "release_ms": 60.0},
                {"freq": 3200.0, "gain_db":  2.0, "Q": 0.9, "threshold_db": -30.0,
                 "ratio": 2.0, "attack_ms": 10.0, "release_ms": 120.0},
            ]
        self.bands = []
        for b in bands:
            self.bands.append({
                "freq": b["freq"],
                "gain_db": b["gain_db"],
                "Q": b["Q"],
                "threshold": 10 ** (b["threshold_db"] / 20.0),
                "ratio": b["ratio"],
                "atk": np.exp(-1.0 / (b["attack_ms"] * 0.001 * sample_rate)),
                "rel": np.exp(-1.0 / (b["release_ms"] * 0.001 * sample_rate)),
                "env": 0.0,
                "filter": _peaking(sample_rate, b["freq"], b["gain_db"], b["Q"]),
                "detector": _peaking(sample_rate, b["freq"], 0.0, b["Q"]),
            })

    def process(self, x: float) -> float:
        for band in self.bands:
            detected = band["detector"].process(x)
            rectified = abs(detected)
            if rectified > band["env"]:
                band["env"] = band["atk"] * band["env"] + (1 - band["atk"]) * rectified
            else:
                band["env"] = band["rel"] * band["env"] + (1 - band["rel"]) * rectified
            if band["env"] > band["threshold"]:
                gr = (band["threshold"] / band["env"]) ** (1.0 - 1.0 / band["ratio"])
            else:
                gr = 1.0
            current_gain_db = band["gain_db"] * (1.0 - gr)
            band["filter"] = _peaking(self.fs, band["freq"], current_gain_db, band["Q"])
            x = band["filter"].process(x)
        return x

    def process_block(self, x):
        return np.array([self.process(float(s)) for s in x], dtype=np.float64)

    def reset(self):
        for band in self.bands:
            band["env"] = 0.0
            band["filter"].reset()
            band["detector"].reset()


class NoiseGateBlock(DSPBlock):
    """
    Noise gate with hysteresis and hold time.
    Removes noise when the signal is below threshold.
    Codec: gate
    """
    name = "noise_gate"
    codec_key = "gate"

    def __init__(self, sample_rate: float, threshold_db: float = -60.0,
                 attack_ms: float = 1.0, hold_ms: float = 50.0,
                 release_ms: float = 100.0):
        self.threshold = 10 ** (threshold_db / 20.0)
        self.atk = np.exp(-1.0 / (attack_ms * 0.001 * sample_rate))
        self.rel = np.exp(-1.0 / (release_ms * 0.001 * sample_rate))
        self.hold_samples = int(hold_ms * 0.001 * sample_rate)
        self.hold_counter = 0
        self.gain = 1.0

    def process(self, x: float) -> float:
        rectified = abs(x)
        if rectified > self.threshold:
            self.hold_counter = self.hold_samples
            target = 1.0
        elif self.hold_counter > 0:
            self.hold_counter -= 1
            target = 1.0
        else:
            target = 0.0
        if target < self.gain:
            self.gain = self.rel * self.gain + (1 - self.rel) * target
        else:
            self.gain = self.atk * self.gain + (1 - self.atk) * target
        return x * self.gain

    def process_block(self, x):
        return np.array([self.process(float(s)) for s in x], dtype=np.float64)

    def reset(self):
        self.gain = 1.0
        self.hold_counter = 0


class DitherBlock(DSPBlock):
    """
    Dither + optional second-order noise shaping for final bit-depth reduction.
    Codec: dither
    """
    name = "dither"
    codec_key = "dither"

    def __init__(self, target_bits: int = 16, dither_type: str = "tpdf",
                 noise_shaping: bool = True):
        self.target_bits = target_bits
        self.dither_type = dither_type
        self.noise_shaping = noise_shaping
        self.quantization_step = 2.0 / (2 ** target_bits)
        self.error_history = [0.0, 0.0]

    def _generate_dither(self) -> float:
        if self.dither_type == "tpdf":
            return (np.random.rand() - np.random.rand()) * self.quantization_step
        if self.dither_type == "rpdf":
            return (np.random.rand() - 0.5) * self.quantization_step
        return 0.0

    def process(self, x: float) -> float:
        dithered = x + self._generate_dither()
        quantized = np.round(dithered / self.quantization_step) * self.quantization_step
        if self.noise_shaping:
            error = dithered - quantized
            shaped = error - 2 * self.error_history[0] + self.error_history[1]
            self.error_history[1] = self.error_history[0]
            self.error_history[0] = error
            quantized = quantized + shaped
        return quantized

    def process_block(self, x):
        return np.array([self.process(float(s)) for s in x], dtype=np.float64)

    def reset(self):
        self.error_history = [0.0, 0.0]



class AutomatedEQBlock(DSPBlock):
    """
    EQ with automation curve.
    Gain of each band is interpolated over time according to control points.
    Codec: autoeq  (optional — inject via replace_stage or custom)
    """
    name = "automated_eq"
    codec_key = "autoeq"

    def __init__(self, sample_rate: float, bands: list = None,
                 automation: dict = None, duration_samples: int = 44100):
        self.fs = sample_rate
        if bands is None:
            bands = [
                {"freq": 160.0,  "Q": 0.7, "base_gain_db": 0.5, "max_gain_db": 2.0},
                {"freq": 3200.0, "Q": 0.9, "base_gain_db": 1.0, "max_gain_db": 3.0},
                {"freq": 11000.0,"Q": 0.7, "base_gain_db": 0.5, "max_gain_db": 2.0},
            ]
        self.bands = []
        for b in bands:
            self.bands.append({
                "freq": b["freq"],
                "Q": b["Q"],
                "base_gain_db": b["base_gain_db"],
                "max_gain_db": b["max_gain_db"],
                "filter": _peaking(sample_rate, b["freq"], b["base_gain_db"], b["Q"]),
            })
        self.automation = automation or {}
        self.duration = max(1, duration_samples)
        self.sample_index = 0

    def _interpolate(self, points, t):
        if not points:
            return 0.0
        if t <= points[0][0]:
            return points[0][1]
        if t >= points[-1][0]:
            return points[-1][1]
        for i in range(len(points) - 1):
            t0, v0 = points[i]
            t1, v1 = points[i + 1]
            if t0 <= t <= t1:
                frac = (t - t0) / (t1 - t0) if t1 != t0 else 0.0
                return v0 + frac * (v1 - v0)
        return points[-1][1]

    def process(self, x: float) -> float:
        t = self.sample_index / self.duration
        for i, band in enumerate(self.bands):
            if i in self.automation:
                gain_fraction = self._interpolate(self.automation[i], t)
                current_gain_db = (band["base_gain_db"] +
                                   (band["max_gain_db"] - band["base_gain_db"]) * gain_fraction)
            else:
                current_gain_db = band["base_gain_db"]
            band["filter"] = _peaking(self.fs, band["freq"], current_gain_db, band["Q"])
            x = band["filter"].process(x)
        self.sample_index += 1
        return x

    def process_block(self, x):
        return np.array([self.process(float(s)) for s in x], dtype=np.float64)

    def reset(self):
        self.sample_index = 0
        for band in self.bands:
            band["filter"].reset()


class FormantTrackingEQBlock(DSPBlock):
    """
    EQ that tracks fundamental frequency and shifts formant bands.
    Simple autocorrelation pitch detector.
    Codec: formant  (optional — inject via replace_stage or custom)
    """
    name = "formant_tracking_eq"
    codec_key = "formant"

    def __init__(self, sample_rate: float, formants: list = None,
                 min_f0: float = 80.0, max_f0: float = 400.0):
        self.fs = sample_rate
        if formants is None:
            formants = [
                {"freq": 500.0,  "Q": 1.0, "gain_db": 1.5},
                {"freq": 1500.0, "Q": 1.2, "gain_db": 2.0},
                {"freq": 2500.0, "Q": 1.0, "gain_db": 1.0},
            ]
        self.formants = []
        for f in formants:
            self.formants.append({
                "base_freq": f["freq"],
                "Q": f["Q"],
                "gain_db": f["gain_db"],
                "filter": _peaking(sample_rate, f["freq"], f["gain_db"], f["Q"]),
            })
        self.min_f0 = min_f0
        self.max_f0 = max_f0
        self.buffer = np.zeros(2048)
        self.buf_idx = 0

    def _detect_pitch(self) -> float:
        window = self.buffer[-1024:]
        window = window - np.mean(window)
        if np.max(np.abs(window)) < 1e-6:
            return 0.0
        corr = np.correlate(window, window, mode="full")
        corr = corr[len(corr)//2:]
        min_lag = int(self.fs / self.max_f0)
        max_lag = int(self.fs / self.min_f0)
        if max_lag >= len(corr):
            return 0.0
        peak_lag = np.argmax(corr[min_lag:max_lag]) + min_lag
        if peak_lag == 0:
            return 0.0
        return self.fs / peak_lag

    def process(self, x: float) -> float:
        self.buffer[self.buf_idx] = x
        self.buf_idx = (self.buf_idx + 1) % len(self.buffer)
        if self.buf_idx % 512 == 0:
            f0 = self._detect_pitch()
            if f0 > 0:
                for formant in self.formants:
                    ratio = f0 / 175.0
                    new_freq = formant["base_freq"] * ratio
                    formant["filter"] = _peaking(
                        self.fs, new_freq, formant["gain_db"], formant["Q"]
                    )
        for formant in self.formants:
            x = formant["filter"].process(x)
        return x

    def process_block(self, x):
        return np.array([self.process(float(s)) for s in x], dtype=np.float64)

    def reset(self):
        self.buffer[:] = 0.0
        self.buf_idx = 0
        for formant in self.formants:
            formant["filter"].reset()


class NoiseFloorAnalyzer:
    """
    Analyzes noise floor of an audio signal.
    Returns overall dBFS and per-band spectrum of the quietest window.
    Utility — not a DSPBlock in the chain.
    """
    def __init__(self, sample_rate: float, fft_size: int = 4096):
        self.fs = sample_rate
        self.fft_size = fft_size

    def analyze(self, x: np.ndarray) -> dict:
        window_size = self.fft_size
        num_windows = len(x) // window_size
        min_energy = np.inf
        quietest = None
        for i in range(num_windows):
            window = x[i * window_size:(i + 1) * window_size]
            energy = np.sum(window ** 2)
            if energy < min_energy:
                min_energy = energy
                quietest = window
        if quietest is None:
            return {"overall_db": -np.inf, "bands": []}
        spectrum = np.fft.rfft(quietest * np.hanning(window_size))
        magnitude = np.abs(spectrum) / window_size
        db = 20 * np.log10(magnitude + 1e-12)
        overall_db = 20 * np.log10(np.sqrt(min_energy / window_size) + 1e-12)
        freqs = np.fft.rfftfreq(window_size, 1.0 / self.fs)
        return {"overall_db": overall_db, "bands": list(zip(freqs, db))}


    def _generate_dither(self) -> float:
        if self.dither_type == "tpdf":
            return (np.random.rand() - np.random.rand()) * self.quantization_step
        if self.dither_type == "rpdf":
            return (np.random.rand() - 0.5) * self.quantization_step
        return 0.0

    def process(self, x: float) -> float:
        dithered = x + self._generate_dither()
        quantized = np.round(dithered / self.quantization_step) * self.quantization_step
        if self.noise_shaping:
            error = dithered - quantized
            shaped = error - 2 * self.error_history[0] + self.error_history[1]
            self.error_history[1] = self.error_history[0]
            self.error_history[0] = error
            quantized = quantized + shaped
        return quantized

    def process_block(self, x):
        return np.array([self.process(float(s)) for s in x], dtype=np.float64)

    def reset(self):
        self.error_history = [0.0, 0.0]


# =============================================================================
# V. GLUE / MASTER BLOCK
# =============================================================================
#
# ADVICE FOR CUSTOM DSP:
#   Replace LookAheadLimiterBlock with your preferred brickwall / true-peak
#   limiter, or a soft clipper + final bus compressor.
#   Loudness targets remain: streaming ≈ −14 LUFS, preserve dynamics.
# =============================================================================

class LookAheadLimiterBlock(DSPBlock):
    """Codec: lim:Weiss"""
    name = "limiter"
    codec_key = "lim:Weiss"
    def __init__(self, sample_rate: float, ceiling_db: float = -0.5,
                 lookahead_ms: float = 5.0, release_ms: float = 80.0):
        self.ceiling = 10 ** (ceiling_db / 20.0)
        self.n = max(1, int(lookahead_ms * 0.001 * sample_rate))
        self.buf = np.zeros(self.n)
        self.rel = np.exp(-1.0 / (release_ms * 0.001 * sample_rate))
        self.gain = 1.0

    def process(self, x: float) -> float:
        self.buf = np.roll(self.buf, 1)
        self.buf[0] = abs(x)
        peak = np.max(self.buf)
        target = self.ceiling / peak if peak > self.ceiling else 1.0
        if target < self.gain:
            self.gain = target
        else:
            self.gain = self.rel * self.gain + (1 - self.rel) * target
        return x * self.gain

    def process_block(self, x):
        return np.array([self.process(float(s)) for s in x], dtype=np.float64)

    def reset(self):
        self.buf[:] = 0.0
        self.gain = 1.0


# =============================================================================
# VI. THE ORDER — orchestrator
# =============================================================================

class TheOrder:
    """
    Full modular chain. Stages are stored in a dict and executed in fixed order.

    Codec keys are attached to every stage so hardware emulation targets are explicit:
      pre:U47>1073>Lavry>Genesys|hp|subeq:550A|fastcomp:1176|slowcomp:LA2A|
      deess:902|addeq:Pultec|sat:Vulture|delay:Echoplex|rev:EMT140|bus:SSL|lim:Weiss

    To inject custom DSP after construction:
        chain.replace_stage("fast_comp", MyCustom1176())   # still uses stage name
        # the codec_key travels with the block if you set it on your class

    Or pass overrides at init:
        chain = TheOrder(sample_rate, custom={"saturation": MyTapeModel()})
    """

    # Canonical execution order (do not reorder unless you know why)
    STAGE_ORDER = [
        "highpass",        # hp
        "subtractive_eq",  # subeq:550A
        "noise_gate",      # gate
        "fast_comp",       # fastcomp:1176
        "slow_comp",       # slowcomp:LA2A
        "parallel_comp",   # optional density
        "deesser",         # deess:902
        "dynamic_eq",      # dyneq
        "additive_eq",     # addeq:Pultec
        "saturation",      # sat:Vulture
        "delay",           # delay:Echoplex
        "reverb",          # rev:EMT140
        "limiter",         # lim:Weiss
        "dither",          # dither
    ]

    def __init__(self, sample_rate: float = 44100.0,
                 voice_type: str = "male",
                 enable_parallel: bool = True,
                 custom: Optional[Dict[str, DSPBlock]] = None):
        self.fs = sample_rate
        self.voice_type = voice_type
        custom = custom or {}

        hp_cut = 85.0 if voice_type == "male" else 100.0
        deess_f = 7200.0 if voice_type == "male" else 8200.0

        # Default blocks (each already carries its codec_key)
        defaults: Dict[str, DSPBlock] = {
            "highpass":       HighPassBlock(sample_rate, hp_cut),
            "subtractive_eq": SubtractiveEQBlock(sample_rate),
            "noise_gate":     NoiseGateBlock(sample_rate),
            "fast_comp":      FastCompBlock(sample_rate),
            "slow_comp":      SlowCompBlock(sample_rate),
            "parallel_comp":  ParallelCompressorBlock(sample_rate) if enable_parallel else _Bypass(),
            "deesser":        DeEsserBlock(sample_rate, freq=deess_f),
            "dynamic_eq":     DynamicEQBlock(sample_rate),
            "additive_eq":    AdditiveEQBlock(sample_rate),
            "saturation":     SaturationBlock(drive=1.4, mix=0.22, mode="tape"),
            "delay":          DelayBlock(sample_rate),
            "reverb":         ReverbBlock(sample_rate),
            "limiter":        LookAheadLimiterBlock(sample_rate),
            "dither":         DitherBlock(target_bits=16, noise_shaping=True),
        }

        # Apply user overrides
        for name, block in custom.items():
            if name not in defaults:
                raise KeyError(f"Unknown stage '{name}'. Valid: {list(defaults)}")
            # Ensure codec_key is set if the custom block omitted it
            if not getattr(block, "codec_key", ""):
                block.codec_key = CODEC_KEYS.get(name, name)
            defaults[name] = block

        self.stages: Dict[str, DSPBlock] = defaults

    def replace_stage(self, name: str, block: DSPBlock) -> None:
        """Hot-swap any stage with your custom DSP. Codec key is preserved or inherited."""
        if name not in self.stages:
            raise KeyError(f"Unknown stage '{name}'")
        if not getattr(block, "codec_key", ""):
            block.codec_key = CODEC_KEYS.get(name, name)
        self.stages[name] = block
        print(f"[TheOrder] Stage '{name}' ({block.codec_key}) ← {block.__class__.__name__}")

    def disable_stage(self, name: str) -> None:
        self.replace_stage(name, _Bypass())

    def process(self, audio: np.ndarray) -> np.ndarray:
        """Run the full immutable order."""
        x = np.asarray(audio, dtype=np.float64).copy()
        if x.ndim > 1:
            x = x.mean(axis=1)  # mono for this version

        for name in self.STAGE_ORDER:
            x = self.stages[name].process_block(x)

        return np.clip(x, -1.0, 1.0)

    def reset(self) -> None:
        for b in self.stages.values():
            b.reset()

    def summary(self) -> str:
        lines = ["THE ORDER — current pipeline (stage → codec_key → class):"]
        for i, name in enumerate(self.STAGE_ORDER, 1):
            blk = self.stages[name]
            key = getattr(blk, "codec_key", CODEC_KEYS.get(name, "?"))
            lines.append(f"  {i:02d}. {name:<16} [{key:<18}] → {blk.__class__.__name__}")
        lines.append("")
        lines.append(f"CODEC_STRING = {CODEC_STRING}")
        return "\n".join(lines)

    def codec_map(self) -> Dict[str, str]:
        """Return {stage_name: codec_key} for the live pipeline."""
        return {
            name: getattr(self.stages[name], "codec_key", CODEC_KEYS.get(name, name))
            for name in self.STAGE_ORDER
        }


class _Bypass(DSPBlock):
    name = "bypass"
    codec_key = "bypass"
    def process_block(self, x): return x


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("THE ORDER — Modular Vocal Chain (Codec Keys Embedded)")
    print("Source first. Then correction. Then control.")
    print("Then character. Then space. Then glue.")
    print("=" * 70)
    print()
    print("CODEC_STRING:")
    print(" ", CODEC_STRING)
    print()

    fs = 44100
    t = np.linspace(0, 1.5, int(fs * 1.5), endpoint=False)

    # Synthetic vocal-ish test tone with formants + envelope
    voice = (0.40 * np.sin(2 * np.pi * 175 * t) +
             0.22 * np.sin(2 * np.pi * 520 * t) +
             0.14 * np.sin(2 * np.pi * 2100 * t) +
             0.08 * np.sin(2 * np.pi * 3400 * t))
    env = np.exp(-t * 1.1) * (0.55 + 0.45 * np.sin(2 * np.pi * 2.8 * t))
    voice = (voice * env + 0.015 * np.random.randn(len(t)))
    voice /= np.max(np.abs(voice)) + 1e-12
    voice *= 0.65

    chain = TheOrder(sample_rate=fs, voice_type="male", enable_parallel=True)
    print(chain.summary())
    print()

    out = chain.process(voice)
    print(f"Input peak  : {np.max(np.abs(voice)):.4f}")
    print(f"Output peak : {np.max(np.abs(out)):.4f}")
    print("Chain executed successfully.")
    print()
    print("Codec map:", chain.codec_map())
    print()
    print("To inject custom DSP (codec key is auto-attached if missing):")
    print('  chain.replace_stage("saturation", MyCustomVulture())  # sat:Vulture')
    print('  chain.replace_stage("reverb", MyEMT140())             # rev:EMT140')
