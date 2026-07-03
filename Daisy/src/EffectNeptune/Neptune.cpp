#include "Neptune.h"

using namespace daisy;
using namespace daisysp;

void NeptuneEffect::DelayChannel::Init(DelayLineOct<float, MAX_DELAY>* delayLine, float sampleRate) {
    del = delayLine;
    del->Init();
    del->setOctave(false);
    
    tone.Init(sampleRate);
    tone.SetFreq(3000.0f);
    
    currentDelay = 2400.0f;
    delayTarget = 2400.0f;
    feedback = 0.5f;
    active = true;
}

float NeptuneEffect::DelayChannel::Process(float in) {
    // Lissage du temps de delay pour éviter les clics
    fonepole(currentDelay, delayTarget, .0002f);
    del->SetDelay(currentDelay);

    // Lecture du son retardé
    float del_read = del->Read();

    // Application du filtre passe-bas
    float read = tone.Process(del_read); 

    // Écriture dans la ligne de delay (avec feedback)
    if (active) {
        del->Write((feedback * read) + in);
    } else {
        del->Write(feedback * read);                // Si inactif, seul le feedback est réinjecté
    }

    return read;
}

NeptuneEffect::NeptuneEffect(daisy::DaisySeed& hw, float sampleRate) : hardware(hw) {
    // Initialisation des canaux de delay
    delayL.Init(&delayLineOctLeft, sampleRate);
    delayR.Init(&delayLineOctRight, sampleRate);

    // Valeurs par défaut
    SetMix(0.5f);
    SetDelayTime(0.5f);
    SetFeedback(0.7f);
}

void NeptuneEffect::update(const float** in, float** out, int idx) {
    float inputL = in[0][idx];
    float inputR = in[1][idx];


    // Traitement du son par les lignes de delay
    float delay_outL = delayL.Process(inputL);
    float delay_outR = delayR.Process(inputR);

    // Mixage du son original (dry) et du son traité (wet)
    out[0][idx] = inputL * dryMix + delay_outL * wetMix;
    out[1][idx] = inputR * dryMix + delay_outR * wetMix;
}

float NeptuneEffect::updateTest(const float in, float out, int idx) {
    return in; // Implémentation factice pour satisfaire le compilateur
}


void NeptuneEffect::SetMix(float mix) {
    wetMix = fclamp(mix, 0.0f, 1.0f);
    dryMix = 1.0f - wetMix;
}

void NeptuneEffect::SetDelayTime(float time) {
    vdelayTime = fclamp(time, 0.0f, 1.0f);
    // Mise à jour de l'état actif et de la cible du delay uniquement quand la valeur change
    bool isActive = (vdelayTime > 0.01f);
    delayL.active = isActive;
    delayR.active = isActive;

    float target = fmap(vdelayTime, 2400.0f, static_cast<float>(MAX_DELAY), Mapping::LOG);
    delayL.delayTarget = target;
    delayR.delayTarget = target;
}

void NeptuneEffect::SetFeedback(float fdbk) {
    vdelayFDBK = fclamp(fdbk, 0.0f, 0.99f);

    delayL.feedback = vdelayFDBK;
    delayR.feedback = vdelayFDBK;
}


void NeptuneEffect::SetParameter(int param_id, float value) {

}
