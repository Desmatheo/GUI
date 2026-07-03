
/*
  AudioEffectDelayMod.cpp
  Implémentation d'un delay modulé (avec lissage de temps) et options de mix / feedback, optimisé pour buffers en PSRAM sur Teensy 4.1.

  Remarques importantes :
  - Les allocations en PSRAM/EXTMEM utilisent extmem_malloc/extmem_free quand c'est nécessaire.
  - Les paramètres sont conçus pour être modifiables à chaud ; certaines transitions sont lissées pour éviter des clics.
*/

#include "AudioEffectDelayMod.h"
#include <cstring>   // memset
#include <cstdlib>   // malloc/free

AudioEffectDelayMod::AudioEffectDelayMod()
: AudioStream(1, inputQueueArray_)
{
    // PAS d'allocation ici : on le fait dans begin()
    write_idx_ = 0;
    buf_len_   = 0;
    updateLfoDphase();
}

AudioEffectDelayMod::~AudioEffectDelayMod() {
    if (buffer_) {
        if (use_extmem_) extmem_free(buffer_);
        else             free(buffer_);
        buffer_ = nullptr;
    }
    ready_ = false;
}

bool AudioEffectDelayMod::begin(uint32_t max_delay_ms) {
    // Calcule la longueur nécessaire en échantillons :
    //   (max_delay_ms + marge modulation ~16ms) * 44.1 samples/ms
    const float samples_per_ms = AUDIO_SAMPLE_RATE_EXACT / 1000.0f;
    uint32_t need = (uint32_t)((max_delay_ms + 16) * samples_per_ms);
    if (need < 1024) need = 1024;               // minimum de sécurité
    need = (need + 127) & ~127u;                // aligne sur 128 pour le confort

    buf_len_ = need;

    // On force l'allocation dans la RAM interne standard (modif par rapprot au 1er fichier)
    buffer_ = (int16_t*)malloc(buf_len_ * sizeof(int16_t)); //modif Paul on utlisie la RAM interne 
    if (buffer_) {
        use_extmem_ = false;
        memset(buffer_, 0, buf_len_ * sizeof(int16_t));     //Paul: on initialise le buf a 0 pour éviter les pops au démarrage 
        write_idx_ = 0;
        ready_ = true;
        return true;
    }

    // Échec propre
    ready_ = false;
    buf_len_ = 0;
    return false;
}

// ---- Setters ----
void AudioEffectDelayMod::setTimeMs(float ms)      { 
    time_ms_      = clampf(ms, 0.0f, 750.0f); 
    Serial.print("Delay time fait !");
}
void AudioEffectDelayMod::setFeedback(float fb)    { 
    feedback_     = clampf(fb, 0.0f, 1.0f); 
    Serial.print("Delay Feedback fait !");
}

// mix utilisateur + mise à jour du mix effectif (ON/OFF)
void AudioEffectDelayMod::setMix(float mix) {
    mix_        = clampf(mix, 0.0f, 1.0f);
    active_mix_ = active ? mix_ : 0.0f;
    Serial.print("Delay Mix fait !");
}

void AudioEffectDelayMod::setModRate(float hz)     { mod_rate_hz_  = clampf(hz, 0.0f, 5.0f); updateLfoDphase(); }
void AudioEffectDelayMod::setModDepthMs(float ms)  { mod_depth_ms_ = clampf(ms, 0.0f, 10.0f); }


// Ancienne version Proto Projet Yes
void AudioEffectDelayMod::setParams(float time_ms, float fb, float mix, float rate_hz, float depth_ms) {
    setTimeMs(time_ms);
    setFeedback(fb);
    setMix(mix);          // met à jour mix_ + active_mix_ en fonction de enabled_
    setModRate(rate_hz);
    setModDepthMs(depth_ms);
}

// Nouvelle version Proto 
void AudioEffectDelayMod::setParameter(int param_id, float value) {
    switch (param_id){
        case 0: 
            setMix(value);
            break;
        case 1: 
            setTimeMs(value);
            break;
        case 2 : 
            setFeedback(value);
            break;
        case 3 : 
            setModRate(value);
            break;
        case 4 : 
            setModDepthMs(value);
            break;
        default : 
            Serial.print("Parametre invalide");
            Serial.println(param_id);
    };
}

void AudioEffectDelayMod::setEnabled(bool e) {
    if (e && !active) {
        // Vidage du buffer à la réactivation pour éviter de relire un "vieux" bout de son
        if (buffer_ && buf_len_ > 0) {
            memset(buffer_, 0, buf_len_ * sizeof(int16_t));
        }
    }
    active = e;
    active_mix_ = active ? mix_ : 0.0f;
}


// ---- Traitement audio ----
void AudioEffectDelayMod::update() {
  // --- Traitement audio temps réel (appelé par l’ISR audio) ---
  // On lit un bloc d’entrée, on applique le delay/modulation, puis on écrit le bloc de sortie.

    audio_block_t* in = receiveReadOnly(0);
    if (!in) return;

    if (!active || !ready_) {
        // Effet inactif ou non prêt -> Bypass (pass-through direct sans utiliser le CPU)
        transmit(in, 0);
        release(in);
        return;
    }

    audio_block_t* out = allocate();
    if (!out) { release(in); return; }

    // Pré-calculs (ms -> samples)
    const float base_samp  = time_ms_      * (AUDIO_SAMPLE_RATE_EXACT / 1000.0f);
    const float depth_samp = mod_depth_ms_ * (AUDIO_SAMPLE_RATE_EXACT / 1000.0f);
    const float mix = active_mix_;          // mix effectif (ON/OFF)
    const float fb  = feedback_;

    for (int i = 0; i < AUDIO_BLOCK_SAMPLES; ++i) { //Paul on traite échantillon par échantillon pour la modulation
        // Lecture entrée
        const int16_t x16 = in->data[i];
        float x = (float)x16 / 32768.0f;  // [-1, 1)  //Paul on les convertit en float en -1 et 1 pour les calculs (modulation, mix, feedback)

        // LFO (par sample)
        lfo_phase_ += lfo_dphase_per_sample_;
        if (lfo_phase_ >= 2.0f * PI) lfo_phase_ -= 2.0f * PI;

        // Délai courant (samples), borné par la taille du buffer - 2 (pour interp)
        float d_samples = base_samp + arm_sin_f32(lfo_phase_) * depth_samp;     // Pauldelai modulé avec la modulation sinusoïdale ( 2lignes au dessus)
        if (d_samples < 0.0f) d_samples = 0.0f;  // Paul on s'assure que le délai ne devient pas négatif 
        float maxDelay = (float)(buf_len_ - 2);  // On pour pas depasser la taille du buffer 
        if (d_samples > maxDelay) d_samples = maxDelay; //Paul on s'assure que le délai ne dépasse pas la taille du buffer 

        // Index lecture (wrap) + interpolation linéaire
        float read_idx_f = (float)write_idx_ - d_samples; // Paul on calcule l'index de lecture en soustrayant le délai modulé à l'index d'écriture
        while (read_idx_f < 0.0f) read_idx_f += (float)buf_len_; //  ???

        uint32_t r0 = (uint32_t)read_idx_f;  //Paul index entier de lecture
        uint32_t r1 = r0 + 1; if (r1 >= buf_len_) r1 = 0; //Paul index suivant pour l'interpolation linéaire (wrap)
        float frac = read_idx_f - (float)r0;   // Paul fraction pour l'interpolation linéaire

        // Paul On prend un pourcentage de l'echantillon actuelle est le reste du prochain echnatillon.
        float y0  = (float)buffer_[r0] / 32768.0f;
        float y1  = (float)buffer_[r1] / 32768.0f;
        float wet = y0 + (y1 - y0) * frac;

        // Mix dry/wet
        float y = (1.0f - mix) * x + mix * wet;

        // Écrire dans le buffer avec feedback
        float w = x + fb * wet;  // pour le nvx son on y add le feedback du son delay précédant (wet) multiplié par le feedback
        if (w > 1.0f)  w = 1.0f;
        if (w < -1.0f) w = -1.0f;       // pour eviter de saturer
        buffer_[write_idx_] = (int16_t)(w * 32767.0f);

        // Avance écriture (wrap)
        write_idx_++;
        if (write_idx_ >= buf_len_) write_idx_ = 0;

        // Sortie bornée
        if (y > 1.0f)  y = 1.0f;
        if (y < -1.0f) y = -1.0f;
        out->data[i] = (int16_t)(y * 32767.0f);
    }

    transmit(out, 0);
    release(out);
    release(in);
}
