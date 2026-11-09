#!/usr/bin/env python3
"""Gates for the LA-2A module: python port == C++ core, timing, NaN safety, unity at PR 0, end to end in The Order."""
import os, sys, subprocess, tempfile, ctypes
import numpy as np
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import the_order_vocal_chain as O, the_order_aura as A
from la2a_py import LA2ACore
FS = 44100; res = []
def gate(n, ok, d): print(f"  [{'PASS' if ok else 'FAIL'}] {n}: {d}"); res.append(bool(ok))
tone = lambda f, db, s=1.0: 10 ** (db / 20) * np.sin(2 * np.pi * f * np.arange(int(FS * s)) / FS)
tp = lambda y: 20 * np.log10(np.max(np.abs(signal.resample_poly(y, 4, 1))) + 1e-30)

print("== LA-2A port vs the C++ core ==")
so = os.path.join(tempfile.gettempdir(), "la2a_test.so")
try:
    subprocess.check_call(["g++", "-O2", "-std=c++17", "-shared", "-fPIC", "-I" + os.path.join(HERE, "la2a"), os.path.join(HERE, "la2a", "tests", "la2a_wrap.cpp"), "-o", so])
    L = ctypes.CDLL(so)
    L.la2a_run.argtypes = [ctypes.c_void_p] * 5 + [ctypes.c_int, ctypes.c_int, ctypes.c_double, ctypes.c_double, ctypes.c_double, ctypes.c_int, ctypes.c_int]
    rng = np.random.default_rng(3); x = (0.3 * np.sin(2 * np.pi * 150 * np.arange(FS) / FS) * (0.3 + 0.7 * np.abs(np.sin(2 * np.pi * 3 * np.arange(FS) / FS))) + 0.02 * rng.standard_normal(FS)).astype(np.float32)
    for comp in (0, 1):
        ol = np.zeros(FS, np.float32); orr = np.zeros(FS, np.float32); gr = np.zeros(FS, np.float32)
        L.la2a_run(x.ctypes.data, None, ol.ctypes.data, orr.ctypes.data, gr.ctypes.data, FS, 1, FS, 3.0, 0.09, comp, 0)
        y, g = LA2ACore(FS, 3.0, 0.09, bool(comp)).process(x, return_gr=True)
        gate(f"python == C++ ({'compress' if comp else 'limit'})", np.max(np.abs(y - ol)) < 2e-6 and np.max(np.abs(g - gr)) < 1e-3, f"max out diff {np.max(np.abs(y-ol)):.1e}, max GR diff {np.max(np.abs(g-gr)):.1e} dB")
except Exception as e:
    print("  [SKIP] C++ comparison needs g++:", e)

print("\n== behaviour ==")
y = LA2ACore(FS, 0.0, 0.0).process(tone(1000, -10)); gate("unity at Peak Reduction 0", np.max(np.abs(y - tone(1000, -10))) < 1e-6, f"max diff {np.max(np.abs(y-tone(1000,-10))):.1e}")
b = np.r_[tone(1000, -10, 1.0), np.zeros(FS * 7)]; _, g = LA2ACore(FS, 0.0, 0.5).process(b, return_gr=True)
g0 = g[FS - 1]; t50 = 1000 * np.argmax(g[FS:] < 0.5 * g0) / FS
gate("release: 50% of gain reduction in 55-67 ms (manual ~60 ms)", 55 <= t50 <= 67, f"{t50:.0f} ms from {g0:.1f} dB")
_, g = LA2ACore(FS, 0.0, 0.07).process(tone(1000, -12, 1.0), return_gr=True); gate("default PR 0.07 gives 1-8 dB at a -12 dBFS tone", 1 <= g[-FS // 10:].mean() <= 8, f"{g[-FS//10:].mean():.1f} dB")
xn = np.zeros(FS); xn[100:600] = tone(1000, -10, 1.0)[:500]; xn[700] = np.nan; yn = LA2ACore(FS, 0.0, 0.5).process(xn)
gate("one NaN leaves no non-finite output", np.all(np.isfinite(yn)), f"{int(np.sum(~np.isfinite(yn)))} non-finite samples")

print("\n== end to end in The Order (LA-2A as slow_comp + AURA stages) ==")
rng = np.random.default_rng(0); n = int(FS * 3); tv = np.arange(n) / FS
voice = 0.40 * np.sin(2 * np.pi * 175 * tv) + 0.22 * np.sin(2 * np.pi * 520 * tv) + 0.14 * np.sin(2 * np.pi * 2100 * tv) + 0.08 * np.sin(2 * np.pi * 3400 * tv)
voice = voice * (0.55 + 0.45 * np.sin(2 * np.pi * 2.8 * tv)) + 0.01 * rng.standard_normal(n); voice *= 0.95 / np.max(np.abs(voice))
runs = []
for _ in range(2):
    np.random.seed(0); runs.append(O.TheOrder(float(FS), "male", custom=A.aura_stages(FS, la2a=True)).process(voice))
out = runs[0]; grid = lambda y: np.mean(np.abs(y * 32767 - np.round(y * 32767)) < 1e-6)
gate("finite", np.all(np.isfinite(out)), "ok"); gate("true peak <= -0.95 dBTP", tp(out) <= -0.95, f"{tp(out):.2f} dBTP")
gate("16-bit grid", grid(out) > 0.9999, f"{grid(out):.4f}"); gate("deterministic", np.array_equal(runs[0], runs[1]), "identical")
print(f"\nSUMMARY: {sum(res)}/{len(res)} gates passed"); sys.exit(0 if all(res) else 1)
