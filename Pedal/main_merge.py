import customtkinter as ctk
import random
import json
import os
import mido
import time
import datetime
 
# region 1. Setup et configuration Multi-Effets
 
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")
 
win = ctk.CTk()
win.title("Pédale Hexa - Contrôleur MIDI (Teensy/Daisy)")
win.geometry("1300x900")
 
# --- CONSTANTES DE CONFIGURATION ---
USE_LOOPMIDI = False  
NOM_PORT_BOUCLE = 'loopMIDI Port 1'
# -----------------------------------

# --- Chargement des presets (Cordes et Hexa) ---
presets_corde = []
presets_hexa = []
try:
    chemin_corde = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets_corde.json")
    if not os.path.exists(chemin_corde):
        with open(chemin_corde, "w") as f: json.dump({"presets": []}, f)
    with open(chemin_corde, "r") as f:
        presets_corde = json.load(f).get("presets", [])
        
    chemin_hexa = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets_hexa.json")
    if not os.path.exists(chemin_hexa):
        with open(chemin_hexa, "w") as f: json.dump({"presets": []}, f)
    with open(chemin_hexa, "r") as f:
        presets_hexa = json.load(f).get("presets", [])
        
    print(f"OK {len(presets_corde)} presets corde et {len(presets_hexa)} presets hexa chargés")
except Exception as e:
    print(f"WARN Impossible de charger les presets : {e}")

noms_presets_corde = ["---"] + [p["name"] for p in presets_corde]
noms_presets_hexa = ["---"] + [p["name"] for p in presets_hexa]
# --------------------------------------
 
# region MIDI Setup
midi_ok = False
port_midi = None
port_midi_in = None  # Port MIDI en entrée (pour recevoir la charge CPU)
 
def get_midi_out_port(search_term, generate_simulation=False):
    try:
        ports = mido.get_output_names()
       
        if generate_simulation:
            return None, True
 
        target = next((p for p in ports if search_term.lower() in p.lower()), None)
        if target:
            p = mido.open_output(target)
            print(f"Connecté à : {target}")
            return p, True
        else:
            return None, False
    except Exception as e:
        print(f"Erreur d'initialisation MIDI : {e}")
        return None, False

def get_midi_in_port(search_term):
    """Recherche et ouvre un port MIDI en entrée."""
    try:
        ports = mido.get_input_names()
        target = next((p for p in ports if search_term.lower() in p.lower()), None)
        if target:
            p = mido.open_input(target)
            print(f"OK Port MIDI IN ouvert : {target}")
            return p
        else:
            return None
    except Exception as e:
        print(f"WARN Erreur ouverture port MIDI IN : {e}")
        return None
 
# --- Liste pour stocker les ports morts et empêcher le Garbage Collector de les fermer ---
zombie_ports = []

def rescanner_midi():
    """Ferme les ports MIDI existants et relance la détection (OUT + IN)."""
    global port_midi, midi_ok, port_midi_in, zombie_ports
    
    # --- Fermeture propre des ports existants ---
    # Sous Windows, fermer un port déconnecté (ou laisser le Garbage Collector le détruire)
    # provoque un crash fatal en C++ (Segfault). On garde donc le port "vivant" dans une liste zombie.
    if port_midi:
        zombie_ports.append(port_midi)
        port_midi = None
    if port_midi_in:
        zombie_ports.append(port_midi_in)
        port_midi_in = None
    midi_ok = False
    
    # --- Reconnexion SORTIE ---
    if USE_LOOPMIDI:
        port_midi, midi_ok = get_midi_out_port(NOM_PORT_BOUCLE, generate_simulation=True)
    else:
        port_midi, midi_ok = get_midi_out_port("teensy")
        if not midi_ok:
            port_midi, midi_ok = get_midi_out_port("daisy")
        if not midi_ok:
            port_midi, midi_ok = get_midi_out_port("usb")
    
    if not midi_ok:
        print("MIDI désactivé. L'interface fonctionnera sans envoi de messages.")
    
    # --- Reconnexion ENTRÉE ---
    port_midi_in = get_midi_in_port("teensy")
    if not port_midi_in:
        port_midi_in = get_midi_in_port("daisy")
    if not port_midi_in:
        port_midi_in = get_midi_in_port("usb")
    if not port_midi_in:
        print("WARN Pas de port MIDI en entrée trouvé (le moniteur CPU sera inactif).")
    
    # --- Feedback visuel (si le panneau CPU existe déjà) ---
    try:
        if midi_ok and port_midi_in:
            lbl_cpu_status.configure(text="OK MIDI reconnecté !", text_color="#22C55E")
        elif midi_ok:
            lbl_cpu_status.configure(text="OK MIDI OUT ok — IN absent", text_color="#F59E0B")
        else:
            lbl_cpu_status.configure(text="FAIL Aucun port MIDI trouvé", text_color="#DC2626")
    except NameError:
        pass  # Le panneau CPU n'est pas encore créé au premier lancement

# Premier scan au démarrage
rescanner_midi()
# endregion
 
win.grid_columnconfigure(0, weight=1)
win.grid_rowconfigure(0, weight=1)
 
center_container = ctk.CTkFrame(master=win, fg_color="transparent")
center_container.grid(row=0, column=0)
 
# endregion
 
# region 2. Définitions et Structures de Données
 
CONFIG_EFFETS = {
    "Delay": {
        "base_cc": 10,
        "bypass_cc": 48,
        "params": [
            {"nom": "Type", "min": 0, "max": 1, "unite": "delay_type", "steps": 1},
            {"nom": "Time", "min": 0, "max": 127, "unite": "time"},
            {"nom": "Tap", "type": "button"},
            {"nom": "Temps", "min": 1, "max": 8, "unite": "div", "steps": 7},
            {"nom": "FeedBack", "min": 0, "max": 100, "unite": "%"},
            {"nom": "Vol", "min": 0, "max": 10, "unite": ""},
            {"nom": "Mix", "min": 0, "max": 100, "unite": "%"}
        ]
    },
    "Distortion": {
        "base_cc": 50,
        "bypass_cc": 88,
        "params": [
            {"nom": "--"},
            {"nom": "Gain", "min": 0, "max": 10, "unite": ""},
            {"nom": "Mode", "min": 1, "max": 8, "unite": "mode", "steps": 7},
            {"nom": "Tone", "min": 500, "max": 2000, "unite": "Hz"},
            {"nom": "Intens", "min": 0, "max": 100, "unite": "%"},
            {"nom": "Oversamp", "min": 0, "max": 1, "unite": "bool", "steps": 1},
            {"nom": "Vol", "min": 0, "max": 10, "unite": ""}
        ]
    },
    "Earth": {
        "base_cc": 90,
        "bypass_cc": 89,
        "params": [
            {"nom": "Mix", "min": 0, "max": 100, "unite": "%"},
            {"nom": "Octave", "min": 0, "max": 2, "unite": "oct_mode", "steps": 2},
            {"nom": "--"},
            {"nom": "--"},
            {"nom": "--"},
            {"nom": "Vol", "min": 0, "max": 10, "unite": ""}
        ]
    },
    "Tremolo": {
        "base_cc": 110,
        "bypass_cc": 118,
        "params": [
            {"nom": "Mix", "min": 0, "max": 100, "unite": "%"},
            {"nom": "Depth", "min": 0, "max": 100, "unite": "%"},
            {"nom": "Rate", "min": 0.1, "max": 20, "unite": "Hz"},
            {"nom": "Wave", "min": 0, "max": 3, "unite": "wave_mode", "steps": 3},
            {"nom": "Offset", "min": 0, "max": 100, "unite": "%"},
            {"nom": "Vol", "min": 0, "max": 10, "unite": ""}
        ]
    },
    "Equalizer": {
        "base_cc": 70,
        "bypass_cc": 78,
        "params": [
            {"nom": "80 Hz", "min": -12, "max": 12, "unite": "dB"},
            {"nom": "250 Hz", "min": -12, "max": 12, "unite": "dB"},
            {"nom": "750 Hz", "min": -12, "max": 12, "unite": "dB"},
            {"nom": "2.2 kHz", "min": -12, "max": 12, "unite": "dB"},
            {"nom": "6.6 kHz", "min": -12, "max": 12, "unite": "dB"},
            {"nom": "Vol", "min": 0, "max": 10, "unite": ""}
        ]
    }
}
 
corde_active = 0
corde_precedente = 0  
noms_cordes = ["Mi (E2)", "La (A2)", "Ré (D3)", "Sol (G3)", "Si (B3)", "Mi (E4)"]
 
bypass_global = False
cordes_mute = [False] * 6
 
memoire_effets = {
    nom_effet: {corde: [0 if i == 0 else 64 for i in range(len(CONFIG_EFFETS[nom_effet]["params"]))] for corde in range(6)}
    for nom_effet in CONFIG_EFFETS.keys()
}
 
chainage_slots = [[0, 0, 0] for _ in range(6)]
EFFETS_MAP = {"None": 0, "Delay": 1, "Distortion": 2, "Earth": 3, "Tremolo": 4, "Equalizer": 5}
EFFETS_LIST = list(EFFETS_MAP.keys())

# endregion
 
# region 3. Fonctions, Evenements et Affichage Écran
 
# Variables pour le Tap Tempo
tap_history = []
last_tap_time = 0
TAP_TIMEOUT = 2.0  # 2 secondes max entre les clics
MAX_TAPS = 4       # On garde les 4 derniers intervalles pour la moyenne

frame_effets = {}          
effect_title_labels = {}  
slider_container_frames = {}
sliders = {nom_effet: [] for nom_effet in CONFIG_EFFETS.keys()}
slider_labels = {nom_effet: [] for nom_effet in CONFIG_EFFETS.keys()}
bypass_buttons = {}
leds = []
string_buttons = []
btn_all = None  
 
def map_valeur_reelle(val_midi, val_min, val_max):
    pourcentage = val_midi / 127.0
    return val_min + pourcentage * (val_max - val_min)
 
def get_texte_label(param_info, val_midi):
    if param_info["nom"] == "--" or param_info.get("type") == "button":
        return ""
       
    if "min" not in param_info or "max" not in param_info:
        return f"{param_info['nom']}: {val_midi}"
       
    val_reelle = map_valeur_reelle(val_midi, param_info["min"], param_info["max"])
   
    # --- LOGIQUE SPÉCIALE POUR L'AFFICHAGE DE L'OCTAVER EARTH ---
    if param_info["unite"] == "oct_mode":
        cran = int(round(val_reelle))
        if cran == 0:
            return f"{param_info['nom']}: -2 oct"
        elif cran == 1:
            return f"{param_info['nom']}: -1 oct"
        else:
            return f"{param_info['nom']}: +1 oct"

    if param_info["unite"] == "wave_mode":
        cran = int(round(val_reelle))
        if cran == 0:
            return f"{param_info['nom']}: Sine"
        elif cran == 1:
            return f"{param_info['nom']}: Tri"
        elif cran == 2:
            return f"{param_info['nom']}: Square"
        else:
            return f"{param_info['nom']}: Saw"

    if param_info["unite"] == "mode":
        cran = int(round(val_reelle))
        noms_modes = {
            1: "Hard Clip (Gain, Int)",
            2: "Soft Clip (Gain)",
            3: "Fuzz (Gain, Int)",
            4: "Tube (Gain, Int)",
            5: "Multi (Gain, Int)",
            6: "Diode (Gain, Int)",
            7: "Test (Gain)",
            8: "Test OD (Intens)"
        }
        nom = noms_modes.get(cran, f"Type {cran}")
        return f"{param_info['nom']}: {nom}"

    if param_info["unite"] == "bool":
        etat = "ON" if val_reelle >= 0.5 else "OFF"
        return f"{param_info['nom']}: {etat}"
 
    # --- LOGIQUE CLASSIQUE POUR LE RESTE ---
    if param_info["max"] > 10:
        return f"{param_info['nom']}: {int(val_reelle)} {param_info['unite']}"
    else:
        return f"{param_info['nom']}: {val_reelle:.1f} {param_info['unite']}"
 
def maj_delay_dynamic_ui():
    if "Delay" not in sliders or not sliders["Delay"]: return
    corde_ref = 0 if corde_active == "ALL" else corde_active
    valeurs = memoire_effets["Delay"][corde_ref]
    
    type_val = valeurs[0]
    is_tempo = (type_val / 127.0) >= 0.5
    
    slider_labels["Delay"][0].configure(text=f"Type : {'Tempo' if is_tempo else 'Manual'}")
    
    val_1 = valeurs[1]
    if is_tempo:
        bpm = 40 + (val_1 / 127.0) * (240 - 40)
        slider_labels["Delay"][1].configure(text=f"Tempo: {int(bpm)} bpm")
        sliders["Delay"][2].configure(text="Tap Tempo")
        slider_labels["Delay"][3].pack(anchor="w")
        sliders["Delay"][3].pack(pady=2, anchor="w")
        
        val_3 = valeurs[3]
        temps = 1 + (val_3 / 127.0) * (8 - 1)
        slider_labels["Delay"][3].configure(text=f"Temps : {int(round(temps))}")
    else:
        ms = 50 + (val_1 / 127.0) * (4000 - 50)
        slider_labels["Delay"][1].configure(text=f"Delay : {int(ms)} ms")
        sliders["Delay"][2].configure(text="Tap Delay")
        slider_labels["Delay"][3].pack_forget()
        sliders["Delay"][3].pack_forget()

def maj_sliders_visuels():
    texte_titre = f"CORDE ACTIVE : {noms_cordes[corde_active] if corde_active != 'ALL' else '[MODE ALL]'}"
    label_info_corde.configure(text=texte_titre, text_color="#0088FF" if corde_active == "ALL" else "white")
   
    for nom_effet, config in CONFIG_EFFETS.items():
        corde_ref = 0 if corde_active == "ALL" else corde_active
        valeurs = memoire_effets[nom_effet][corde_ref]
       
        for i, v in enumerate(valeurs):
            param_info = config["params"][i]
            if param_info.get("type") == "button":
                continue
            sliders[nom_effet][i].set(v)
            if param_info["nom"] != "--":
                if nom_effet == "Delay" and i in (0, 1, 3):
                    pass
                else:
                    texte = get_texte_label(param_info, v)
                    slider_labels[nom_effet][i].configure(text=texte)
        
        # Réappliquer le visuel bypass après la mise à jour des sliders
        appliquer_visuel_bypass(nom_effet)

    if "Delay" in sliders:
        maj_delay_dynamic_ui()

def button_callback(nom_effet, index):
    global tap_history, last_tap_time

    # Gestion spécifique du Tap Tempo pour le Delay (index 2)
    if nom_effet == "Delay" and index == 2:
        current_time = time.time()
        
        # Si trop de temps s'est écoulé depuis le dernier clic, on réinitialise
        if current_time - last_tap_time > TAP_TIMEOUT:
            tap_history = []
            
        # Si c'est le 2ème clic (ou plus) dans le délai imparti
        if last_tap_time > 0 and (current_time - last_tap_time) <= TAP_TIMEOUT:
            delta = current_time - last_tap_time
            tap_history.append(delta)
            
            if len(tap_history) > MAX_TAPS:
                tap_history.pop(0)
                
            avg_delta = sum(tap_history) / len(tap_history)
            
            # Récupération du mode (Tempo ou Manual)
            corde_ref = 0 if corde_active == "ALL" else corde_active
            is_tempo = map_valeur_reelle(memoire_effets["Delay"][corde_ref][0], 0, 1) >= 0.5
            
            if is_tempo:
                bpm = 60.0 / avg_delta
                bpm = max(40, min(240, bpm))
                val_midi = int(round((bpm - 40) / (240 - 40) * 127.0))
            else:
                ms = avg_delta * 1000.0
                ms = max(50, min(4000, ms))
                val_midi = int(round((ms - 50) / (4000 - 50) * 127.0))
            
            # Mise à jour du slider Tempo/Delay (index 1) et envoi MIDI
            slider_idx = 1
            sliders["Delay"][slider_idx].set(val_midi)
            slider_callback(val_midi, "Delay", slider_idx)
            
        last_tap_time = current_time
        return # Fin de l'exécution pour le Tap Tempo (pas d'envoi du CC du bouton)

    # Pour d'éventuels autres boutons, on envoie juste 127
    base_cc = CONFIG_EFFETS[nom_effet]["base_cc"]
    cc_num = base_cc + index
    if corde_active == "ALL":
        for channel in range(6):
            msg = mido.Message('control_change', channel=channel, control=cc_num, value=127)
            send_midi_message(msg)
    else:
        msg = mido.Message('control_change', channel=corde_active, control=cc_num, value=127)
        send_midi_message(msg)
 
def slider_callback(valeur, nom_effet, index):
    marquer_preset_modifie()
    v_int = int(float(valeur))
    param_info = CONFIG_EFFETS[nom_effet]["params"][index]
    base_cc = CONFIG_EFFETS[nom_effet]["base_cc"]
    cc_num = base_cc + index
 
    if corde_active == "ALL":
        for channel in range(6):
            memoire_effets[nom_effet][channel][index] = v_int
            msg = mido.Message('control_change', channel=channel, control=cc_num, value=v_int)
            send_midi_message(msg)
    else:
        memoire_effets[nom_effet][corde_active][index] = v_int
        msg = mido.Message('control_change', channel=corde_active, control=cc_num, value=v_int)
        send_midi_message(msg)
           
    if nom_effet == "Delay" and index in (0, 1, 3):
        maj_delay_dynamic_ui()
    else:
        texte = get_texte_label(param_info, v_int)
        slider_labels[nom_effet][index].configure(text=texte)
 
def appliquer_visuel_bypass(nom_effet):
    """Met à jour l'apparence visuelle d'un effet selon sa présence dans la chaîne de la corde active."""
    corde_ref = 0 if corde_active == "ALL" else corde_active
    val_int_effet = EFFETS_MAP.get(nom_effet, -1)
    
    # Bypassed if the effect is NOT in the chain for the active string
    est_bypasse = val_int_effet not in chainage_slots[corde_ref]
    
    c_active_frame, c_bypassed_frame = "#2A2A2A", "#1A1A1A"
    c_active_text, c_bypassed_text = "white", "#AAAAAA"
    c_active_slider, c_bypassed_slider = "#3B8ED0", "#555555"

    etat_ui = "disabled" if est_bypasse else "normal"
    couleur_text = c_bypassed_text if est_bypasse else c_active_text
   
    if nom_effet in frame_effets:
        frame_effets[nom_effet].configure(fg_color=c_bypassed_frame if est_bypasse else c_active_frame)
    if nom_effet in effect_title_labels:
        effect_title_labels[nom_effet].configure(text_color=couleur_text)

    for lbl in slider_labels[nom_effet]:
        lbl.configure(text_color=couleur_text)

    for idx, slider in enumerate(sliders[nom_effet]):
        param_info = CONFIG_EFFETS[nom_effet]["params"][idx]
        if param_info.get("type") == "button":
            slider.configure(state=etat_ui, fg_color=c_bypassed_slider if est_bypasse else c_active_slider)
        else:
            slider.configure(state=etat_ui, button_color=c_bypassed_slider if est_bypasse else c_active_slider, progress_color=c_bypassed_slider if est_bypasse else c_active_slider)
            
    if nom_effet in bypass_buttons:
        bypass_buttons[nom_effet].configure(fg_color="#A12222" if est_bypasse else "#555555")

def log_midi_message(msg):
    try:
        if not show_midi_log.get():
            return
        
        if msg.type == 'control_change':
            texte = f"[OUT] CH:{msg.channel:2d} | CC:{msg.control:3d} | VAL:{msg.value:3d}"
        else:
            texte = f"[OUT] {msg}"
            
        textbox_midi_log.insert("end", texte + "\n")
        textbox_midi_log.see("end")
        
        lines = int(textbox_midi_log.index('end-1c').split('.')[0])
        if lines > 100:
            textbox_midi_log.delete("1.0", "2.0")
    except NameError:
        pass

def send_midi_message(msg):
    if midi_ok and port_midi:
        try:
            port_midi.send(msg)
            log_midi_message(msg)
            import time
            time.sleep(0.002) # Petite pause pour ne pas surcharger la Daisy
        except Exception:
            pass

def envoyer_tout_midi():
    if not midi_ok or not port_midi:
        return
    for channel in range(6):
        effets_inactifs = []
        effets_actifs = []
        for nom_effet, config in CONFIG_EFFETS.items():
            val_int = EFFETS_MAP.get(nom_effet, -1)
            if val_int in chainage_slots[channel]:
                effets_actifs.append((nom_effet, config))
            else:
                effets_inactifs.append((nom_effet, config))
                
        for nom_effet, config in effets_inactifs + effets_actifs:
            base_cc = config["base_cc"]
            valeurs = memoire_effets[nom_effet][channel]
            for index, v in enumerate(valeurs):
                param_info = config["params"][index]
                if param_info["nom"] != "--" and param_info.get("type") != "button":
                    cc_num = base_cc + index
                    send_midi_message(mido.Message('control_change', channel=channel, control=cc_num, value=int(v)))
        
        envoyer_chainage_midi(channel)

def toggle_bypass_effet(nom_effet):
    marquer_preset_modifie()
    val_int_effet = EFFETS_MAP.get(nom_effet, 0)
    if val_int_effet == 0: return

    def _toggle_pour_corde(c):
        if val_int_effet in chainage_slots[c]:
            chainage_slots[c] = [0 if slot == val_int_effet else slot for slot in chainage_slots[c]]
        else:
            if 0 in chainage_slots[c]:
                idx_libre = chainage_slots[c].index(0)
                chainage_slots[c][idx_libre] = val_int_effet
            else:
                chainage_slots[c][2] = val_int_effet
        envoyer_chainage_midi(c)

    if corde_active == "ALL":
        for c in range(6):
            _toggle_pour_corde(c)
    else:
        _toggle_pour_corde(corde_active)
        
    appliquer_visuel_bypass(nom_effet)
    maj_ui_chainage()
    maj_sliders_visuels()

def mettre_a_jour_dropdowns():
    global noms_presets_corde, noms_presets_hexa
    noms_presets_corde = ["---", "Custom"] + [p["name"] for p in presets_corde]
    noms_presets_hexa = ["---"] + [p["name"] for p in presets_hexa]
    
    for dp in preset_dropdowns_cordes:
        dp.configure(values=noms_presets_corde)
        val = dp.get().replace("*", "")
        if val not in noms_presets_corde:
            dp.set("---")
            
    preset_dropdown_global.configure(values=noms_presets_hexa)
    if preset_dropdown_global.get().replace("*", "") not in noms_presets_hexa:
        preset_dropdown_global.set("---")
        
    maj_dropdown_supprimer()
    maj_bouton_save()

banque_suppression_active = "Hexa"

def maj_dropdown_supprimer():
    try:
        if banque_suppression_active == "Hexa":
            vals = [p["name"] for p in presets_hexa]
        else:
            vals = [p["name"] for p in presets_corde]
        dropdown_supprimer.configure(values=vals if vals else ["---"])
        if dropdown_supprimer.get() not in vals:
            dropdown_supprimer.set("---" if not vals else vals[0])
    except NameError:
        pass

def dialog_nouvelle_version(nom_base, param_corde, idx_corde):
    dialog = ctk.CTkToplevel(win)
    dialog.title("Modification détectée")
    dialog.geometry("400x200")
    dialog.attributes('-topmost', True)
    dialog.grab_set()

    lbl = ctk.CTkLabel(dialog, text=f"La corde {idx_corde+1} (Preset: {nom_base}) a été modifiée.\nVoulez-vous créer une nouvelle version de ce preset corde\nou garder ces réglages uniquement dans ce preset Hexa ?", wraplength=350)
    lbl.pack(pady=20)

    choix = ctk.StringVar(value="")

    def on_v2():
        choix.set("v2")
        dialog.destroy()

    def on_custom():
        choix.set("custom")
        dialog.destroy()

    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack(pady=10)
    
    ctk.CTkButton(btn_frame, text=f"Créer {nom_base}_v2", command=on_v2).pack(side="left", padx=10)
    ctk.CTkButton(btn_frame, text="Indépendant (Custom)", command=on_custom, fg_color="#555555").pack(side="left", padx=10)

    win.wait_window(dialog)
    return choix.get()

def dialog_nom_preset():
    dialog = ctk.CTkInputDialog(text="Entrez le nom du preset :", title="Sauvegarde")
    return dialog.get_input()

def sauvegarder_preset_json_hexa():
    nom = dialog_nom_preset()
    if not nom: return
    nom = nom.strip()
    if not nom or nom == "---": return
        
    global presets_hexa
    preset_existant = next((p for p in presets_hexa if p["name"] == nom), None)
    if preset_existant:
        presets_hexa.remove(preset_existant)
        
    nouveau_preset = {"name": nom, "strings_data": {}}
    
    for c in range(6):
        nom_actuel = preset_dropdowns_cordes[c].get()
        
        string_params = {"chainage": list(chainage_slots[c]), "effects": {}}
        for nom_effet, config in CONFIG_EFFETS.items():
            val_int = EFFETS_MAP.get(nom_effet, -1)
            est_bypasse = val_int not in chainage_slots[c]
            if not est_bypasse:
                string_params["effects"][nom_effet] = {
                    "bypass": False,
                    "params": list(memoire_effets[nom_effet][c])
                }
                
        if nom_actuel.endswith("*") and nom_actuel != "---*" and nom_actuel != "Custom*":
            nom_base = nom_actuel[:-1]
            choix = dialog_nouvelle_version(nom_base, string_params, c)
            if choix == "v2":
                nv_nom = nom_base + "_" + datetime.datetime.now().strftime("%d-%m-%Hh%M")
                sauvegarder_preset_corde(nv_nom, string_params)
                nouveau_preset["strings_data"][str(c)] = {"type": "ref", "preset_name": nv_nom}
                preset_dropdowns_cordes[c].set(nv_nom)
            else:
                nouveau_preset["strings_data"][str(c)] = {"type": "custom", "params": string_params}
                preset_dropdowns_cordes[c].set("Custom")
        elif nom_actuel == "---" or nom_actuel == "---*" or "Custom" in nom_actuel:
            nouveau_preset["strings_data"][str(c)] = {"type": "custom", "params": string_params}
        else:
            nouveau_preset["strings_data"][str(c)] = {"type": "ref", "preset_name": nom_actuel}
            
    presets_hexa.append(nouveau_preset)
    chemin_hexa = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets_hexa.json")
    with open(chemin_hexa, "w") as f:
        json.dump({"presets": presets_hexa}, f, indent=4)
    print(f"OK Preset Hexa '{nom}' sauvegardé.")
    mettre_a_jour_dropdowns()


def sauvegarder_preset_json_corde():
    if corde_active == "ALL":
        return
        
    nom = dialog_nom_preset()
    if not nom: return
    nom = nom.strip()
    if not nom or nom == "---": return
        
    string_params = {"chainage": list(chainage_slots[corde_active]), "effects": {}}
    for nom_effet, config in CONFIG_EFFETS.items():
        val_int = EFFETS_MAP.get(nom_effet, -1)
        est_bypasse = val_int not in chainage_slots[corde_active]
        if not est_bypasse:
            string_params["effects"][nom_effet] = {
                "bypass": False,
                "params": list(memoire_effets[nom_effet][corde_active])
            }
    sauvegarder_preset_corde(nom, string_params)
    preset_dropdowns_cordes[corde_active].set(nom)
    mettre_a_jour_dropdowns()

def sauvegarder_preset_corde(nom, string_params):
    global presets_corde
    preset_existant = next((p for p in presets_corde if p["name"] == nom), None)
    if preset_existant:
        presets_corde.remove(preset_existant)
    nouveau_preset = {"name": nom, "chainage": string_params["chainage"], "effects": string_params["effects"]}
    presets_corde.append(nouveau_preset)
    chemin_corde = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets_corde.json")
    with open(chemin_corde, "w") as f:
        json.dump({"presets": presets_corde}, f, indent=4)
    print(f"OK Preset Corde '{nom}' sauvegardé.")
    mettre_a_jour_dropdowns()

def supprimer_preset_json():
    nom = dropdown_supprimer.get()
    if not nom or nom == "---": return
    
    if banque_suppression_active == "Hexa":
        global presets_hexa
        presets_hexa = [p for p in presets_hexa if p["name"] != nom]
        chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets_hexa.json")
        with open(chemin, "w") as f: json.dump({"presets": presets_hexa}, f, indent=4)
    else:
        global presets_corde
        presets_corde = [p for p in presets_corde if p["name"] != nom]
        chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets_corde.json")
        with open(chemin, "w") as f: json.dump({"presets": presets_corde}, f, indent=4)
        
    print(f"OK Preset '{nom}' supprimé.")
    mettre_a_jour_dropdowns()

def Activation_mute(index):
    cordes_mute[index] = not cordes_mute[index]
    val = 127 if cordes_mute[index] else 0
    send_midi_message(mido.Message('control_change', control=index, value=val))
        
    if not cordes_mute[index]:
        for nom_effet, config in CONFIG_EFFETS.items():
            val_int = EFFETS_MAP.get(nom_effet, -1)
            if val_int in chainage_slots[index]:
                for idx, p_val in enumerate(memoire_effets[nom_effet][index]):
                    if config["params"][idx].get("type") == "button":
                        continue
                    cc_num = config["base_cc"] + idx
                    send_midi_message(mido.Message('control_change', channel=index, control=cc_num, value=p_val))
        envoyer_chainage_midi(index)
    maj_leds()
 
def Activation_bypass():
    global bypass_global
    bypass_global = not bypass_global
    val = 127 if bypass_global else 0
    send_midi_message(mido.Message('control_change', control=126, value=val))
        
    if not bypass_global:
        envoyer_tout_midi()

    btn_bypass.configure(fg_color="#A12222" if bypass_global else "#555555")

def appliquer_string_params(c, data):
    chainage_slots[c] = data.get("chainage", [0, 0, 0])[:3]
    while len(chainage_slots[c]) < 3: chainage_slots[c].append(0)
    
    slot_idx = 0
    for nom_effet, effet_data in data.get("effects", {}).items():
        if nom_effet not in CONFIG_EFFETS: continue
        config = CONFIG_EFFETS[nom_effet]
        est_bypasse = effet_data.get("bypass", True)
        if "chainage" not in data and not est_bypasse and slot_idx < 3:
            val_int = EFFETS_MAP.get(nom_effet, 0)
            chainage_slots[c][slot_idx] = val_int
            slot_idx += 1
            
        if "params" in effet_data:
            for idx, val_midi in enumerate(effet_data["params"]):
                if idx < len(config["params"]):
                    param_info = config["params"][idx]
                    if param_info.get("type") == "button" or param_info["nom"] == "--":
                        continue
                    memoire_effets[nom_effet][c][idx] = val_midi
    envoyer_chainage_midi(c)

def appliquer_preset_factory(nom_preset, corde):
    if nom_preset == "---": return
    
    if corde == "ALL":
        # Load Hexa
        preset = next((p for p in presets_hexa if p["name"] == nom_preset), None)
        if not preset: return
        
        for c in range(6):
            s_data = preset.get("strings_data", {}).get(str(c), {})
            if s_data.get("type") == "ref":
                p_name = s_data.get("preset_name")
                p_corde = next((p for p in presets_corde if p["name"] == p_name), None)
                if p_corde:
                    appliquer_string_params(c, p_corde)
                    preset_dropdowns_cordes[c].set(p_name)
                else:
                    preset_dropdowns_cordes[c].set("---")
            elif s_data.get("type") == "custom":
                appliquer_string_params(c, s_data.get("params", {}))
                preset_dropdowns_cordes[c].set("Custom")
    else:
        # Load String
        preset = next((p for p in presets_corde if p["name"] == nom_preset), None)
        if not preset: return
        appliquer_string_params(corde, preset)
        preset_dropdowns_cordes[corde].set(nom_preset)

    for nom_effet in CONFIG_EFFETS.keys():
        appliquer_visuel_bypass(nom_effet)
        
    maj_ui_chainage()
    maj_sliders_visuels()
    envoyer_tout_midi()
    print(f"OK Preset '{nom_preset}' appliqué à {'toutes les cordes' if corde == 'ALL' else f'corde {corde + 1}'}")

def marquer_preset_modifie():
    """Ajoute un astérisque (*) au nom du preset actif si des modifications sont apportées."""
    try:
        if corde_active == "ALL":
            val = preset_dropdown_global.get()
            if val != "---" and not val.endswith("*"):
                preset_dropdown_global.set(val + "*")
            
            for dropdown in preset_dropdowns_cordes:
                val_c = dropdown.get()
                if val_c != "---" and not val_c.endswith("*"):
                    dropdown.set(val_c + "*")
        else:
            dropdown = preset_dropdowns_cordes[corde_active]
            val = dropdown.get()
            if val != "---" and not val.endswith("*"):
                dropdown.set(val + "*")
    except NameError:
        pass

def Reset_All():
    """Remet tous les paramètres à 0, et unmute toutes les cordes"""
    for nom_effet in CONFIG_EFFETS.keys():
        for corde in range(6):
            for idx in range(len(CONFIG_EFFETS[nom_effet]["params"])):
                memoire_effets[nom_effet][corde][idx] = 0
                
    # Reset Chainage
    for corde in range(6):
        chainage_slots[corde] = [0, 0, 0]
        send_midi_message(mido.Message('control_change', channel=corde, control=20, value=0))
        send_midi_message(mido.Message('control_change', channel=corde, control=21, value=0))
        send_midi_message(mido.Message('control_change', channel=corde, control=22, value=0))

    # Unmute all strings
    for corde in range(6):
        cordes_mute[corde] = False
        send_midi_message(mido.Message('control_change', control=corde, value=0))
            
    # Refresh GUI
    maj_leds()
    for nom_effet in CONFIG_EFFETS.keys():
        appliquer_visuel_bypass(nom_effet)
    selectionner_corde(corde_active) # Refresh sliders
    
    # Send all zeroed MIDI values
    envoyer_tout_midi()
 
def selectionner_corde(index):
    global corde_active, corde_precedente
    corde_active = index
    corde_precedente = index
    maj_leds()
    maj_ui_chainage()
    maj_dropdown_supprimer()
    maj_bouton_save()
    maj_bouton_save()
    
    # Mettre à jour les sliders pour correspondre à la corde sélectionnée
    for nom_effet, sliders_effet in sliders.items():
        valeurs = memoire_effets[nom_effet][corde_active] if corde_active != "ALL" else memoire_effets[nom_effet][0]
        for idx, slider in enumerate(sliders_effet):
            param_info = CONFIG_EFFETS[nom_effet]["params"][idx]
            if param_info.get("type") == "button":
                continue
            slider.configure(command=lambda v: None)
            slider.set(valeurs[idx])
            if param_info["nom"] != "--":
                if nom_effet == "Delay" and idx in (0, 1, 3):
                    pass
                else:
                    texte = get_texte_label(param_info, valeurs[idx])
                    slider_labels[nom_effet][idx].configure(text=texte)
            slider.configure(command=lambda v, ne=nom_effet, i=idx: slider_callback(v, ne, i))

    if "Delay" in sliders:
        maj_delay_dynamic_ui()
 
def toggle_mode_all():
    global corde_active, corde_precedente
    if corde_active == "ALL":
        corde_active = corde_precedente
    else:
        corde_active = "ALL"
    maj_leds()
    maj_ui_chainage()
    maj_dropdown_supprimer()
    maj_bouton_save()
 
def maj_leds():
    for i, led in enumerate(leds):
        if cordes_mute[i]:
            led.configure(fg_color="#FF0000", text="M")
        else:
            led.configure(fg_color="#1a331a", text="")
           
    for i, btn in enumerate(string_buttons):
        if corde_active == "ALL":
            btn.configure(fg_color="#0088FF", text_color="white")
        elif i == corde_active:
            btn.configure(fg_color="#00FF00", text_color="black")
        else:
            btn.configure(fg_color="#333333", text_color="white")
           
    if btn_all:
        if corde_active == "ALL":
            btn_all.configure(fg_color="#0088FF", text_color="white")
        else:
            btn_all.configure(fg_color="#333333", text_color="white")
           
    maj_sliders_visuels()
 
def envoyer_chainage_midi(corde):
    send_midi_message(mido.Message('control_change', channel=corde, control=20, value=chainage_slots[corde][0]))
    send_midi_message(mido.Message('control_change', channel=corde, control=21, value=chainage_slots[corde][1]))
    send_midi_message(mido.Message('control_change', channel=corde, control=22, value=chainage_slots[corde][2]))
        
def on_slot_change(slot_idx, value):
    marquer_preset_modifie()
    val_int = EFFETS_MAP[value]
    if corde_active == "ALL":
        for c in range(6):
            chainage_slots[c][slot_idx] = val_int
            envoyer_chainage_midi(c)
    else:
        chainage_slots[corde_active][slot_idx] = val_int
        envoyer_chainage_midi(corde_active)
    
    # Mettre à jour l'apparence grisée/normale
    maj_sliders_visuels()

def maj_ui_chainage():
    try:
        corde_ref = 0 if corde_active == "ALL" else corde_active
        menu_slot1.set(EFFETS_LIST[chainage_slots[corde_ref][0]])
        menu_slot2.set(EFFETS_LIST[chainage_slots[corde_ref][1]])
        menu_slot3.set(EFFETS_LIST[chainage_slots[corde_ref][2]])
    except NameError:
        pass # Handle case before UI components are created

# endregion
 
# region 4. Ecran, Navigation et Menu Effets
 
frame_nav = ctk.CTkFrame(master=center_container, fg_color="transparent")
frame_nav.grid(row=0, column=0, pady=5, sticky="ew")
 
nav_controls_frame = ctk.CTkFrame(frame_nav, fg_color="transparent")
nav_controls_frame.pack(expand=True)
 
strings_frame = ctk.CTkFrame(nav_controls_frame, fg_color="transparent")
strings_frame.pack(pady=5)
 
string_names = [s.split(" ")[0] for s in noms_cordes]
 
for i in range(6):
    btn = ctk.CTkButton(strings_frame, text=string_names[i], width=45, height=35, font=("Arial", 12, "bold"),
                        command=lambda idx=i: selectionner_corde(idx))
    btn.grid(row=0, column=i, padx=5, pady=2)
    string_buttons.append(btn)
 
btn_all = ctk.CTkButton(strings_frame, text="ALL", width=60, height=35, font=("Arial", 12, "bold"),
                        command=toggle_mode_all)
btn_all.grid(row=0, column=6, padx=15, pady=2)
 
def afficher_aide():
    dialog = ctk.CTkToplevel(win)
    dialog.title("Aide & Fonctionnement")
    dialog.geometry("500x350")
    dialog.attributes('-topmost', True)
    
    txt = """🎵 Bienvenue sur la Pédale Hexaphonique !

1. SÉLECTION (Le Manche) :
Cliquez sur les boutons Mi, La, Ré... en haut pour éditer une corde spécifique.
Le bouton ALL est une 'Macro' : il vous permet d'éditer les 6 cordes en même temps !

2. LE SON (Chaînage) :
Choisissez vos effets dans les listes déroulantes Slot 1, 2, 3 pour les activer. 
(S'ils ne sont pas dans un slot, ils sont by-passés).

3. LES PRESETS (Sauvegarde) :
- SAVE CORDE : Sauvegarde le réglage de la corde actuelle.
- SAVE HEXA : Sauvegarde l'état complet de la pédale (les 6 cordes).
Si vous modifiez une corde existante et que vous sauvegardez un Preset Hexa, le système vous proposera intelligemment de créer une nouvelle version pour ne pas écraser votre son d'origine !"""
    
    lbl = ctk.CTkLabel(dialog, text=txt, font=("Arial", 13), justify="left", wraplength=450)
    lbl.pack(padx=20, pady=20, fill="both", expand=True)
    
    btn_ok = ctk.CTkButton(dialog, text="Compris !", command=dialog.destroy)
    btn_ok.pack(pady=10)

btn_aide = ctk.CTkButton(strings_frame, text="❔", width=35, height=35, font=("Arial", 16, "bold"), fg_color="#8e44ad", hover_color="#9b59b6", command=afficher_aide)
btn_aide.grid(row=0, column=7, padx=(5, 10), pady=2)
 
for i in range(6):
    l = ctk.CTkButton(strings_frame, text="", width=30, height=30, corner_radius=15,
                      command=lambda idx=i: Activation_mute(idx))
    l.grid(row=1, column=i, padx=5, pady=5)
    leds.append(l)

def changer_zoom(val):
    val_float = float(val)
    ctk.set_widget_scaling(val_float)
    ctk.set_window_scaling(val_float)
    lbl_zoom.configure(text=f"Zoom: {int(val_float*100)}%")

zoom_frame = ctk.CTkFrame(frame_nav, fg_color="transparent")
zoom_frame.pack(pady=5)
lbl_zoom = ctk.CTkLabel(zoom_frame, text="Zoom: 80%", font=("Arial", 12))
lbl_zoom.pack(side="left", padx=5)
slider_zoom = ctk.CTkSlider(zoom_frame, from_=0.5, to=1.5, number_of_steps=20, command=changer_zoom, width=150)
slider_zoom.set(0.8)
slider_zoom.pack(side="left", padx=5)
 
label_info_corde = ctk.CTkLabel(frame_nav, text="", font=("Arial", 14, "bold"))
label_info_corde.pack(pady=5)
 
# endregion
 
# region 4.5. Chaînage (Testation Mode)

frame_chainage = ctk.CTkFrame(center_container, border_width=2, corner_radius=10)
frame_chainage.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

lbl_chain_title = ctk.CTkLabel(frame_chainage, text="🔗 CHAÎNAGE DES EFFETS (Mode Superposé)", font=("Arial", 14, "bold"))
lbl_chain_title.grid(row=0, column=0, columnspan=6, pady=(10, 5))

ctk.CTkLabel(frame_chainage, text="Slot 1 :", font=("Arial", 12)).grid(row=1, column=0, padx=(20,5), pady=10)
menu_slot1 = ctk.CTkOptionMenu(frame_chainage, values=EFFETS_LIST, command=lambda v: on_slot_change(0, v))
menu_slot1.grid(row=1, column=1, padx=5, pady=10)

ctk.CTkLabel(frame_chainage, text="Slot 2 :", font=("Arial", 12)).grid(row=1, column=2, padx=(20,5), pady=10)
menu_slot2 = ctk.CTkOptionMenu(frame_chainage, values=EFFETS_LIST, command=lambda v: on_slot_change(1, v))
menu_slot2.grid(row=1, column=3, padx=5, pady=10)

ctk.CTkLabel(frame_chainage, text="Slot 3 :", font=("Arial", 12)).grid(row=1, column=4, padx=(20,5), pady=10)
menu_slot3 = ctk.CTkOptionMenu(frame_chainage, values=EFFETS_LIST, command=lambda v: on_slot_change(2, v))
menu_slot3.grid(row=1, column=5, padx=(5, 20), pady=10)

# Call it once to init state
maj_ui_chainage()

# region 5. Grille des effets et potentiomètres
 
frame_effets_container = ctk.CTkFrame(center_container, fg_color="transparent")
frame_effets_container.grid(row=2, column=0, padx=10, pady=5)
 
for i, (nom_effet, config) in enumerate(CONFIG_EFFETS.items()):
    frame_effet = ctk.CTkFrame(frame_effets_container, border_width=2)
    frame_effet.grid(row=0, column=i, padx=15, pady=5, sticky="nsew")
    frame_effets[nom_effet] = frame_effet
 
    frame_titre = ctk.CTkFrame(frame_effet, fg_color="transparent")
    frame_titre.pack(pady=5, padx=10, fill="x")
   
    lbl_titre = ctk.CTkLabel(frame_titre, text=nom_effet.upper(), font=("Arial", 16, "bold"))
    lbl_titre.pack(side="left", expand=True)
    effect_title_labels[nom_effet] = lbl_titre
   
    if "bypass_cc" in config:
        btn_bypass_effet = ctk.CTkButton(frame_titre, text="Bypass", width=70, fg_color="#555555",
                                         command=lambda n=nom_effet: toggle_bypass_effet(n))
        # btn_bypass_effet.pack(side="left", padx=5) # Masqué
        bypass_buttons[nom_effet] = btn_bypass_effet
 
    frame_potards_effet = ctk.CTkFrame(frame_effet, fg_color="transparent")
    frame_potards_effet.pack(pady=5, padx=10)
    slider_container_frames[nom_effet] = frame_potards_effet
 
    for j, param_info in enumerate(config["params"]):
        cellule = ctk.CTkFrame(frame_potards_effet, fg_color="transparent")
        cellule.grid(row=j, column=0, padx=5, pady=4, sticky="w")
       
        lbl = ctk.CTkLabel(cellule, text=f"{param_info['nom']}: --", font=("Arial", 12))

        if param_info.get("type") == "button":
            lbl.configure(text="")
            lbl.pack(anchor="w")
            slider_labels[nom_effet].append(lbl)
            
            btn = ctk.CTkButton(cellule, text=param_info["nom"], width=180,
                                command=lambda ne=nom_effet, idx=j: button_callback(ne, idx))
            btn.pack(pady=2, anchor="w")
            sliders[nom_effet].append(btn)
            continue

        lbl.pack(anchor="w")
        slider_labels[nom_effet].append(lbl)
       
        # --- CONFIGURATION DES CRANS POUR L'OCTAVER ---
        nb_steps = param_info.get("steps", 0)
       
        if nb_steps > 0:
            s = ctk.CTkSlider(cellule, from_=0, to=127, orientation="horizontal", width=180,
                              number_of_steps=nb_steps,
                              command=lambda v, ne=nom_effet, idx=j: slider_callback(v, ne, idx))
        else:
            s = ctk.CTkSlider(cellule, from_=0, to=127, orientation="horizontal", width=180,
                              command=lambda v, ne=nom_effet, idx=j: slider_callback(v, ne, idx))
                             
        s.set(64)
        s.pack(pady=2, anchor="w")
        sliders[nom_effet].append(s)
 
        if param_info["nom"] == "--":
            lbl.configure(text="")
            s.pack_forget()

# --- Panneau Presets Factory (à droite des effets) ---
frame_presets_panel = ctk.CTkFrame(frame_effets_container, border_width=2, width=180)
frame_presets_panel.grid(row=0, column=len(CONFIG_EFFETS), padx=15, pady=5, sticky="nsew")
frame_presets_panel.grid_propagate(False)

lbl_presets_titre = ctk.CTkLabel(frame_presets_panel, text="Presets Corde", font=("Arial", 16, "bold"))
lbl_presets_titre.pack(pady=(10, 5))

# Dropdowns par corde (1-6)
preset_dropdowns_cordes = []
for idx_corde in range(6):
    frame_ligne = ctk.CTkFrame(frame_presets_panel, fg_color="transparent")
    frame_ligne.pack(fill="x", padx=10, pady=3)
    
    lbl_num = ctk.CTkLabel(frame_ligne, text=f"{idx_corde + 1}", font=("Arial", 13, "bold"), width=20)
    lbl_num.pack(side="left", padx=(0, 5))
    
    dropdown = ctk.CTkOptionMenu(
        frame_ligne,
        values=noms_presets_corde,
        width=130,
        height=28,
        font=("Arial", 11),
        command=lambda val, c=idx_corde: appliquer_preset_factory(val, c)
    )
    dropdown.set("---")
    dropdown.pack(side="left", fill="x", expand=True)
    preset_dropdowns_cordes.append(dropdown)

# Séparateur visuel
separateur = ctk.CTkFrame(frame_presets_panel, height=2, fg_color="#555555")
separateur.pack(fill="x", padx=10, pady=(10, 5))

# Dropdown global
lbl_global = ctk.CTkLabel(frame_presets_panel, text="Preset Hexa", font=("Arial", 14, "bold"))
lbl_global.pack(pady=(5, 3))

preset_dropdown_global = ctk.CTkOptionMenu(
    frame_presets_panel,
    values=noms_presets_hexa,
    width=150,
    height=28,
    font=("Arial", 11),
    command=lambda val: appliquer_preset_factory(val, "ALL")
)
preset_dropdown_global.set("---")
preset_dropdown_global.pack(padx=10, pady=(0, 5))

# Séparateur visuel
separateur2 = ctk.CTkFrame(frame_presets_panel, height=2, fg_color="#555555")
separateur2.pack(fill="x", padx=10, pady=(5, 5))

lbl_edit = ctk.CTkLabel(frame_presets_panel, text="Suppression", font=("Arial", 12, "bold"))
lbl_edit.pack(pady=(2, 2))


# Ligne Suppression
frame_del = ctk.CTkFrame(frame_presets_panel, fg_color="transparent")
frame_del.pack(fill="x", padx=10, pady=(2, 10))

def on_segment_change(value):
    global banque_suppression_active
    banque_suppression_active = value
    maj_dropdown_supprimer()

segment_suppression = ctk.CTkSegmentedButton(frame_del, values=["Corde", "Hexa"], command=on_segment_change, font=("Arial", 11))
segment_suppression.set("Hexa")
segment_suppression.pack(fill="x", pady=(0, 5))

frame_del_dropdown = ctk.CTkFrame(frame_del, fg_color="transparent")
frame_del_dropdown.pack(fill="x")

dropdown_supprimer = ctk.CTkOptionMenu(
    frame_del_dropdown,
    values=[p["name"] for p in presets_hexa] if presets_hexa else ["---"],
    width=105,
    font=("Arial", 11)
)
dropdown_supprimer.pack(side="left", padx=(0, 5), fill="y")
btn_del_preset = ctk.CTkButton(frame_del_dropdown, text="-", width=28, fg_color="#A12222", hover_color="#7A1A1A", command=supprimer_preset_json)
btn_del_preset.pack(side="left", fill="y")
 
# endregion
 
def maj_bouton_save():
    try:
        if corde_active == "ALL":
            btn_save_corde.configure(state="disabled", text="SAVE CORDE (Désactivé)", fg_color="#555555")
        else:
            nom_corde = ["Mi", "La", "Ré", "Sol", "Si", "Mi"][corde_active]
            btn_save_corde.configure(state="normal", text=f"SAVE CORDE ({nom_corde})", fg_color="#2980b9")
    except NameError:
        pass

def appliquer_random():
    import random
    cordes = range(6) if corde_active == "ALL" else [corde_active]
    for c in cordes:
        for nom_effet, config in CONFIG_EFFETS.items():
            if EFFETS_MAP.get(nom_effet, -1) in chainage_slots[c]:
                for idx, param in enumerate(config["params"]):
                    if param.get("type") != "button" and param["nom"] != "--":
                        memoire_effets[nom_effet][c][idx] = random.randint(0, 127)
    maj_sliders_visuels()
    envoyer_tout_midi()
    marquer_preset_modifie()

# region 6. Footswitches et Presets
 
frame_sw = ctk.CTkFrame(center_container, fg_color="transparent")
frame_sw.grid(row=3, column=0, columnspan=2, pady=15, sticky="ew")
 
btn_bypass = ctk.CTkButton(frame_sw, text="BYPASS", fg_color="#555555", width=160, height=70, corner_radius=35, command=Activation_bypass)
btn_bypass.pack(side="left", padx=20, expand=True)
 
btn_save_corde = ctk.CTkButton(frame_sw, text="SAVE CORDE", command=sauvegarder_preset_json_corde, fg_color="#2980b9", width=160, height=70, corner_radius=35)
btn_save_corde.pack(side="left", padx=10, expand=True)

btn_save_hexa = ctk.CTkButton(frame_sw, text="SAVE HEXA", command=sauvegarder_preset_json_hexa, fg_color="#27ae60", width=160, height=70, corner_radius=35)
btn_save_hexa.pack(side="left", padx=10, expand=True)

btn_random = ctk.CTkButton(frame_sw, text="RANDOM", command=appliquer_random, fg_color="#8e44ad", width=160, height=70, corner_radius=35)
btn_random.pack(side="left", padx=20, expand=True)

ctk.CTkButton(frame_sw, text="RESET", command=Reset_All, fg_color="#A12222", width=160, height=70, corner_radius=35).pack(side="left", padx=20, expand=True)
maj_bouton_save()
 
# endregion

# region 7. Moniteur CPU DaisySeed

cpu_avg_value = 0
cpu_max_value = 0

frame_cpu = ctk.CTkFrame(center_container, border_width=2, corner_radius=10)
frame_cpu.grid(row=4, column=0, padx=10, pady=(5, 15), sticky="ew")

# Titre du panneau + bouton rescan
frame_cpu_header = ctk.CTkFrame(frame_cpu, fg_color="transparent")
frame_cpu_header.pack(fill="x", padx=10, pady=(8, 4))

cpu_title = ctk.CTkLabel(frame_cpu_header, text="POWER CHARGE CPU — DaisySeed", font=("Arial", 14, "bold"))
cpu_title.pack(side="left", expand=True)

btn_rescan = ctk.CTkButton(frame_cpu_header, text="🔄 RESCAN USB", width=120, height=28,
                           font=("Arial", 11, "bold"), fg_color="#2c3e50", hover_color="#3d566e",
                           command=rescanner_midi)
btn_rescan.pack(side="right", padx=5)

# --- Ligne AVG ---
frame_avg = ctk.CTkFrame(frame_cpu, fg_color="transparent")
frame_avg.pack(fill="x", padx=15, pady=2)

lbl_avg_title = ctk.CTkLabel(frame_avg, text="Moy.", font=("Arial", 12), width=40)
lbl_avg_title.pack(side="left")

pbar_avg = ctk.CTkProgressBar(frame_avg, width=300, height=18, corner_radius=8)
pbar_avg.set(0)
pbar_avg.pack(side="left", padx=8, expand=True, fill="x")

lbl_avg_pct = ctk.CTkLabel(frame_avg, text="-- %", font=("Courier", 13, "bold"), width=55)
lbl_avg_pct.pack(side="left")

# --- Ligne MAX ---
frame_max = ctk.CTkFrame(frame_cpu, fg_color="transparent")
frame_max.pack(fill="x", padx=15, pady=(2, 8))

lbl_max_title = ctk.CTkLabel(frame_max, text="Max.", font=("Arial", 12), width=40)
lbl_max_title.pack(side="left")

pbar_max = ctk.CTkProgressBar(frame_max, width=300, height=18, corner_radius=8)
pbar_max.set(0)
pbar_max.pack(side="left", padx=8, expand=True, fill="x")

lbl_max_pct = ctk.CTkLabel(frame_max, text="-- %", font=("Courier", 13, "bold"), width=55)
lbl_max_pct.pack(side="left")

# --- Indicateur d'état ---
lbl_cpu_status = ctk.CTkLabel(frame_cpu, text="En attente de données MIDI…", 
                              font=("Arial", 11), text_color="#888888")
lbl_cpu_status.pack(pady=(0, 8))

def couleur_charge(pct):
    """Retourne une couleur selon le pourcentage de charge CPU (0-100)"""
    if pct < 50:
        return "#22C55E"   # Vert
    elif pct < 75:
        return "#F59E0B"   # Orange
    elif pct < 90:
        return "#EF4444"   # Rouge
    else:
        return "#DC2626"   # Rouge vif

def maj_cpu_monitor(avg, maxi):
    """Met à jour l'affichage du moniteur CPU"""
    avg = max(0, min(100, avg))
    maxi = max(0, min(100, maxi))
    
    # Barres de progression (valeurs 0.0 - 1.0)
    pbar_avg.set(avg / 100.0)
    pbar_max.set(maxi / 100.0)
    
    # Couleurs des barres
    pbar_avg.configure(progress_color=couleur_charge(avg))
    pbar_max.configure(progress_color=couleur_charge(maxi))
    
    # Labels pourcentage
    lbl_avg_pct.configure(text=f"{avg:3d} %")
    lbl_max_pct.configure(text=f"{maxi:3d} %")
    
    # Indicateur d'état
    if maxi > 90:
        lbl_cpu_status.configure(text="WARN SURCHARGE CPU !", text_color="#DC2626")
    elif maxi > 75:
        lbl_cpu_status.configure(text="POWER Charge élevée", text_color="#F59E0B")
    elif maxi > 50:
        lbl_cpu_status.configure(text="OK Charge modérée", text_color="#F59E0B")
    else:
        lbl_cpu_status.configure(text="OK CPU tranquille", text_color="#22C55E")

def ecouter_midi_entrant():
    """Scrute le port MIDI en entrée pour recevoir la charge CPU (CC 80 & 81)"""
    global cpu_avg_value, cpu_max_value, port_midi_in, zombie_ports
    if port_midi_in:
        try:
            for msg in port_midi_in.iter_pending():
                if msg.type == 'control_change':
                    if msg.control == 80:
                        cpu_avg_value = msg.value
                    elif msg.control == 81:
                        cpu_max_value = msg.value
                maj_cpu_monitor(cpu_avg_value, cpu_max_value)
        except Exception:
            pass
    win.after(50, ecouter_midi_entrant)

# endregion

# region 8. Console MIDI
frame_midi_log = ctk.CTkFrame(center_container, border_width=2, corner_radius=10)
frame_midi_log.grid(row=5, column=0, padx=10, pady=(5, 15), sticky="ew")

frame_midi_header = ctk.CTkFrame(frame_midi_log, fg_color="transparent")
frame_midi_header.pack(fill="x", padx=10, pady=(8, 4))

midi_log_title = ctk.CTkLabel(frame_midi_header, text="🎹 LOG MIDI (OUT)", font=("Arial", 14, "bold"))
midi_log_title.pack(side="left")

show_midi_log = ctk.BooleanVar(value=False)
chk_midi_log = ctk.CTkSwitch(frame_midi_header, text="Afficher Log", variable=show_midi_log)
chk_midi_log.pack(side="right")

textbox_midi_log = ctk.CTkTextbox(frame_midi_log, height=120, font=("Courier", 12))
textbox_midi_log.pack(fill="x", padx=10, pady=(0, 10))
textbox_midi_log.insert("end", "En attente de messages MIDI...\n")
# endregion
 
maj_leds()
envoyer_tout_midi()

# Appliquer le visuel bypass au démarrage (tous les effets commencent bypassés)
for nom_effet in CONFIG_EFFETS:
    appliquer_visuel_bypass(nom_effet)

# Lancement de la boucle de scrutation MIDI en entrée
win.after(50, ecouter_midi_entrant)

win.mainloop()
