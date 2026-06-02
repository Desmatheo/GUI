#include <Arduino.h>
#include <Audio.h>
#include "AudioEffectDelayMod.h"
#include "AudioEffectDrive.h"
#include "AudioEffectRev.h"

#define MODE_HEXAPHONIQUE

#ifdef MODE_HEXAPHONIQUE

    void OnControlChange(byte channel, byte control, byte value);

    #pragma region Objet audios
    AudioSynthWaveform       mesOscs[6];       //combinaison d'oscillateurs,
    AudioEffectDrive         mesDistos[6];     // reverb, distos et delays pour chaque corde
    AudioEffectDelayMod      mesDelays[6];     
    AudioEffectRev           mesReverbs[6];    

    // Comme la reverb est stéréo, il faut 2 canaux de mixage
    AudioMixer4              mixerL_1a4;   
    AudioMixer4              mixerL_5et6;  
    AudioMixer4              masterL;      

    AudioMixer4              mixerR_1a4;   
    AudioMixer4              mixerR_5et6;  
    AudioMixer4              masterR;      

    AudioOutputUSB           usbOut;           // Sortie audio de la teensy
    #pragma endregion

    #pragma region Connexions audio 
    //Source, Port de Sortie, Desrtination, Port d'Entrée)
    // Oscillateur dans la Disto
    AudioConnection p_osc_dist0(mesOscs[0], 0, mesDistos[0], 0);
    AudioConnection p_osc_dist1(mesOscs[1], 0, mesDistos[1], 0);
    AudioConnection p_osc_dist2(mesOscs[2], 0, mesDistos[2], 0);
    AudioConnection p_osc_dist3(mesOscs[3], 0, mesDistos[3], 0);
    AudioConnection p_osc_dist4(mesOscs[4], 0, mesDistos[4], 0);
    AudioConnection p_osc_dist5(mesOscs[5], 0, mesDistos[5], 0);

    // Disto dans le Delay
    AudioConnection p_dist_dly0(mesDistos[0], 0, mesDelays[0], 0);
    AudioConnection p_dist_dly1(mesDistos[1], 0, mesDelays[1], 0);
    AudioConnection p_dist_dly2(mesDistos[2], 0, mesDelays[2], 0);
    AudioConnection p_dist_dly3(mesDistos[3], 0, mesDelays[3], 0);
    AudioConnection p_dist_dly4(mesDistos[4], 0, mesDelays[4], 0);
    AudioConnection p_dist_dly5(mesDistos[5], 0, mesDelays[5], 0);

    // Delay dans la Reverb (entrée L/Mono de la Reverb)
    AudioConnection p_dly_rev0(mesDelays[0], 0, mesReverbs[0], 0);
    AudioConnection p_dly_rev1(mesDelays[1], 0, mesReverbs[1], 0);
    AudioConnection p_dly_rev2(mesDelays[2], 0, mesReverbs[2], 0);
    AudioConnection p_dly_rev3(mesDelays[3], 0, mesReverbs[3], 0);
    AudioConnection p_dly_rev4(mesDelays[4], 0, mesReverbs[4], 0);
    AudioConnection p_dly_rev5(mesDelays[5], 0, mesReverbs[5], 0);

    // Reverb gauche (entrée 0) dans le mixer Mixers gauche
    AudioConnection p_rev0_L(mesReverbs[0], 0, mixerL_1a4, 0);
    AudioConnection p_rev1_L(mesReverbs[1], 0, mixerL_1a4, 1);
    AudioConnection p_rev2_L(mesReverbs[2], 0, mixerL_1a4, 2);
    AudioConnection p_rev3_L(mesReverbs[3], 0, mixerL_1a4, 3);
    AudioConnection p_rev4_L(mesReverbs[4], 0, mixerL_5et6, 0);
    AudioConnection p_rev5_L(mesReverbs[5], 0, mixerL_5et6, 1);

    // Reverb droite (entrée 1) dans le mixer Mixers droit
    AudioConnection p_rev0_R(mesReverbs[0], 1, mixerR_1a4, 0);
    AudioConnection p_rev1_R(mesReverbs[1], 1, mixerR_1a4, 1);
    AudioConnection p_rev2_R(mesReverbs[2], 1, mixerR_1a4, 2);
    AudioConnection p_rev3_R(mesReverbs[3], 1, mixerR_1a4, 3);
    AudioConnection p_rev4_R(mesReverbs[4], 1, mixerR_5et6, 0);
    AudioConnection p_rev5_R(mesReverbs[5], 1, mixerR_5et6, 1);

    // Mixers sous-groupes dans le Masters
    AudioConnection p_mastL1(mixerL_1a4, 0, masterL, 0);
    AudioConnection p_mastL2(mixerL_5et6, 0, masterL, 1);
    AudioConnection p_mastR1(mixerR_1a4, 0, masterR, 0);
    AudioConnection p_mastR2(mixerR_5et6, 0, masterR, 1);

    // Masters -> USB 
    AudioConnection p_outL(masterL, 0, usbOut, 0);
    AudioConnection p_outR(masterR, 0, usbOut, 1);
    #pragma endregion

    
    unsigned long tempsDerniereNote = 0;
    int cordeCourante = 0;
    float volumesCordes[6] = {0.00001f, 0.00001f, 0.00001f, 0.00001f, 0.00001f, 0.00001f};
    const float frequencesGuitare[6] = {82.41, 110.00, 146.83, 196.00, 246.94, 329.63};
    
    // --- NOUVELLES VARIABLES MUTE ET BYPASS ---
    bool cordeMute[6] = {false, false, false, false, false, false};
    bool globalBypass = false;

    void setup() {
        Serial.begin(9600);

        AudioMemory(120); // on alloue une mémoire suffisante 

        #pragma region Initialisation des effets et oscillateurs
        for (int i = 0; i < 6; i++) {
            mesOscs[i].begin(WAVEFORM_TRIANGLE);
            mesOscs[i].amplitude(volumesCordes[i]);
            mesOscs[i].frequency(frequencesGuitare[i]);
            
            // Initialisation de la Disto
            mesDistos[i].begin(2048);
            mesDistos[i].setMix(0.0f); // Par défaut bypass
            
            // Initialisation de chaque delay
            mesDelays[i].begin(800);
            mesDelays[i].setMix(0.0f); // Par défaut bypass

            // Initialisation de la Reverb
            mesReverbs[i].begin();
            mesReverbs[i].setMix(0.0f); // Par défaut bypass
        }
        #pragma endregion

        usbMIDI.setHandleControlChange(OnControlChange); //Active la fonction OnControlChange() des qu'il y a un CC 
    }

    void loop() {
        usbMIDI.read();  //lire le midi via l'usb
        unsigned long tempsActuel = millis(); // temps actuel en ms depuis le démarrage du programme

        
        if (tempsActuel - tempsDerniereNote >= 400) { // on joue une corde toutes les 400 ms
            tempsDerniereNote = tempsActuel;  
            if (!cordeMute[cordeCourante]) {         // On ne joue la corde QUE si elle n'est pas muette
                volumesCordes[cordeCourante] = 0.3f; 
                mesOscs[cordeCourante].frequency(frequencesGuitare[cordeCourante]);
            }
            cordeCourante = (cordeCourante + 1) % 6; // Modulo 6 pour tourner en boucle
        }
        

        // Gestion du Decay (extinction du son) indépendant pour chaque corde
        for (int i = 0; i < 6; i++) {
            if (volumesCordes[i] > 0.00001f) {
                volumesCordes[i] *= 0.99f; // Extinction lente pour laisser résonner les notes ensemble
                
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

            if (corde >= 0 && corde < 6) {
                if (potard == 0) mesDistos[corde].setDriveDb(valNorm * 30.0f);            // Gain
                if (potard == 1) mesDistos[corde].setToneHz(800.0f + valNorm * 7200.0f);  // Tone
                if (potard == 2) mesDistos[corde].setMix(valNorm);                        // Mix
            }
        }

        // --- TRANCHE 3 : REVERB (CC 90 à 125 - Remplace l'Octaver) ---
        else if (control >= 90 && control <= 125) {
            int ccRelatif = control - 90;
            int corde = ccRelatif / 6;
            int potard = ccRelatif % 6;

            if (corde >= 0 && corde < 6) {
                if (potard == 0) mesReverbs[corde].setRoomSize(valNorm);
                if (potard == 1) mesReverbs[corde].setDamping(valNorm);
                if (potard == 2) mesReverbs[corde].setMix(valNorm);
            }
        }

        // --- TRANCHE 4 : MUTE DES CORDES INDIVIDUELLES (CC 0 à 5) ---
        else if (control >= 0 && control <= 5) {
            int corde = control;
            cordeMute[corde] = (value > 63); // Convertit MIDI(0-127) en Booléen
            if (cordeMute[corde]) {          // Si on mute, on coupe le son instantanément
                volumesCordes[corde] = 0.0f;
                mesOscs[corde].amplitude(0.0f);
            }
        }
        
        // --- TRANCHE 5 : BYPASS GLOBAL (CC 126) ---
        else if (control == 126) {
            globalBypass = (value > 63);
            for (int i = 0; i < 6; i++) {
                mesDistos[i].setEnabled(!globalBypass);
                mesDelays[i].setEnabled(!globalBypass);
                mesReverbs[i].setEnabled(!globalBypass);
            }
        }
    }
#else

    void OnControlChange(byte channel, byte control, byte value);

    #pragma region Objet audios
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
    #pragma endregion

    unsigned long tempsDerniereNote = 0;
    float volumeCourant = 0.00001f;
    int indexNote = 0;

    const float notes[] = {164.81, 220.00, 293.66, 392.00}; 

    bool isMuted = false;
    bool globalBypass = false;

    void setup() {
        Serial.begin(9600);
        AudioMemory(40); 

        monOscillateur.begin(WAVEFORM_SINE);
        monOscillateur.amplitude(volumeCourant);
        monOscillateur.frequency(notes[0]);

        // Initialisation des effets
        maDisto.begin(2048);
        maDisto.setMix(0.0f); 

        monDelay.begin(800);
        monDelay.setMix(0.0f); 

        maReverb.begin();
        maReverb.setMix(0.0f); 

        usbMIDI.setHandleControlChange(OnControlChange);
    }

    void loop() {
        usbMIDI.read();
        unsigned long tempsActuel = millis();

    
        if (tempsActuel - tempsDerniereNote >= 1200) {
            tempsDerniereNote = tempsActuel;
            
        
            monOscillateur.frequency(notes[indexNote]);
            indexNote = (indexNote + 1) % 4; // Boucle de 0 à 3
            
            if (!isMuted) {
                volumeCourant = 0.4f; 
            }
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

        
        if (control >= 10 && control <= 15) {
            if (control == 10) monDelay.setTimeMs(valNorm * 750.0f); // 
            if (control == 11) monDelay.setFeedback(valNorm * 0.95f); // 
            if (control == 12) monDelay.setMix(valNorm);
            if (control == 13) monDelay.setModRate(valNorm * 5.0f);
            if (control == 14) monDelay.setModDepthMs(valNorm * 10.0f);
        }
        
        else if (control >= 50 && control <= 55) {
            if (control == 50) maDisto.setDriveDb(valNorm * 30.0f);            
            if (control == 51) maDisto.setToneHz(800.0f + valNorm * 7200.0f);  
            if (control == 52) maDisto.setMix(valNorm);                       
        }
        
        else if (control >= 90 && control <= 95) {
            if (control == 90) maReverb.setRoomSize(valNorm);
            if (control == 91) maReverb.setDamping(valNorm);
            if (control == 92) maReverb.setMix(valNorm);
        }
    }


#endif

