#define USE_DAISY_POD 1

#if USE_DAISY_POD
#include "daisy_pod.h"
#else
#include "daisy_seed.h"
#endif

#include "EffectEarth/Earth.h"
#include "EffectUranus/Uranus.h"
#include "EffectNeptune/Neptune.h"
#include <new> // Nécessaire pour le "placement new"
#include <cstring> // Nécessaire pour memset

#include "main.h"

using namespace daisy;



Chord chords[] = {
    Chord(EffectType::Bypass, 0),
    Chord(EffectType::Bypass, 1),
    Chord(EffectType::Bypass, 2),
    Chord(EffectType::Bypass, 3),
    Chord(EffectType::Bypass, 4),
    Chord(EffectType::Bypass, 5)
};

#if USE_DAISY_POD
DaisyPod hardware;

bool volatile btnSwitchEffet = false;
bool volatile btnSwitchparam = false;

#else
DaisySeed hardware;
#endif


// Allocation d'un bloc statique en SDRAM de la taille exacte de notre classe
// alignas() est CRUCIAL pour éviter un crash d'alignement mémoire (HardFault) sur processeur ARM
alignas(EarthEffect) static uint8_t DSY_SDRAM_BSS earth_mem[sizeof(EarthEffect)];
alignas(UranusEffect) static uint8_t DSY_SDRAM_BSS uranus_mem[sizeof(UranusEffect)];
alignas(NeptuneEffect) static uint8_t DSY_SDRAM_BSS neptune_mem[sizeof(NeptuneEffect)];

void AudioCallback(AudioHandle::InputBuffer in, AudioHandle::OutputBuffer out, size_t size) {
    float mixed_in = 0;
    for (int i = 0; i < (int)size; i++){
        for (int j = 0; j < 6; j++){

        }






        // switch (selectEffect)
        // {
        //     case EffectType::Earth:
        //         if (earth_effect != nullptr)
        //         {
        //             earth_effect->update(in, out, i);
        //         }
        //         break;
        //     case EffectType::Uranus:
        //         if (uranus_effect != nullptr)
        //         {
        //             uranus_effect->update(in, out, i);
        //         }
        //         break;
        //     case EffectType::Neptune:
        //         if (neptune_effect != nullptr)
        //         {
        //             neptune_effect->update(in, out, i);
        //         }
        //     break;
        //     case EffectType::Bypass:
        //         #if USE_DAISY_POD
        //             // On additionne les entrées Gauche et Droite pour être sûr d'avoir le son,
        //             // peu importe dans quel trou vous êtes branché.
        //             mixed_in = (in[0][i] + in[1][i]); 
        //             out[0][i] = mixed_in; 
        //             out[1][i] = mixed_in;
        //         #else
        //             // Passthrough Mono vers Stéréo pour la Seed
        //             out[0][i] = out[1][i] = in[0][i];
        //         #endif
        //         break;
        //     default:
        //         #if USE_DAISY_POD
        //             // Par sécurité, on mélange aussi ici si un effet est mal configuré
        //             mixed_in = (in[0][i] + in[1][i]);
        //             out[0][i] = mixed_in;
        //             out[1][i] = mixed_in;
        //         #else
        //             out[0][i] = out[1][i] = in[0][i];
        //         #endif
        //         break;
        // }
    };

}

int main(void)
{
    float samplerate;

    // Initialisation du matériel cible
#if USE_DAISY_POD
    // Initialise le Daisy Pod (codec audio, contrôles, LEDs, etc.)
    hardware.Init();
#else
    // Configure et initialise la Daisy Seed seule
    hardware.Configure();
    hardware.Init();
#endif

    // Allume la LED en Bleu pour indiquer le début de l'allocation mémoire
#if USE_DAISY_POD
        hardware.led1.Set(0.f, 0.f, 1.f); // Bleu
        hardware.UpdateLeds();
#else
        hardware.SetLed(true);
#endif

    // Configuration audio commune
    hardware.SetAudioBlockSize(48); // LIMITE LIBDAISY : la taille max est de 256. 48 est sûr et multiple de 6.
    samplerate = hardware.AudioSampleRate();

    // La SDRAM n'est pas mise à zéro par défaut. On la vide pour éviter des bruits stridents dans la reverb.
    memset(earth_mem, 0, sizeof(EarthEffect));
    memset(uranus_mem, 0, sizeof(UranusEffect));
    memset(neptune_mem, 0, sizeof(NeptuneEffect));

    // Instanciation des effets en SDRAM
#if USE_DAISY_POD
    earth_effect = new(earth_mem) EarthEffect(hardware.seed, samplerate);
    uranus_effect = new(uranus_mem) UranusEffect(hardware.seed, samplerate);
    neptune_effect = new(neptune_mem) NeptuneEffect(hardware.seed, samplerate);
#else
    earth_effect = new(earth_mem) EarthEffect(hardware, samplerate);
    uranus_effect = new(uranus_mem) UranusEffect(hardware, samplerate);
    neptune_effect = new(neptune_mem) NeptuneEffect(hardware, samplerate);
#endif

    // Allume la LED en Vert pour prouver que l'allocation a réussi et que la carte n'a pas planté
#if USE_DAISY_POD
        hardware.led1.Set(0.f, 1.f, 0.f); // Vert
        hardware.UpdateLeds();
        System::Delay(1000);
        hardware.led1.Set(0.f, 0.f, 0.f); // Éteint
        hardware.UpdateLeds();
#else
        hardware.SetLed(false);
#endif
    System::Delay(200);

    // Valeurs par défaut pour que l'effet s'entende directement
    earth_effect->SetMix(0.5f);
    earth_effect->SetOctaveMode(1);

    // Valeurs par défaut pour Uranus
    uranus_effect->SetMix(0.5f);

    // Valeurs par défaut pour Neptune
    neptune_effect->SetMix(0.5f);
    neptune_effect->SetDelayTime(0.5f);
    neptune_effect->SetFeedback(0.7f);

    hardware.StartAdc();
    hardware.StartAudio(AudioCallback);

    bool led_state = true;
    uint32_t last_blink = System::GetNow();

    // Loop forever
    while(1)
    {
        #if USE_DAISY_POD
        hardware.ProcessAnalogControls();
        hardware.ProcessDigitalControls();

        // Si on clique sur le bouton 1, on change d'effet
        if(hardware.button1.RisingEdge()) {
            btnSwitchEffet = true;
            if(selectEffect == EffectType::Bypass) {
                selectEffect = EffectType::Earth;
            } else if(selectEffect == EffectType::Earth) {
                selectEffect = EffectType::Uranus;
            } else if(selectEffect == EffectType::Uranus) {
                selectEffect = EffectType::Neptune;
            } 
            else {
                selectEffect = EffectType::Bypass;
            }
        }
        #endif

        // Timer non-bloquant : on fait clignoter la LED toutes les 500ms
        if(System::GetNow() - last_blink > 500) {
            last_blink = System::GetNow();

#if USE_DAISY_POD
            // Clignote en rouge (Bypass), vert (Earth), bleu (Uranus) ou cyan (Neptune)
            float r = (selectEffect == EffectType::Bypass && led_state) ? 1.f : 0.f;
            float g = ((selectEffect == EffectType::Earth  || selectEffect == EffectType::Neptune) && led_state) ? 1.f : 0.f;
            float b = ((selectEffect == EffectType::Uranus || selectEffect == EffectType::Neptune) && led_state) ? 1.f : 0.f;
            hardware.led1.Set(r, g, b); 
            hardware.UpdateLeds();
#else
            hardware.SetLed(led_state);
#endif
            led_state = !led_state;
        }
        
        // Délai très court (1ms) obligatoire pour que la lecture des boutons (debouncing) fonctionne !
        System::Delay(1);
    }
}
