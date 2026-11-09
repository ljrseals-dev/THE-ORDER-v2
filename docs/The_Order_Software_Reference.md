# THE ORDER — Software Architecture Reference

**CASE FILE 22-EAR-4**  
**Classification:** THE ORDER — SOFTWARE EXECUTION LAYER  
**Status:** FINAL  
**Artifact:** `/home/workdir/artifacts/The_Order_Software_Reference.md`  
**Companion:** `/home/workdir/artifacts/Hardware_Codec_Mapping.md`  
**Source module:** `the_order_vocal_chain.py`

This is the official software architecture reference for the modular vocal processing chain. It is written so that any runtime — Python, C++, Rust, JavaScript/TypeScript, or a future binding — can implement the same contract, the same stage order, and the same numeric philosophy without ambiguity.

---

## 1. COLD OPEN

The hardware chain is the instrument.  
The software chain is the performance of that instrument under digital law.

Fourteen physical units — Neumann U 47 through Weiss DS1-MK3 — define the perfect order. The modular DSP architecture executes that order as eleven named stages plus an optional parallel density path. The stages do not invent a new philosophy; they translate the existing one into floating-point arrays.

Six acts remain sacred:

```
SOURCE → CORRECTION → CONTROL → CHARACTER → SPACE → AUTOMATION → GLUE
```

In software the first act lives outside the process loop (capture is irreversible). The remaining acts are the `STAGE_ORDER` list. Reordering the list breaks the reference. Replacing the contents of any stage is the entire point of the architecture.

The contract is language-agnostic. The numbers are not.

---

## 2. STAGE CONTRACT SPEC (LANGUAGE-AGNOSTIC)

Every processing unit implements the same abstract surface.

```
INTERFACE DSPBlock
    name       : string          # stable stage identifier
    codec_key  : string          # hardware alias, e.g. "fastcomp:1176"
    process_block(x : float_array) → float_array
    reset() → void
```

### Invariants

| Rule | Requirement |
|------|-------------|
| Dimensionality | Mono. Input and output are 1-D. |
| Shape | Output length equals input length. |
| Numeric domain | Nominal range [−1, 1]. Overshoot is permitted; final clip is the orchestrator’s responsibility. |
| State | Any delay line, envelope, or coefficient memory must be clearable by `reset()`. |
| Allocation | No hidden per-sample heap allocation inside the hot path unless the port documents it as non-RT. |
| Threading | Single-threaded by default. Real-time ports must document locking or lock-free design. |
| Sample rate | Captured at construction. Changing sample rate requires a new instance (or an explicit `set_sample_rate` extension). |

A block that violates shape preservation or fails to expose `reset()` is non-conformant.

---

## 3. FULL BLOCK TABLE

| Order | Stage Name       | Block Class                 | Act        | Purpose                              | Key Parameters (defaults)                          | Statefulness | Replaceable |
|-------|------------------|-----------------------------|------------|--------------------------------------|----------------------------------------------------|--------------|-------------|
| 1     | `highpass`       | `HighPassBlock`             | Correction | Remove subsonic / plosive energy     | cutoff 85 Hz (male) / 100 Hz (female), Q 0.707     | Yes (biquad) | Yes         |
| 2     | `subtractive_eq` | `SubtractiveEQBlock`        | Correction | Narrow cuts: mud, harsh, pre-sib     | 280 Hz −3.5 dB; 2.2 kHz −2.5 dB; 6.5 kHz −2.0 dB   | Yes (3 biquads) | Yes      |
| 3     | `fast_comp`      | `FastCompBlock`             | Control    | FET-style peak control (1176)        | thresh −16 dB, ratio 4:1, atk 0.4 ms, rel 80 ms    | Yes (envelope) | Yes       |
| 4     | `slow_comp`      | `SlowCompBlock`             | Control    | Opto-style level consistency (LA-2A) | thresh −18 dB, ratio 2.5:1, atk 15 ms, rel 280 ms, makeup +1.5 dB | Yes | Yes |
| 5     | `parallel_comp`  | `ParallelCompressorBlock`   | Control    | Optional density path                | mix 0.25, thresh −28 dB, ratio 12:1, atk 0.3 ms, rel 60 ms | Yes | Yes (or disable) |
| 6     | `deesser`        | `DeEsserBlock`              | Control    | Sibilance control after compression  | freq 7.2 kHz (male) / 8.2 kHz (female), thresh −22 dB, ratio 5:1 | Yes | Yes |
| 7     | `additive_eq`    | `AdditiveEQBlock`           | Character  | Broad musical boosts (Pultec-style)  | 160 Hz +1.8 dB shelf; 3.2 kHz +2.2 dB; 11 kHz +1.5 dB shelf | Yes | Yes |
| 8     | `saturation`     | `SaturationBlock`           | Character  | Harmonic enrichment                  | drive 1.4, mix 0.22, mode “tape”                   | No           | Yes         |
| 9     | `delay`          | `DelayBlock`                | Space      | Filtered rhythmic / slap delay       | 95 ms, feedback 0.22, mix 0.15, HP 250 Hz, LP 5 kHz | Yes (buffer) | Yes      |
| 10    | `reverb`         | `ReverbBlock`               | Space      | Dattorro-style FDN plate             | decay 0.62, damping 0.45, mix 0.16, predelay 28 ms | Yes (FDN)    | Yes         |
| 11    | `limiter`        | `LookAheadLimiterBlock`     | Glue       | Final peak control                   | ceiling −0.5 dB, lookahead 5 ms, release 80 ms     | Yes (buffer + envelope) | Yes |
| —     | `_Bypass`        | `_Bypass`                   | —          | Identity (used by `disable_stage`)   | none                                               | No           | Internal    |

`parallel_comp` is optional density and may be disabled without breaking the reference. All other stages in `STAGE_ORDER` are required for conformance.

---

## 4. BLOCK-BY-BLOCK REFERENCE

### 4.1 `HighPassBlock` — `name = "highpass"` · `codec_key = "hp"`

**Constructor**  
`HighPassBlock(sample_rate, cutoff=85.0, Q=0.707)`

**Primitives**  
`_highpass` → `BiquadFilter` (Direct-Form I)

**Signal path**  
Second-order high-pass. Removes energy below cutoff.

**Safe ranges**  
cutoff 40–150 Hz; Q 0.5–1.0. Outside this range risk of either thinning the voice or incomplete rumble removal.

**Failure modes**  
- Cutoff too high → thin, brittle vocal  
- Linear-phase substitution without documenting pre-ring → smeared plosives

**Custom DSP hook**  
Replace with any HPF (FIR, linear-phase, dynamic) that preserves length and exposes `reset()`.

**Hardware origin**  
Console / API 550A HPF section. See Hardware Codec Mapping Act II.

---

### 4.2 `SubtractiveEQBlock` — `name = "subtractive_eq"` · `codec_key = "subeq:550A"`

**Constructor**  
`SubtractiveEQBlock(sample_rate)`

**Primitives**  
Three `_peaking` biquads: mud 280 Hz −3.5 dB Q 1.4; harsh 2200 Hz −2.5 dB Q 1.8; sib 6500 Hz −2.0 dB Q 2.5.

**Signal path**  
Serial narrow cuts only. No boosts.

**Safe ranges**  
Gain cuts −1 to −6 dB. Wider or positive gains violate the subtractive contract.

**Failure modes**  
- Turning cuts into boosts  
- Over-narrow Q that rings

**Custom DSP hook**  
Any multi-band corrective EQ or dynamic EQ that only removes masking energy.

**Hardware origin**  
API 550A.

---

### 4.3 `FastCompBlock` — `name = "fast_comp"` · `codec_key = "fastcomp:1176"`

**Constructor**  
`FastCompBlock(sample_rate, threshold_db=-16.0, ratio=4.0, attack_ms=0.4, release_ms=80.0)`

**Primitives**  
`CompressorCore` (feed-forward peak detector + gain computer)

**Envelope formula (must be preserved)**  
```
atk = exp(-1.0 / (attack_ms * 0.001 * sample_rate))
rel = exp(-1.0 / (release_ms * 0.001 * sample_rate))
```
Gain: `(threshold / env) ** (1 - 1/ratio)` when env > threshold, else 1.0.

**Safe ranges**  
GR target 2–4 dB; attack ≤ 1 ms for true peak catching.

**Failure modes**  
- Excess GR → dead transients  
- Attack too slow → peaks escape into later stages

**Custom DSP hook**  
Any FET / VCA / 1176-model compressor with independent attack/release.

**Hardware origin**  
UREI 1176LN.

---

### 4.4 `SlowCompBlock` — `name = "slow_comp"` · `codec_key = "slowcomp:LA2A"`

**Constructor**  
`SlowCompBlock(sample_rate, threshold_db=-18.0, ratio=2.5, attack_ms=15.0, release_ms=280.0, makeup_db=1.5)`

**Primitives**  
Same `CompressorCore` with slower constants and makeup gain.

**Safe ranges**  
GR 2–3 dB. Makeup 0–3 dB.

**Failure modes**  
- Heavy GR that flattens performance  
- Using as the only compressor (peaks escape)

**Custom DSP hook**  
Opto, variable-mu, or LA-2A model.

**Hardware origin**  
Teletronix LA-2A.

---

### 4.5 `ParallelCompressorBlock` — `name = "parallel_comp"` · `codec_key = "parallel"`

**Constructor**  
`ParallelCompressorBlock(sample_rate, mix=0.25, threshold_db=-28.0, ratio=12.0, attack_ms=0.3, release_ms=60.0)`

**Signal path**  
Dry + heavily compressed wet. Mix controls density.

**Custom DSP hook**  
Any aggressive parallel path. Disable via `disable_stage("parallel_comp")` if density is unwanted.

---

### 4.6 `DeEsserBlock` — `name = "deesser"` · `codec_key = "deess:902"`

**Constructor**  
`DeEsserBlock(sample_rate, freq=7200.0, threshold_db=-22.0, ratio=5.0, attack_ms=0.8, release_ms=45.0)`

**Current implementation**  
Broadband compressor after a detection peaking filter (placeholder). Production ports should implement true split-band or dynamic EQ.

**Failure modes**  
- Broadband reduction that lisps the whole voice  
- Placement before compressors

**Custom DSP hook**  
Split-band, dynamic EQ, or neural de-esser. Must act after dynamics.

**Hardware origin**  
dbx 902.

---

### 4.7 `AdditiveEQBlock` — `name = "additive_eq"` · `codec_key = "addeq:Pultec"`

**Constructor**  
`AdditiveEQBlock(sample_rate)`

**Primitives**  
`_lowshelf` 160 Hz +1.8 dB; `_peaking` 3200 Hz +2.2 dB Q 0.9; `_highshelf` 11 kHz +1.5 dB.

**Safe ranges**  
Boosts 1–3 dB. Larger moves risk cumulative gain into saturation.

**Custom DSP hook**  
Any broad, musical additive EQ (Pultec, Neve, API shelves).

**Hardware origin**  
Pultec EQP-1A.

---

### 4.8 `SaturationBlock` — `name = "saturation"` · `codec_key = "sat:Vulture"`

**Constructor**  
`SaturationBlock(drive=1.4, mix=0.22, mode="tape")`

**Signal path**  
`mode="tape"`: `tanh(x * drive) / tanh(drive)`, dry/wet mix.  
`mode` otherwise: asymmetric tanh for even-order emphasis.

**Stateless.**

**Custom DSP hook**  
Tape, tube, console, waveshaper, or neural saturation. Keep mix low unless density is intentional.

**Hardware origin**  
Culture Vulture.

---

### 4.9 `DelayBlock` — `name = "delay"` · `codec_key = "delay:Echoplex"`

**Constructor**  
`DelayBlock(sample_rate, delay_ms=95.0, feedback=0.22, mix=0.15, hp_freq=250.0, lp_freq=5000.0)`

**Primitives**  
Circular buffer + high-pass + peaking (current LP is a soft notch; production ports should use a true low-pass biquad).

**Failure modes**  
- Unfiltered returns → mud  
- Feedback ≥ 0.5 → runaway

**Custom DSP hook**  
Any filtered delay or tape-echo model. Filtering on the return is mandatory.

**Hardware origin**  
Echoplex EP-3.

---

### 4.10 `ReverbBlock` — `name = "reverb"` · `codec_key = "rev:EMT140"`

**Constructor**  
`ReverbBlock(sample_rate=44100.0, decay=0.62, damping=0.45, mix=0.16, predelay_ms=28.0)`

**Primitives**  
Predelay buffer + 2 input allpasses + 4 tank delays with damping low-passes (simplified Dattorro FDN).

**Failure modes**  
- Decay too high → wash  
- Zero pre-delay → voice sits inside the reverb  
- Missing `reset()` → state carries between files

**Custom DSP hook**  
Plate, chamber, convolution, or full Dattorro. Prefer send/return topology conceptually.

**Hardware origin**  
EMT 140.

---

### 4.11 `LookAheadLimiterBlock` — `name = "limiter"` · `codec_key = "lim:Weiss"`

**Constructor**  
`LookAheadLimiterBlock(sample_rate, ceiling_db=-0.5, lookahead_ms=5.0, release_ms=80.0)`

**Primitives**  
Circular (or rolling) peak buffer + instantaneous attack / smoothed release gain envelope.

**Note on current Python implementation**  
Uses `np.roll` per sample (O(n) per sample). Production ports **must** use a true circular buffer with write index for real-time safety.

**Custom DSP hook**  
Any true-peak or look-ahead brickwall limiter. Ceiling and look-ahead are the contractual parameters.

**Hardware origin**  
Weiss DS1-MK3.

---

## 5. ORCHESTRATOR SPEC — `TheOrder`

### Constructor

```
TheOrder(
    sample_rate: float = 44100.0,
    voice_type:  str   = "male",          # "male" | "female"  → HPF & de-ess freq
    enable_parallel: bool = True,         # include ParallelCompressorBlock
    custom: Optional[Dict[str, DSPBlock]] = None
)
```

`voice_type` selects:
- male → HPF 85 Hz, de-ess 7200 Hz  
- female → HPF 100 Hz, de-ess 8200 Hz

### STAGE_ORDER (authoritative, immutable)

```
highpass → subtractive_eq → fast_comp → slow_comp → parallel_comp →
deesser → additive_eq → saturation → delay → reverb → limiter
```

Reordering this list breaks the reference. The architecture exists so that **implementation** can change while **order** stays sacred.

### `replace_stage(name, block)`

- Validates `name` exists in the live stage map.  
- Raises on unknown name.  
- If the incoming block has an empty `codec_key`, the orchestrator stamps the canonical key from `CODEC_KEYS`.  
- Side effect: prints confirmation with stage name, codec key, and class.

### `disable_stage(name)`

Replaces the named stage with `_Bypass` (identity). Codec key becomes `"bypass"`.

### `process(audio)`

1. Convert to float64 (or the port’s working type), copy.  
2. If `ndim > 1`, downmix to mono by mean across channels.  
3. Execute every stage in `STAGE_ORDER`.  
4. Final hard clip to [−1, 1].  
5. Return the array.

### `reset()`

Calls `reset()` on every live stage. Must return all delay lines, envelopes, and filter states to zero / construction defaults.

### `summary()`

Human-readable listing:

```
01. highpass         [hp                ] → HighPassBlock
02. subtractive_eq   [subeq:550A        ] → SubtractiveEQBlock
...
```

### `custom={...}` at construction

Dictionary of stage-name → block instances. Unknown keys raise. Codec keys are auto-filled if missing.

### `codec_map()`

Returns `{stage_name: codec_key}` for the live pipeline.

---

## 6. MULTI-LANGUAGE PORTING GUIDE (“MAD LANGUAGES”)

Bit-exact identity across languages is **not** required. Acceptable tolerance: peak difference ≤ 0.5 dB on the canonical synthetic vocal; RMS per stage within ±0.3 dB after the same parameter set.

### 6.1 Python (Reference)

- Already exists: `the_order_vocal_chain.py`  
- Type: `float64` / `np.ndarray`  
- Interface: `DSPBlock` ABC  
- RT: not real-time safe (Python + `np.roll` in limiter)

### 6.2 C++ (Header-Only, RT-Safe)

**Trait translation**
```cpp
struct DspBlock {
    virtual ~DspBlock() = default;
    virtual const char* name() const = 0;
    virtual const char* codec_key() const = 0;
    virtual void process_block(float* x, size_t n) = 0;
    virtual void reset() = 0;
};
```

**Numeric type**  
`float` (f32) for RT; optionally double for offline masters.

**Filter state**  
Member variables `x1,x2,y1,y2` inside a `Biquad` struct. No heap in `process_block`.

**CompressorCore**  
Preserve exact exponential coefficients:
```cpp
atk = std::exp(-1.0f / (attack_ms * 0.001f * sample_rate));
```

**Reverb FDN**  
Pre-allocate all delay buffers in the constructor. Circular indices only.

**Limiter**  
True circular buffer + write index. **Never** `memmove`/`std::rotate` per sample.

**Hello block**
```cpp
struct GainBlock : DspBlock {
    float g = 1.f;
    const char* name() const override { return "gain"; }
    const char* codec_key() const override { return "gain"; }
    void process_block(float* x, size_t n) override {
        for (size_t i = 0; i < n; ++i) x[i] *= g;
    }
    void reset() override {}
};
```

### 6.3 Rust

**Trait**
```rust
pub trait DspBlock {
    fn name(&self) -> &str;
    fn codec_key(&self) -> &str;
    fn process_block(&mut self, x: &mut [f32]);
    fn reset(&mut self);
}
```

**Numeric type**  
`f32` for RT; `f64` optional offline.

**State**  
Owned buffers inside the struct. `&mut self` guarantees exclusive access.

**Hello block**
```rust
struct GainBlock { g: f32 }
impl DspBlock for GainBlock {
    fn name(&self) -> &str { "gain" }
    fn codec_key(&self) -> &str { "gain" }
    fn process_block(&mut self, x: &mut [f32]) {
        for s in x.iter_mut() { *s *= self.g; }
    }
    fn reset(&mut self) {}
}
```

### 6.4 JavaScript / TypeScript (Worklet-Friendly)

**Interface**
```typescript
interface DspBlock {
  readonly name: string;
  readonly codecKey: string;
  processBlock(x: Float32Array): Float32Array;
  reset(): void;
}
```

**Numeric type**  
`Float32Array` exclusively. No per-sample object allocation.

**Hello block**
```typescript
class GainBlock implements DspBlock {
  name = "gain";
  codecKey = "gain";
  constructor(private g = 1.0) {}
  processBlock(x: Float32Array): Float32Array {
    const out = new Float32Array(x.length);
    for (let i = 0; i < x.length; i++) out[i] = x[i] * this.g;
    return out;
  }
  reset() {}
}
```

For AudioWorklet: process in-place on the supplied channel arrays; never allocate inside `process`.

### 6.5 Other Runtimes (Proposed Bindings — Spec Only)

| Runtime        | Binding Style                          | Notes |
|----------------|----------------------------------------|-------|
| JUCE           | `juce::dsp::ProcessorBase` subclass    | Map `process_block` → `process`; use `AudioBlock<float>` |
| Max / MSP      | External with `dsp_add`                | Signal inlets/outlets; `reset` on loadbang |
| SuperCollider  | UGen or plugin                         | `ar` rate; clear state on `clear` |
| Web Audio API  | AudioWorkletProcessor                  | Same as JS/TS above; register processor |
| Faust          | Faust DSP with matching process order  | Generate C++ then wrap as `DspBlock` |
| C-ABI          | `extern "C"` vtable                    | Enables any language that can call C |

### Cross-Language Parity Checklist

- [ ] Identical `STAGE_ORDER`  
- [ ] Identical default parameters (within floating-point representation)  
- [ ] `reset()` returns all state to construction defaults  
- [ ] Final clip to [−1, 1] (or equivalent hard limit)  
- [ ] Mono downmix by channel mean when input is multi-channel  
- [ ] Unknown stage name rejected by `replace_stage`  
- [ ] Peak difference on synthetic vocal ≤ 0.5 dB vs Python reference  

---

## 7. INTERFACE BINDING MATRIX

| Language     | Interface Mechanism          | Sample Type   | Buffer Type        | Real-Time Safe? | Notes |
|--------------|------------------------------|---------------|--------------------|-----------------|-------|
| Python       | ABC `DSPBlock`               | float64       | `np.ndarray`       | No              | Reference implementation |
| C++          | Abstract base / concept      | float (f32)   | raw pointer + size | Yes (if no alloc) | Header-only preferred |
| Rust         | Trait `DspBlock`             | f32           | `&mut [f32]`       | Yes             | Exclusive `&mut self` |
| JS / TS      | Interface / class            | Float32Array  | Float32Array       | Yes (Worklet)   | No GC in process |
| C-ABI        | Function pointers / vtable   | float         | float* + size_t    | Yes             | Universal FFI |
| JUCE         | `dsp::ProcessorBase`         | float         | AudioBlock         | Yes             | Proposed |
| Web Audio    | AudioWorkletProcessor        | Float32Array  | channel arrays     | Yes             | Proposed |
| Faust        | Generated process            | float         | generated buffers  | Yes             | Proposed |

---

## 8. CUSTOM DSP INJECTION EXAMPLES

### Python

```python
class My1176(DSPBlock):
    name = "fast_comp"
    codec_key = "fastcomp:1176"
    def process_block(self, x): ...
    def reset(self): ...

# Construction injection
chain = TheOrder(48000, custom={"fast_comp": My1176()})

# Hot-swap
chain.replace_stage("saturation", MyVulture())

# Disable
chain.disable_stage("parallel_comp")
```

### C++

```cpp
struct My1176 : DspBlock {
    const char* name() const override { return "fast_comp"; }
    const char* codec_key() const override { return "fastcomp:1176"; }
    void process_block(float* x, size_t n) override { /* ... */ }
    void reset() override { /* ... */ }
};

TheOrder chain(48000.f);
chain.replace_stage("fast_comp", std::make_unique<My1176>());
chain.disable_stage("parallel_comp");
```

### TypeScript

```typescript
class My1176 implements DspBlock {
  name = "fast_comp";
  codecKey = "fastcomp:1176";
  processBlock(x: Float32Array) { /* ... */ return x; }
  reset() {}
}

const chain = new TheOrder(48000, { custom: { fast_comp: new My1176() } });
chain.replaceStage("saturation", new MyVulture());
chain.disableStage("parallel_comp");
```

---

## 9. GAIN STAGING AND HEADROOM

| Stage            | Typical level change          | Makeup? | Notes |
|------------------|-------------------------------|---------|-------|
| highpass         | negligible                    | No      | — |
| subtractive_eq   | small loss (cuts)             | No      | Do not compensate here |
| fast_comp        | GR 2–4 dB                     | No      | Peaks reduced |
| slow_comp        | GR 2–3 dB                     | +1.5 dB | Restores average |
| parallel_comp    | adds density                  | internal| Mix-controlled |
| deesser          | intermittent reduction        | No      | Only on sibilance |
| additive_eq      | +1–3 dB cumulative            | —       | Watch saturation input |
| saturation       | peak can rise                 | mix     | Drive + mix control |
| delay / reverb   | wet lower than dry            | —       | Send level |
| limiter          | ceiling enforcement           | —       | Last defense |

**Philosophy**  
Headroom is deliberately left until the final limiter. Intermediate stages may overshoot 0 dBFS; the orchestrator’s final `clip(−1, 1)` (or equivalent) is the safety net. Ports must not insert earlier hard clips unless they document a different policy.

**Canonical smoke-test signal** (from the Python demo)  
Synthetic four-partial “vocal” + exponential envelope + low-level noise, normalized to peak ≈ 0.65. After the full chain, output peak is expected near the limiter ceiling (≈ 0.94 for −0.5 dB ceiling) with no NaNs and no DC offset after `reset()`.

---

## 10. VALIDATION AND CONFORMANCE

Any language port claiming conformance must pass:

1. **Synthetic vocal generator** (identical coefficients to the Python demo).  
2. **Peak in / peak out** recorded; difference from Python reference ≤ 0.5 dB.  
3. **Stage-by-stage RMS** (optional but recommended) within ±0.3 dB of reference.  
4. **`reset()`** returns every delay line and envelope to zero; second process after reset must match first process of a fresh instance (within float noise).  
5. **`replace_stage("unknown", …)`** raises / returns error.  
6. **`disable_stage("delay")`** produces identity through that stage (output of previous stage equals input of next).  
7. **Final values** lie in [−1, 1].

Reference numbers are taken from the Python implementation at the time of this document; ports should publish their own measured peaks alongside the reference for transparency.

---

## 11. QUICK-REFERENCE CARD

**Stage order (one line)**  
`highpass|subtractive_eq|fast_comp|slow_comp|parallel_comp|deesser|additive_eq|saturation|delay|reverb|limiter`

**Codec string**  
`pre:U47>1073>Lavry>Genesys|hp|subeq:550A|fastcomp:1176|slowcomp:LA2A|deess:902|addeq:Pultec|sat:Vulture|delay:Echoplex|rev:EMT140|bus:SSL|lim:Weiss`

**Block → class**  
hp→HighPass · subeq→SubtractiveEQ · fastcomp→FastComp · slowcomp→SlowComp · parallel→ParallelComp · deess→DeEsser · addeq→AdditiveEQ · sat→Saturation · delay→Delay · rev→Reverb · lim→LookAheadLimiter

**Interface contract (4 lines)**  
```
name, codec_key : string
process_block(x : float_array) → float_array   # same length
reset() → void                                 # clear all state
# mono, shape-preserving, final clip owned by orchestrator
```

**Mad-languages matrix**  
Python (ref) · C++ (RT) · Rust (RT) · JS/TS (Worklet) · C-ABI · JUCE / WebAudio / Faust (proposed)

---

## 12. VALIDATION CHECKLIST

| Check | Status |
|-------|--------|
| All 11 stages in STAGE_ORDER documented | PASS |
| Optional `parallel_comp` and `_Bypass` noted | PASS |
| All block classes covered with constructors & defaults | PASS |
| Orchestrator fully specified | PASS |
| Multi-language guide covers Python, C++, Rust, JS/TS + proposed bindings | PASS |
| Custom DSP injection examples in Python, C++, TypeScript | PASS |
| Conformance test defined with reference policy | PASS |
| Gain-staging / headroom philosophy documented | PASS |
| Cross-link to Hardware Codec Mapping present | PASS |
| Markdown tables complete | PASS |
| File written to `/home/workdir/artifacts/The_Order_Software_Reference.md` | PASS |

---

**END OF ARTIFACT**

The order is the will.  
The blocks are the instruments.  
The languages are the dialects in which the same prayer is spoken.

SOURCE FIRST. THEN CORRECTION. THEN CONTROL. THEN CHARACTER. THEN SPACE. THEN AUTOMATION. THEN GLUE.
