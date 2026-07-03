#pragma once

#include "daisy_seed.h"
#include "daisysp.h"
#include "granularplayermod.h"
#include "../Effect.h"

class UranusEffect : public Effect {
public:
    static constexpr int TESTMULT = 6;
    static constexpr int MAX_SAMPLE = static_cast<int>(48000.0 / 2); // 24000
    static constexpr size_t MAX_SAMPLE_SIZET = static_cast<size_t>(TESTMULT * MAX_SAMPLE); // 144000

    daisy::DaisySeed& hardware;

    // Paramètres internes
    float dryMix = 0.5f;
    float wetMix = 0.5f;
    float vpitch = 0.0f;
    float vpitch1 = 0.0f;
    float vpitch2 = -1200.0f; // 1 octave en dessous
    float vspeed = 1.0f;
    float current_grainsize = 0.0f;
    
    float vgrain_size = 150.0f; // ms
    float vfeedback = 0.5f;
    float vwidth = 25.0f;       // ms

    bool hold = false;

    // Mémoire audio et objets DSP
    float audioSample[MAX_SAMPLE_SIZET];  
    GranularPlayerMod swarm[2];
    int sample_index = 0;

    daisysp::Oscillator LFO;
    float LFO_depth = 0.0f;

    UranusEffect(daisy::DaisySeed& hw, float sampleRate);

    void update(const float** in, float** out, int idx) override;
    float updateTest(const float in, float out, int idx) override;

    // Setters pour personnalisation
    void SetMix(float mix);

    void SetParameter(int param_id, float value) override;
};
