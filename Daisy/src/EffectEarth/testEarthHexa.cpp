// Earth Reverbscape

#include "daisy_petal.h"
#include "daisysp.h"
#include "../include/funbox.h"

#include <float.h>

#include "../Dattorro/Dattorro.hpp"


#include <q/fx/biquad.hpp>
#include <q/support/literals.hpp>
#include <span>
#include "Util/Multirate.h"
#include "Util/OctaveGenerator.h"
namespace q = cycfi::q;
using namespace q::literals;

using namespace daisy;
using namespace daisysp;
using namespace funbox; 



// Declare a local daisy_petal for hardware access
DaisyPetal hw;
bool      bypass;

float dryMix;
float wetMix;

Dattorro reverb(48000, 16, 4.0);   // samplerate, max_lfo_depth, max_timescale
int effect_mode = 0;

static Decimator2 decimate;
static Interpolator interpolate;
static const auto sample_rate_temp = 48000; //hard code for now                          // NOTE: the sample_rate must be divisible by the resample_factor (48/6 = 8)
static OctaveGenerator octave(sample_rate_temp / resample_factor); // resample_factor is defined in Multirate.h and equals 6
static q::highshelf eq1(-11, 140_Hz, sample_rate_temp);
static q::lowshelf eq2(5, 160_Hz, sample_rate_temp);
float buff[6];
float buff_out[6];
int bin_counter = 0;

float current_ODswell;


Overdrive overdrive;
Overdrive overdrive2;
bool odOn = false;
// This runs at a fixed rate, to prepare audio samples
static void AudioCallback(AudioHandle::InputBuffer  in,
                          AudioHandle::OutputBuffer out,
                          size_t                    size)
{

    // Knob and Expression Processing ////////////////////



    // Set Reverb Parameters ///////////////



    // Dipswitch 1 disables input diffusion (turn switch to on position to disable input diffusion)

    float inputL;
    float inputR;

    effect_mode = 1;

    if(!bypass) {
        for (size_t i = 0; i < size; i++)
        {

            inputL = inputR = in[0][i];
 
            // NOTE: Octave before reverb sounds better (personal preference), and doing octave after reverb would require another 
            // polyoctave for second channel anyway
            buff[bin_counter] = inputL;
            // do calculation every 6 samples
            if (bin_counter > 4) {

                std::span<const float, resample_factor> in_chunk(&(buff[0]), resample_factor);  // std::span is c++ 20 feature

                const auto sample = decimate(in_chunk); 

                float octave_mix = 0.0;
                octave.update(sample);

                if (effect_mode != 0)
                    octave_mix += octave.up1() * 2.0;

                auto out_chunk = interpolate(octave_mix);
                for (size_t j = 0; j < out_chunk.size(); ++j)
                {
                    float mix = eq2(eq1(out_chunk[j]));

                    // const auto dry_signal = buff[j];
                    // // TODO Add dipswitch to enable octave out only when activated (currently mixing normal signal in)
                    // float dryLevel = 0.5;
                    if (effect_mode != 0)
                        buff_out[j] = mix;
                    else 
                        buff_out[j] = 0.0;
                }

            }
                // Sets increments the buffer index from 0 to 5 (workaround to adapt code)
            bin_counter += 1;
            if (bin_counter > 5)
                bin_counter = 0;


            float reverb_in = inputL;

            if (effect_mode != 0 ) { // Up oct or down oct
                reverb_in = buff_out[bin_counter]; // This adds 6 samples of latency to the octave sound
            }

            // Calculate Reverb
            reverb.process(reverb_in, reverb_in);

            // Momentary Overdrive Swell
            float reverbLeftOut = reverb.getLeftOutput();  
            float reverbRightOut = reverb.getRightOutput();
            float effectLeftOut = 0.0;
            float effectRightOut = 0.0;

            if (odOn) {
                // Really cool sound when the low octave is overdriven, like epic sci fi blade runner
                effectLeftOut = overdrive.Process(reverbLeftOut*0.25) *  (1.0 - (current_ODswell * current_ODswell * 2.8 - 0.1296)); // reduce volume as od drive goes up (otherwise way too loud)
                effectRightOut = overdrive2.Process(reverbRightOut*0.25) *  (1.0 - (current_ODswell * current_ODswell * 2.8 - 0.1296));
              
            } else {
                effectLeftOut = reverb.getLeftOutput();
                effectRightOut = reverb.getRightOutput();
            }

            float leftOutput = inputL * dryMix + effectLeftOut * wetMix * 0.4;  // 0.4 is for overall volume reduction on reverb
            float rightOutput = inputR * dryMix + effectRightOut * wetMix* 0.4;

            out[0][i] = leftOutput;
            out[1][i] = rightOutput;

        }

    } else {
        for (size_t i = 0; i < size; i++)
        {
            inputL = in[0][i];
            inputR = in[0][i];

            out[0][i] = inputL;
            out[1][i] = inputR;
        }
    }
}

// // Ajout de 'volatile' pour empêcher le compilateur de supprimer ce tableau inutilisé
// volatile float test[1 * 48];


int main(void)
{

    // for (int i = 0; i < 1 * 48; ++i) {
    //     test[i] = FLT_MAX;
    // }     


    float samplerate;

    hw.Init(true);
    //hw.SetAudioSampleRate(SaiHandle::Config::SampleRate::SAI_32KHZ);
    hw.SetAudioBlockSize(6 * 48);
    samplerate = hw.AudioSampleRate();

    float inputDampLow = 0.;
    float inputDampHigh = 0.;
    float reverbDampLow = 0.;
    float reverbDampHigh = 0.;
    float diffusion = 1.;

    reverb.setSampleRate(samplerate);

    reverb.setTimeScale(4.0);
    reverb.setPreDelay(0.0);

    reverb.setInputFilterLowCutoffPitch(10. * inputDampLow);
    reverb.setInputFilterHighCutoffPitch(10. - (10. * inputDampHigh));
    reverb.enableInputDiffusion(true);
    reverb.setDecay(0.877465);
    reverb.setTankDiffusion(diffusion * 0.7);
    reverb.setTankFilterLowCutFrequency(10. * reverbDampLow);
    reverb.setTankFilterHighCutFrequency(10. - (10. * reverbDampHigh));
    reverb.setTankModSpeed(1.0);
    reverb.setTankModDepth(0.5);
    reverb.setTankModShape(0.5); // <-- currently not controllable, maybe use dipswitch for different shape
    reverb.clear();

    // Initialize buffers for polyoctave to 0
    for (int j = 0; j < 6; ++j) {
        buff[j] = 0.0;
        buff_out[j] = 0.0;
    }

    overdrive.Init();
    overdrive.SetDrive(0.4);
    overdrive2.Init();
    overdrive2.SetDrive(0.4);

    current_ODswell= 0.4;

    // Init the LEDs and set activate bypass
    bypass = false;

    hw.StartAdc();
    hw.StartAudio(AudioCallback);

    bool led_state = false;

    while(1)
    {
        // test[tmp] = tmp;
        // tmp = (tmp + 1) % (1 * 48);

        hw.seed.SetLed(led_state);
        led_state = !led_state;

	    System::Delay(100);
    }
}