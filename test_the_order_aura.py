#!/usr/bin/env python3
"""Gates for the AURA replacement stages in THE ORDER. Run: python test_the_order_aura.py  (exit 0 = all pass)"""
import os, sys
import numpy as np
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import the_order_vocal_chain as O
import the_order_aura as A

FS = 44100
results = []
def gate(name, ok, detail):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}"); results.append(bool(ok))

def tp_dbtp(y): return 20 * np.log10(np.max(np.abs(signal.resample_poly(y, 4, 1))) + 1e-30)
def resid(y, f0, fs=FS):
    seg = y[len(y) // 4:]; N = len(seg); S = np.abs(np.fft.rfft(seg * signal.windows.blackmanharris(N))) ** 2; f = np.fft.rfftfreq(N, 1 / fs)
    m = np.ones(len(f), bool)
    for k in range(0, int(fs / 2 / f0) + 2): m &= abs(f - k * f0) > 25
    i = np.argmin(abs(f - f0)); return 10 * np.log10(S[m].sum() / S[i - 3:i + 4].sum() + 1e-30)
def harm(y, f0, k, fs=FS):
    seg = y[len(y) // 4:]; N = len(seg); S = np.abs(np.fft.rfft(seg * signal.windows.blackmanharris(N))) ** 2; f = np.fft.rfftfreq(N, 1 / fs)
    L = lambda j: S[np.argmin(abs(f - j * f0)) - 3:np.argmin(abs(f - j * f0)) + 4].sum(); return 10 * np.log10(L(k) / L(1) + 1e-30)
def band(e, a, b):
    f, P = signal.welch(e, FS, nperseg=2 ** 14); return 10 * np.log10(np.mean(P[(f >= a) & (f <= b)]) + 1e-40)

print("== SATURATION (A=0.9, 1013 Hz) ==")
t = np.arange(FS * 2) / FS; x = 0.9 * np.sin(2 * np.pi * 1013 * t)
stock = O.SaturationBlock().process_block(x); aura = A.VantageSaturationBlock(FS).process_block(x)
stress = A.VantageSaturationBlock(FS, a=6.0, mix=1.0).process_block(x)
print(f"  stock tape: H2={harm(stock,1013,2):.1f} H3={harm(stock,1013,3):.1f} dBc | aura default: H2={harm(aura,1013,2):.1f} H3={harm(aura,1013,3):.1f} dBc")
gate("even-order content added (aura H2 > stock H2 + 20 dB)", harm(aura, 1013, 2) > harm(stock, 1013, 2) + 20, f"{harm(aura,1013,2):.1f} vs {harm(stock,1013,2):.1f} dBc")
gate("alias residual <= -90 dBc at a=6, mix=1", resid(stress, 1013) <= -90, f"{resid(stress,1013):.1f} dBc")
small = 0.01 * np.sin(2 * np.pi * 1000 * t); g = 20 * np.log10(np.std(A.VantageSaturationBlock(FS).process_block(small)[FS // 2:]) / np.std(small[FS // 2:]))
gate("unity small-signal gain within 0.1 dB", abs(g) < 0.1, f"{g:+.3f} dB")
dc = abs(np.mean(stress[FS:])); gate("DC after blocker < 1e-3 (a=6, mix=1)", dc < 1e-3, f"{dc:.2e}")

print("\n== LIMITER (ceiling -1.0 dBTP) ==")
tt = np.arange(FS) / FS; hot = 1.6 * np.sin(2 * np.pi * (FS / 4 * 0.97) * tt + 0.5) + 0.3 * np.sin(2 * np.pi * 1013 * tt)
lim = A.TruePeakLimiterBlock(FS); y = lim.process_block(hot); ys = O.LookAheadLimiterBlock(FS).process_block(hot)
print(f"  stock: {tp_dbtp(ys):.2f} dBTP (ceiling -0.5 sample peak) | aura: {tp_dbtp(y):.2f} dBTP")
gate("true peak <= -0.95 dBTP on hot signal", tp_dbtp(y) <= -0.95, f"{tp_dbtp(y):.2f} dBTP")
quiet = 0.5 * np.sin(2 * np.pi * 440 * tt); gate("bit-exact below ceiling", np.array_equal(lim.process_block(quiet), quiet), "unchanged")
n = FS // 4; z = 0.05 * np.sin(2 * np.pi * 300 * np.arange(n) / FS); n0 = n // 2; z[n0] = 2.0; yz = lim.process_block(z)
g10 = yz[n0 - 10] / z[n0 - 10]; gate("real look-ahead (gain already reduced 10 samples before a spike)", g10 < 0.98, f"gain {g10:.3f} (stock: 1.000)")
gate("limiter declares latency", lim.latency_samples == int(5e-3 * FS), f"{lim.latency_samples} samples")

print("\n== DITHER (16-bit, -60 dBFS 1 kHz) ==")
d = 10 ** (-60 / 20) * np.sin(2 * np.pi * 1000 * t); np.random.seed(1)
ys = O.DitherBlock(16, noise_shaping=True).process_block(d); yp = A.ProDitherBlock(FS).process_block(d); yf = A.ProDitherBlock(FS, shaping="none").process_block(d)
grid = lambda y, q: np.mean(np.abs(y * q - np.round(y * q)) < 1e-6)
print(f"  on-grid fraction: stock {grid(ys, 32768):.3f} | aura {grid(yp, 32767):.3f}")
gate("100% of samples on the 16-bit grid", grid(yp, 32767) > 0.9999, f"{grid(yp,32767):.4f}")
e1, e0 = band(yp - d, 1000, 5000), band(yf - d, 1000, 5000)
gate("1-5 kHz floor >= 10 dB below flat TPDF", e1 <= e0 - 10, f"{e1-e0:+.1f} dB (stock shaped: {band(ys-d,1000,5000)-band(yf-d,1000,5000):+.1f} dB)")

print("\n== END TO END (3 s voice-like, hot) ==")
rng = np.random.default_rng(0); n = int(FS * 3); tv = np.arange(n) / FS
voice = 0.40 * np.sin(2 * np.pi * 175 * tv) + 0.22 * np.sin(2 * np.pi * 520 * tv) + 0.14 * np.sin(2 * np.pi * 2100 * tv) + 0.08 * np.sin(2 * np.pi * 3400 * tv)
voice = voice * (0.55 + 0.45 * np.sin(2 * np.pi * 2.8 * tv)) + 0.01 * rng.standard_normal(n); voice *= 0.95 / np.max(np.abs(voice))
runs = []
for _ in range(2):
    np.random.seed(0); chain = O.TheOrder(float(FS), "male", custom=A.aura_stages(FS)); runs.append(chain.process(voice))
out = runs[0]; print(chain.summary().splitlines()[1:15] and "\n".join(l for l in chain.summary().splitlines() if any(k in l for k in ("saturation", "limiter", "dither"))))
gate("finite output", np.all(np.isfinite(out)), "ok")
gate("true peak <= -0.95 dBTP at the chain output", tp_dbtp(out) <= -0.95, f"{tp_dbtp(out):.2f} dBTP")
gate("16-bit grid at the chain output", grid(out, 32767) > 0.9999, f"{grid(out,32767):.4f}")
gate("deterministic (same seed -> identical)", np.array_equal(runs[0], runs[1]), "identical" if np.array_equal(runs[0], runs[1]) else f"max diff {np.max(abs(runs[0]-runs[1])):.2e}")
print(f"\nSUMMARY: {sum(results)}/{len(results)} gates passed")
sys.exit(0 if all(results) else 1)
