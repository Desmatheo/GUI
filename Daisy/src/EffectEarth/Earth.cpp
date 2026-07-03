// Earth Reverbscape

#include "daisy_seed.h"
#include "daisysp.h"
#include "../include/funbox.h"

#include "Earth.h"

#include <span>
#include <q/support/literals.hpp>
namespace q = cycfi::q;
using namespace q::literals;

using namespace daisy;
using namespace daisysp;
using namespace funbox; 

#define eq_ON 1
#define od_ON 1

EarthEffect::EarthEffect(daisy::DaisySeed& hw, float sampleRate)
    : hw(hw),
      octave(sampleRate / resample_factor),
      eq1(-11, 140_Hz, sampleRate),
      eq2(5, 160_Hz, sampleRate)
{
    for (int j = 0; j < 6; ++j) {
        buff[j] = 0.0f;
        buff_out[j] = 0.0f;
    }

    SetMix(1.0f);
    SetOctaveMode(1);

#if od_ON
    overdrive.Init();
    overdrive.SetDrive(0.4f);
    current_ODswell = 0.4f;
#endif
}

void EarthEffect::update(const float** in, float** out, int idx) {
    float inputL;
    float inputR;

#if od_ON 
    // Applique l'action momentanée (Momentary Overdrive) FS2
    odOn = (momentary_active && fs_action == 1);
#endif

    // Applique l'action momentanée (Momentary Octave) FS2
    int active_effect_mode = effect_mode;
    if (momentary_active && fs_action == 2) {
        active_effect_mode = (effect_mode == 0) ? 1 : effect_mode;
    }

    inputL = inputR = in[0][idx] + 1e-9f; // Anti-denormal

    buff[bin_counter] = inputL;
    
    if (bin_counter > 4) {
        if (1) {
            std::span<const float, resample_factor> in_chunk(&(buff[0]), resample_factor);
            const auto sample = decimate2(in_chunk); 

            float octave_mix = 0.0;

#if CPU_LoadEffect
            uint32_t start_ticks = daisy::System::GetTick();
#endif
            octave.update(sample, effect_mode);
#if CPU_LoadEffect
            profiled_ticks += (daisy::System::GetTick() - start_ticks);
#endif

            if (effect_mode == 1) octave_mix += octave.up1() * 6.0;
            if (effect_mode == 2) octave_mix += octave.down1() * 6.0;
            if (effect_mode == 3) octave_mix += octave.down2() * 6.0;

            auto out_chunk = interpolate(octave_mix);
            for (size_t j = 0; j < out_chunk.size(); ++j) {
#if eq_ON
                buff_out[j] = eq2(eq1(out_chunk[j]));
#else
                buff_out[j] = out_chunk[j];
#endif
            }
        } 
        else {
            // Optimisation CPU : on ne calcule pas l'octaver s'il est coupé
            for (size_t j = 0; j < 6; ++j) {
                buff_out[j] = 0.0f;
            }
        }
    }

    // Avance le compteur de temps (0 à 5)
    bin_counter += 1;
    if (bin_counter > 5) bin_counter = 0;

    // Le signal d'effet est le son de l'octaver (ou 0 si désactivé)
    float octave_signal = buff_out[bin_counter];

    // Le signal qui va être traité par l'overdrive
    float effect_input = inputL;
    if (active_effect_mode != 0) { // Up oct or down oct
        if (1) {
            effect_input = octave_signal; // Octave only mode (Dip Switch 2)
        } else {
            effect_input = inputL + octave_signal; // Mix Dry + Octave
        }
    }

    // Le signal de sortie de la chaîne d'effet (avant le mix dry/wet)
    float effect_output = effect_input;

    // Application de l'overdrive si activé
#if od_ON
    if (odOn) {
        // Really cool sound when the low octave is overdriven, like epic sci fi blade runner
        effect_output = overdrive.Process(effect_input * 0.25f) * (1.0f - (current_ODswell * current_ODswell * 2.8f - 0.1296f));
    }
#endif

    // Mixage final dry/wet pour cet effet de corde
    out[0][idx] = inputL * dryMix + effect_output * wetMix;
    out[1][idx] = out[0][idx];
}

float EarthEffect::updateTest(const float in, float out, int idx) {
    return in; // Implémentation factice pour satisfaire le compilateur
}

// --- Implémentation des Setters Spécifiques ---

void EarthEffect::SetMix(float mix) {
    dryMix = 1.0f - mix;
    wetMix = mix;
}

void EarthEffect::SetOctaveMode(int mode) {
    effect_mode = mode;
}

void EarthEffect::SetFootswitchAction(int action) {
    fs_action = action;
}

void EarthEffect::SetOctaveOnlyMode(bool enable) {
    octave_only = enable;
}

void EarthEffect::SetMomentaryAction(bool active) {
    momentary_active = active;
}

void EarthEffect::SetParameter(int param_id, float value) {
    if (param_id == 0) {
        SetMix(value);
    } else if (param_id == 1) {
        if (value > 0.66f) SetOctaveMode(1);
        else if ((0.66f > value) && (value > 0.33f)) SetOctaveMode(2);
        else SetOctaveMode(3);
    }

}