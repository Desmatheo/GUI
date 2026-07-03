// 1 pour Daisy 0 pour Teensy
#define DAISY 0

#define MODE_HEXAPHONIQUE

#define InputTDM 1    // 1: Entrée Guitare (TDM), 0: Séquenceur d'Oscillateurs
#if InputTDM
#define OutputTDM 1   // 1: Sortie Jack CS42448 (TDM), 0: Désactivé
#endif
#define OutputUSB 1   // 1: Sortie Casque/PC (USB), 0: Désactivé
#define DelayPaulo 0



// static inline float clampf1(float v, float lo, float hi) {
//     return (v < lo) ? lo : (v > hi) ? hi : v;
// }