#pragma once

#include "daisy_seed.h"
#include "daisysp.h"
#include "delayline_oct.h"
#include "../../DaisySP/DaisySP-LGPL/Source/Filters/tone.h"
#include "../Effect.h"

using namespace daisy;
using namespace daisysp;

class NeptuneEffect : public Effect {
public:
    static constexpr size_t MAX_DELAY = static_cast<size_t>(48000 * 4.0f); // 4 secondes de delay max

    daisy::DaisySeed& hardware;

    // Paramètres internes
    float dryMix = 0.5f;
    float wetMix = 0.5f;
    float vdelayTime = 0.5f;
    float vdelayFDBK = 0.7f;

    // Lignes de delay
    DelayLineOct<float, MAX_DELAY> delayLineOctLeft;
    DelayLineOct<float, MAX_DELAY> delayLineOctRight;

    // Structure interne pour gérer proprement un canal de delay (gauche/droite)
    struct DelayChannel {
        DelayLineOct<float, MAX_DELAY>* del;
        Tone tone;
        float currentDelay = 0.0f;
        float delayTarget = 0.0f;
        float feedback = 0.0f;
        bool active = false;

        void Init(DelayLineOct<float, MAX_DELAY>* delayLine, float sampleRate);
        float Process(float in);
    };

    DelayChannel delayL;
    DelayChannel delayR;  

    NeptuneEffect(DaisySeed& hw, float sampleRate);

    void update(const float** in, float** out, int idx) override;
    float updateTest(const float in, float out, int idx) override;

    // Setters pour personnalisation
    void SetMix(float mix);
    void SetDelayTime(float time);
    void SetFeedback(float fdbk);
    void SetParameter(int param_id, float value) override;
};