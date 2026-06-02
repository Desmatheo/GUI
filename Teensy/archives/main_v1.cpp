#include <Arduino.h>
#include <Audio.h>
#include "AudioEffectDelayMod.h"

void OnControlChange(byte channel, byte control, byte value);

AudioSynthWaveform       monOscillateur; 
AudioEffectDelayMod      monDelay;       
AudioOutputUSB           usbOut;         

AudioConnection          patch1(monOscillateur, 0, monDelay, 0); 
AudioConnection          patch2(monDelay, 0, usbOut, 0); 
AudioConnection          patch3(monDelay, 0, usbOut, 1); 

unsigned long dernierTemps = 0;
bool noteAllumee = false;
unsigned long lastBlink = 0;
bool ledState = false;

void setup() {
    Serial.begin(9600);
    
    AudioMemory(40); 

    monOscillateur.begin(WAVEFORM_SAWTOOTH);
    monOscillateur.amplitude(0.00001f); 
    monOscillateur.frequency(440.0);

    monDelay.begin(800);

    pinMode(LED_BUILTIN, OUTPUT);
    digitalWrite(LED_BUILTIN, LOW);

    usbMIDI.setHandleControlChange(OnControlChange);
    
    Serial.println("--- TEENSY DEMARRE ET PRET ---");
    Serial.println("Heartbeat LED enabled; audio -> USB output");
}

void loop() {
    usbMIDI.read();

    unsigned long tempsActuel = millis();

    if (tempsActuel - dernierTemps >= 1000) {
        dernierTemps = tempsActuel;
        float frequence = random(200, 800);
        monOscillateur.frequency(frequence);
        monOscillateur.amplitude(0.2f); 
        noteAllumee = true;
    }

    if (noteAllumee && (tempsActuel - dernierTemps >= 100)) {
        monOscillateur.amplitude(0.00001f); 
        noteAllumee = false;
    }

    // LED heartbeat (non bloquant)
    if (tempsActuel - lastBlink >= 500) {
        lastBlink = tempsActuel;
        ledState = !ledState;
        digitalWrite(LED_BUILTIN, ledState ? HIGH : LOW);
    }
}

void OnControlChange(byte channel, byte control, byte value) {

    Serial.print("MIDI Recu ! CC : ");
    Serial.print(control);
    Serial.print(" | Valeur : ");
    Serial.println(value);

    float valNorm = value / 127.0f;
    if (control == 10) monDelay.setTimeMs(valNorm * 750.0f);
    if (control == 11) monDelay.setFeedback(valNorm * 0.95f);
    if (control == 12) monDelay.setMix(valNorm);
}