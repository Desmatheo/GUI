#pragma once

#include "daisy_seed.h"
#include "daisysp.h"
#include "../Effect.h"

using namespace daisy;
using namespace daisysp;

class PitchShiftEffect : public Effect {
public:
    daisy::DaisySeed& hardware;

    // Instances de DaisySP
    PitchShifter pitchShifterL;
    PitchShifter pitchShifterR;

    float dryMix = 0.5f;
    float wetMix = 0.5f;

    PitchShiftEffect(daisy::DaisySeed& hw, float sampleRate);

    void update(const float** in, float** out, int idx) override;
    
    float updateTest(const float in, float out, int idx) override;

    void SetMix(float mix);
    
    void SetTransposition(float semitones);

    void SetDelSize(uint32_t size);

    void SetParameter(int param_id, float value) override;
};
