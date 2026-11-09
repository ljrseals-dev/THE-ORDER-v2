CASE FILE 22-EAR-4 — SUPPLEMENTAL ADDENDUM

CLASSIFICATION: THE ORDER — MOTION & NOISE
STATUS: OPEN — TWO DIMENSIONS PREVIOUSLY UNEXAMINED
SUBJECT: The Motion of the EQ and the Noise

---

PREAMBLE

The previous specification addressed the static chain: fixed filters, fixed compressors, fixed time-based effects. But a voice is not static. A synthesizer patch is not static. The filter moves. The envelope moves. The noise breathes.

Two dimensions were missing from the manifest:

1. The Motion of the EQ — how the filter behaves over time
2. The Noise — what the noise floor is, where it comes from, and what it means

Eargle knew this. In his framework, the voice is a synthesizer, and a synthesizer without filter motion and without noise is dead. The motion is the life. The noise is the breath.

---

PART I: THE MOTION OF THE EQ

1.1 Static EQ Is a Lie

In the chain as written, SubtractiveEQBlock and AdditiveEQBlock use fixed biquad coefficients. These are static filters. They do not move.

But the voice moves. The vocal tract changes shape for every phoneme. The formants shift. The sibilance moves. The mud moves. A static EQ cannot track this.

The synthesizer analogy:
In a subtractive synth, the filter has an envelope. The cutoff frequency sweeps. The resonance moves. The filter is modulated. A static filter on a synth is a pad. A moving filter is a lead.

The voice analogy:
The vocal tract is a filter that moves with every syllable. The "cutoff frequency" is the formant. The "resonance" is the formant bandwidth. The filter is modulated by the articulation.

The mixing implication:
A static EQ on a voice is a compromise. It works on average. It fails on the extremes. The "perfected" chain requires dynamic EQ — filters that move with the voice.

1.2 Three Types of EQ Motion

Type Description Time Scale Example
Dynamic EQ Filter coefficients change in response to signal energy in a band Milliseconds De-esser, multiband compressor
Automated EQ Filter coefficients change according to a pre-drawn automation curve Seconds to minutes Verse/chorus EQ changes
Modulated EQ Filter coefficients change according to an LFO or envelope follower Milliseconds to seconds Phaser, auto-wah, formant shifter

The "perfected" chain uses all three.

1.3 Dynamic EQ: The De-Esser Is Only the Beginning

The DeEsserBlock is already a dynamic EQ. It detects energy in the sibilant band and reduces gain only when sibilance is present. This is the model.

Extend it to every band:

· Dynamic high-pass: The HPF cutoff rises when the voice is loud and falls when the voice is soft. This preserves low-end warmth on quiet passages while removing rumble on loud passages.
· Dynamic mud cut: The 280 Hz cut deepens when the voice is in the mud range and relaxes when it is not. This removes boxiness only when it is present.
· Dynamic harshness cut: The 2.2 kHz cut deepens when the voice is harsh and relaxes when it is smooth.
· Dynamic presence boost: The 3.2 kHz boost increases when the voice is buried and decreases when it is forward.

The synthesizer analogy:
This is a filter bank with envelope followers. Each band has its own envelope. Each band moves independently. This is what a vocoder does. This is what the vocal tract does.

1.4 Automated EQ: The Macro Motion

The voice changes over the course of a song. The verse is intimate. The chorus is explosive. The bridge is vulnerable. The EQ must follow.

The "perfected" automation curve:

Section High-Pass Mud Cut Presence Air
Verse 80 Hz −2 dB +1 dB +0.5 dB
Pre-Chorus 85 Hz −3 dB +2 dB +1 dB
Chorus 90 Hz −4 dB +3 dB +2 dB
Bridge 75 Hz −1 dB +0.5 dB +0.5 dB
Final Chorus 95 Hz −4.5 dB +3.5 dB +2.5 dB

The synthesizer analogy:
This is the filter envelope. The cutoff moves over the course of the note. The EQ moves over the course of the song.

1.5 Modulated EQ: The Micro Motion

The voice has vibrato. The voice has tremolo. The voice has natural fluctuations in pitch and amplitude. The EQ can track these.

Formant tracking:
The formants of the voice shift with pitch. When the voice rises, the formants rise. A static EQ cannot track this. A modulated EQ can.

Implementation:
Use a pitch detector (e.g., YIN, CREPE) to extract the fundamental frequency. Map the fundamental to a formant shift. Adjust the EQ coefficients in real time.

The synthesizer analogy:
This is filter key tracking. The cutoff follows the pitch. The filter moves with the note.

1.6 The Group Delay Problem

Every filter introduces phase shift. The phase shift is frequency-dependent. This means different frequencies are delayed by different amounts. This is group delay.

Why it matters:
Group delay smears transients. A voice with plosives and sibilance has fast transients. A filter with high group delay will smear those transients. The voice will lose intelligibility.

The "perfected" solution:
Use linear-phase filters for the corrective EQ. Use minimum-phase filters for the character EQ. The corrective EQ removes masking without smearing. The character EQ adds phase shift that is musically pleasing.

The synthesizer analogy:
This is the difference between a linear-phase filter and a ladder filter. The linear-phase filter is transparent. The ladder filter has character.

1.7 Code: Dynamic EQ Block

```python
class DynamicEQBlock(DSPBlock):
    """
    Dynamic EQ with sidechain detection.
    Each band has its own envelope follower and gain computer.
    The filter coefficients are updated in real time.
    """
    name = "dynamic_eq"

    def __init__(self, sample_rate: float, bands: list):
        """
        bands: list of dicts with keys:
            freq: center frequency
            gain_db: maximum gain reduction (negative for cut, positive for boost)
            Q: filter Q
            threshold_db: sidechain threshold
            ratio: sidechain ratio
            attack_ms: sidechain attack
            release_ms: sidechain release
        """
        self.fs = sample_rate
        self.bands = []
        for b in bands:
            self.bands.append({
                'freq': b['freq'],
                'gain_db': b['gain_db'],
                'Q': b['Q'],
                'threshold': 10 ** (b['threshold_db'] / 20.0),
                'ratio': b['ratio'],
                'atk': np.exp(-1.0 / (b['attack_ms'] * 0.001 * sample_rate)),
                'rel': np.exp(-1.0 / (b['release_ms'] * 0.001 * sample_rate)),
                'env': 0.0,
                'filter': _peaking(sample_rate, b['freq'], b['gain_db'], b['Q']),
                'detector': _peaking(sample_rate, b['freq'], 0.0, b['Q']),
            })

    def process(self, x: float) -> float:
        for band in self.bands:
            # Detect energy in the band
            detected = band['detector'].process(x)
            rectified = abs(detected)

            # Envelope follower
            if rectified > band['env']:
                band['env'] = (band['atk'] * band['env'] +
                               (1 - band['atk']) * rectified)
            else:
                band['env'] = (band['rel'] * band['env'] +
                               (1 - band['rel']) * rectified)

            # Gain computation
            if band['env'] > band['threshold']:
                gain_reduction = (band['threshold'] / band['env']) ** (
                    1.0 - 1.0 / band['ratio']
                )
            else:
                gain_reduction = 1.0

            # Update filter gain
            current_gain_db = band['gain_db'] * (1.0 - gain_reduction)
            band['filter'] = _peaking(
                self.fs, band['freq'], current_gain_db, band['Q']
            )

            # Apply filter
            x = band['filter'].process(x)

        return x

    def process_block(self, x):
        return np.array([self.process(float(s)) for s in x], dtype=np.float64)

    def reset(self):
        for band in self.bands:
            band['env'] = 0.0
            band['filter'].reset()
            band['detector'].reset()
```

1.8 Code: Automated EQ Block

```python
class AutomatedEQBlock(DSPBlock):
    """
    EQ with automation curve.
    The gain of each band is interpolated over time according to a control signal.
    """
    name = "automated_eq"

    def __init__(self, sample_rate: float, bands: list,
                 automation: dict, duration_samples: int):
        """
        bands: list of dicts with keys: freq, Q, base_gain_db, max_gain_db
        automation: dict mapping band index to a list of (time_fraction, gain_fraction) tuples
        duration_samples: total length of the audio
        """
        self.fs = sample_rate
        self.bands = []
        for b in bands:
            self.bands.append({
                'freq': b['freq'],
                'Q': b['Q'],
                'base_gain_db': b['base_gain_db'],
                'max_gain_db': b['max_gain_db'],
                'filter': _peaking(sample_rate, b['freq'], b['base_gain_db'], b['Q']),
            })
        self.automation = automation
        self.duration = duration_samples
        self.sample_index = 0

    def process(self, x: float) -> float:
        t = self.sample_index / self.duration
        for i, band in enumerate(self.bands):
            # Interpolate gain at time t
            if i in self.automation:
                points = self.automation[i]
                gain_fraction = self._interpolate(points, t)
                current_gain_db = (band['base_gain_db'] +
                                   (band['max_gain_db'] - band['base_gain_db']) *
                                   gain_fraction)
            else:
                current_gain_db = band['base_gain_db']

            # Update filter
            band['filter'] = _peaking(
                self.fs, band['freq'], current_gain_db, band['Q']
            )
            x = band['filter'].process(x)

        self.sample_index += 1
        return x

    def _interpolate(self, points, t):
        """Linear interpolation between automation points."""
        if t <= points[0][0]:
            return points[0][1]
        if t >= points[-1][0]:
            return points[-1][1]
        for i in range(len(points) - 1):
            t0, v0 = points[i]
            t1, v1 = points[i + 1]
            if t0 <= t <= t1:
                frac = (t - t0) / (t1 - t0)
                return v0 + frac * (v1 - v0)
        return points[-1][1]

    def process_block(self, x):
        return np.array([self.process(float(s)) for s in x], dtype=np.float64)

    def reset(self):
        self.sample_index = 0
        for band in self.bands:
            band['filter'].reset()
```

1.9 Code: Formant Tracking EQ Block

```python
class FormantTrackingEQBlock(DSPBlock):
    """
    EQ that tracks the fundamental frequency and shifts the formant bands.
    Uses a simple autocorrelation pitch detector.
    """
    name = "formant_tracking_eq"

    def __init__(self, sample_rate: float, formants: list,
                 min_f0: float = 80.0, max_f0: float = 400.0):
        """
        formants: list of dicts with keys: freq, Q, gain_db
        min_f0, max_f0: expected pitch range
        """
        self.fs = sample_rate
        self.formants = []
        for f in formants:
            self.formants.append({
                'base_freq': f['freq'],
                'Q': f['Q'],
                'gain_db': f['gain_db'],
                'filter': _peaking(sample_rate, f['freq'], f['gain_db'], f['Q']),
            })
        self.min_f0 = min_f0
        self.max_f0 = max_f0
        self.buffer = np.zeros(2048)
        self.buf_idx = 0

    def _detect_pitch(self) -> float:
        """Simple autocorrelation pitch detection."""
        # Use a window of the buffer
        window = self.buffer[-1024:]
        window = window - np.mean(window)
        if np.max(np.abs(window)) < 1e-6:
            return 0.0

        # Autocorrelation
        corr = np.correlate(window, window, mode='full')
        corr = corr[len(corr)//2:]

        # Find peak in expected range
        min_lag = int(self.fs / self.max_f0)
        max_lag = int(self.fs / self.min_f0)
        if max_lag >= len(corr):
            return 0.0

        peak_lag = np.argmax(corr[min_lag:max_lag]) + min_lag
        if peak_lag == 0:
            return 0.0
        return self.fs / peak_lag

    def process(self, x: float) -> float:
        # Update buffer
        self.buffer[self.buf_idx] = x
        self.buf_idx = (self.buf_idx + 1) % len(self.buffer)

        # Detect pitch every 512 samples
        if self.buf_idx % 512 == 0:
            f0 = self._detect_pitch()
            if f0 > 0:
                # Shift formants proportionally to pitch
                for formant in self.formants:
                    ratio = f0 / 175.0  # reference pitch
                    new_freq = formant['base_freq'] * ratio
                    formant['filter'] = _peaking(
                        self.fs, new_freq, formant['gain_db'], formant['Q']
                    )

        # Apply filters
        for formant in self.formants:
            x = formant['filter'].process(x)

        return x

    def process_block(self, x):
        return np.array([self.process(float(s)) for s in x], dtype=np.float64)

    def reset(self):
        self.buffer[:] = 0.0
        self.buf_idx = 0
        for formant in self.formants:
            formant['filter'].reset()
```

---

PART II: THE NOISE

2.1 Noise Is Not a Defect

In the synthesizer voice, noise is a source. It is the breath. It is the air. It is the sibilance. It is the plosive. It is not a defect. It is part of the patch.

In the recording chain, noise is everywhere:

· Room noise: HVAC, traffic, footsteps, the building's hum
· Microphone self-noise: thermal noise in the capsule and electronics
· Preamp noise: thermal noise in the transistors and resistors
· Converter noise: quantization noise, jitter
· Tape noise: hiss, wow, flutter
· Console noise: thermal noise in every channel
· Compressor noise: makeup gain raises the noise floor
· Saturation noise: harmonic distortion adds noise-like content
· Delay noise: the delay line adds noise
· Reverb noise: the reverb tail adds noise
· Limiter noise: makeup gain raises the noise floor
· Dither: intentional noise added at the final stage

Eargle's principle:
The noise floor determines the dynamic range. The dynamic range determines the intimacy. The intimacy determines the humanity.

2.2 The Noise Floor Budget

The "perfected" chain minimizes noise floor until the character stages, where noise is added intentionally.

Stage Noise Floor Contribution Action
Room −60 to −40 dBFS Treat the room. Isolate.
Microphone −120 dBFS (self-noise) Use a quiet mic.
Preamp −128 dBu (EIN) Use a clean preamp.
Converter −120 dBFS (dynamic range) Use a high-resolution converter.
Console −90 dBFS (per channel) Use a clean console.
Subtractive EQ −120 dBFS (digital) No noise added.
Fast Comp −80 dBFS (makeup gain) Accept the noise.
Slow Comp −80 dBFS (makeup gain) Accept the noise.
De-Esser −90 dBFS Minimal noise.
Additive EQ −80 dBFS (boost) Accept the noise.
Saturation −70 dBFS (harmonic distortion) Intentional noise.
Delay −75 dBFS (delay line) Intentional noise.
Reverb −70 dBFS (reverb tail) Intentional noise.
Limiter −80 dBFS (makeup gain) Accept the noise.
Dither −90 dBFS (intentional) Intentional noise.

The "perfected" noise floor:
The final noise floor should be around −80 dBFS. This is low enough to preserve the voice's detail but high enough to mask the digital artifacts. The noise should be shaped to match the voice's spectrum.

2.3 Noise as Masking

The noise floor masks low-level detail. If the noise floor is too high, you lose:

· The decay of the voice
· The breath
· The room
· The subtle harmonics

The "perfected" solution:
Use subtractive EQ to remove noise in specific bands. The high-pass filter removes rumble. The mud cut removes low-frequency noise. The harshness cut removes mid-frequency noise. The sibilance cut removes high-frequency noise.

The synthesizer analogy:
This is the noise gate. The gate removes noise when the signal is below the threshold. The EQ removes noise in specific bands.

2.4 Noise as Signal

The noise is not always a defect. The breath is noise. The sibilance is noise. The plosive is noise. These are part of the patch.

The "perfected" solution:
Do not remove all noise. Preserve the breath. Preserve the sibilance. Preserve the plosive. These are the transients that make the voice human.

The synthesizer analogy:
This is the noise generator. It is a source. It is not a defect. It is part of the patch.

2.5 Dither: The Final Noise

Dither is intentional noise added at the final stage. It is added when reducing bit depth. It is shaped to match the voice's spectrum.

The "perfected" solution:
Use shaped dither. Move the noise floor to frequencies where the ear is less sensitive. This is noise shaping.

The synthesizer analogy:
This is the final filter. It shapes the noise to match the patch.

2.6 Code: Noise Floor Analyzer

```python
class NoiseFloorAnalyzer:
    """
    Analyzes the noise floor of an audio signal.
    Returns the noise floor in dBFS per frequency band.
    """
    def __init__(self, sample_rate: float, fft_size: int = 4096):
        self.fs = sample_rate
        self.fft_size = fft_size

    def analyze(self, x: np.ndarray) -> dict:
        """
        Returns a dict with:
            overall_db: overall noise floor in dBFS
            bands: list of (freq, db) tuples
        """
        # Find the quietest section of the signal
        # (assuming the noise floor is present when the signal is silent)
        window_size = self.fft_size
        num_windows = len(x) // window_size

        min_energy = np.inf
        quietest_window = None

        for i in range(num_windows):
            window = x[i * window_size:(i + 1) * window_size]
            energy = np.sum(window ** 2)
            if energy < min_energy:
                min_energy = energy
                quietest_window = window

        if quietest_window is None:
            return {'overall_db': -np.inf, 'bands': []}

        # FFT of the quietest window
        spectrum = np.fft.rfft(quietest_window * np.hanning(window_size))
        magnitude = np.abs(spectrum) / window_size
        db = 20 * np.log10(magnitude + 1e-12)

        # Overall noise floor
        overall_db = 20 * np.log10(np.sqrt(min_energy / window_size) + 1e-12)

        # Per-band noise floor
        freqs = np.fft.rfftfreq(window_size, 1.0 / self.fs)
        bands = list(zip(freqs, db))

        return {'overall_db': overall_db, 'bands': bands}
```

2.7 Code: Dither and Noise Shaping

```python
class DitherBlock(DSPBlock):
    """
    Dither and noise shaping for final bit-depth reduction.
    Uses a simple second-order noise shaping filter.
    """
    name = "dither"

    def __init__(self, target_bits: int = 16, dither_type: str = "tpdf",
                 noise_shaping: bool = True):
        self.target_bits = target_bits
        self.dither_type = dither_type
        self.noise_shaping = noise_shaping
        self.quantization_step = 2.0 / (2 ** target_bits)
        self.error_history = [0.0, 0.0]

    def _generate_dither(self) -> float:
        if self.dither_type == "tpdf":
            # Triangular PDF dither
            return (np.random.rand() - np.random.rand()) * self.quantization_step
        elif self.dither_type == "rpdf":
            # Rectangular PDF dither
            return (np.random.rand() - 0.5) * self.quantization_step
        else:
            return 0.0

    def process(self, x: float) -> float:
        # Add dither
        dithered = x + self._generate_dither()

        # Quantize
        quantized = np.round(dithered / self.quantization_step) * self.quantization_step

        # Noise shaping
        if self.noise_shaping:
            error = dithered - quantized
            # Second-order noise shaping
            shaped_error = error - 2 * self.error_history[0] + self.error_history[1]
            self.error_history[1] = self.error_history[0]
            self.error_history[0] = error
            quantized = quantized + shaped_error

        return quantized

    def process_block(self, x):
        return np.array([self.process(float(s)) for s in x], dtype=np.float64)

    def reset(self):
        self.error_history = [0.0, 0.0]
```

2.8 Code: Noise Gate Block

```python
class NoiseGateBlock(DSPBlock):
    """
    Noise gate with hysteresis and hold time.
    Removes noise when the signal is below the threshold.
    """
    name = "noise_gate"

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
            # Signal present: open gate
            self.hold_counter = self.hold_samples
            target_gain = 1.0
        elif self.hold_counter > 0:
            # Hold period: keep gate open
            self.hold_counter -= 1
            target_gain = 1.0
        else:
            # Signal absent: close gate
            target_gain = 0.0

        # Smooth gain
        if target_gain < self.gain:
            self.gain = self.rel * self.gain + (1 - self.rel) * target_gain
        else:
            self.gain = self.atk * self.gain + (1 - self.atk) * target_gain

        return x * self.gain

    def process_block(self, x):
        return np.array([self.process(float(s)) for s in x], dtype=np.float64)

    def reset(self):
        self.gain = 1.0
        self.hold_counter = 0
```

---

PART III: THE MOTION OF THE NOISE

3.1 The Noise Envelope

The noise is not static. It moves with the voice. The breath is loud at the beginning of a phrase and quiet at the end. The sibilance is loud at the sibilant and quiet between. The room noise is present always but masked by the voice.

The "perfected" solution:
Use a noise envelope follower to track the noise. Use the envelope to control the noise gate. Use the gate to remove noise only when the voice is absent.

The synthesizer analogy:
This is the noise envelope. The noise generator has its own envelope. The envelope shapes the noise.

3.2 The Noise Spectrum

The noise is not flat. It has a spectrum. The room noise is low-frequency. The microphone self-noise is high-frequency. The tape hiss is high-frequency. The breath is broadband.

The "perfected" solution:
Use a spectral noise reducer to remove noise in specific bands. Use the noise floor analyzer to identify the noise spectrum. Use the dynamic EQ to remove noise only in the bands where it is present.

The synthesizer analogy:
This is the noise filter. The noise generator has its own filter. The filter shapes the noise.

3.3 The Noise Modulation

The noise is not constant. It modulates with the voice. The breath modulates with the articulation. The sibilance modulates with the phoneme.

The "perfected" solution:
Use a noise modulator to track the voice. Use the voice envelope to control the noise gate. Use the voice spectrum to control the noise filter.

The synthesizer analogy:
This is the noise modulation. The noise generator is modulated by the voice. The noise is part of the patch.

---

PART IV: THE PERFECTED CHAIN — MOTION AND NOISE

4.1 Updated Stage Order

The chain now includes the motion and noise stages:

# Stage Name Category Motion Noise
1 highpass Correction Static or dynamic Removes rumble
2 subtractive_eq Correction Dynamic Removes mud, harshness, sibilance
3 noise_gate Correction Envelope follower Removes noise when voice absent
4 fast_comp Control Envelope follower Makeup gain raises noise floor
5 slow_comp Control Envelope follower Makeup gain raises noise floor
6 parallel_comp Control Envelope follower Adds density
7 deesser Control Dynamic EQ Removes sibilance
8 dynamic_eq Control Dynamic EQ Tracks formants
9 additive_eq Character Automated Boosts noise floor
10 saturation Character Level-dependent Adds harmonic noise
11 delay Space Modulated Adds delay line noise
12 reverb Space Modulated Adds reverb tail noise
13 limiter Glue Envelope follower Makeup gain raises noise floor
14 dither Glue Noise shaping Adds intentional noise
15 soft_clip Glue Static Final safety

4.2 The Motion of the EQ — Summary

EQ Type Time Scale Implementation
Dynamic EQ Milliseconds Sidechain envelope follower
Automated EQ Seconds to minutes DAW automation or interpolation
Modulated EQ Milliseconds to seconds LFO or pitch tracker
Formant Tracking Milliseconds Pitch detector + coefficient update

4.3 The Noise — Summary

Noise Type Source Action
Room noise Environment Treat the room, use a gate
Mic self-noise Capsule Use a quiet mic
Preamp noise Electronics Use a clean preamp
Converter noise Quantization Use a high-resolution converter
Console noise Electronics Use a clean console
Compressor noise Makeup gain Accept the noise
Saturation noise Harmonic distortion Intentional noise
Delay noise Delay line Intentional noise
Reverb noise Reverb tail Intentional noise
Dither Intentional Use shaped dither

---

PART V: THE FINAL CASE FILE — MOTION AND NOISE

CASE NO: 22-EAR-4
CLASSIFICATION: THE ORDER — MOTION & NOISE
STATUS: CLOSED — ETERNAL OPEN

THE MOTION OF THE EQ:
The voice moves. The filter must move. Dynamic EQ, automated EQ, modulated EQ. The filter is not static. The filter is alive.

THE NOISE:
The noise is not a defect. The noise is the breath. The noise is the air. The noise is the sibilance. The noise is the plosive. The noise is part of the patch. Do not remove all noise. Preserve the breath. Preserve the sibilance. Preserve the plosive. These are the transients that make the voice human.

THE MOTION OF THE NOISE:
The noise moves with the voice. The noise envelope follows the voice envelope. The noise spectrum follows the voice spectrum. The noise modulation follows the voice modulation. The noise is not static. The noise is alive.

THE PERFECTED CHAIN:
Source first. Then correction. Then control. Then character. Then space. Then automation. Then glue. Keep the voice as an instrument. Keep the motion. Keep the noise. Keep the humanity.

THE PRAYER:
The voice is a synthesizer. The synthesizer is a voice. The filter moves. The noise breathes. The order is the will of God made audible.

SOURCE FIRST. THEN CORRECTION. THEN CONTROL. THEN CHARACTER. THEN SPACE. THEN AUTOMATION. THEN GLUE. THEN MOTION. THEN NOISE.

END OF FILE.
