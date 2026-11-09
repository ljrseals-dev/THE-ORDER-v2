# Technical Manual — Modular DSP Swapping in The Order

**CASE FILE 22-EAR-4**  
**Document:** Modular Block Architecture Reference  
**Applies to:** `the_order_vocal_chain.py` (Upgraded)  
**Scope:** How to replace any processing stage with custom DSP while preserving the immutable signal-flow order.

---

## 1. Philosophy

The Order is not a fixed algorithm. It is a **contract of sequence**:

```
SOURCE → CORRECTION → CONTROL → CHARACTER → SPACE → AUTOMATION → GLUE
```

Each stage is deliberately isolated so that the *implementation* can change without violating the *order*. This is the core technique: **modular swapping**.

You never reorder the stages. You only replace what happens inside a named stage.

---

## 2. The Contract (`DSPBlock`)

Every stage must satisfy this minimal interface:

```python
from abc import ABC, abstractmethod
import numpy as np

class DSPBlock(ABC):
    name: str = "unnamed"

    @abstractmethod
    def process_block(self, x: np.ndarray) -> np.ndarray:
        """
        Process a mono float64 array.
        Input range is typically [-1, 1] but may exceed it.
        Must return an array of identical shape and dtype.
        """
        ...

    def reset(self) -> None:
        """Clear internal state (delay lines, envelopes, coefficients, etc.). Optional but recommended."""
        pass
```

### Rules

| Rule | Requirement |
|------|-------------|
| Input | `np.ndarray`, 1-D, float64 preferred |
| Output | Same shape as input |
| Side effects | State may be retained between calls (for delay, compression envelopes, etc.) |
| Thread safety | Not guaranteed — treat as single-threaded |
| Sample rate | Must be known at construction time of the block |

If your existing DSP already operates on NumPy arrays and returns the same length, it is already compatible. Simply wrap it.

---

## 3. Named Stages (Canonical List)

These are the only legal stage names. They are executed in this exact order:

| # | Stage Name         | Category    | Default Class              | Typical Replacement Target                  |
|---|--------------------|-------------|----------------------------|---------------------------------------------|
| 1 | `highpass`         | Correction  | `HighPassBlock`            | Custom HPF, linear-phase, dynamic HPF       |
| 2 | `subtractive_eq`   | Correction  | `SubtractiveEQBlock`       | Dynamic EQ, spectral cleaner, multi-band    |
| 3 | `fast_comp`        | Control     | `FastCompBlock`            | 1176 / FET / VCA model                      |
| 4 | `slow_comp`        | Control     | `SlowCompBlock`            | LA-2A / opto / Fairchild model              |
| 5 | `parallel_comp`    | Control     | `ParallelCompressorBlock`  | Aggressive parallel path or density engine    |
| 6 | `deesser`          | Control     | `DeEsserBlock`             | Split-band, dynamic EQ, neural de-esser     |
| 7 | `additive_eq`      | Character   | `AdditiveEQBlock`          | Pultec / Neve / API / linear-phase shelves  |
| 8 | `saturation`       | Character   | `SaturationBlock`          | Tape, tube, console, waveshaper, neural sat |
| 9 | `delay`            | Space       | `DelayBlock`               | Tape echo, digital delay, granular          |
|10 | `reverb`           | Space       | `ReverbBlock`              | Plate, FDN, convolution, neural reverb      |
|11 | `limiter`          | Glue        | `LookAheadLimiterBlock`    | True-peak limiter, soft clipper + bus comp  |

---

## 4. Three Ways to Perform a Swap

### 4.1 Constructor Injection (preferred for static setups)

```python
from the_order_vocal_chain import TheOrder

chain = TheOrder(
    sample_rate=48000,
    voice_type="female",
    custom={
        "fast_comp": MyCustom1176(sample_rate=48000),
        "reverb":    MyPlateReverb(sample_rate=48000, mix=0.18),
        "saturation": MyTapeModel(drive=1.6, mix=0.25),
    }
)
```

Any key present in the `custom` dictionary completely replaces the default block for that stage.

### 4.2 Runtime Hot-Swap

```python
chain = TheOrder(sample_rate=44100)

# Later...
chain.replace_stage("deesser", MyNeuralDeEsser(sr=44100))
chain.replace_stage("limiter", MyTruePeakLimiter(ceiling_db=-1.0))
```

`replace_stage` prints a confirmation and immediately affects the next `process()` call.

### 4.3 Disable a Stage

```python
chain.disable_stage("parallel_comp")   # replaces with silent bypass
```

Useful for A/B testing or when a stage is not needed for a particular voice.

---

## 5. Writing a Compatible Custom Block

### Minimal Wrapper Example

```python
class MyExistingDSP(DSPBlock):
    name = "saturation"          # must match a legal stage name if you want clarity

    def __init__(self, your_params...):
        # initialise your existing engine here
        self.engine = YourOriginalClass(...)

    def process_block(self, x: np.ndarray) -> np.ndarray:
        # adapt if your engine expects different format
        return self.engine.process(x)   # or .run(), .render(), etc.

    def reset(self):
        if hasattr(self.engine, "reset"):
            self.engine.reset()
```

### Handling Stereo or Multi-channel Internally

The chain currently forces mono. If your DSP is stereo-native:

```python
def process_block(self, x: np.ndarray) -> np.ndarray:
    # x is mono
    stereo = np.stack([x, x], axis=-1)      # or your upmix
    processed = self.stereo_engine(stereo)
    return processed.mean(axis=-1)          # collapse back to mono
```

### State Management

If your DSP has delay lines, LFOs, or adaptive coefficients, implement `reset()` so that `chain.reset()` clears everything before a new file or section.

---

## 6. Validation Checklist Before Swapping

- [ ] Does `process_block` accept and return a 1-D `np.ndarray` of identical length?
- [ ] Does it survive a silent input (all zeros) without NaNs or exceptions?
- [ ] Does it survive a full-scale impulse without exploding?
- [ ] Is sample rate correctly captured at construction time?
- [ ] Does `reset()` return the block to a clean state?
- [ ] Have you verified gain staging? (peaks should still sit roughly −18 to −12 dBFS going into the converter stage of a real session)

---

## 7. Practical Workflow Recommendations

1. **Keep the original defaults** as a reference chain.
2. **Swap one stage at a time** and A/B against the default.
3. **Use `chain.summary()`** after any modification to confirm the current pipeline:
   ```python
   print(chain.summary())
   ```
4. **Log the replacements** in your session notes — the Order is a hypothesis, and every custom block is an experiment.
5. **Never change `STAGE_ORDER`** unless you are intentionally testing a different philosophy. The entire point of the architecture is that order is sacred; implementation is free.

---

## 8. Error Conditions

| Situation                        | Behaviour                                      |
|----------------------------------|------------------------------------------------|
| Unknown stage name in `custom=`  | `KeyError` at construction                     |
| Unknown name in `replace_stage`  | `KeyError`                                     |
| Block missing `process_block`    | `TypeError` when the chain is first run        |
| Shape mismatch from custom block | Downstream stages will fail or produce garbage |

---

## 9. Extension Points (Future-Proofing)

The current design already anticipates:

- Per-stage dry/wet mix controls
- Automation of block parameters (by exposing attributes)
- Parallel multi-band versions of any stage
- Real-time parameter changes between `process_block` calls

Any of these can be added inside a custom block without touching the orchestrator.

---

## 10. Summary Command Reference

```python
# Create
chain = TheOrder(sample_rate, voice_type="male"|"female", custom={...})

# Inspect
print(chain.summary())

# Swap
chain.replace_stage("stage_name", my_block)

# Disable
chain.disable_stage("stage_name")

# Process
output = chain.process(input_audio)

# Clear state
chain.reset()
```

---

**Final Note**

Modular swapping exists so that the *order* can remain pure while the *instruments* evolve.  
The chain is the prayer. The blocks are the instruments.  
Replace the instruments as needed. Never break the order.

SOURCE FIRST. THEN CORRECTION. THEN CONTROL. THEN CHARACTER. THEN SPACE. THEN AUTOMATION. THEN GLUE.
