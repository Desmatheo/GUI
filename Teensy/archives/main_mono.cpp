#include <Arduino.h>
#include <Audio.h>
#include "AudioEffectDelayMod.h"
#include "AudioEffectDrive.h"
#include "AudioEffectRev.h"

void OnControlChange(byte channel, byte control, byte value);

AudioSynthWaveform       monOscillateur; 
AudioEffectDrive         maDisto;
AudioEffectDelayMod      monDelay;       
AudioEffectRev           maReverb;
AudioOutputUSB           usbOut;         

AudioConnection          patch1(monOscillateur, 0, maDisto, 0); 
AudioConnection          patch2(maDisto, 0, monDelay, 0); 
AudioConnection          patch3(monDelay, 0, maReverb, 0); 
AudioConnection          patch4(maReverb, 0, usbOut, 0); 
AudioConnection          patch5(maReverb, 1, usbOut, 1); // La reverb sort en stéréo

unsigned long tempsDerniereNote = 0;

float volumeCourant = 0.00001f;
int indexNote = 0;

const float notes[] = {164.81, 220.00, 293.66, 392.00}; 

void setup() {
    Serial.begin(9600);
    AudioMemory(40); 

    monOscillateur.begin(WAVEFORM_SINE);
    monOscillateur.amplitude(volumeCourant);
    monOscillateur.frequency(notes[0]);

    // Initialisation des effets
    maDisto.begin(2048);
    maDisto.setMix(0.0f); // Par défaut bypass

    monDelay.begin(800);
    monDelay.setMix(0.0f); // Par défaut bypass

    maReverb.begin();
    maReverb.setMix(0.0f); // Par défaut bypass

    usbMIDI.setHandleControlChange(OnControlChange);
}

void loop() {
    usbMIDI.read();
    unsigned long tempsActuel = millis();

   
    if (tempsActuel - tempsDerniereNote >= 1200) {
        tempsDerniereNote = tempsActuel;
        
     
        monOscillateur.frequency(notes[indexNote]);
        indexNote = (indexNote + 1) % 4; // Boucle de 0 à 3
        
        
        volumeCourant = 0.4f; 
    }

    
    if (volumeCourant > 0.00001f) {
        // On diminue le volume de 2% à chaque passage dans la loop
        volumeCourant *= 0.98f; 
        
       
        if (volumeCourant < 0.00001f) volumeCourant = 0.00001f;
        
        monOscillateur.amplitude(volumeCourant);
    }
    
    
    delay(2); 
}

void OnControlChange(byte channel, byte control, byte value) {
    float valNorm = value / 127.0f;

    // --- TRANCHE 1 : DELAY (CC 10 à 15) ---
    if (control >= 10 && control <= 15) {
        if (control == 10) monDelay.setTimeMs(valNorm * 750.0f);
        if (control == 11) monDelay.setFeedback(valNorm * 0.95f);
        if (control == 12) monDelay.setMix(valNorm);
        if (control == 13) monDelay.setModRate(valNorm * 5.0f);
        if (control == 14) monDelay.setModDepthMs(valNorm * 10.0f);
    }
    // --- TRANCHE 2 : DISTORTION (CC 50 à 55) ---
    else if (control >= 50 && control <= 55) {
        if (control == 50) maDisto.setDriveDb(valNorm * 30.0f);            // Gain (0 à 30dB)
        if (control == 51) maDisto.setToneHz(800.0f + valNorm * 7200.0f);  // Tone (800 à 8000Hz)
        if (control == 52) maDisto.setMix(valNorm);                        // Mix
    }
    // --- TRANCHE 3 : REVERB (CC 90 à 95 - Remplace l'Octaver) ---
    else if (control >= 90 && control <= 95) {
        if (control == 90) maReverb.setRoomSize(valNorm);
        if (control == 91) maReverb.setDamping(valNorm);
        if (control == 92) maReverb.setMix(valNorm);
    }
}