import customtkinter as ctk
import random
import json
import mido
 
# region 1. Setup et configuration Multi-Effets
 
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")
 
win = ctk.CTk()
win.title("Pédale Hexa - Contrôleur MIDI (Teensy/Daisy)")
win.geometry("950x780")
 
# --- CONSTANTES DE CONFIGURATION ---
USE_LOOPMIDI = False  
NOM_PORT_BOUCLE = 'loopMIDI Port 1'
# -----------------------------------
 
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
            print(f"✓ Port MIDI IN ouvert : {target}")
            return p
        else:
            return None
    except Exception as e:
        print(f"⚠ Erreur ouverture port MIDI IN : {e}")
        return None
 
def rescanner_midi():
    """Ferme les ports MIDI existants et relance la détection (OUT + IN)."""
    global port_midi, midi_ok, port_midi_in
    
    # --- Fermeture propre des ports existants ---
    if port_midi:
        try:
            port_midi.close()
        except Exception:
            pass
        port_midi = None
    if port_midi_in:
        try:
            port_midi_in.close()
        except Exception:
            pass
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
        print("⚠ Pas de port MIDI en entrée trouvé (le moniteur CPU sera inactif).")
    
    # --- Feedback visuel (si le panneau CPU existe déjà) ---
    try:
        if midi_ok and port_midi_in:
            lbl_cpu_status.configure(text="✓ MIDI reconnecté !", text_color="#22C55E")
        elif midi_ok:
            lbl_cpu_status.configure(text="✓ MIDI OUT ok — IN absent", text_color="#F59E0B")
        else:
            lbl_cpu_status.configure(text="✗ Aucun port MIDI trouvé", text_color="#DC2626")
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
            {"nom": "Mix", "min": 0, "max": 100, "unite": "%"},
            {"nom": "DelayTime", "min": 20, "max": 1000, "unite": "ms"},
            {"nom": "FeedBack", "min": 0, "max": 100, "unite": "%"},
            {"nom": "--"},
            {"nom": "--"},
            {"nom": "Vol", "min": 0, "max": 10, "unite": ""}
        ]
    },
    "Distortion": {
        "base_cc": 50,
        "bypass_cc": 88,
        "params": [
            {"nom": "Mix", "min": 0, "max": 100, "unite": "%"},
            {"nom": "Mode", "min": 1, "max": 6, "unite": "mode", "steps": 5},
            {"nom": "Tone", "min": 500, "max": 2000, "unite": "Hz"},
            {"nom": "Vol", "min": 0, "max": 10, "unite": ""},
            {"nom": "Gain", "min": 0, "max": 10, "unite": ""},
            {"nom": "Intens", "min": 0, "max": 100, "unite": "%"},
            {"nom": "Oversamp", "min": 0, "max": 1, "unite": "bool", "steps": 1}
        ]
    },
    "Earth": {
        "base_cc": 90,
        "bypass_cc": 89,
        "params": [
            {"nom": "Mix", "min": 0, "max": 100, "unite": "%"},
            # steps=2 crée 3 crans : Position 0, 1 et 2 (soit les MIDI 0, 64 et 127)
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
            {"nom": "--"},
            {"nom": "Vol", "min": 0, "max": 10, "unite": ""}
        ]
    }
}
 
corde_active = 0
corde_precedente = 0  
noms_cordes = ["Mi (E2)", "La (A2)", "Ré (D3)", "Sol (G3)", "Si (B3)", "Mi (E4)"]
 
bypass_global = False
bypass_effets = {
    nom_effet: {corde: True for corde in range(6)}
    for nom_effet in CONFIG_EFFETS.keys()
}
cordes_mute = [False] * 6
 
memoire_effets = {
    nom_effet: {corde: [0 if i == 0 else 64 for i in range(len(CONFIG_EFFETS[nom_effet]["params"]))] for corde in range(6)}
    for nom_effet in CONFIG_EFFETS.keys()
}
 
# endregion
 
# region 3. Fonctions, Evenements et Affichage Écran
 
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
    if param_info["nom"] == "--":
        return ""
       
    val_reelle = map_valeur_reelle(val_midi, param_info["min"], param_info["max"])
   
    # --- LOGIQUE SPÉCIALE POUR L'AFFICHAGE DE L'OCTAVER EARTH ---
    if param_info["unite"] == "oct_mode":
        # val_reelle ira de 0 à 2.
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
        return f"{param_info['nom']}: Type {cran}"

    if param_info["unite"] == "bool":
        etat = "ON" if val_reelle >= 0.5 else "OFF"
        return f"{param_info['nom']}: {etat}"
 
    # --- LOGIQUE CLASSIQUE POUR LE RESTE ---
    if param_info["max"] > 10:
        return f"{param_info['nom']}: {int(val_reelle)} {param_info['unite']}"
    else:
        return f"{param_info['nom']}: {val_reelle:.1f} {param_info['unite']}"
 
def maj_sliders_visuels():
    texte_titre = f"CORDE ACTIVE : {noms_cordes[corde_active] if corde_active != 'ALL' else '[MODE ALL]'}"
    label_info_corde.configure(text=texte_titre, text_color="#0088FF" if corde_active == "ALL" else "white")
   
    for nom_effet, config in CONFIG_EFFETS.items():
        corde_ref = 0 if corde_active == "ALL" else corde_active
        valeurs = memoire_effets[nom_effet][corde_ref]
       
        for i, v in enumerate(valeurs):
            sliders[nom_effet][i].set(v)
            param_info = config["params"][i]
            if param_info["nom"] != "--":
                texte = get_texte_label(param_info, v)
                slider_labels[nom_effet][i].configure(text=texte)
        
        # Réappliquer le visuel bypass après la mise à jour des sliders
        appliquer_visuel_bypass(nom_effet)
 
def slider_callback(valeur, nom_effet, index):
    v_int = int(float(valeur))
    param_info = CONFIG_EFFETS[nom_effet]["params"][index]
    base_cc = CONFIG_EFFETS[nom_effet]["base_cc"]
    cc_num = base_cc + index
 
    if corde_active == "ALL":
        for channel in range(6):
            memoire_effets[nom_effet][channel][index] = v_int
            if midi_ok and port_midi:
                try:
                    msg = mido.Message('control_change', channel=channel, control=cc_num, value=v_int)
                    port_midi.send(msg)
                except Exception:
                    pass # Ignore l'erreur si le tampon USB est plein
    else:
        memoire_effets[nom_effet][corde_active][index] = v_int
        if midi_ok and port_midi:
            try:
                msg = mido.Message('control_change', channel=corde_active, control=cc_num, value=v_int)
                port_midi.send(msg)
            except Exception:
                pass # Ignore l'erreur si le tampon USB est plein
           
    texte = get_texte_label(param_info, v_int)
    slider_labels[nom_effet][index].configure(text=texte)
 
def appliquer_visuel_bypass(nom_effet):
    """Met à jour l'apparence visuelle d'un effet selon son état de bypass pour la corde active."""
    corde_ref = 0 if corde_active == "ALL" else corde_active
    est_bypasse = bypass_effets[nom_effet][corde_ref]
    
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

    for slider in sliders[nom_effet]:
        slider.configure(state=etat_ui, button_color=c_bypassed_slider if est_bypasse else c_active_slider, progress_color=c_bypassed_slider if est_bypasse else c_active_slider)
       
    if nom_effet in bypass_buttons:
        bypass_buttons[nom_effet].configure(fg_color="#A12222" if est_bypasse else "#555555")
 
def envoyer_tout_midi():
    if not midi_ok or not port_midi:
        return
    for channel in range(6):
        # Séparer les effets inactifs (Mix == 0) et actifs (Mix > 0)
        effets_inactifs = []
        effets_actifs = []
        for nom_effet, config in CONFIG_EFFETS.items():
            if memoire_effets[nom_effet][channel][0] > 0:
                effets_actifs.append((nom_effet, config))
            else:
                effets_inactifs.append((nom_effet, config))
                
        # Envoyer d'abord les inactifs, PUIS les actifs pour que le dernier envoyé 
        # (et donc celui qui reste actif dans la Daisy) soit celui qui a du Mix.
        for nom_effet, config in effets_inactifs + effets_actifs:
            base_cc = config["base_cc"]
            valeurs = memoire_effets[nom_effet][channel]
            for index, v in enumerate(valeurs):
                if config["params"][index]["nom"] != "--":
                    cc_num = base_cc + index
                    try:
                        msg = mido.Message('control_change', channel=channel, control=cc_num, value=int(v))
                        port_midi.send(msg)
                    except:
                        pass


def toggle_bypass_effet(nom_effet):
    """Active ou désactive le Bypass pour un effet sur la corde active"""
    if corde_active == "ALL":
        # On inverse par rapport à la corde 0
        target_state = not bypass_effets[nom_effet][0]
        for corde in range(6):
            bypass_effets[nom_effet][corde] = target_state
            if midi_ok and port_midi:
                val = 127 if target_state else 0
                if "bypass_cc" in CONFIG_EFFETS[nom_effet]:
                    msg = mido.Message('control_change', channel=corde, control=CONFIG_EFFETS[nom_effet]["bypass_cc"], value=val)
                    try:
                        port_midi.send(msg)
                    except Exception:
                        pass
                
                # Si on active l'effet (bypass = False), on renvoie tous les paramètres
                if not target_state:
                    for index, p_val in enumerate(memoire_effets[nom_effet][corde]):
                        cc_num = CONFIG_EFFETS[nom_effet]["base_cc"] + index
                        try:
                            port_midi.send(mido.Message('control_change', channel=corde, control=cc_num, value=p_val))
                        except Exception:
                            pass

    else:
        # Toggle sur la corde active uniquement
        bypass_effets[nom_effet][corde_active] = not bypass_effets[nom_effet][corde_active]
        if midi_ok and port_midi:
            val = 127 if bypass_effets[nom_effet][corde_active] else 0
            if "bypass_cc" in CONFIG_EFFETS[nom_effet]:
                msg = mido.Message('control_change', channel=corde_active, control=CONFIG_EFFETS[nom_effet]["bypass_cc"], value=val)
                try:
                    port_midi.send(msg)
                except Exception:
                    pass

            # Si on active l'effet (bypass = False), on renvoie tous les paramètres
            if not bypass_effets[nom_effet][corde_active]:
                for index, p_val in enumerate(memoire_effets[nom_effet][corde_active]):
                    cc_num = CONFIG_EFFETS[nom_effet]["base_cc"] + index
                    try:
                        port_midi.send(mido.Message('control_change', channel=corde_active, control=cc_num, value=p_val))
                    except Exception:
                        pass
   
    appliquer_visuel_bypass(nom_effet)
 
def Sauvegarder_preset(nom):
    """Sauvegarde le preset courant (réglages + bypass)"""
    data_save = {
        "preset": nom,
        "reglages_effets": memoire_effets,
        "bypass_effets": bypass_effets
    }
    with open(f"preset_{nom}.json", "w") as f:
        json.dump(data_save, f, indent=4)
    print(f"✓ Preset '{nom}' sauvegardé")

def Charger_preset(nom):
    global memoire_effets, bypass_effets
    try:
        with open(f"preset_{nom}.json", "r") as f:
            data = json.load(f)
            for eff, cordes_data in data["reglages_effets"].items():
                if eff in memoire_effets:
                    for corde_str, valeurs in cordes_data.items():
                        expected_len = len(CONFIG_EFFETS[eff]["params"])
                        if len(valeurs) < expected_len:
                            valeurs.extend([64] * (expected_len - len(valeurs)))
                        memoire_effets[eff][int(corde_str)] = valeurs
            
            # Chargement des états de bypass
            if "bypass_effets" in data:
                for eff, bypass_data in data["bypass_effets"].items():
                    if eff in bypass_effets:
                        # Si l'ancien format était un simple booléen
                        if isinstance(bypass_data, bool):
                            for corde in range(6):
                                bypass_effets[eff][corde] = bypass_data
                        else:
                            # Nouveau format (dictionnaire de cordes)
                            for corde_str, etat in bypass_data.items():
                                bypass_effets[eff][int(corde_str)] = etat
            
            # Réappliquer les bypass en MIDI + Visuel pour toutes les cordes
            for eff in CONFIG_EFFETS.keys():
                for corde in range(6):
                    if midi_ok and port_midi and "bypass_cc" in CONFIG_EFFETS[eff]:
                        val = 127 if bypass_effets[eff][corde] else 0
                        msg = mido.Message('control_change', channel=corde, control=CONFIG_EFFETS[eff]["bypass_cc"], value=val)
                        try:
                            port_midi.send(msg)
                        except Exception:
                            pass
                appliquer_visuel_bypass(eff)
    except Exception as e:
        print(f"Erreur preset : {e}")
    maj_sliders_visuels()
    envoyer_tout_midi()
 
def Activation_mute(index):
    cordes_mute[index] = not cordes_mute[index]
    if midi_ok and port_midi:
        val = 127 if cordes_mute[index] else 0
        msg = mido.Message('control_change', control=index, value=val)
        try:
            port_midi.send(msg)
        except Exception:
            pass
        
        # Si on unmute la corde (mute == False), on renvoie tous ses paramètres
        if not cordes_mute[index]:
            for nom_effet, config in CONFIG_EFFETS.items():
                if not bypass_effets[nom_effet][index]:
                    for idx, p_val in enumerate(memoire_effets[nom_effet][index]):
                        cc_num = config["base_cc"] + idx
                        try:
                            port_midi.send(mido.Message('control_change', channel=index, control=cc_num, value=p_val))
                        except Exception:
                            pass

    maj_leds()
 
def Activation_bypass():
    global bypass_global
    bypass_global = not bypass_global
    if midi_ok and port_midi:
        val = 127 if bypass_global else 0
        msg = mido.Message('control_change', control=126, value=val)
        try:
            port_midi.send(msg)
        except Exception:
            pass
        
        # Si on désactive le bypass global (bypass = False), on renvoie tout
        if not bypass_global:
            envoyer_tout_midi()

    btn_bypass.configure(fg_color="#A12222" if bypass_global else "#555555")

def Reset_All():
    """Remet tous les paramètres à 0, active le bypass de tous les effets et unmute toutes les cordes"""
    for nom_effet in CONFIG_EFFETS.keys():
        for corde in range(6):
            bypass_effets[nom_effet][corde] = True
            for idx in range(len(CONFIG_EFFETS[nom_effet]["params"])):
                memoire_effets[nom_effet][corde][idx] = 0
                
    # Unmute all strings
    for corde in range(6):
        cordes_mute[corde] = False
        if midi_ok and port_midi:
            try:
                port_midi.send(mido.Message('control_change', control=corde, value=0))
            except Exception:
                pass
            
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
    
    # Mettre à jour les sliders pour correspondre à la corde sélectionnée
    for nom_effet, sliders_effet in sliders.items():
        valeurs = memoire_effets[nom_effet][corde_active] if corde_active != "ALL" else memoire_effets[nom_effet][0]
        for idx, slider in enumerate(sliders_effet):
            slider.configure(command=lambda v: None)
            slider.set(valeurs[idx])
            param_info = CONFIG_EFFETS[nom_effet]["params"][idx]
            if param_info["nom"] != "--":
                texte = get_texte_label(param_info, valeurs[idx])
                slider_labels[nom_effet][idx].configure(text=texte)
            slider.configure(command=lambda v, ne=nom_effet, i=idx: slider_callback(v, ne, i))
 
def toggle_mode_all():
    global corde_active, corde_precedente
    if corde_active == "ALL":
        corde_active = corde_precedente
    else:
        corde_active = "ALL"
    maj_leds()
 
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
 
for i in range(6):
    l = ctk.CTkButton(strings_frame, text="", width=30, height=30, corner_radius=15,
                      command=lambda idx=i: Activation_mute(idx))
    l.grid(row=1, column=i, padx=5, pady=5)
    leds.append(l)
 
label_info_corde = ctk.CTkLabel(frame_nav, text="", font=("Arial", 14, "bold"))
label_info_corde.pack(pady=5)
 
# endregion
 
# region 5. Grille des effets et potentiomètres
 
frame_effets_container = ctk.CTkFrame(center_container, fg_color="transparent")
frame_effets_container.grid(row=1, column=0, padx=10, pady=5)
 
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
        btn_bypass_effet.pack(side="left", padx=5)
        bypass_buttons[nom_effet] = btn_bypass_effet
 
    frame_potards_effet = ctk.CTkFrame(frame_effet, fg_color="transparent")
    frame_potards_effet.pack(pady=5, padx=10)
    slider_container_frames[nom_effet] = frame_potards_effet
 
    for j, param_info in enumerate(config["params"]):
        cellule = ctk.CTkFrame(frame_potards_effet, fg_color="transparent")
        cellule.grid(row=j, column=0, padx=5, pady=4, sticky="w")
       
        lbl = ctk.CTkLabel(cellule, text=f"{param_info['nom']}: --", font=("Arial", 12))
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
 
# endregion
 
# region 6. Footswitches et Presets
 
frame_sw = ctk.CTkFrame(center_container, fg_color="transparent")
frame_sw.grid(row=2, column=0, columnspan=2, pady=15, sticky="ew")
 
btn_bypass = ctk.CTkButton(frame_sw, text="BYPASS", fg_color="#555555", width=160, height=70, corner_radius=35, command=Activation_bypass)
btn_bypass.pack(side="left", padx=20, expand=True)
 
ctk.CTkButton(frame_sw, text="SAVE A", command=lambda: Sauvegarder_preset("A"), fg_color="#2c3e50", width=160, height=70, corner_radius=35).pack(side="left", padx=20, expand=True)
ctk.CTkButton(frame_sw, text="LOAD A", command=lambda: Charger_preset("A"), width=160, height=70, corner_radius=35).pack(side="left", padx=20, expand=True)
ctk.CTkButton(frame_sw, text="SAVE B", command=lambda: Sauvegarder_preset("B"), fg_color="#2c3e50", width=160, height=70, corner_radius=35).pack(side="left", padx=20, expand=True)
ctk.CTkButton(frame_sw, text="LOAD B", command=lambda: Charger_preset("B"), width=160, height=70, corner_radius=35).pack(side="left", padx=20, expand=True)
ctk.CTkButton(frame_sw, text="RESET", command=Reset_All, fg_color="#A12222", width=160, height=70, corner_radius=35).pack(side="left", padx=20, expand=True)
 
# endregion

# region 7. Moniteur CPU DaisySeed

cpu_avg_value = 0
cpu_max_value = 0

frame_cpu = ctk.CTkFrame(center_container, border_width=2, corner_radius=10)
frame_cpu.grid(row=3, column=0, padx=10, pady=(5, 15), sticky="ew")

# Titre du panneau + bouton rescan
frame_cpu_header = ctk.CTkFrame(frame_cpu, fg_color="transparent")
frame_cpu_header.pack(fill="x", padx=10, pady=(8, 4))

cpu_title = ctk.CTkLabel(frame_cpu_header, text="⚡ CHARGE CPU — DaisySeed", font=("Arial", 14, "bold"))
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
        lbl_cpu_status.configure(text="⚠ SURCHARGE CPU !", text_color="#DC2626")
    elif maxi > 75:
        lbl_cpu_status.configure(text="⚡ Charge élevée", text_color="#F59E0B")
    elif maxi > 50:
        lbl_cpu_status.configure(text="✓ Charge modérée", text_color="#F59E0B")
    else:
        lbl_cpu_status.configure(text="✓ CPU tranquille", text_color="#22C55E")

def ecouter_midi_entrant():
    """Scrute le port MIDI en entrée pour recevoir la charge CPU (CC 80 & 81)"""
    global cpu_avg_value, cpu_max_value
    if port_midi_in:
        for msg in port_midi_in.iter_pending():
            if msg.type == 'control_change':
                if msg.control == 80:
                    cpu_avg_value = msg.value
                elif msg.control == 81:
                    cpu_max_value = msg.value
                maj_cpu_monitor(cpu_avg_value, cpu_max_value)
    win.after(50, ecouter_midi_entrant)

# endregion
 
maj_leds()
envoyer_tout_midi()

# Appliquer le visuel bypass au démarrage (tous les effets commencent bypassés)
for nom_effet in CONFIG_EFFETS:
    appliquer_visuel_bypass(nom_effet)

# Lancement de la boucle de scrutation MIDI en entrée
win.after(50, ecouter_midi_entrant)

win.mainloop()