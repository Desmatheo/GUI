

/*
  AudioEffectDrive.cpp
  Implémentation d'un overdrive / waveshaper avec courbes sélectionnables, drive en dB, tone (filtre) et mix.

  Remarques importantes :
  - Les allocations en PSRAM/EXTMEM utilisent extmem_malloc/extmem_free quand c'est nécessaire.
  - Les paramètres sont conçus pour être modifiables à chaud ; certaines transitions sont lissées pour éviter des clics.
*/

#include "AudioEffectDrive.h"
#include <math.h>
#include <string.h> // memset
#include "../../include/Utils.h"

AudioEffectDrive::AudioEffectDrive()
: AudioStream(1, inputQueueArray_)
{
    updateToneCoeffs();
}

AudioEffectDrive::~AudioEffectDrive()
{
    if (table_) {
        if (use_extmem_) {
            extmem_free(table_);
        } else {
            free(table_);
        }
        table_ = nullptr;
    }
    ready_ = false;
}

// --- Initialisation PSRAM : allocation de la LUT ---
bool AudioEffectDrive::begin(uint32_t table_len)
{
    if (table_len < 256) table_len = 256;   // minimum raisonnable
    // alignement sur 32
    table_len = (table_len + 31u) & ~31u;

    table_len_ = table_len;

    // On tente la PSRAM
    table_ = (int16_t*)extmem_malloc(table_len_ * sizeof(int16_t));
    if (table_) {
        use_extmem_ = true;
        rebuildTable();
        ready_ = true;
        return true;
    }
    
    table_ = nullptr;
    use_extmem_ = false;
    ready_ = false;
    return false;
}

// --- Mise à jour des coefficients du low-pass 1er ordre ---
void AudioEffectDrive::updateToneCoeffs()
{
    float fc = (tone_hz_ < 800.0f) ? 800.0f : (tone_hz_ > 8000.0f) ? 8000.0f : tone_hz_;
    tone_hz_ = fc;

    float fs = AUDIO_SAMPLE_RATE_EXACT;
    float alpha = expf(-2.0f * (float)PI * fc / fs);

    // y[n] = (1-alpha)*x[n] + alpha*y[n-1]
    tone_a0_ = 1.0f - alpha;
    tone_b1_ = alpha;
}

// --- Paramètres ---

void AudioEffectDrive::setDriveDb(float dB)
{
    drive_dB_   = (dB < 0.0f) ? 0.0f : (dB > 30.0f) ? 30.0f : dB;
    drive_gain_ = powf(10.0f, drive_dB_ / 20.0f);
}

void AudioEffectDrive::setToneHz(float hz)
{
    tone_hz_ = hz;
    updateToneCoeffs();
}

void AudioEffectDrive::setMix(float mix)
{
    mix_        = (mix < 0.0f) ? 0.0f : (mix > 1.0f) ? 1.0f : mix;
    active_mix_ = enabled_ ? mix_ : 0.0f;
}

void AudioEffectDrive::setVolume(float vol)
{
    volume_ = (vol < 0.0f) ? 0.0f : (vol > 1.0f) ? 1.0f : vol;
}

void AudioEffectDrive::setCurve(curve_t c)
{
    curve_ = c;
    if (ready_ && table_) {
        rebuildTable();
    }
}

void AudioEffectDrive::setParams(float drive_dB, float tone_hz, float mix, curve_t curve)
{
    setDriveDb(drive_dB);
    tone_hz_ = tone_hz;
    updateToneCoeffs();
    setMix(mix);
    setCurve(curve);
}

void AudioEffectDrive::setParameter(int param_id, float value)
{
    switch (param_id) {
        case 0:
            setDriveDb(value * 30.0f);            // Gain (0 à 30 dB)
            break;
        case 1:
            setToneHz(800.0f + value * 7200.0f);  // Tone (800 à 8000 Hz)
            break;
        case 2:
            setMix(value);                        // Mix (0 à 1)
            break;
        case 5:
            setVolume(value);                     // Level / Volume (0 à 1)
            break;
        default:
            Serial.print("Parametre invalide: ");
            Serial.println(param_id);
            break;
    }
}


// ON/OFF soft basé sur le mix
void AudioEffectDrive::setEnabled(bool e)
{
  // Active/désactive l’effet sans casser la continuité : on conserve les paramètres internes.

    enabled_    = e;
    active_mix_ = enabled_ ? mix_ : 0.0f;
}

// --- Courbe théorique pour remplir la LUT ---
float AudioEffectDrive::evalCurve(curve_t c, float x)
{
    // sécurité
    if (x > 3.0f)  x = 3.0f;
    if (x < -3.0f) x = -3.0f;

    switch (c) {
        case CURVE_SOFT:
        default:
            // Soft clip polynomial : f(x) = x - x^3/3
            return x - (x * x * x) / 3.0f;

        case CURVE_HARD: {
            const float th = 0.5f;
            if (x >  th) return th;
            if (x < -th) return -th;
            return x;
        }

        case CURVE_TANH:
            return tanhf(x);

        case CURVE_ASYM:
            if (x >= 0.0f) {
                return tanhf(0.8f * x);
            } else {
                return 0.5f * tanhf(1.4f * x);
            }
    }
}

// --- Reconstruction de la LUT en PSRAM ---
void AudioEffectDrive::rebuildTable()
{
    if (!table_ || table_len_ == 0) return;

    for (uint32_t i = 0; i < table_len_; ++i) {
        // Map i dans [-1, +1]
        float t = (float)i / (float)(table_len_ - 1); // 0..1
        float x = 2.0f * t - 1.0f;                    // -1..1

        float y = evalCurve(curve_, x);
        if (y > 1.0f)  y = 1.0f;
        if (y < -1.0f) y = -1.0f;

        table_[i] = (int16_t)(y * 32767.0f);
    }
}

// --- Lookup dans la LUT : x ∈ [-1,1] -> y ∈ [-1,1] ---
inline float AudioEffectDrive::shapeSampleLut(float x) const
{
    if (!table_ || table_len_ == 0) return x;

    // Clip dans [-1,1]
    if (x > 1.0f)  x = 1.0f;
    if (x < -1.0f) x = -1.0f;

    float pos = (x + 1.0f) * 0.5f * (float)(table_len_ - 1); // 0..len-1
    uint32_t idx0 = (uint32_t)pos;
    float frac = pos - (float)idx0;
    uint32_t idx1 = idx0 + 1;
    if (idx1 >= table_len_) idx1 = table_len_ - 1;

    float y0 = (float)table_[idx0] / 32768.0f;
    float y1 = (float)table_[idx1] / 32768.0f;
    return y0 + (y1 - y0) * frac;
}

// --- Traitement audio ---
void AudioEffectDrive::update()
{
    audio_block_t* in = receiveReadOnly(0);
    if (!in) return;

    audio_block_t* out = allocate();
    if (!out) {
        release(in);
        return;
    }

    // Si pas prêt ou pas de LUT => pass-through
    if (!ready_ || !table_) {
        memcpy(out->data, in->data, sizeof(out->data));
        transmit(out, 0);
        release(out);
        release(in);
        return;
    }

    const float mix  = active_mix_;     // 0..1 (0 si disabled)
    const float one_minus_mix = 1.0f - mix;
    const float drive_gain = drive_gain_;
    float z1 = tone_z1_;

    for (int i = 0; i < AUDIO_BLOCK_SAMPLES; ++i) {
        float x = (float)in->data[i] / 32768.0f;  // dry [-1,1]
        float dry = x * 0.5;

        // Pré-gain (drive)
        float xd = x * drive_gain;

        // Waveshaper via LUT en PSRAM
        float ws = shapeSampleLut(xd);

        // Low-pass post-drive
        float yLP = tone_a0_ * ws + tone_b1_ * z1;
        z1 = yLP;

        // Ajustement du niveau de l'effet (Level)
        float wet = yLP * volume_;

        // Mix dry/wet
        float y = one_minus_mix * dry + mix * wet;

        // clamp & convert
        if (y > 1.0f)  y = 1.0f;
        if (y < -1.0f) y = -1.0f;
        out->data[i] = (int16_t)(y * 32767.0f);
    }

    tone_z1_ = z1;

    transmit(out, 0);
    release(out);
    release(in);
}
