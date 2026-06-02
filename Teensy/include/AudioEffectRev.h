/*
  Fichier commenté (exploitable)
  - Commentaires en français centrés sur le "pourquoi" et le "comment".
  - La logique audio n'est pas modifiée : uniquement de la documentation.
*/

/*
  AudioEffectRev.h
  Interface de la classe AudioEffectRev (begin(), setParams(room_size,damping,mix), setEnabled()).

  Remarques importantes :
  - Fichier conservé "compilable" : les commentaires n'altèrent pas la logique.
  - Les allocations en PSRAM/EXTMEM utilisent extmem_malloc/extmem_free quand c'est nécessaire.
  - Les paramètres sont conçus pour être modifiables à chaud ; certaines transitions sont lissées pour éviter des clics.
*/

#pragma once

#include <Arduino.h>
#include "AudioStream.h"
#include "arm_math.h"

/*
 * AudioEffectRev
 *
 * Reverb stéréo globale légère (Schroeder / mini-Freeverb)
 * - room_size (0..1)
 * - damping   (0..1)
 * - mix       (0..1)
 * - ON/OFF via setEnabled()
 * - Toutes les lignes de retard en PSRAM (extmem_malloc)
 *
 * À placer après ton mix global stéréo.
 */

class AudioEffectRev : public AudioStream
{
public:
    // On les met en public pour pouvoir les utiliser dans le .cpp
    static constexpr int NUM_COMB    = 4;
    static constexpr int NUM_ALLPASS = 2;

    AudioEffectRev();
    virtual ~AudioEffectRev();

    virtual void update() override;

    // Alloue les buffers en PSRAM
    bool begin();

    // Paramètres
    void setRoomSize(float room);
    void setDamping(float damp);
    void setMix(float mix);
    void setParams(float room, float damp, float mix);

    // ON / OFF
    void setEnabled(bool e);
    bool isEnabled() const { return enabled_; }

    bool ready() const { return ready_; }

private:
    audio_block_t* inputQueueArray_[2];

    // --- Paramètres utilisateur ---
    float room_size_   = 0.5f;
    float damping_     = 0.3f;
    float mix_         = 0.2f;
    float active_mix_  = 0.2f;
    bool  enabled_     = true;

    bool use_extmem_ = false;
    bool ready_      = false;

    // Structure réverbe
    float* combBufL_[NUM_COMB]    = {nullptr};
    float* combBufR_[NUM_COMB]    = {nullptr};
    uint32_t combLenL_[NUM_COMB]  = {0};
    uint32_t combLenR_[NUM_COMB]  = {0};
    uint32_t combIdxL_[NUM_COMB]  = {0};
    uint32_t combIdxR_[NUM_COMB]  = {0};
    float combStoreL_[NUM_COMB]   = {0};
    float combStoreR_[NUM_COMB]   = {0};

    float* allpassBufL_[NUM_ALLPASS]   = {nullptr};
    float* allpassBufR_[NUM_ALLPASS]   = {nullptr};
    uint32_t allpassLenL_[NUM_ALLPASS] = {0};
    uint32_t allpassLenR_[NUM_ALLPASS] = {0};
    uint32_t allpassIdxL_[NUM_ALLPASS] = {0};
    uint32_t allpassIdxR_[NUM_ALLPASS] = {0};

    // Coeffs internes
    float combFeedback_    = 0.7f;
    float combDamp1_       = 0.2f;
    float combDamp2_       = 0.8f;
    float allpassFeedback_ = 0.5f;

    // Helpers
    static inline float clampf(float v, float lo, float hi) {
        return (v < lo) ? lo : (v > hi) ? hi : v;
    }

    void updateInternalParams();
    bool allocBuffers();
    void freeBuffers();

    // DSP interne
    float processComb(float in, float* buf, uint32_t& idx, uint32_t len, float& store);
    float processAllpass(float in, float* buf, uint32_t& idx, uint32_t len);
};
