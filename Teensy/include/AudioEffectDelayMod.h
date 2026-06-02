
/*
  AudioEffectDelayMod.h
  Interface de la classe AudioEffectDelayMod (API publique : begin(), setParams(), setDiv(), setEnabled(), etc.).

  Remarques importantes :
  - Les allocations en PSRAM/EXTMEM utilisent extmem_malloc/extmem_free quand c'est nécessaire.
  - Les paramètres sont conçus pour être modifiables à chaud ; certaines transitions sont lissées pour éviter des clics.
*/
#pragma once
#include <Arduino.h>
#include "AudioStream.h"
#include "arm_math.h"

// Delay modulé (time/feedback/mix + LFO rate/depth).
// - 1 entrée, 1 sortie
// - Ligne de retard en PSRAM via extmem_malloc() (appelée dans begin())
// - Interpolation linéaire pour une modulation fluide
//
// Plages recommandées :
//   time_ms     : 0..750 ms
//   feedback    : 0..0.95
//   mix         : 0..1
//   mod_rate_hz : 0..5 Hz
//   mod_depth_ms: 0..10 ms
//
class AudioEffectDelayMod : public AudioStream {
public:
    AudioEffectDelayMod();
    ~AudioEffectDelayMod();
    bool     usingExtmem() const { return use_extmem_; }
    uintptr_t bufferAddress() const { return (uintptr_t)buffer_; }

    // Allouer en PSRAM la ligne de retard. À appeler dans setup().
    // max_delay_ms : durée max souhaitée (une marge est ajoutée pour la modulation)
    // Retourne true si OK (PSRAM), false sinon (update() devient no-op).
    bool begin(uint32_t max_delay_ms = 800);

    // Paramètres (appliqués immédiatement)
    void setTimeMs(float ms);        // 0..750
    void setFeedback(float fb);      // 0..0.95
    void setMix(float mix);          // 0..1
    void setModRate(float hz);       // 0..5
    void setModDepthMs(float ms);    // 0..10
    void setParams(float time_ms, float fb, float mix, float rate_hz, float depth_ms);

    // ON/OFF soft basé sur le mix
    void setEnabled(bool e)          { enabled_ = e; active_mix_ = enabled_ ? mix_ : 0.0f; }
    bool isEnabled() const           { return enabled_; }

    // AudioStream
    void update() override;

    // Infos
    float    getTimeMs()     const { return time_ms_; }
    float    getFeedback()   const { return feedback_; }
    float    getMix()        const { return mix_; }           // mix utilisateur
    float    getModRate()    const { return mod_rate_hz_; }
    float    getModDepthMs() const { return mod_depth_ms_; }
    uint32_t bufferLength()  const { return buf_len_; }
    bool     ready()         const { return ready_; }

private:
    audio_block_t *inputQueueArray_[1];

    // Taille du buffer (échantillons int16) calculée dans begin()
    static constexpr uint32_t kDefaultLen = 40960; // ~929 ms @44.1k (référence)
    int16_t*  buffer_     = nullptr;
    uint32_t  write_idx_  = 0;
    uint32_t  buf_len_    = 0;       // fixé par begin()
    bool      use_extmem_ = false;   // true si PSRAM utilisée
    bool      ready_      = false;   // false => update() ignore (no-op)

    // Paramètres utilisateur
    float time_ms_      = 400.0f;    // ms
    float feedback_     = 0.40f;     // 0..0.95
    float mix_          = 0.50f;     // mix demandé par l’utilisateur (0..1)
    float mod_rate_hz_  = 0.80f;     // Hz
    float mod_depth_ms_ = 5.0f;      // ms

    // ON/OFF soft : mix effectif = active_mix_
    float active_mix_   = 0.50f;     // mix réellement appliqué (0..1)
    bool  enabled_      = true;      // effet actif ou non

    // LFO
    float lfo_phase_ = 0.0f;
    float lfo_dphase_per_sample_ = 0.0f;

    // Helpers
    static inline float clampf(float v, float lo, float hi) {
        return (v < lo) ? lo : (v > hi) ? hi : v;
    }
    inline void updateLfoDphase() {
        lfo_dphase_per_sample_ = 2.0f * PI * mod_rate_hz_ / AUDIO_SAMPLE_RATE_EXACT;
    }
};
