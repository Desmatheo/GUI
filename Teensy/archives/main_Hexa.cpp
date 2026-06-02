#include <Arduino.h>
#include <Audio.h>
#include "AudioEffectDelayMod.h"

void OnControlChange(byte channel, byte control, byte value);

// --- 1. CONFIGURATION DU RACK AUDIO HEXAPHONIQUE ---
AudioSynthWaveform       mesOscs[6];       // 6 générateurs de bips (1 par corde)
AudioEffectDelayMod      mesDelays[6];     // 6 delays indépendants (1 par corde)

// Pour mélanger 6 cordes, il nous faut trois Mixers (car ils ont 4 entrées max chacun)
AudioMixer4              mixerCordes1a4;   
AudioMixer4              mixerCordes5et6;  
AudioMixer4              masterMixer;      

AudioOutputUSB           usbOut;           // Sortie casque USB

// --- 2. CÂBLAGE INTERNE (PATCH CORDS) ---
// Connexions individuelles : Oscillateur -> Delay
AudioConnection          p_osc0(mesOscs[0], 0, mesDelays[0], 0);
AudioConnection          p_osc1(mesOscs[1], 0, mesDelays[1], 0);
AudioConnection          p_osc2(mesOscs[2], 0, mesDelays[2], 0);
AudioConnection          p_osc3(mesOscs[3], 0, mesDelays[3], 0);
AudioConnection          p_osc4(mesOscs[4], 0, mesDelays[4], 0);
AudioConnection          p_osc5(mesOscs[5], 0, mesDelays[5], 0);

// Connexions des Delays vers les sous-mixers
AudioConnection          p_mix0(mesDelays[0], 0, mixerCordes1a4, 0);
AudioConnection          p_mix1(mesDelays[1], 0, mixerCordes1a4, 1);
AudioConnection          p_mix2(mesDelays[2], 0, mixerCordes1a4, 2);
AudioConnection          p_mix3(mesDelays[3], 0, mixerCordes1a4, 3);

AudioConnection          p_mix4(mesDelays[4], 0, mixerCordes5et6, 0);
AudioConnection          p_mix5(mesDelays[5], 0, mixerCordes5et6, 1);

// Fusion des sous-mixers dans le master
AudioConnection          p_mast1(mixerCordes1a4, 0, masterMixer, 0);
AudioConnection          p_mast2(mixerCordes5et6, 0, masterMixer, 1);

// Master vers la sortie Stéréo (Gauche/Droite)
AudioConnection          p_outL(masterMixer, 0, usbOut, 0);
AudioConnection          p_outR(masterMixer, 0, usbOut, 1);

// --- 3. VARIABLES DU SEQUENCER (ARPEGGIO) ---
unsigned long tempsDerniereNote = 0;
int cordeCourante = 0;
float volumesCordes[6] = {0.00001f, 0.00001f, 0.00001f, 0.00001f, 0.00001f, 0.00001f};

// Fréquences réelles des 6 cordes à vide d'une guitare (E2, A2, D3, G3, B3, E4)
const float frequencesGuitare[6] = {82.41, 110.00, 146.83, 196.00, 246.94, 329.63};

void setup() {
    Serial.begin(9600);
    
    // On passe à 80 blocs de mémoire pour encaisser les 6 buffers de delay en même temps
    AudioMemory(80); 

    // Initialisation des 6 canaux
    for (int i = 0; i < 6; i++) {
        mesOscs[i].begin(WAVEFORM_TRIANGLE);
        mesOscs[i].amplitude(volumesCordes[i]);
        mesOscs[i].frequency(frequencesGuitare[i]);
        
        // Initialisation de chaque delay
        mesDelays[i].begin(800);
    }

    usbMIDI.setHandleControlChange(OnControlChange);
    Serial.println("--- SYSTEME HEXAPHONIQUE PRET ---");
}

void loop() {
    usbMIDI.read();
    unsigned long tempsActuel = millis();

    // On joue un arpeggio rapide : une corde se réveille toutes les 350 ms
    if (tempsActuel - tempsDerniereNote >= 350) {
        tempsDerniereNote = tempsActuel;
        
        // On "pince" la corde active courante
        volumesCordes[cordeCourante] = 0.3f;
        mesOscs[cordeCourante].frequency(frequencesGuitare[cordeCourante]);
        
        // On passe à la corde suivante (0, 1, 2, 3, 4, 5 puis retour à 0)
        cordeCourante = (cordeCourante + 1) % 6;
    }

    // Gestion du Decay (extinction du son) indépendant pour chaque corde
    for (int i = 0; i < 6; i++) {
        if (volumesCordes[i] > 0.00001f) {
            volumesCordes[i] *= 0.96f; // Extinction naturelle de la note
            
            if (volumesCordes[i] < 0.00001f) volumesCordes[i] = 0.00001f;
            mesOscs[i].amplitude(volumesCordes[i]);
        }
    }

    delay(2);
}

void OnControlChange(byte channel, byte control, byte value) {
    float valNorm = value / 127.0f;

    // --- TRANCHE 1 : DELAY (CC 10 à 45) ---
    if (control >= 10 && control <= 45) {
        int ccRelatif = control - 10;
        int corde = ccRelatif / 6;  // Division entière -> Donne la corde (0 à 5)
        int potard = ccRelatif % 6; // Reste -> Donne le bouton (0 à 5)

        if (corde >= 0 && corde < 6) {
            // Affichage mouchard dans la console VS Code
            Serial.print("MIDI -> Effet: DELAY | Corde: ");
            Serial.print(corde);
            Serial.print(" | Potard: P");
            Serial.print(potard + 1);
            Serial.print(" | Valeur: ");
            Serial.println(value);

            // Application du paramètre sur la corde ciblée uniquement
            if (potard == 0) mesDelays[corde].setTimeMs(valNorm * 750.0f);
            if (potard == 1) mesDelays[corde].setFeedback(valNorm * 0.95f);
            if (potard == 2) mesDelays[corde].setMix(valNorm);
            if (potard == 3) mesDelays[corde].setModRate(valNorm * 5.0f);
            if (potard == 4) mesDelays[corde].setModDepthMs(valNorm * 10.0f);
        }
    }
    
    // --- TRANCHE 2 : DISTORTION (CC 50 à 85) ---
    else if (control >= 50 && control <= 85) {
        int ccRelatif = control - 50;
        int corde = ccRelatif / 6;
        int potard = ccRelatif % 6;

        Serial.print("MIDI -> Effet: DISTO (Non instancié) | Corde: ");
        Serial.print(corde);
        Serial.print(" | Potard: P");
        Serial.println(potard + 1);
        // C'est ici qu'on branchera tes fonctions disto plus tard !
    }

    // --- TRANCHE 3 : OCTAVER (CC 90 à 125) ---
    else if (control >= 90 && control <= 125) {
        int ccRelatif = control - 90;
        int corde = ccRelatif / 6;
        int potard = ccRelatif % 6;

        Serial.print("MIDI -> Effet: OCTAVER (Non instancié) | Corde: ");
        Serial.print(corde);
        Serial.print(" | Potard: P");
        Serial.println(potard + 1);
        // C'est ici qu'on branchera tes fonctions octaver plus tard !
    }
}