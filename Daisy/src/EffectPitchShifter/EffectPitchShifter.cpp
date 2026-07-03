#include "EffectPitchShifter.h"

using namespace daisy;
using namespace daisysp;

PitchShiftEffect::PitchShiftEffect(daisy::DaisySeed& hw, float sampleRate) : hardware(hw) {
    // Initialisation avec la fréquence d'échantillonnage
    pitchShifterL.Init(sampleRate);
    pitchShifterR.Init(sampleRate);

    // +12 = Octave du dessus, -12 = Octave du dessous
    pitchShifterL.SetTransposition(12.0f);
    // pitchShifterR.SetTransposition(12.0f);

    // pitchShifterL.SetDelSize(16000); 

    SetMix(0.5f); 

}

void PitchShiftEffect::update(const float** in, float** out, int idx) {
    float inputL = in[0][idx];
    float inputR = in[1][idx];

    // Traitement du signal par les PitchShifters
    float pitch_outL = pitchShifterL.Process(inputL);
    // float pitch_outR = pitchShifterR.Process(inputR);

    // Mixage Dry/Wet
    out[0][idx] = pitch_outL * wetMix;
    // out[1][idx] = inputR * dryMix + pitch_outL * wetMix;
    out[1][idx] = out[0][idx];
}

float PitchShiftEffect::updateTest(const float in, float out, int idx) {
    return in;
}

void PitchShiftEffect::SetMix(float mix) {
    wetMix = fclamp(mix, 0.0f, 1.0f);
    dryMix = 1.0f - wetMix;
}

void PitchShiftEffect::SetTransposition(float semitones) {
    pitchShifterL.SetTransposition(semitones);
    // pitchShifterR.SetTransposition(semitones);
}

void PitchShiftEffect::SetDelSize(uint32_t size){
    // pitchShifterL.SetDelSize(size);
    // pitchShifterR.SetDelSize(size);
}

void PitchShiftEffect::SetParameter(int param_id, float value) {
    // "value" est la position du POT1, toujours comprise entre 0.0f et 1.0f
    if (param_id == 0) {
        // Transposition : mapping de la course [0.0, 1.0] vers des crans de [-24, +24] demi-tons
        int semi_tones = (int)(value * 24.0f) - 12; 
        SetTransposition((float)semi_tones);
    } 
    else if (param_id == 1) {
        // Mix : mapping direct [0.0, 1.0]
        SetMix(value);
    }
    // else if (param_id == 2) {
    //     // DelSize : mapping de [0.0, 1.0] vers une plage de tailles de delay (ex: 100 à 16000 échantillons)
    //     uint32_t del_size = (uint32_t)(value * 8000.0f) + 8000; 
    //     SetDelSize(del_size);
    // }
}
