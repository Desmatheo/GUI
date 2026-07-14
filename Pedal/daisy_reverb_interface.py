import customtkinter as ctk
import random
import json
import mido

# region 1. Setup et configuration Réverb Dattorro

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

win = ctk.CTk()
win.title("Daisy Seed - Réverbération Dattorro")
win.geometry("900x600")

# --- CONNEXION MIDI DIRECTE (RTMIDI) ---
try:
    ports_out = mido.get_output_names()
    ports_in = mido.get_input_names()

    daisy_port_out = next((p for p in ports_out if "Daisy" in p or "USB" in p), None)
    daisy_port_in = next((p for p in ports_in if "Daisy" in p or "USB" in p), None)

    if daisy_port_out and daisy_port_in:
        port_midi = mido.open_output(daisy_port_out) 
        port_midi_in = mido.open_input(daisy_port_in)
        print(f"✓ Connecté à la Daisy Seed (Out: '{daisy_port_out}' | In: '{daisy_port_in}')")
    else:
        print("⚠ Daisy non trouvée. Lancement de l'interface en mode SANS MIDI.")
        port_midi = None
        port_midi_in = None
    midi_ok = (port_midi is not None)
except Exception as e:
    port_midi = None
    port_midi_in = None
    midi_ok = False
    print(f"✗ Erreur MIDI : {e}")

# Centrer les Frames
win.grid_columnconfigure(0, weight=1)
win.grid_rowconfigure(0, weight=1)

center_container = ctk.CTkFrame(master=win, fg_color="transparent")
center_container.grid(row=0, column=0, sticky="nsew")

# --- PARAMÈTRES DE LA RÉVERB DATTORRO ---
CONFIG_REVERB = {
    "PreDelay": {"cc": 14, "min": 0, "max": 127, "label": "Pre-Delay"},
    "Mix": {"cc": 15, "min": 0, "max": 127, "label": "Dry/Wet Mix"},
    "Decay": {"cc": 16, "min": 0, "max": 127, "label": "Decay Time"},
    "ModDepth": {"cc": 17, "min": 0, "max": 127, "label": "Mod Depth"},
    "ModSpeed": {"cc": 18, "min": 0, "max": 127, "label": "Mod Speed"},
    "CutoffFreq": {"cc": 19, "min": 0, "max": 127, "label": "Input Filter"}
}

# Mémoire des valeurs
reverb_values = {k: 64 for k in CONFIG_REVERB.keys()}

sliders, slider_labels = [], []

# endregion

# region 2. Fonctions et Événements

def maj_ecran():
    """Affiche les paramètres actuels"""
    vals = reverb_values
    l1 = f"Pre-Delay: {int(vals['PreDelay']):<3} | Mix: {int(vals['Mix']):<3} | Decay: {int(vals['Decay']):<3}"
    l2 = f"Mod Depth: {int(vals['ModDepth']):<3} | Mod Speed: {int(vals['ModSpeed']):<3} | Filter: {int(vals['CutoffFreq']):<3}"
    
    ecran_reverb.configure(text=f"DATTORRO REVERB\n{'-'*50}\n{l1}\n{l2}")

def slider_callback(valeur, param_name):
    v_int = int(float(valeur))
    reverb_values[param_name] = v_int
    
    # Mise à jour du label du slider
    slider_labels[list(CONFIG_REVERB.keys()).index(param_name)].configure(
        text=f"{CONFIG_REVERB[param_name]['label']} : {v_int}"
    )
    
    maj_ecran()
    
    # Envoi MIDI
    if midi_ok and port_midi:
        cc_num = CONFIG_REVERB[param_name]["cc"]
        msg = mido.Message('control_change', control=cc_num, value=v_int)
        port_midi.send(msg)

def action_random():
    """Valeurs aléatoires pour tous les paramètres"""
    for param_name in CONFIG_REVERB.keys():
        val_rand = random.randint(0, 127)
        reverb_values[param_name] = val_rand
        idx = list(CONFIG_REVERB.keys()).index(param_name)
        sliders[idx].set(val_rand)
    maj_ecran()

def sauvegarder_preset(nom):
    """Sauvegarde le preset courant"""
    data = {"preset": nom, "reverb": reverb_values}
    with open(f"daisy_preset_{nom}.json", "w") as f:
        json.dump(data, f, indent=4)
    print(f"✓ Preset '{nom}' sauvegardé")
    maj_ecran()

def charger_preset(nom):
    """Charge un preset"""
    global reverb_values
    try:
        with open(f"daisy_preset_{nom}.json", "r") as f:
            data = json.load(f)
            reverb_values = data["reverb"]
            for i, param_name in enumerate(CONFIG_REVERB.keys()):
                sliders[i].set(reverb_values[param_name])
            print(f"✓ Preset '{nom}' chargé")
            maj_ecran()
    except Exception as e:
        print(f"✗ Erreur chargement preset : {e}")

# Fonction appelée périodiquement par CustomTkinter
def ecouter_midi_entrant():
    if midi_ok and port_midi_in:
        # iter_pending() dépile tous les messages arrivés sans bloquer le programme
        for msg in port_midi_in.iter_pending():
            if msg.type == 'control_change':
                # Cherche à quel paramètre correspond ce CC
                for param_name, config in CONFIG_REVERB.items():
                    if config["cc"] == msg.control:
                        v_int = msg.value
                        reverb_values[param_name] = v_int
                        
                        # Mise à jour graphique du slider correspondant
                        idx = list(CONFIG_REVERB.keys()).index(param_name)
                        sliders[idx].set(v_int)
                        slider_labels[idx].configure(text=f"{config['label']} : {v_int}")
                        maj_ecran()
                        break
                        
    # On redemande à CustomTkinter de rappeler cette fonction dans 20 millisecondes
    win.after(20, ecouter_midi_entrant)

# endregion

# region 3. Interface Graphique

# Écran d'affichage
ecran_reverb = ctk.CTkLabel(master=center_container, text="DATTORRO REVERB", 
                            font=("Courier", 16, "bold"),
                            text_color="#00FF00", fg_color="#1a1a1a", 
                            corner_radius=10, height=100, width=700)
ecran_reverb.grid(row=0, column=0, columnspan=3, pady=20, padx=10)

# Grille des sliders (2 lignes x 3 colonnes)
frame_sliders = ctk.CTkFrame(center_container, fg_color="transparent")
frame_sliders.grid(row=1, column=0, columnspan=3, padx=20, pady=20, sticky="nsew")

params_list = list(CONFIG_REVERB.keys())
for i, param_name in enumerate(params_list):
    ligne = i // 3
    colonne = i % 3
    
    cellule = ctk.CTkFrame(frame_sliders, fg_color="transparent")
    cellule.grid(row=ligne, column=colonne, padx=15, pady=15, sticky="nsew")
    
    # Label du paramètre
    lbl = ctk.CTkLabel(cellule, text=f"{CONFIG_REVERB[param_name]['label']} : 64", 
                       font=("Arial", 12, "bold"))
    lbl.pack()
    slider_labels.append(lbl)
    
    # Slider
    s = ctk.CTkSlider(cellule, from_=0, to=127, orientation="vertical", height=150,
                      command=lambda v, p=param_name: slider_callback(v, p))
    s.set(64)
    s.pack(pady=8)
    sliders.append(s)

# Boutons de contrôle
frame_boutons = ctk.CTkFrame(center_container, fg_color="transparent")
frame_boutons.grid(row=2, column=0, columnspan=3, pady=20, sticky="ew")

ctk.CTkButton(frame_boutons, text="🎲 RANDOM", command=action_random, 
              fg_color="#7022A1", width=150, height=50).pack(side="left", padx=10, expand=True)
ctk.CTkButton(frame_boutons, text="💾 SAVE A", command=lambda: sauvegarder_preset("A"), 
              fg_color="#2c3e50", width=150, height=50).pack(side="left", padx=10, expand=True)
ctk.CTkButton(frame_boutons, text="📂 LOAD A", command=lambda: charger_preset("A"), 
              fg_color="#2c3e50", width=150, height=50).pack(side="left", padx=10, expand=True)
ctk.CTkButton(frame_boutons, text="💾 SAVE B", command=lambda: sauvegarder_preset("B"), 
              fg_color="#2c3e50", width=150, height=50).pack(side="left", padx=10, expand=True)
ctk.CTkButton(frame_boutons, text="📂 LOAD B", command=lambda: charger_preset("B"), 
              fg_color="#2c3e50", width=150, height=50).pack(side="left", padx=10, expand=True)

# endregion

maj_ecran()

# Lancement de la boucle de scrutation MIDI
win.after(20, ecouter_midi_entrant) 

win.mainloop()
