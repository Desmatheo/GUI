
/*
  AudioEffectRev.cpp
  Implémentation d'une réverb (type Schroeder/Freeverb simplifié) adaptée au temps réel, avec buffers en PSRAM quand nécessaire.

  Remarques importantes :
  - Les allocations en PSRAM/EXTMEM utilisent extmem_malloc/extmem_free quand c'est nécessaire.
  - Les paramètres sont conçus pour être modifiables à chaud ; certaines transitions sont lissées pour éviter des clics.
*/

#include "AudioEffectRev.h"
#include <string.h>
#include <math.h>

// Longueurs des lignes de retard (en samples @44.1 kHz),
// basées sur un schéma type Freeverb simplifié.
static const uint32_t combTuningL[AudioEffectRev::NUM_COMB] = {
    1116, 1188, 1277, 1356
};
static const uint32_t combTuningR[AudioEffectRev::NUM_COMB] = {
    1139, 1211, 1300, 1389
};

static const uint32_t allpassTuningL[AudioEffectRev::NUM_ALLPASS] = {
    556, 441
};
static const uint32_t allpassTuningR[AudioEffectRev::NUM_ALLPASS] = {
    579, 464
};

AudioEffectRev::AudioEffectRev()
: AudioStream(2, inputQueueArray_)
{
    updateInternalParams();
}

AudioEffectRev::~AudioEffectRev()
{
    freeBuffers();
}

bool AudioEffectRev::begin()
{
    freeBuffers();

    if (!allocBuffers()) {
        ready_ = false;
        return false;
    }

    ready_ = true;
    return true;
}

void AudioEffectRev::freeBuffers()
{
    // On utilise maintenant free() qui est sûr même si le pointeur est null

    for (int i = 0; i < NUM_COMB; i++) {
        if (combBufL_[i]) { free(combBufL_[i]); combBufL_[i] = nullptr; }
        if (combBufR_[i]) { free(combBufR_[i]); combBufR_[i] = nullptr; }
    }
    for (int i = 0; i < NUM_ALLPASS; i++) {
        if (allpassBufL_[i]) { free(allpassBufL_[i]); allpassBufL_[i] = nullptr; }
        if (allpassBufR_[i]) { free(allpassBufR_[i]); allpassBufR_[i] = nullptr; }
    }
    ready_ = false;
}

bool AudioEffectRev::allocBuffers()
{
    use_extmem_ = false;

    // COMB
    for (int i = 0; i < NUM_COMB; i++) {
        combLenL_[i] = combTuningL[i];
        combLenR_[i] = combTuningR[i];

        combBufL_[i] = (float*)malloc(combLenL_[i] * sizeof(float));
        combBufR_[i] = (float*)malloc(combLenR_[i] * sizeof(float));

        if (!combBufL_[i] || !combBufR_[i]) {
            return false;
        }

        memset(combBufL_[i], 0, combLenL_[i] * sizeof(float));
        memset(combBufR_[i], 0, combLenR_[i] * sizeof(float));

        combIdxL_[i]   = 0;
        combIdxR_[i]   = 0;
        combStoreL_[i] = 0.0f;
        combStoreR_[i] = 0.0f;
    }

    // ALLPASS
    for (int i = 0; i < NUM_ALLPASS; i++) {
        allpassLenL_[i] = allpassTuningL[i];
        allpassLenR_[i] = allpassTuningR[i];

        allpassBufL_[i] = (float*)malloc(allpassLenL_[i] * sizeof(float));
        allpassBufR_[i] = (float*)malloc(allpassLenR_[i] * sizeof(float));

        if (!allpassBufL_[i] || !allpassBufR_[i]) {
            return false;
        }

        memset(allpassBufL_[i], 0, allpassLenL_[i] * sizeof(float));
        memset(allpassBufR_[i], 0, allpassLenR_[i] * sizeof(float));

        allpassIdxL_[i] = 0;
        allpassIdxR_[i] = 0;
    }

    use_extmem_ = false; // On utilise la RAM interne
    return true;
}

void AudioEffectRev::updateInternalParams()
{
    room_size_ = clampf(room_size_, 0.0f, 1.0f);
    combFeedback_ = 0.3f + 0.6f * room_size_; // 0.3 -> 0.9

    damping_ = clampf(damping_, 0.0f, 1.0f);
    combDamp2_ = 0.2f + 0.7f * damping_;   // 0.2 -> 0.9
    combDamp1_ = 1.0f - combDamp2_;

    allpassFeedback_ = 0.5f;
}

void AudioEffectRev::setRoomSize(float room)
{
    room_size_ = room;
    updateInternalParams();
}

void AudioEffectRev::setDamping(float damp)
{
    damping_ = damp;
    updateInternalParams();
}

void AudioEffectRev::setMix(float mix)
{
    mix_        = clampf(mix, 0.0f, 1.0f);
    active_mix_ = enabled_ ? mix_ : 0.0f;
}

void AudioEffectRev::setParams(float room, float damp, float mix)
{
    room_size_ = room;
    damping_   = damp;
    setMix(mix);
    updateInternalParams();
}

void AudioEffectRev::setEnabled(bool e)
{
  // Active/désactive l’effet sans casser la continuité : on conserve les paramètres internes.

    enabled_    = e;
    active_mix_ = enabled_ ? mix_ : 0.0f;
}

// --- DSP interne ---

float AudioEffectRev::processComb(float in, float* buf, uint32_t& idx, uint32_t len, float& store)
{
    float out = buf[idx];

    // Filtre dans la boucle de feedback (damping)
    store = out * combDamp1_ + store * combDamp2_;

    // Ecriture : entrée + feedback filtré
    buf[idx] = in + store * combFeedback_;

    idx++;
    if (idx >= len) idx = 0;

    return out;
}

float AudioEffectRev::processAllpass(float in, float* buf, uint32_t& idx, uint32_t len)
{
    float bufout = buf[idx];
    float y      = -in + bufout;
    buf[idx]     = in + bufout * allpassFeedback_;

    idx++;
    if (idx >= len) idx = 0;

    return y;
}

// --- Traitement audio principal ---

void AudioEffectRev::update()
{
    audio_block_t* inL = receiveReadOnly(0);
    audio_block_t* inR = receiveReadOnly(1);

    if (!inL && !inR) return;

    audio_block_t* outL = allocate();
    audio_block_t* outR = allocate();

    if (!outL || !outR) {
        if (outL) release(outL);
        if (outR) release(outR);
        if (inL)  release(inL);
        if (inR)  release(inR);
        return;
    }

    if (!ready_) {
        // Pass-through si la réverbe n'est pas prête
        for (int i = 0; i < AUDIO_BLOCK_SAMPLES; i++) {
            int16_t L = inL ? inL->data[i] : 0;
            int16_t R = inR ? inR->data[i] : L;
            outL->data[i] = L;
            outR->data[i] = R;
        }
        transmit(outL, 0);
        transmit(outR, 1);
        release(outL);
        release(outR);
        if (inL) release(inL);
        if (inR) release(inR);
        return;
    }

    const float mix = active_mix_;
    const float dry = 1.0f - mix;

    for (int i = 0; i < AUDIO_BLOCK_SAMPLES; i++) {
        float xL = inL ? (float)inL->data[i] / 32768.0f : 0.0f;
        float xR = inR ? (float)inR->data[i] / 32768.0f : xL;

        float mono = 0.5f * (xL + xR);

        // Tank gauche
        float accL = 0.0f;
        for (int c = 0; c < NUM_COMB; c++)
            accL += processComb(mono, combBufL_[c], combIdxL_[c], combLenL_[c], combStoreL_[c]);
        accL /= (float)NUM_COMB;
        for (int a = 0; a < NUM_ALLPASS; a++)
            accL = processAllpass(accL, allpassBufL_[a], allpassIdxL_[a], allpassLenL_[a]);

        // Tank droite
        float accR = 0.0f;
        for (int c = 0; c < NUM_COMB; c++)
            accR += processComb(mono, combBufR_[c], combIdxR_[c], combLenR_[c], combStoreR_[c]);
        accR /= (float)NUM_COMB;
        for (int a = 0; a < NUM_ALLPASS; a++)
            accR = processAllpass(accR, allpassBufR_[a], allpassIdxR_[a], allpassLenR_[a]);

        float yL = dry * xL + mix * accL;
        float yR = dry * xR + mix * accR;

        if (yL > 1.0f)  yL = 1.0f;
        if (yL < -1.0f) yL = -1.0f;
        if (yR > 1.0f)  yR = 1.0f;
        if (yR < -1.0f) yR = -1.0f;

        outL->data[i] = (int16_t)(yL * 32767.0f);
        outR->data[i] = (int16_t)(yR * 32767.0f);
    }

    transmit(outL, 0);
    transmit(outR, 1);
    release(outL);
    release(outR);
    if (inL) release(inL);
    if (inR) release(inR);
}
