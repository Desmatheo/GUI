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

# --- CONSTANTES DE CONFIGURATION (façon "#define") ---
USE_LOOPMIDI = False  # Mettre à True pour utiliser loopMIDI (Windows)
NOM_PORT_BOUCLE = 'loopMIDI Port 1'
# -----------------------------------------------------

# Connexion midi
try:
    ports = mido.get_output_names()
    
    print("\n--- PORTS MIDI DÉTECTÉS ---")
    for p in ports:
        print(f" - {p}")
    print("---------------------------\n")

    if USE_LOOPMIDI:
        port_midi = mido.open_output(NOM_PORT_BOUCLE)
        print(f"Connecté en SIMULATION sur : {NOM_PORT_BOUCLE}")
        midi_ok = True
    else:
        port_midi = None
        # Recherche matérielle (insensible à la casse), priorité à la Teensy
        port_name = next((p for p in ports if "teensy" in p.lower()), None)
        device_type = "TEENSY"

        # Si pas de Teensy, on cherche une Daisy Seed
        if not port_name:
            port_name = next((p for p in ports if "daisy" in p.lower() or "usb" in p.lower()), None)
            device_type = "DAISY (ou port USB générique)"

        if port_name:
            try:
                port_midi = mido.open_output(port_name)
                print(f"Connecté à {device_type} via RtMidi : {port_name}")
                midi_ok = True
            except Exception as e:
                print(f"Erreur à l'ouverture du port '{port_name}': {e}")
                port_midi = None
                midi_ok = False

        if not port_midi:
            midi_ok = False
            print("Port MIDI (Teensy ou Daisy) non trouvé, lancement de l'interface SANS MIDI.")
except Exception as e:
    port_midi = None
    midi_ok = False
    print(f"Erreur MIDI SETUP : {e}")

# Centrer les Frames
win.grid_columnconfigure(0, weight=1)
win.grid_rowconfigure(0, weight=1)

center_container = ctk.CTkFrame(master=win, fg_color="transparent")
center_container.grid(row=0, column=0)

# Config des effets et paramètres
CONFIG_EFFETS = {
    "Delay": {
        "base_cc": 10,
        "bypass_cc": 48,
        "params": ["Mix", "DelayTime", "FeedBack", "--", "--", "Vol"]
    },
    "Distortion": {
        "base_cc": 50,
        "bypass_cc": 88,
        "params": ["Gain", "Tone", "Mix", "--", "--", "Vol"]
    },
    "Earth": {
        "base_cc": 90,
        "bypass_cc": 89,
        "params": ["Mix", "Octave", "--", "--", "--", "Vol"]
    }
}

corde_active = 0
noms_cordes = ["Mi (E2)", "La (A2)", "Ré (D3)", "Sol (G3)", "Si (B3)", "Mi (E4)"]

bypass_global = False
bypass_effets = {nom_effet: False for nom_effet in CONFIG_EFFETS.keys()}
cordes_mute = [False] * 6

# Mémoire pour chaque effet et chaque corde
memoire_effets = {
    nom_effet: {corde: [64] * 6 for corde in range(6)}
    for nom_effet in CONFIG_EFFETS.keys()
}

sliders = {nom_effet: [] for nom_effet in CONFIG_EFFETS.keys()}
slider_labels = {nom_effet: [] for nom_effet in CONFIG_EFFETS.keys()}
bypass_buttons = {}
leds = []

# endregion

# region 2. Fonctions, Evenements et Affichage Écran

#Affichage titre potards et valeurs
def maj_sliders_visuels():
    for nom_effet, config in CONFIG_EFFETS.items():
        valeurs = memoire_effets[nom_effet][corde_active]
        for i, v in enumerate(valeurs):
            sliders[nom_effet][i].set(v)
            param_label = config["params"][i]
            if param_label != "--":
                slider_labels[nom_effet][i].configure(text=f"{param_label}: {int(v)}")

def slider_callback(valeur, nom_effet, index):
    v_int = int(float(valeur))
    memoire_effets[nom_effet][corde_active][index] = v_int
    
    param_label = CONFIG_EFFETS[nom_effet]["params"][index]
    slider_labels[nom_effet][index].configure(text=f"{param_label}: {v_int}")
    
    # Envoi du MIDI
    if midi_ok and port_midi:
        base_cc = CONFIG_EFFETS[nom_effet]["base_cc"]
        # NOUVELLE LOGIQUE : On utilise les canaux MIDI
        cc_num = base_cc + index
        msg = mido.Message('control_change', channel=corde_active, control=cc_num, value=v_int)
        port_midi.send(msg)
        
def action_random_effet(nom_effet):
    valeurs = memoire_effets[nom_effet][corde_active]
    base_cc = CONFIG_EFFETS[nom_effet]["base_cc"]
    for i in range(len(valeurs)):
        val_rand = random.randint(0, 127)
        valeurs[i] = val_rand
        if midi_ok and port_midi:
            cc_num = base_cc + i
            # NOUVELLE LOGIQUE : On utilise les canaux MIDI
            msg = mido.Message('control_change', channel=corde_active, control=cc_num, value=val_rand)
            port_midi.send(msg)
    maj_sliders_visuels()

def sauvegarder_dans_preset(nom):
    data_save = {"preset": nom, "reglages_effets": memoire_effets}
    with open(f"preset_{nom}.json", "w") as f:
        json.dump(data_save, f, indent=4)

def charger_preset(nom):
    global memoire_effets
    try:
        with open(f"preset_{nom}.json", "r") as f:
            data = json.load(f)
            for eff, cordes_data in data["reglages_effets"].items():
                if eff in memoire_effets:
                    for corde_str, valeurs in cordes_data.items():
                        memoire_effets[eff][int(corde_str)] = valeurs
    except Exception as e:
        print(f"Erreur preset : {e}")
    maj_sliders_visuels()

def toggle_bypass_effet(nom_effet):
    """Active ou désactive le Bypass pour un effet"""
    bypass_effets[nom_effet] = not bypass_effets[nom_effet]
    
    if midi_ok and port_midi:
        val = 127 if bypass_effets[nom_effet] else 0
        if "bypass_cc" in CONFIG_EFFETS[nom_effet]:
            cc_num = CONFIG_EFFETS[nom_effet]["bypass_cc"]
            port_midi.send(mido.Message('control_change', control=cc_num, value=val))
    
    if nom_effet in bypass_buttons:
        bypass_buttons[nom_effet].configure(fg_color="#A12222" if bypass_effets[nom_effet] else "#555555")

def Activation_mute(index):
    """Mute ou demute une corde"""
    cordes_mute[index] = not cordes_mute[index]
    if midi_ok and port_midi:
        val = 127 if cordes_mute[index] else 0
        port_midi.send(mido.Message('control_change', control=index, value=val))
    maj_leds()

def Activation_bypass():
    """Active ou désactive le Bypass global"""
    global bypass_global
    bypass_global = not bypass_global
    if midi_ok and port_midi:
        val = 127 if bypass_global else 0
        port_midi.send(mido.Message('control_change', control=126, value=val))
    
    btn_bypass.configure(fg_color="#A12222" if bypass_global else "#555555")

def maj_leds():
    for i, led in enumerate(leds):
        if cordes_mute[i]:
            color = "#FF0000"  # Rouge si Mute
            text = "M"
        elif i == corde_active:
            color = "#00FF00"  # Vert clair si c'est la corde sélectionnée
            text = ""
        else:
            color = "#1a331a"  # Vert sombre par défaut
            text = ""
        led.configure(fg_color=color, text=text)
    maj_sliders_visuels()

def changer_corde(direction):
    global corde_active
    if direction == "up":
        # Si on dépasse la corde 5 (index 5), on revient à 0, sinon on avance
        corde_active = (corde_active + 1) % 6
    elif direction == "down":
        # Si on descend en dessous de 0, on bascule à la corde 5, sinon on recule
        corde_active = (corde_active - 1 + 6) % 6
    maj_leds()

# endregion

# region 3. Ecran, Navigation et Menu Effets

frame_nav = ctk.CTkFrame(master=center_container, fg_color="transparent")
frame_nav.grid(row=0, column=0, pady=5, sticky="ew")

# --- Frame pour centrer les contrôles de navigation ---
nav_controls_frame = ctk.CTkFrame(frame_nav, fg_color="transparent")
nav_controls_frame.pack(expand=True)

ctk.CTkButton(nav_controls_frame, text="▼", width=50, command=lambda: changer_corde("down")).pack(side="left", padx=10, pady=5)

# --- Frame pour les cordes (titres + leds) ---
strings_frame = ctk.CTkFrame(nav_controls_frame, fg_color="transparent")
strings_frame.pack(side="left", padx=10)

# --- Titres des cordes ---
labels_frame = ctk.CTkFrame(strings_frame, fg_color="transparent")
labels_frame.pack()
string_names = [s.split(" ")[0] for s in noms_cordes] # "Mi", "La", "Ré"...
for name in string_names:
    lbl = ctk.CTkLabel(labels_frame, text=name, width=25, font=("Arial", 10))
    lbl.pack(side="left", padx=10, pady=2)

# --- LEDs des cordes ---
leds_box = ctk.CTkFrame(strings_frame, fg_color="#1a1a1a", corner_radius=15)
leds_box.pack(pady=2)

for i in range(6):
    l = ctk.CTkButton(leds_box, text="", width=25, height=25, corner_radius=12, command=lambda idx=i: Activation_mute(idx))
    l.pack(side="left", padx=10, pady=5)
    leds.append(l)

ctk.CTkButton(nav_controls_frame, text="▲", width=50, command=lambda: changer_corde("up")).pack(side="left", padx=10, pady=5)

# endregion

# region 4. Grille des effets et potentiomètres

frame_effets_container = ctk.CTkFrame(center_container, fg_color="transparent")
frame_effets_container.grid(row=1, column=0, padx=10, pady=5)

for i, (nom_effet, config) in enumerate(CONFIG_EFFETS.items()):
    
    # --- Conteneur pour un effet ---
    frame_effet = ctk.CTkFrame(frame_effets_container, border_width=2)
    frame_effet.grid(row=0, column=i, padx=15, pady=5, sticky="nsew")
    
    # --- Titre et boutons de l'effet ---
    frame_titre = ctk.CTkFrame(frame_effet, fg_color="transparent")
    frame_titre.pack(pady=5, padx=10, fill="x")
    
    ctk.CTkLabel(frame_titre, text=nom_effet.upper(), font=("Arial", 16, "bold")).pack(side="left", expand=True)
    
    # On ajoute le bouton bypass seulement si un 'bypass_cc' est défini
    if "bypass_cc" in config:
        btn_bypass_effet = ctk.CTkButton(frame_titre, text="Bypass", width=70, fg_color="#555555",
                                         command=lambda n=nom_effet: toggle_bypass_effet(n))
        btn_bypass_effet.pack(side="left", padx=5)
        bypass_buttons[nom_effet] = btn_bypass_effet

    # --- Grille des potentiomètres pour cet effet ---
    frame_potards_effet = ctk.CTkFrame(frame_effet, fg_color="transparent")
    frame_potards_effet.pack(pady=5, padx=10)

    for j, param_name in enumerate(config["params"]):
        cellule = ctk.CTkFrame(frame_potards_effet, fg_color="transparent")
        cellule.grid(row=j, column=0, padx=5, pady=4, sticky="w")
        
        is_active_param = (param_name != "--")

        lbl = ctk.CTkLabel(cellule, text=f"{param_name}: --" if is_active_param else "", font=("Arial", 12))
        lbl.pack(anchor="w")
        slider_labels[nom_effet].append(lbl)
        
        s = ctk.CTkSlider(cellule, from_=0, to=127, orientation="horizontal", width=180,
                          command=lambda v, ne=nom_effet, idx=j: slider_callback(v, ne, idx))
        s.set(64)
        if is_active_param:
            s.pack(pady=2, anchor="w")
        sliders[nom_effet].append(s)

    ctk.CTkButton(frame_effet, text="🎲 RANDOM", command=lambda n=nom_effet: action_random_effet(n), 
                  fg_color="#7022A1", width=120).pack(pady=(2, 10), padx=10)

# endregion

# region 5. Footswitches

frame_sw = ctk.CTkFrame(center_container, fg_color="transparent")
frame_sw.grid(row=2, column=0, columnspan=2, pady=15, sticky="ew")

btn_bypass = ctk.CTkButton(frame_sw, text="BYPASS", fg_color="#555555", width=160, height=70, corner_radius=35, command=Activation_bypass)
btn_bypass.pack(side="left", padx=20, expand=True)
ctk.CTkButton(frame_sw, text="LOAD A", command=lambda: charger_preset("A"), width=160, height=70, corner_radius=35).pack(side="left", padx=20, expand=True)
ctk.CTkButton(frame_sw, text="LOAD B", command=lambda: charger_preset("B"), width=160, height=70, corner_radius=35).pack(side="left", padx=20, expand=True)

# endregion

maj_leds()
maj_sliders_visuels()
win.mainloop()