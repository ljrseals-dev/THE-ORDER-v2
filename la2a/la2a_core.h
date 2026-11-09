// LA-2A manual-faithful behavioral core (C++ port of docs/reference_model_python.py).
// NOT hardware-equivalent. Source of truth: Teletronix LA-2A manual (3-66 + 11-66 addendum).
// Every unmeasured number is UNVERIFIED; [?] = not in the manual.
#pragma once
#include <algorithm>
#include <cmath>

namespace la2a {

// Two-exponential cell model in the dB (gain-reduction) domain. Manual p.2: attack ~10 us, ~60 ms for 50%
// release, 0.5-5 s complete release. "Release" is read as GAIN recovery (dB domain). [HYPOTHESIS]
// Both stages attack fast, so burst duration is NOT remembered (UA manual describes that memory; modeling it
// would slow the attack and conflict with p.2). Constants/weights are one fit, UNVERIFIED.
struct T4Cell {
    double fa = 0, fr = 0, sa = 0, sr = 0, wf = 0.56, ws = 0.44, gf = 0, gs = 0;
    static double coef(double t, double fs) { return std::exp(-1.0 / (std::max(t, 1.0 / fs) * fs)); }
    void prepare(double fs, double attack = 10e-6, double fastRel = 0.030, double slowRel = 2.0) {
        // 10 us is below one sample at 48 kHz (20.8 us): clamped to one sample (effective ~40-60 us).
        fa = sa = coef(attack, fs); fr = coef(fastRel, fs); sr = coef(slowRel, fs); reset();
    }
    void reset() { gf = gs = 0; }
    double step(double targetDb) {
        double k = targetDb > gf ? fa : fr; gf = k * gf + (1 - k) * targetDb;
        k = targetDb > gs ? sa : sr;        gs = k * gs + (1 - k) * targetDb;
        if (gf < 1e-18) gf = 0;
        if (gs < 1e-18) gs = 0;                           // flush denormals
        return wf * gf + ws * gs;                         // weights sum to 1 -> steady state = target
    }
};

class Engine {
public:
    static constexpr int kMaxCh = 2;
    void prepare(double fs) {
        sr_ = fs; for (auto& c : cell_) c.prepare(fs);
        smooth_ = 1.0 - std::exp(-1.0 / (0.010 * fs));
        gain_ = gainT_; pr_ = prT_; grDb_ = 0;
    }
    void reset() { for (auto& c : cell_) c.reset(); grDb_ = 0; }
    // gainDb: [?] range chosen by the plugin (+/-20 dB); pr 0..1; compress=false -> limit (1965 default)
    void setParams(double gainDb, double pr, bool compress, bool link) {
        gainT_ = std::pow(10.0, gainDb / 20.0); prT_ = pr; compress_ = compress; link_ = link;
    }
    double grDb() const { return grDb_; }

    void process(const float* const* in, float* const* out, int n, int nch) {
        nch = std::min(nch, kMaxCh);
        const double gamma = compress_ ? 2.0 / 3.0 : 1.0;      // slope 1-gamma = 1/3 -> 3:1 (addendum); mechanism [?]
        for (int i = 0; i < n; ++i) {
            gain_ += smooth_ * (gainT_ - gain_); pr_ += smooth_ * (prT_ - pr_);
            const double K = 400.0 * pr_ * pr_ + 1e-9;           // quadratic taper is a guess [?]
            double v[kMaxCh], light[kMaxCh], gr[kMaxCh]; double worst = 0;
            for (int c = 0; c < nch; ++c) { v[c] = in[c][i]; if (!std::isfinite(v[c])) v[c] = 0.0; /* NaN/Inf would poison the cell state forever */ light[c] = std::fabs(v[c]); } // EL responds to |V| (physics, p.4)
            auto targetDb = [&](double l) { return 20.0 * std::log10(1.0 + K * (compress_ ? std::pow(l, gamma) : l)); };
            // Smooth divider 1/(1+K*L^gamma) in dB; does NOT model the -30 dB breakaway / -20 dB knee (p.3). [HYPOTHESIS]
            if (link_ && nch > 1) {                              // terminals 6/7: shared control (p.5-6)
                gr[0] = gr[1] = cell_[0].step(targetDb(std::max(light[0], light[1])));
            } else for (int c = 0; c < nch; ++c) gr[c] = cell_[c].step(targetDb(light[c]));
            for (int c = 0; c < nch; ++c) {
                // Gain applied post-attenuation (makeup style); manual says "input level" (p.3). [?]
                out[c][i] = static_cast<float>(v[c] * std::pow(10.0, -gr[c] / 20.0) * gain_);
                worst = std::max(worst, gr[c]);
            }
            grDb_ = worst;
        }
    }
private:
    double sr_ = 48000, smooth_ = 0.001, gain_ = 1, gainT_ = 1, pr_ = 0.4, prT_ = 0.4, grDb_ = 0;
    bool compress_ = false, link_ = false; T4Cell cell_[kMaxCh];
};

} // namespace la2a
