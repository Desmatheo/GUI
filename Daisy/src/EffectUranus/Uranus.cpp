#include "Uranus.h"
#include <cstring>

using namespace daisy;
using namespace daisysp;

UranusEffect::UranusEffect(daisy::DaisySeed& hw, float sampleRate) : hardware(hw) {
    // Initialisation de la mémoire à zéro
    memset(audioSample, 0, sizeof(audioSample));
    
    sample_index = 0;

    // Initialisation des générateurs de grains (GranularPlayers)
    swarm[0].Init(audioSample, MAX_SAMPLE, sampleRate, 0.0, 0.5);
    swarm[1].Init(audioSample, MAX_SAMPLE, sampleRate, 0.25, 0.75);

    swarm[0].setEnvelopeMode(1);
    swarm[1].setEnvelopeMode(1);

    // Espace stéréo par défaut
    for (int j = 0; j < 2; j++) {
        swarm[j].setStereoSpread(0.4);
    }

    // LFO pour moduler le pitch
    LFO.Init(sampleRate);
    LFO.SetFreq(0.25); 
    LFO.SetWaveform(0); // Onde sinusoïdale
    LFO.SetAmp(2.0); 
    LFO_depth = 0.0;   // 0 à 200 (2 demi-tons)
}

void UranusEffect::update(const float** in, float** out, int idx) {
    float input = in[0][idx];

    if (!hold) {
        float next_sample_feedback = audioSample[sample_index] * vfeedback;
        audioSample[sample_index] = next_sample_feedback + input;
        sample_index += 1;
        if (sample_index > (MAX_SAMPLE-1)) {
            sample_index = 0;
        }
    }

    float gran_out_right = 0.0;
    float gran_out_left = 0.0;

    fonepole(current_grainsize, vgrain_size, .0001f);

    float LFO_out = LFO.Process() - 1.0f;
    float pitch_mod = LFO_out * LFO_depth;

    swarm[0].Process(vspeed, vpitch + vpitch1 + pitch_mod, current_grainsize, vwidth);
    swarm[1].Process(vspeed, vpitch + vpitch2 + pitch_mod, current_grainsize, vwidth);

    gran_out_left += swarm[0].getLeftOut();
    gran_out_right += swarm[0].getRightOut();

    gran_out_left += swarm[1].getLeftOut();
    gran_out_right += swarm[1].getRightOut();
    
    out[0][idx] = gran_out_left * wetMix + input * dryMix;
    out[1][idx] = gran_out_right * wetMix + input * dryMix; 
}


float UranusEffect::updateTest(const float in, float out, int idx) {
    return in; // Implémentation factice pour satisfaire le compilateur
}

void UranusEffect::SetMix(float mix) {
    dryMix = 1.0f - mix;
    wetMix = mix;
}

void UranusEffect::SetParameter(int param_id, float value) {

}