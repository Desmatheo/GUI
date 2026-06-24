#include <Arduino.h>
#include <Audio.h>

// Ce code transforme la Teensy en une interface audio USB 6x6.
// Il route 3 flux stéréo (6 canaux) depuis le PC vers une Daisy Seed via TDM,
// et route les 6 canaux traités de la Daisy vers le PC.

// --- 1. Objets Audio pour le routage USB <-> TDM ---

// Entrée audio depuis le PC
// L'option -D AUDIO_USB_INPUT_CHANNELS=6 active 6 canaux.
AudioInputUSB            usbIn;

// Sortie TDM vers la Daisy (envoi du son "dry")
// On utilise les 6 premiers ports (0 à 5)
AudioOutputTDM           tdmOut;

// Entrée TDM depuis la Daisy (réception du son "wet")
// On écoute les 6 premiers ports (0 à 5)
AudioInputTDM            tdmIn;

// Sortie audio vers le PC
// L'option -D AUDIO_USB_OUTPUT_CHANNELS=6 active 6 canaux.
AudioOutputUSB           usbOut;

// --- 2. Câblage (Audio Connections) ---

// Flux aller : PC -> USB -> TDM -> Daisy
// On connecte chaque canal USB à un port TDM.
// La librairie TDM utilise des ports 16 bits. On utilise uniquement les ports pairs
// pour envoyer nos données sur les 16 bits de poids fort de chaque slot 32 bits.
AudioConnection          patch_fwd_0(usbIn, 0, tdmOut, 0); // Fichier 1 (L) -> Slot 0
AudioConnection          patch_fwd_1(usbIn, 1, tdmOut, 2); // Fichier 1 (R) -> Slot 1
AudioConnection          patch_fwd_2(usbIn, 2, tdmOut, 4); // Fichier 2 (L) -> Slot 2
AudioConnection          patch_fwd_3(usbIn, 3, tdmOut, 6); // Fichier 2 (R) -> Slot 3
AudioConnection          patch_fwd_4(usbIn, 4, tdmOut, 8); // Fichier 3 (L) -> Slot 4
AudioConnection          patch_fwd_5(usbIn, 5, tdmOut, 10); // Fichier 3 (R) -> Slot 5

// Flux retour : Daisy -> TDM -> USB -> PC
// On fait le chemin inverse.
AudioConnection          patch_ret_0(tdmIn, 0, usbOut, 0); // Slot 0 -> Fichier 1 (L)
AudioConnection          patch_ret_1(tdmIn, 2, usbOut, 1); // Slot 1 -> Fichier 1 (R)
AudioConnection          patch_ret_2(tdmIn, 4, usbOut, 2); // Slot 2 -> Fichier 2 (L)
AudioConnection          patch_ret_3(tdmIn, 6, usbOut, 3); // Slot 3 -> Fichier 2 (R)
AudioConnection          patch_ret_4(tdmIn, 8, usbOut, 4); // Slot 4 -> Fichier 3 (L)
AudioConnection          patch_ret_5(tdmIn, 10, usbOut, 5); // Slot 5 -> Fichier 3 (R)

void setup() {
    Serial.begin(9600);
    
    // Allouer la mémoire pour le système audio
    // TDM est gourmand, 50 est une valeur sûre.
    AudioMemory(50);

    // Configuration TDM/I2S
    // La Teensy est le "Master" : elle génère les horloges BCLK et LRCLK.
    // La Daisy sera configurée en "Slave".

    Serial.println("Système de routage audio USB <-> TDM prêt.");
}

void loop() {
    // Le système audio fonctionne par interruptions.
    // Le loop peut rester vide ou être utilisé pour d'autres tâches
    // comme la lecture de messages MIDI pour contrôler la Daisy.
    // usbMIDI.read(); // Décommenter si vous gérez du MIDI
}
