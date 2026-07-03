#pragma once 

#include "daisy_pod.h"
#include "daisy_seed.h"
#include "Effect.h"
#include "EffectEarth/Earth.h"
#include "EffectUranus/Uranus.h"
#include "EffectNeptune/Neptune.h"
#include "EffectPitchShifter/EffectPitchShifter.h"
#include "EffectPitchbkshep/pitch_shifter_module.h"

EarthEffect* earth_effects[6] = {nullptr};
UranusEffect* uranus_effects[6] = {nullptr};
NeptuneEffect* neptune_effects[6] = {nullptr};
PitchShiftEffect* pitchshift_effects[6] = {nullptr};
bkshepherd::PitchShifterModule* pitchshiftbkshep_effects[6] = {nullptr};

enum class EffectType {
    Mute,
    Bypass,
    Earth,
    PitchShift,
    pitchShiftbkshep,
    Uranus,
    Neptune
};

class StringUtil{
public : 
    EffectType type;
    int index;
    Effect* active_effect;
    bkshepherd::BaseEffectModule* active_effect_module;

    StringUtil(EffectType type, int index){
        this->type = type;
        this->index = index;
        this->active_effect = nullptr;
        this->active_effect_module = nullptr;
    }

    EffectType GetType() {
        return type;
    }
};

int volatile idxString = 0;

class paramUtil{
public : 
    int current_param;
    int max_params;
    bool changing = false;

    paramUtil(int max = 1){
        current_param = 0;
        max_params = max;
    }

    void setMaxParams(int max) {
        max_params = max;
        if (current_param >= max_params) current_param = 0;
    }

    // Change le paramètre sélectionné avec l'encodeur
    void changeParam(int increment) {
        if (increment == 0 || max_params <= 0) return;
        
        current_param = (current_param + increment) % max_params;
        if (current_param < 0) {
            current_param += max_params; 
        }
    }

    int GetParam() {
        return current_param;
    }
};