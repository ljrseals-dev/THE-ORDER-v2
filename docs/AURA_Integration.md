# AURA integration (stages 10, 13, 14)

```python
import the_order_vocal_chain as O, the_order_aura as A
chain = O.TheOrder(44100.0, "male", custom=A.aura_stages(44100.0))
```

| Stage | Replacement | Why |
|---|---|---|
| 10 saturation | `VantageSaturationBlock` (biased tanh at 4x, DC-blocked, unity small-signal gain) | adds even-order content; alias residual at the measurement floor (about -102 dBc at a=6) |
| 13 limiter | `TruePeakLimiterBlock` (real look-ahead, 4x true-peak detection, default -1.0 dBTP) | the stock limiter has no look-ahead (buffer holds past samples only) and reached +0.53 dBTP against a -0.5 ceiling |
| 14 dither | `ProDitherBlock` (TPDF + Lipshitz feedback, subtracted) | the stock noise-shaped path never quantises (0% on the 16-bit grid) and does not lower the 1-5 kHz floor |

Run the gates: `python test_the_order_aura.py` (14 gates, exit code 0 = pass). Needs numpy and scipy.

Offline processing. Real-time latency to report: Vantage 60 samples, limiter 220 samples at 44.1 kHz.
ProDither quantises to k/32767 (x32767 export). The Order has no make-up gain, so the end-to-end test does not
push the limiter; the limiter is verified at stage level on a hot signal.

## LA-2A module (optional, stage "slow_comp")

```python
chain = O.TheOrder(44100.0, "male", custom=A.aura_stages(44100.0, la2a=True))
```

`LA2ASlowCompBlock` runs the manual-faithful LA-2A behavioral core (`la2a/la2a_core.h`, ported to `la2a_py.py` and checked
sample-for-sample against the C++). It replaces the stock `slow_comp`, which only claimed LA-2A style.
Measured: attack to 90% in 0.15 ms, 50% release in 61 ms, below 1 dB after 5.2 s, no memory of burst length.
**Peak Reduction is steep**: 0.04-0.10 gives about 1-6 dB at vocal peaks, while 0.5 is about 30 dB. Base gain is unity (use gain_db).
Known: about 4.4% THD at 30 Hz, 1.7% at 100 Hz, 0.2% at 1 kHz under heavy limiting; unvalidated against hardware.
NaN fix applied to `la2a_core.h`. Run `python test_la2a_block.py` (10 gates).
