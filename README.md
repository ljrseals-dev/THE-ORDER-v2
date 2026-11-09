# THE ORDER

**CASE FILE 22-EAR-4**

> The voice is already a synthesizer.  
> You are not fixing it. You are preserving a patch made of flesh and breath.

---

## What this is

A **14-stage processing chain** for recorded vocals.

It is built on one idea: the human voice behaves like a synthesizer.  
Vocal folds = oscillator. Vocal tract = filter. Breath = noise.  
If that is true, then mixing a voice means **preserving a patch**, not rewriting it.

The chain does not invent a new sound.  
It enforces a **fixed order of decisions** so every step serves the voice instead of fighting it.

---

## The rule that never changes

```
SOURCE → CORRECTION → CONTROL → CHARACTER → SPACE → GLUE
```

You may replace *what* happens inside any step.  
You may not reorder the steps.

That is the entire architecture.

---

## The 14 stages (plain English)

| # | Stage | What it does in one sentence | Why it is here |
|---|--------|------------------------------|----------------|
| 1 | **High-pass** | Cuts the lowest rumble and plosive thumps. | Nothing useful lives under the voice’s fundamental. Clean the floor first. |
| 2 | **Subtractive EQ** | Makes narrow cuts where the voice sounds muddy, nasal, or harsh. | Remove what *hides* the core before you try to shape tone. |
| 3 | **Noise gate** | Closes the signal when the singer is silent. | Kill room and electronic noise only when the voice is gone. Keep the breath. |
| 4 | **Fast compressor** | Catches sudden peaks (the “1176” job). | Stop spikes before they hit everything downstream. |
| 5 | **Slow compressor** | Smooths overall level (the “LA-2A” job). | Keep the performance even without killing its life. |
| 6 | **Parallel compressor** | Blends a heavily compressed copy underneath. | Optional density. Adds weight without flattening the main path. Can be turned off. |
| 7 | **De-esser** | Tames only the “sss” and “shh” sounds. | Compression often makes sibilance worse; clean it *after* the compressors. |
| 8 | **Dynamic EQ** | Moves cuts and boosts in real time as the voice moves. | Static EQ is a compromise. The voice changes; the filter should follow. |
| 9 | **Additive EQ** | Broad, gentle boosts for warmth, presence, and air. | Now shape tone. Small moves only (1–3 dB). |
| 10 | **Saturation** | Adds subtle harmonic richness (tape/tube style). | Keeps the voice from sounding sterile or “digital.” |
| 11 | **Delay** | Short, filtered echoes for depth. | Place the voice in space without adding mud. |
| 12 | **Reverb** | Plate-style room that matches the rest of the mix. | Same acoustic space as the instruments. Not a wash. |
| 13 | **Limiter** | Final ceiling so nothing clips. | Last safety net and loudness control. |
| 14 | **Dither** | Tiny intentional noise when reducing bit depth. | Makes low-level detail cleaner when you go to 16-bit or similar. |

---

## What is *not* inside the 14 stages

- **Capture** (microphone → preamp → converter → console)  
  That is irreversible. It happens *before* this software chain starts.

- **Mix-bus glue** (e.g. SSL-style bus compressor)  
  That sits above the vocal chain, on the bus or master.

Those appear in the full “codec string” as labels for the hardware story.  
They are not steps inside the vocal process loop.

---

## The hardware names (reference only)

The stages are labeled after classic units so engineers know the *intent*:

```
Neumann U 47 → Neve 1073 → Lavry Gold → Neve Genesys →
API 550A → UREI 1176 → Teletronix LA-2A → dbx 902 →
Pultec EQP-1A → Culture Vulture → Echoplex → EMT 140 →
SSL Bus → Weiss DS1
```

**Important:**  
These labels are **targets**, not claims that the code *is* that hardware.  
Real circuits have physical non-linearities, transformers, and magnetic tape that software only approximates.  
When you have a better model, drop it into the matching stage. The order stays the same.

---

## How to use it

```bash
pip install numpy
python the_order_vocal_chain.py
```

```python
from the_order_vocal_chain import TheOrder

chain = TheOrder(sample_rate=48000, voice_type="male")  # or "female"
processed = chain.process(your_mono_audio)

print(chain.summary())
```

### Swap any stage

```python
chain.replace_stage("fast_comp", MyBetter1176())
chain.replace_stage("saturation", MyTapeModel())
chain.disable_stage("parallel_comp")   # turn density off
```

Any object that implements `process_block(audio) → audio` can be inserted.  
That is the whole point of the modular design.

---

## Why the order is strict

1. **Clean before you color** — Remove masking first so later boosts and saturation act on a clearer signal.  
2. **Catch peaks before you level** — Fast control first; smooth control second.  
3. **De-ess after compression** — Compression often creates the sibilance problem.  
4. **Move the EQ before you set static tone** — Dynamic EQ tracks the performance; additive EQ then sets the overall color.  
5. **Add harmonics before space** — Saturation on the dry voice, not on the reverb tail.  
6. **Space before the final ceiling** — Delay and reverb before the limiter.  
7. **Dither last** — Only after everything else is done.

Break the order and you are no longer running *this* system.  
You are running a different one.

---

## Documentation in this repo

| File | What it covers |
|------|----------------|
| `docs/Hardware_Codec_Mapping.md` | Hardware unit → software stage mapping |
| `docs/The_Order_Software_Reference.md` | Full architecture + how to port to C++ / Rust / JS |
| `docs/Manual.md` | How to hot-swap stages |
| `docs/The_Order.md` | The original hypothesis |
| `docs/Motion_and_Noise_Addendum.md` | Why EQ must move and why noise is not always a defect |
| `docs/BUGS_TECHNICAL REVIEW.md` | Engineering review notes |

---

## What this project claims — and what it does not

| It claims | It does not claim |
|-----------|-------------------|
| A clear sequence of decisions for vocal processing | That software equals the physical hardware chain |
| Named slots you can fill with better algorithms | Perfect analog emulation |
| A portable contract (Python today; other languages later) | Bit-exact identity across every platform |

Emulations are approximations.  
Better math can always be injected.  
The ear remains the final authority.

---

## Requirements

```
numpy >= 1.20
```

---

## The one-line summary

**Source first. Correction. Control. Character. Space. Glue. Motion. Noise.**  
Keep the voice as an instrument, and the mix keeps its humanity.

---

## License

See [LICENSE](LICENSE).
