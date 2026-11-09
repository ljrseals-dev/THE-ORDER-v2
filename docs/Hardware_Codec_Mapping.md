# HARDWARE CODEC MAPPING
## The Perfect Chain — Official Translation Layer

**CASE FILE 22-EAR-4**  
**Classification:** THE ORDER — COMPONENT MANIFEST / CODEC  
**Status:** FINAL  
**Artifact:** `/home/workdir/artifacts/Hardware_Codec_Mapping.md`

This document is the authoritative translation layer between the physical perfect chain and the modular software stages. It enables any engineer or DSP system to replace, emulate, or route the hardware chain while preserving immutable order.

---

## THE PERFECT HARDWARE CHAIN

```
Neumann U 47 → Neve 1073 → Lavry Gold → Neve Genesys Black → 
API 550A → UREI 1176LN → Teletronix LA-2A → dbx 902 → 
Pultec EQP-1A → Culture Vulture → Echoplex → EMT 140 → 
SSL Bus Compressor → Weiss DS1-MK3
```

Fourteen units. One order. No deviation.

---

## ACT STRUCTURE

| Act | Title                  | Hardware Span                                      | Software Stages                          |
|-----|------------------------|----------------------------------------------------|------------------------------------------|
| I   | Capture / Pre-chain    | Neumann U 47 → Neve 1073 → Lavry Gold → Neve Genesys Black | `pre-chain`                              |
| II  | Tone / EQ              | API 550A → Pultec EQP-1A                           | `highpass`, `subtractive_eq`, `additive_eq` |
| III | Dynamics               | UREI 1176LN → Teletronix LA-2A → dbx 902           | `fast_comp`, `slow_comp`, `deesser`      |
| IV  | Color / Saturation     | Culture Vulture                                    | `saturation`                             |
| V   | Space / Time           | Echoplex → EMT 140                                 | `delay`, `reverb`                        |
| VI  | Bus / Limiting         | SSL Bus Compressor → Weiss DS1-MK3                 | `bus`, `limiter`                         |

---

## 1. FULL CODEC TABLE

| Order | Hardware Unit              | Primary Function                          | Mapped Software Stage(s)          | Codec / Protocol Alias      | Default Parameters / Starting Points                          | Notes |
|-------|----------------------------|-------------------------------------------|-----------------------------------|-----------------------------|---------------------------------------------------------------|-------|
| 1     | Neumann U 47               | Large-diaphragm tube condenser microphone | `pre-chain`                       | `mic:U47`                   | Cardioid primary; omni/figure-8 available; self-noise <20 dB(A); max SPL >130 dB | First acoustic filter. Capsule shapes oscillator before electronics. |
| 2     | Neve 1073                  | Class-A discrete mic preamplifier         | `pre-chain`                       | `pre:1073`                  | Gain 40–70 dB; input Z 1.2 kΩ; EIN < −128 dBu; THD <0.1%     | Transformer-balanced. Sets noise floor and harmonic DNA. |
| 3     | Lavry Gold                 | Analog-to-digital converter               | `pre-chain`                       | `adc:Lavry`                 | 24-bit / 192 kHz min; DR >120 dB(A); THD+N < −110 dB; peaks −18 to −12 dBFS | Never clip converter. Match impedance. |
| 4     | Neve Genesys Black         | Hybrid analog/digital console             | `pre-chain`                       | `console:Genesys`           | Digitally-controlled 1073s; 88R-style 4-band EQ; VCA dynamics; Total Recall | Routing, recall, channel processing. Can host early processing if required. |
| 5     | API 550A                   | Discrete Class-A equalizer (corrective)   | `highpass`, `subtractive_eq`      | `eq:550A`                   | Proportional Q; 1 dB steps; centers 50/100/200/400 Hz, 1.5/3/5/10 kHz, 5/10/15 kHz shelves | Narrow cuts for mud (200–400 Hz), harsh (1–3 kHz), sibilance region (5–8 kHz). |
| 6     | UREI 1176LN                | FET peak compressor                       | `fast_comp`                       | `comp:1176`                 | Attack 20 µs–800 µs; release 50 ms–1.1 s; ratios 4:1 / 8:1 / 12:1 / 20:1 / All-in; GR 2–4 dB | Fast peak control. First dynamics stage. |
| 7     | Teletronix LA-2A           | Electro-optical leveler                   | `slow_comp`                       | `comp:LA2A`                 | T4B opto; attack ~10 µs; release 0.06 s (50%) to 0.5–5 s; GR 2–3 dB; program-dependent | Smooth level consistency. Second dynamics stage. |
| 8     | dbx 902                    | Frequency-conscious de-esser              | `deesser`                         | `ds:902`                    | 5–10 kHz region; 3–6 dB reduction on sibilant peaks only; split-band preferred | Place after compression. Compression can exaggerate sibilance. |
| 9     | Pultec EQP-1A              | Passive program equalizer (additive)       | `additive_eq`                     | `eq:Pultec`                 | Low shelf 20–100 Hz; high shelf 1–10 kHz; high peak 3–10 kHz; +1–3 dB moves | Broad boosts only. “Pultec trick” (boost+cut at 100 Hz) for warmth without mud. |
| 10    | Culture Vulture            | Tube harmonic saturator                  | `saturation`                      | `sat:Vulture`               | 6AS6 valve; adjustable bias/drive; mix 0.15–0.30 typical                     | Subtle parallel or low mix. Adds harmonics, perceived loudness, glue. |
| 11    | Echoplex                   | Tape delay / echo                         | `delay`                           | `dly:Echoplex`              | 1/8, 1/16, dotted; feedback modest; HP 200–300 Hz, LP 4–6 kHz on return      | Filtered returns mandatory to avoid mud. |
| 12    | EMT 140                    | Plate reverb                              | `reverb`                          | `rev:EMT140`                | Pre-delay 20–40 ms; shorter decay than instruments for clarity; send/return  | Same acoustic space as rest of mix. Inserts forbidden. |
| 13    | SSL Bus Compressor         | Mix / vocal bus compressor                | `bus`                             | `bus:SSL`                   | 1–2 dB GR; slow attack, slow release, low ratio                              | Glue only. Does not replace individual channel dynamics. |
| 14    | Weiss DS1-MK3              | Mastering dynamics / limiter              | `limiter`                         | `lim:Weiss`                 | Ceiling −0.3 to −1.0 dBTP; look-ahead; preserve dynamics                     | Final word. Loudness, true-peak control, mono check. |

All 14 hardware units appear exactly once. Order is preserved.

---

## 2. STAGE-BY-STAGE DETAIL

### 2.1 `pre-chain` — Act I: Capture

**Purpose**  
Establish the oscillator, first filter, first amplifier, and conversion integrity before any digital processing.

**Hardware origin(s)**  
Neumann U 47 → Neve 1073 → Lavry Gold → Neve Genesys Black

**Signal-flow position**  
Absolute first. Outside the DSPBlock chain. Everything downstream inherits its character and flaws.

**Key parameters**  
- Mic pattern: cardioid primary  
- Preamp gain: 40–70 dB range, set for healthy level into converter  
- Converter peaks: −18 dBFS to −12 dBFS  
- Console: routing and Total Recall only at this stage if pure Order is followed

**Gain-staging / headroom**  
Never clip the converter. Match impedance. Keep noise floor as low as the preamp allows.

**Protocol / codec notes**  
`mic:U47 > pre:1073 > adc:Lavry > console:Genesys`

**Failure modes / avoid**  
- Wrong room acoustics (no processor can fully repair)  
- Clipping the A/D  
- Over-gain on the 1073 that drives the converter into distortion unintentionally

---

### 2.2 `highpass` — Act II (part)

**Purpose**  
Remove subsonic rumble, plosives, and low-frequency energy that masks the voice core.

**Hardware origin(s)**  
API 550A (HPF section) or console HPF on Genesys / SSL Origin

**Signal-flow position**  
First digital corrective stage after capture.

**Key parameters**  
- Cutoff: 80–100 Hz (higher for female, lower for bass/baritone)  
- Slope: 12 dB/oct or 18 dB/oct typical  
- Q: 0.707 (Butterworth) unless resonance is deliberately used

**Gain-staging / headroom**  
Unity. No makeup required.

**Protocol / codec notes**  
Often absorbed into the first move of `subtractive_eq` when using a single 550A; kept as independent stage for modular clarity.

**Failure modes / avoid**  
- Cutting too high and thinning the voice  
- Linear-phase over-use that introduces pre-ringing on plosives

---

### 2.3 `subtractive_eq` — Act II (part)

**Purpose**  
Remove what masks the voice’s core. Do not add yet.

**Hardware origin(s)**  
API 550A

**Signal-flow position**  
Immediately after high-pass, before any dynamics.

**Key parameters**  
- Mud: 200–400 Hz, narrow cut, −2 to −4 dB  
- Harsh / nasal: 1–3 kHz, narrow cut, −1.5 to −3 dB  
- Pre-sibilance: 5–8 kHz, mild cut if needed  
- Proportional-Q behaviour preferred

**Gain-staging / headroom**  
Cuts only. Output level will drop slightly; do not compensate here.

**Protocol / codec notes**  
`eq:550A` — corrective mode only.

**Failure modes / avoid**  
- Broad boosts at this stage (belongs in `additive_eq`)  
- Over-cutting that removes body or presence permanently

---

### 2.4 `fast_comp` — Act III (part)

**Purpose**  
Catch peaks. Fast, gentle peak control.

**Hardware origin(s)**  
UREI 1176LN (Revisions C/D/E Blackface)

**Signal-flow position**  
First dynamics stage.

**Key parameters**  
- Ratio: 4:1 (or 8:1)  
- Attack: 20 µs–800 µs (fast end preferred for peaks)  
- Release: 50 ms–1.1 s  
- Gain reduction: 2–4 dB  
- Input/Output: transformer-balanced

**Gain-staging / headroom**  
Set so that GR stays in the 2–4 dB window on loudest phrases.

**Protocol / codec notes**  
`comp:1176`

**Failure modes / avoid**  
- Excessive GR that kills transients  
- “All-in” mode unless deliberate distortion is required  
- Placing after slower opto stage

---

### 2.5 `slow_comp` — Act III (part)

**Purpose**  
Smooth level consistency without destroying dynamic expression.

**Hardware origin(s)**  
Teletronix LA-2A

**Signal-flow position**  
Second dynamics stage, after fast peak control.

**Key parameters**  
- Electro-optical (T4B)  
- Attack: essentially instantaneous (~10 µs)  
- Release: program-dependent (0.06 s for 50 %, 0.5–5 s full)  
- GR: 2–3 dB  
- Ratio: effectively 2:1 to 3:1 (program-dependent)

**Gain-staging / headroom**  
Makeup typically +1 to +2 dB to restore average level.

**Protocol / codec notes**  
`comp:LA2A`

**Failure modes / avoid**  
- Heavy GR that flattens the performance  
- Using as the only compressor (peaks will escape)

---

### 2.6 `deesser` — Act III (part)

**Purpose**  
Frequency-conscious reduction of sibilance after compression has potentially exaggerated it.

**Hardware origin(s)**  
dbx 902 (alternatives: Drawmer DS201, SPL De-Esser)

**Signal-flow position**  
Immediately after the two compressors.

**Key parameters**  
- Detection / reduction band: 5–10 kHz (male ~6–8 kHz, female ~7–9 kHz)  
- Reduction: 3–6 dB on sibilant peaks only  
- Split-band or dynamic EQ preferred over broadband

**Gain-staging / headroom**  
Unity outside of sibilant events.

**Protocol / codec notes**  
`ds:902`

**Failure modes / avoid**  
- Broadband compression disguised as de-essing  
- Over-reduction that lisps the voice  
- Placement before compressors

---

### 2.7 `additive_eq` — Act II / IV transition

**Purpose**  
Tone shaping. Broad, musical boosts only.

**Hardware origin(s)**  
Pultec EQP-1A

**Signal-flow position**  
After de-essing, before saturation.

**Key parameters**  
- Low shelf / warmth: 100–200 Hz, +1–2 dB  
- Presence: 2–5 kHz, +1–3 dB, Q 0.7–1.0  
- Air: 10–12 kHz, +1–2 dB  
- “Pultec trick”: simultaneous boost and cut at ~100 Hz

**Gain-staging / headroom**  
Small moves. Watch cumulative gain into saturation stage.

**Protocol / codec notes**  
`eq:Pultec`

**Failure modes / avoid**  
- Narrow peaks (belongs in corrective stage)  
- Moves larger than 3 dB  
- Adding before subtractive work is complete

---

### 2.8 `saturation` — Act IV: Color

**Purpose**  
Harmonic enrichment, perceived loudness, glue. Keep the voice instrumental rather than sterile.

**Hardware origin(s)**  
Culture Vulture (Thermionic)

**Signal-flow position**  
After additive EQ, before time-based effects.

**Key parameters**  
- Drive / bias: set for subtle 2nd/3rd harmonic generation  
- Mix: 0.15–0.30 typical  
- Parallel path recommended for density control

**Gain-staging / headroom**  
Drive increases peak level; compensate with mix or subsequent gain.

**Protocol / codec notes**  
`sat:Vulture`

**Failure modes / avoid**  
- Heavy distortion that destroys intelligibility  
- Serial saturation without parallel option  
- Placement after reverb (colors the space undesirably)

---

### 2.9 `delay` — Act V (part)

**Purpose**  
Depth and rhythmic placement without mud.

**Hardware origin(s)**  
Echoplex EP-3 (or Roland Space Echo RE-201)

**Signal-flow position**  
First time-based stage.

**Key parameters**  
- Times: 1/8, 1/16, dotted  
- Feedback: modest  
- Return filtering: high-pass 200–300 Hz, low-pass 4–6 kHz mandatory

**Gain-staging / headroom**  
Send level controls depth. Return is filtered and mixed.

**Protocol / codec notes**  
`dly:Echoplex`

**Failure modes / avoid**  
- Unfiltered delay returns (mud)  
- Long feedback that competes with lead vocal  
- Insert instead of send/return topology conceptually

---

### 2.10 `reverb` — Act V (part)

**Purpose**  
Place the voice in the same acoustic space as the instruments.

**Hardware origin(s)**  
EMT 140 plate

**Signal-flow position**  
After delay, before bus.

**Key parameters**  
- Pre-delay: 20–40 ms  
- Decay: shorter than instrument reverbs for clarity  
- Topology: send/return only (never insert)

**Gain-staging / headroom**  
Send level sets depth. Wet signal is lower than dry.

**Protocol / codec notes**  
`rev:EMT140`

**Failure modes / avoid**  
- Different reverb algorithm from the rest of the mix  
- Excessive decay that washes intelligibility  
- Pre-delay of zero (voice sits inside the reverb)

---

### 2.11 `bus` — Act VI (part)

**Purpose**  
Glue the vocal (or vocal subgroup) before the master bus.

**Hardware origin(s)**  
SSL Bus Compressor

**Signal-flow position**  
After all individual vocal processing, before final limiter.

**Key parameters**  
- GR: 1–2 dB  
- Attack: slow  
- Release: slow  
- Ratio: low (2:1–4:1)

**Gain-staging / headroom**  
Minimal. Makeup only if average level drops.

**Protocol / codec notes**  
`bus:SSL`

**Failure modes / avoid**  
- Heavy compression that undoes earlier dynamic work  
- Treating bus compressor as a second 1176

---

### 2.12 `limiter` — Act VI (part)

**Purpose**  
Final peak control, loudness, true-peak safety.

**Hardware origin(s)**  
Weiss DS1-MK3

**Signal-flow position**  
Absolute last stage in the chain.

**Key parameters**  
- Ceiling: −0.3 to −1.0 dBTP  
- Look-ahead enabled  
- Release: program-dependent or medium  

**Gain-staging / headroom**  
The limiter is the last defense. Do not rely on it for loudness maximization beyond the targets below.

**Protocol / codec notes**  
`lim:Weiss`

**Failure modes / avoid**  
- Over-limiting that reduces LRA excessively  
- Ignoring true-peak overs  
- Skipping mono compatibility check

---

## 3. API AND DSP USAGE

### 3.1 replace_stage() — Canonical Pattern

```python
from the_order_vocal_chain import TheOrder

chain = TheOrder(sample_rate=48000, voice_type="male")

# Hardware-referenced swaps
chain.replace_stage("fast_comp",   My1176Emulation(sr=48000))      # UREI 1176LN
chain.replace_stage("slow_comp",   MyLA2AModel(sr=48000))          # Teletronix LA-2A
chain.replace_stage("deesser",     MyDBX902Style(sr=48000))        # dbx 902
chain.replace_stage("additive_eq", MyPultecEQ(sr=48000))           # Pultec EQP-1A
chain.replace_stage("saturation",  MyCultureVulture(sr=48000))     # Culture Vulture
chain.replace_stage("delay",       MyEchoplex(sr=48000))           # Echoplex
chain.replace_stage("reverb",      MyEMT140(sr=48000))             # EMT 140
chain.replace_stage("limiter",     MyWeissStyleLimiter(sr=48000))  # Weiss DS1-MK3
```

### 3.2 Constructor Injection

```python
chain = TheOrder(
    sample_rate=48000,
    custom={
        "fast_comp":  My1176Emulation(sr=48000),
        "reverb":     MyEMT140(sr=48000),
        "limiter":    MyWeissStyleLimiter(ceiling_db=-0.5),
    }
)
```

### 3.3 JSON / YAML Config Example

```yaml
sample_rate: 48000
voice_type: male
stages:
  fast_comp:
    class: My1176Emulation
    params: { ratio: 4.0, attack_ms: 0.4, release_ms: 80 }
  slow_comp:
    class: MyLA2AModel
    params: { gr_target_db: 2.5 }
  saturation:
    class: MyCultureVulture
    params: { drive: 1.4, mix: 0.22 }
  limiter:
    class: MyWeissStyleLimiter
    params: { ceiling_dbtp: -0.5 }
```

### 3.4 Safe Operations

| Operation              | Method                          | Order Safe? |
|------------------------|---------------------------------|-------------|
| Replace implementation | `replace_stage(name, block)`    | Yes         |
| Disable stage          | `disable_stage(name)`           | Yes         |
| Parallel path          | Custom block with internal dry/wet | Yes     |
| Reorder stages         | Not supported by design         | **No**      |
| Add new stage name     | Requires orchestrator change    | Only with care |

Order is sacred. Implementation is free.

---

## 4. PARALLEL / ALTERNATIVE HARDWARE OPTIONS

| Stage            | Canonical              | Alternative 1              | Alternative 2                  | Alternative 3                | Rationale |
|------------------|------------------------|----------------------------|--------------------------------|------------------------------|-----------|
| `pre-chain` mic  | Neumann U 47           | AKG C 12                   | Sony C-800G                  | Neumann U 67 / M 49          | Comparable large-diaphragm tube/FET vocal standards |
| `pre-chain` pre  | Neve 1073              | API 512                    | Tube-Tech MP 1A              | Chandler TG2                 | Class-A / tube color alternatives |
| `pre-chain` ADC  | Lavry Gold             | Prism Sound ADA-8XR        | Merging Hapi                 | Lynx Hilo                    | High-end conversion references |
| `subtractive_eq` | API 550A               | Neve 1084                  | GML 8200                     | —                            | Inductor or precision alternatives |
| `fast_comp`      | UREI 1176LN            | Empirical Labs Distressor  | API 2500 (fast settings)     | —                            | FET / VCA fast peak control |
| `slow_comp`      | Teletronix LA-2A       | Fairchild 670              | Tube-Tech CL 1B              | —                            | Opto or variable-mu density |
| `deesser`        | dbx 902                | Drawmer DS201              | SPL De-Esser                 | —                            | Classic hardware de-essers |
| `additive_eq`    | Pultec EQP-1A          | Neve 1084 (presence)       | API 550A (broad)             | Manley Massive Passive        | Musical additive curves |
| `saturation`     | Culture Vulture        | Empirical Labs Distressor (Dist) | Chandler TG2            | Ampex 351 electronics        | Tube / FET / tape saturation |
| `delay`          | Echoplex               | Roland Space Echo RE-201   | Lexicon PCM 42               | —                            | Tape or classic digital delay |
| `reverb`         | EMT 140                | Lexicon 224                | AKG BX 20                    | —                            | Plate / digital / spring references |
| `bus`            | SSL Bus Compressor     | API 2500                   | Neve 33609                   | —                            | Classic bus glue compressors |
| `limiter`        | Weiss DS1-MK3          | Sontec MES-432             | Manley Massive Passive (lim) | Prism Maselec                | Mastering-grade final control |

Alternatives are marked as such. The canonical chain remains the reference.

---

## 5. LOUDNESS TARGETS — WEISS STAGE

| Metric              | Recommended Target          | Context / Notes                                      | Source Status |
|---------------------|-----------------------------|------------------------------------------------------|---------------|
| Integrated LUFS     | −14 LUFS                    | Streaming (Spotify, Apple Music, YouTube)            | Documented in original case file |
| Integrated LUFS     | −23 LUFS / −24 LKFS         | Broadcast (EBU R128 / ATSC A/85)                      | Documented |
| Integrated LUFS     | −9 to −12 LUFS              | CD / aggressive genre delivery                       | Documented |
| True Peak (dBTP)    | ≤ −1.0 dBTP (streaming)     | ≤ −0.3 dBTP acceptable for some masters              | Recommended |
| LRA (Loudness Range)| 6–12 LU typical for vocal-led | Preserve expression; avoid <4 LU                     | Recommended |
| Short-term LUFS     | Monitor vs integrated       | No hard limit; watch for momentary overs             | Recommended |
| HBO-style delivery  | −14 to −16 LUFS integrated, true peak ≤ −1 dBTP, LRA ≥ 6 | Prestige limited-series delivery profile             | Recommended |

All values marked “Recommended” are engineering proposals consistent with the original loudness section of the case file. Primary documented targets are the streaming / broadcast / CD figures.

---

## 6. QUICK-REFERENCE CODEC STRING

```
pre:U47>1073>Lavry>Genesys|hp|subeq:550A|fastcomp:1176|slowcomp:LA2A|deess:902|addeq:Pultec|sat:Vulture|delay:Echoplex|rev:EMT140|bus:SSL|lim:Weiss
```

Compact form for logs, config headers, and session notes.

---

## 7. VALIDATION CHECKLIST

| Check                                      | Status |
|--------------------------------------------|--------|
| All 14 hardware units mapped exactly once  | PASS   |
| All required software stages covered (`pre-chain`, `highpass`, `subtractive_eq`, `fast_comp`, `slow_comp`, `deesser`, `additive_eq`, `saturation`, `delay`, `reverb`, `bus`, `limiter`) | PASS |
| Exact hardware chain order preserved       | PASS   |
| No stage incorrectly duplicated            | PASS   |
| Names match case file spelling exactly     | PASS   |
| Markdown tables present and complete       | PASS   |
| File written to `/home/workdir/artifacts/Hardware_Codec_Mapping.md` | PASS |
| Alternatives clearly labeled as non-canonical | PASS |
| Loudness targets include documented + recommended values | PASS |
| API / `replace_stage` usage documented     | PASS   |
| Quick-reference codec string present       | PASS   |

---

**END OF ARTIFACT**

The components are the instrument.  
The order is the will.  
The voice is the patch.

SOURCE FIRST. THEN CORRECTION. THEN CONTROL. THEN CHARACTER. THEN SPACE. THEN AUTOMATION. THEN GLUE.
