#pragma once

#include "daisy_seed.h"
#include "daisysp.h"
#include "../include/funbox.h"

#include <q/fx/biquad.hpp>
#include "Util/Multirate.h"
#include "Util/OctaveGenerator.h"
#include "../Effect.h"

namespace q = cycfi::q;

using namespace daisy;
using namespace daisysp;
using namespace funbox; 


class EarthEffect : public Effect {
public:

    daisy::DaisySeed& hw;

    float dryMix;
    float wetMix;


    Decimator2 decimate2;
    Interpolator interpolate;
    OctaveGenerator octave;
    q::highshelf eq1;
    q::lowshelf eq2;
    float buff[6];
    float buff_out[6];
    int bin_counter = 0;

    float current_ODswell;

    int effect_mode = 0;

    Overdrive overdrive;
    bool odOn = false;
    bool bypass = false;

    // Control States
    int fs_action = 2;   // 1=OD, 2=Octave
    bool octave_only = false;
    bool momentary_active = false;

    EarthEffect(daisy::DaisySeed& hw, float sampleRate); 

    void midiUpdate();

    void update(const float** in, float** out, int idx) override;
    float updateTest(const float in, float out, int idx) override;

    void SetMix(float mix);                // Ctrl 2 (0.0 -> 1.0)
    
    void SetOctaveMode(int mode);          // 3-Way Switch 2 (0, 1, 2)
    void SetFootswitchAction(int action);  // 3-Way Switch 3 (1, 2)
    
    void SetOctaveOnlyMode(bool enable);         // Dip Switch 2
    
    void SetMomentaryAction(bool active);        // FS 2

    void SetParameter(int param_id, float value) override;
};
