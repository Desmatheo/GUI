#define USE_DAISY_POD 1
#define CPU_METER 1
#define SD_CARD_DS 0
#define Padding_on 0

#if USE_DAISY_POD
#include "daisy_pod.h"
#else
#include "daisy_seed.h"
#endif

#if SD_CARD_DS 
#include "include/WavHexaPlayer.h"
#endif

#include "EffectEarth/Earth.h"
#include "EffectUranus/Uranus.h"
#include "EffectNeptune/Neptune.h"
#include "EffectPitchShifter/EffectPitchShifter.h"
#include "EffectPitchbkshep/pitch_shifter_module.h"
#include <new> // Nécessaire pour le "placement new"
#include <cstring> // Nécessaire pour memset

#include "main.h"

using namespace daisy;

StringUtil strings[] = {
    StringUtil(EffectType::Bypass, 0),
    StringUtil(EffectType::Bypass, 1),
    StringUtil(EffectType::Bypass, 2),
    StringUtil(EffectType::Bypass, 3),
    StringUtil(EffectType::Bypass, 4),
    StringUtil(EffectType::Bypass, 5)
};

#if USE_DAISY_POD
DaisyPod hardware;

bool volatile btnSwitchEffet = false;
bool volatile btnSwitchparam = false;
uint32_t last_blink;
bool led_state;

#else
DaisySeed hardware;
#endif

#if CPU_METER
CpuLoadMeter loadMeter;
#endif


#if SD_CARD_DS
SdmmcHandler   sdcard;
FatFSInterface fsi;
WavHexaPlayer  sampler;
#endif

paramUtil effectParams(3); // On indique qu'il y a 3 paramètres pour l'instant (PitchShifter)

// Allocation dans l'espace mémoire
alignas(EarthEffect) static uint8_t earth_mem[6 * sizeof(EarthEffect)]; // Placé en SRAM interne ultra-rapide !
alignas(UranusEffect) static uint8_t DSY_SDRAM_BSS uranus_mem[6 * sizeof(UranusEffect)];
alignas(NeptuneEffect) static uint8_t DSY_SDRAM_BSS neptune_mem[6 * sizeof(NeptuneEffect)];
alignas(PitchShiftEffect) static uint8_t DSY_SDRAM_BSS pitchshift_mem[6 * sizeof(PitchShiftEffect)];
alignas(bkshepherd::PitchShifterModule) static uint8_t DSY_SDRAM_BSS pitchshiftbkshep_mem[6 * sizeof(bkshepherd::PitchShifterModule)];



void changeEffect(){
    EffectType current = strings[idxString].type;
    if(current == EffectType::Bypass) {
        strings[idxString].type = EffectType::Mute;
        strings[idxString].active_effect = nullptr;
    } else if (current == EffectType::Mute) {
        strings[idxString].type = EffectType::Earth;
        strings[idxString].active_effect = earth_effects[idxString];
    } else if(current == EffectType::Earth) {
        strings[idxString].type = EffectType::PitchShift;
        strings[idxString].active_effect = pitchshift_effects[idxString];
    } else if(current == EffectType::PitchShift) {
        strings[idxString].type = EffectType::pitchShiftbkshep;
        strings[idxString].active_effect_module = pitchshiftbkshep_effects[idxString];
        strings[idxString].active_effect = nullptr;
    } else if(current == EffectType::pitchShiftbkshep) {
    //     strings[idxString].type = EffectType::Uranus;
    //     strings[idxString].active_effect = uranus_effects[idxString];
    // } else if(current == EffectType::Uranus) {
        strings[idxString].type = EffectType::Neptune;
        strings[idxString].active_effect = neptune_effects[idxString];
        strings[idxString].active_effect_module = nullptr;
    } else {
        strings[idxString].type = EffectType::Bypass;
        strings[idxString].active_effect = nullptr;
            strings[idxString].active_effect_module = nullptr;
    }
}

void updateUI(){

#if USE_DAISY_POD
        hardware.ProcessAnalogControls();
        hardware.ProcessDigitalControls();
        
        bool button_pressed = false;

        // Si on tourne l'encodeur
        int enc_inc = hardware.encoder.Increment(); 
        if (enc_inc != 0) {
            effectParams.changeParam(enc_inc);
            effectParams.changing = false;
            button_pressed = true; // Force la mise à jour des LEDs sans attendre
        }

        // Si on appuis sur l'encodeur
        if (hardware.encoder.RisingEdge()) {
            effectParams.changing = !effectParams.changing; // Toggle On/Off du mode édition
            button_pressed = true; 
        }

        // Si on clique sur le bouton 1, on change d'effet
        if(hardware.button1.RisingEdge()) {
            changeEffect();
            effectParams.changing = false; // Quitte le mode édition par sécurité
            button_pressed = true;
        }
        
        // Si on clique sur le bouton 2, on sélectionne la corde suivante
        if(hardware.button2.RisingEdge()) {
            idxString = (idxString + 1) % 6;
            effectParams.changing = false; // Quitte le mode édition par sécurité
            button_pressed = true;
        }

        // Timer non-bloquant : on fait clignoter la LED toutes les 500ms
        if(System::GetNow() - last_blink > 500 || button_pressed) {
            
            if (button_pressed) {
                led_state = true; // Allume tout de suite pour voir le changement
            }
            last_blink = System::GetNow();


            // Affiche la couleur de l'effet assigné à la CORDE ACTUELLE
            EffectType current = strings[idxString].type;
            float r = 0.f, g = 0.f, b = 0.f;
            
            if (led_state) {
                if (current == EffectType::Bypass) {
                    r = 1.f; // Rouge
                } else if (current == EffectType::Earth) {
                    g = 1.f; // Vert classique
                } else if (current == EffectType::PitchShift) {
                    r = 1.f; g = 1.f; // Jaune
                } else if (current == EffectType::pitchShiftbkshep) {
                    r = 1.f; g = 1.f; b = 1.f; // Blanc
                } else if (current == EffectType::Uranus) {
                    b = 1.f; // Bleu
                } else if (current == EffectType::Neptune) {
                    g = 1.f; b = 1.f; // Cyan
                }
            }

            hardware.led1.Set(r, g, b); 


            led_state = !led_state;
        }

        // --- Affiche la couleur du paramètre sélectionné sur la LED 2 ---
        int current_param = effectParams.GetParam();
        float r2 = 0.f, g2 = 0.f, b2 = 0.f;
        
        // Si on édite le paramètre, on fait clignoter la LED en synchro avec la LED 1
        // led_state est inversé à la fin du timer, on regarde donc !led_state
        bool led2_active = !effectParams.changing || !led_state;

        if (led2_active) {
            if (current_param == 0) {
                r2 = 1.f; // Rouge pour le Paramètre 0 (ex: Transposition)
            } else if (current_param == 1) {
                b2 = 1.f; // Bleu pour le Paramètre 1 (ex: Mix)
            } else if (current_param == 2) {
                g2 = 1.f; // Vert pour le Paramètre 2 (ex: Feedback)
            }
        }
        hardware.led2.Set(r2, g2, b2);

        hardware.UpdateLeds();
#else
        if(System::GetNow() - last_blink > 500) {
            last_blink = System::GetNow();
            hardware.SetLed(led_state);
        
            led_state = !led_state;
        }
#endif
}

void AudioCallback(AudioHandle::InputBuffer in, AudioHandle::OutputBuffer out, size_t size) {
#if CPU_METER
#if !CPU_LoadEffect
    loadMeter.OnBlockStart();
#elif CPU_LoadAll
    loadMeter.OnBlockStart();
#endif
#endif

    float pot1_val = 0.0f;

    //parcourt les echantillons du buffer
    for (int i = 0; i < (int)size; i++){
        // Audio de sortie (cumulé des 6 entrées)
        float mixed_out_l = 0.0f;
        float mixed_out_r = 0.0f;

        for (int j = 0; j < 6; j++){
            float out_arr[2][1] = {{0.0f}, {0.0f}};
            float* out_ptrs[2] = {out_arr[0], out_arr[1]};

            // Si la corde est mute on met a 0 sans chercher le sample d'entrée
            if (strings[j].type == EffectType::Mute) {
                out_arr[0][0] = 0;
                out_arr[1][0] = 0;
            }
            else {

#if SD_CARD_DS
                float sample = s162f(sampler.StreamHex(j));
                float in_arr[2][1] = {{sample}, {sample}};
#else 
                float in_arr[2][1] = {{in[0][i]}, {in[1][i]}};    
#endif
                const float* in_ptrs[2] = {in_arr[0], in_arr[1]};


                if (strings[j].type == EffectType::Bypass) {
                    out_arr[0][0] = in_arr[0][0];
                    out_arr[1][0] = in_arr[1][0];
                } else if (strings[j].type == EffectType::Mute) {
                    out_arr[0][0] = 0;
                    out_arr[1][0] = 0;
                } else if (strings[j].active_effect != nullptr) {
                    strings[j].active_effect->update(in_ptrs, out_ptrs, 0);
                    // On met à jour UNIQUEMENT si c'est la corde sélectionnée à l'écran ET qu'on édite
                    if (effectParams.changing && j == idxString && i == 0) { 
                        pot1_val = hardware.knob1.Process(); 
                        strings[j].active_effect->SetParameter(effectParams.GetParam(), pot1_val);
                    }
                } else if (strings[j].active_effect_module != nullptr) {
                    strings[j].active_effect_module->ProcessStereo(in_arr[0][0], in_arr[1][0]);
                    out_arr[0][0] = strings[j].active_effect_module->GetAudioLeft();
                    out_arr[1][0] = strings[j].active_effect_module->GetAudioRight();
                    
                    if (effectParams.changing && j == idxString && i == 0) { 
                        pot1_val = hardware.knob1.Process(); 
                        strings[j].active_effect_module->SetParameterAsMagnitude(effectParams.GetParam(), pot1_val);
                    }
                }
            }

#if Padding_on
            mixed_out_l += out_arr[0][0] * ((j + 1) / 6.0f);
            mixed_out_r += out_arr[1][0] * (1 - ((j + 1) / 6.0f));
#else 
            mixed_out_l += out_arr[0][0];
            mixed_out_r += out_arr[1][0];
#endif
        }
        out[0][i] = mixed_out_l ;// / 6.0f;
        out[1][i] = mixed_out_r ;// / 6.0f;
    };
#if CPU_METER
#if !CPU_LoadEffect
    loadMeter.OnBlockEnd();
#elif CPU_LoadAll
    // À la fin du bloc audio, on sauvegarde la somme des cycles pour l'affichage, et on remet à 0
    if (earth_effects[0] != nullptr) {
        earth_effects[0]->last_profiled_ticks = earth_effects[0]->profiled_ticks;
        earth_effects[0]->profiled_ticks = 0;
    }
    loadMeter.OnBlockEnd();
#else 
    // À la fin du bloc audio, on sauvegarde la somme des cycles pour l'affichage, et on remet à 0
    if (earth_effects[0] != nullptr) {
        earth_effects[0]->last_profiled_ticks = earth_effects[0]->profiled_ticks;
        earth_effects[0]->profiled_ticks = 0;
    }
#endif
#endif
}

int main(void)
{
    float samplerate;

    // Initialisation du matériel cible
#if USE_DAISY_POD
    // Initialise le Daisy Pod (codec audio, contrôles, LEDs, etc.)
    hardware.Init();

    // Allume la LED en Bleu pour indiquer le début de l'allocation mémoire
    hardware.led1.Set(0.f, 0.f, 1.f); // Bleu
    hardware.UpdateLeds();
#else
    // Configure et initialise la Daisy Seed seule
    hardware.Configure();
    hardware.Init();

    hardware.SetLed(true);
#endif

#if SD_CARD_DS
    SdmmcHandler::Config sd_cfg;
    sd_cfg.Defaults();
    sdcard.Init(sd_cfg);
    fsi.Init(FatFSInterface::Config::MEDIA_SD);
    f_mount(&fsi.GetSDFileSystem(), "/", 1);

    sampler.Init(fsi.GetSDPath());
    
    // Ouvre les 6 fichiers
    for(int i = 0; i < 6; i++) {
        if (i < sampler.GetNumberFiles()) {
            sampler.OpenHex(i, i);
            sampler.SetLoopingHex(i, true);
        }
    }
#endif

    // Configuration audio commune
    hardware.SetAudioBlockSize(48); // LIMITE LIBDAISY : la taille max est de 128. 48 est sûr et multiple de 6.
    samplerate = hardware.AudioSampleRate();

#if CPU_METER
    // Initialisation du module de mesure CPU
    hardware.seed.StartLog(true);
    loadMeter.Init(hardware.AudioSampleRate(), hardware.AudioBlockSize());
#endif

    // La SDRAM n'est pas mise à zéro par défaut. On la vide pour éviter des bruits stridents dans la reverb.
    memset(earth_mem, 0, 6 * sizeof(EarthEffect));
    memset(uranus_mem, 0, 6 * sizeof(UranusEffect));
    memset(neptune_mem, 0, 6 * sizeof(NeptuneEffect));
    memset(pitchshift_mem, 0, 6 * sizeof(PitchShiftEffect));
    memset(pitchshiftbkshep_mem, 0, 6 * sizeof(bkshepherd::PitchShifterModule));


    // Instanciation des 6 blocs d'effets en SDRAM
    for (int j = 0; j < 6; j++) {
#if USE_DAISY_POD
        earth_effects[j] = new(&earth_mem[j * sizeof(EarthEffect)]) EarthEffect(hardware.seed, samplerate);
        uranus_effects[j] = new(&uranus_mem[j * sizeof(UranusEffect)]) UranusEffect(hardware.seed, samplerate);
        neptune_effects[j] = new(&neptune_mem[j * sizeof(NeptuneEffect)]) NeptuneEffect(hardware.seed, samplerate);
        pitchshift_effects[j] = new(&pitchshift_mem[j * sizeof(PitchShiftEffect)]) PitchShiftEffect(hardware.seed, samplerate);
        pitchshiftbkshep_effects[j] = new(&pitchshiftbkshep_mem[j * sizeof(bkshepherd::PitchShifterModule)]) bkshepherd::PitchShifterModule();
        pitchshiftbkshep_effects[j]->Init(samplerate);
#else
        earth_effects[j] = new(&earth_mem[j * sizeof(EarthEffect)]) EarthEffect(hardware, samplerate);
        uranus_effects[j] = new(&uranus_mem[j * sizeof(UranusEffect)]) UranusEffect(hardware, samplerate);
        neptune_effects[j] = new(&neptune_mem[j * sizeof(NeptuneEffect)]) NeptuneEffect(hardware, samplerate);
        pitchshift_effects[j] = new(&pitchshift_mem[j * sizeof(PitchShiftEffect)]) PitchShiftEffect(hardware, samplerate);
        pitchshiftbkshep_effects[j] = new(&pitchshiftbkshep_mem[j * sizeof(bkshepherd::PitchShifterModule)]) bkshepherd::PitchShifterModule();
        pitchshiftbkshep_effects[j]->Init(samplerate);
#endif
    }

    // Allume la LED en Vert pour prouver que l'allocation a réussi et que la carte n'a pas planté
#if USE_DAISY_POD
        hardware.led1.Set(0.f, 1.f, 0.f); // Vert
        hardware.UpdateLeds();
        System::Delay(500);
        hardware.led1.Set(0.f, 0.f, 0.f); // Éteint
        hardware.UpdateLeds();
#else
        hardware.SetLed(false);
#endif

    hardware.StartAdc();
    hardware.StartAudio(AudioCallback);

    led_state = true;
    last_blink = System::GetNow();

    uint32_t last_ui_update = System::GetNow();

    // Loop forever
    while(1)
    {
        // Met à jour les boutons et LEDs toutes les 1 ms sans bloquer le CPU
        if (System::GetNow() - last_ui_update >= 1) {
            last_ui_update = System::GetNow();
            updateUI();
        }
        
#if CPU_METER
        static uint32_t last_print = System::GetNow();
        if(System::GetNow() - last_print > 1000) {
            last_print = System::GetNow();
            
            float avgLoad = loadMeter.GetAvgCpuLoad();
            float maxLoad = loadMeter.GetMaxCpuLoad();
            

#if !CPU_LoadEffect
            hardware.seed.PrintLine("Charge CPU Moyenne : %d%% | Max : %d%%", 
                        (int)(avgLoad * 100.0f), 
                        (int)(maxLoad * 100.0f));
#else
            // 480 000 ticks correspondent au temps CPU max disponible pour 1 bloc audio (1 ms)
            // On divise nos ticks par ça pour avoir un pourcentage de charge CPU exact de la fonction ciblée
            float specificLoad = ((float)earth_effects[0]->last_profiled_ticks / 480000.0f) * 100.0f;
            hardware.seed.PrintLine("Charge fonction cible : %d%%", (int)specificLoad);
#if CPU_LoadAll
            hardware.seed.PrintLine("Charge CPU Moyenne : %d%% | Max : %d%%", 
                        (int)(avgLoad * 100.0f), 
                        (int)(maxLoad * 100.0f));
#endif

#endif
        }
#endif

#if SD_CARD_DS
        sampler.update();    
#endif

    }
}