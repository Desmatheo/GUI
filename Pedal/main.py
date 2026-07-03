import customtkinter as ctk
import random
import json
import mido

# region 1. Setup et configuration Multi-Effets

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

win = ctk.CTk()
win.title("Pédale Hexa - Contrôleur MIDI (Teensy/Daisy)")
win.geometry("900x850")

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

# Mode de test True=Mono False=Hexa
MONO_MODE = False

# Config des effets et paramètres
if MONO_MODE:
    CONFIG_EFFETS = {
        "Delay": {
            "base_cc": 10,
            "params": ["Time", "Feedback", "Mix", "Mod R.", "Mod D.", "--"]
        },
        "Distortion": {
            "base_cc": 50,
            "params": ["Gain", "Tone", "Mix", "--", "--", "--"]
        },
        # "Reverb": {
        #     "base_cc": 90,
        #     "params": ["Room Size", "Damping", "Mix", "--", "--", "--"]
        # },
        "Earth": {
            "base_cc": 90,
            "params": ["Mix", "--", "--", "--", "--", "--"]
        }
    }
else:
    CONFIG_EFFETS = {
        "Delay": {
            "base_cc": 10,
            "params": ["Mix", "DelayTime", "FeedBack", "--", "--", "Vol"]
        },
        "Distortion": {
            "base_cc": 50,
            "params": ["Gain", "Tone", "Mix", "--", "--", "Vol"]
        },
        "Earth": {
            "base_cc": 90,
            "params": ["Mix", "Octave", "--", "--", "--", "Vol"]
        }
    }

effet_actif = "Delay"
corde_active = 0
noms_cordes = ["Mi (E2)", "La (A2)", "Ré (D3)", "Sol (G3)", "Si (B3)", "Mi (E4)"]

bypass_global = False
cordes_mute = [False] * 6

# Mémoire pour chaque effet et chaque corde
if MONO_MODE:
    memoire_effets = {
        nom_effet: {0: [64] * len(cfg["params"])}
        for nom_effet, cfg in CONFIG_EFFETS.items()
    }
else:
    memoire_effets = {
        nom_effet: {corde: [64] * 6 for corde in range(6)}
        for nom_effet in CONFIG_EFFETS.keys()
    }

sliders, slider_labels, leds = [], [], []

# endregion

# region 2. Fonctions, Evenements et Affichage Écran

#Affichage de sur l'ecran 
def maj_ecran_physique():
    valeurs = memoire_effets[effet_actif][corde_active]
    p = CONFIG_EFFETS[effet_actif]["params"]

    if MONO_MODE:
        l1 = f"P1:{p[0][:4]}={int(valeurs[0]):<3} | P2:{p[1][:4]}={int(valeurs[1]):<3} | P3:{p[2][:4]}={int(valeurs[2]):<3}"
        l2 = ""
        titre_ecran = f" [{effet_actif.upper()}] "
    else:
        l1 = f"P1:{p[0][:4]}={int(valeurs[0]):<3} | P2:{p[1][:4]}={int(valeurs[1]):<3} | P3:{p[2][:4]}={int(valeurs[2]):<3}"
        l2 = f"P4:{p[3][:4]}={int(valeurs[3]):<3} | P5:{p[4][:4]}={int(valeurs[4]):<3} | P6:{p[5][:4]}={int(valeurs[5]):<3}"
        titre_ecran = f" [{effet_actif.upper()}]  Corde: {noms_cordes[corde_active]} "

    ecran_effet.configure(text=f"{titre_ecran}\n{'-'*43}\n{l1}\n{l2}")

#Affichage titre potards et valeurs
def maj_sliders_visuels():
    valeurs = memoire_effets[effet_actif][corde_active]
    
    for i, v in enumerate(valeurs):
        sliders[i].set(v)
        slider_labels[i].configure(text=f"P{i+1} : {int(v)}")
    
    maj_ecran_physique()

def slider_callback(valeur, index):
    v_int = int(float(valeur))
    memoire_effets[effet_actif][corde_active][index] = v_int
    
    
    slider_labels[index].configure(text=f"P{index+1} : {v_int}")
    
    maj_ecran_physique()
    
    # Envoi du MIDI
    if midi_ok and port_midi:
        base_cc = CONFIG_EFFETS[effet_actif]["base_cc"]
        if MONO_MODE:
            cc_num = base_cc + index
        else:
            cc_num = base_cc + (corde_active * 6) + index
        msg = mido.Message('control_change', control=cc_num, value=v_int)
        port_midi.send(msg)

def changer_effet(nouvel_effet):
    global effet_actif
    effet_actif = nouvel_effet

    # Envoi du message MIDI pour notifier le changement d'effet
    if midi_ok and port_midi:
        try:
            # On associe chaque effet à un index (0, 1, 2...)
            effets_liste = list(CONFIG_EFFETS.keys())
            effet_index = effets_liste.index(nouvel_effet)
            
            # On choisit un numéro de CC qui n'est pas utilisé par les paramètres.
            # Ici, on utilise le CC 9 pour le changement d'effet.
            cc_changement_effet = 9
            
            msg = mido.Message('control_change', control=cc_changement_effet, value=effet_index)
            port_midi.send(msg)
            print(f"MIDI OUT: Changement d'effet sur CC#{cc_changement_effet} -> {nouvel_effet} (valeur: {effet_index})")

            # Envoi de tous les paramètres du nouvel effet (1 à 1)
            base_cc = CONFIG_EFFETS[nouvel_effet]["base_cc"]
            for corde, valeurs in memoire_effets[nouvel_effet].items():
                for index, val in enumerate(valeurs):
                    if MONO_MODE:
                        cc_num = base_cc + index
                    else:
                        cc_num = base_cc + (corde * 6) + index
                    port_midi.send(mido.Message('control_change', control=cc_num, value=int(val)))
            print(f"MIDI OUT: Tous les paramètres pour l'effet {nouvel_effet} ont été envoyés.")

        except Exception as e:
            print(f"Erreur lors de l'envoi MIDI pour changement d'effet : {e}")

    maj_sliders_visuels()

def action_random():
    base_cc = CONFIG_EFFETS[effet_actif]["base_cc"]
    valeurs = memoire_effets[effet_actif][corde_active]
    for i in range(len(valeurs)):
        val_rand = random.randint(0, 127)
        valeurs[i] = val_rand
        if midi_ok and port_midi:
            if MONO_MODE:
                cc_num = base_cc + i
            else:
                cc_num = base_cc + (corde_active * 6) + i
            port_midi.send(mido.Message('control_change', control=cc_num, value=val_rand))
    maj_sliders_visuels()

def sauvegarder_dans_preset(nom):
    data_save = {"preset": nom, "reglages_effets": memoire_effets}
    with open(f"preset_{nom}.json", "w") as f:
        json.dump(data_save, f, indent=4)
    maj_ecran_physique()

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
    if MONO_MODE:
        if 'btn_mute_mono' in globals():
            color = "#FF0000" if cordes_mute[0] else "#1a331a"
            btn_mute_mono.configure(fg_color=color)
        maj_sliders_visuels()
        return
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
        corde_active = corde_active + 1 if corde_active < 5 else 0
    elif direction == "down":
        # Si on descend en dessous de 0, on bascule à la corde 5, sinon on recule
        corde_active = corde_active - 1 if corde_active > 0 else 5
    maj_leds()

# endregion

# region 3. Ecran, Navigation et Menu Effets

ecran_effet = ctk.CTkLabel(master=center_container, text="READY", font=("Courier", 18, "bold"),
                           text_color="#00FF00", fg_color="#1a1a1a", corner_radius=10, height=140, width=600)
ecran_effet.grid(row=0, column=0, columnspan=2, pady=20)

if not MONO_MODE:
    frame_nav = ctk.CTkFrame(master=center_container, fg_color="transparent")
    frame_nav.grid(row=1, column=0, columnspan=2, pady=10)

    ctk.CTkButton(frame_nav, text="▼", width=50, command=lambda: changer_corde("down")).pack(side="left", padx=10)
    leds_box = ctk.CTkFrame(frame_nav, fg_color="#1a1a1a", corner_radius=15)
    leds_box.pack(side="left", padx=10)

    for i in range(6):
        # Modification : On rend le bouton cliquable (commande=toggle_mute)
        l = ctk.CTkButton(leds_box, text="", width=25, height=25, corner_radius=12, command=lambda idx=i: Activation_mute(idx))
        l.pack(side="left", padx=10, pady=10)
        leds.append(l)

    ctk.CTkButton(frame_nav, text="▲", width=50, command=lambda: changer_corde("up")).pack(side="left", padx=10)

    ctk.CTkLabel(frame_nav, text="  Effet:", font=("Arial", 14, "bold")).pack(side="left", padx=5)
    menu_effet = ctk.CTkOptionMenu(frame_nav, values=list(CONFIG_EFFETS.keys()), command=changer_effet, width=120)
    menu_effet.pack(side="left", padx=10)
else:
    frame_nav = ctk.CTkFrame(master=center_container, fg_color="transparent")
    frame_nav.grid(row=1, column=0, columnspan=2, pady=10)
    
    ctk.CTkLabel(frame_nav, text="  Effet (Mono):", font=("Arial", 14, "bold")).pack(side="left", padx=5)
    menu_effet = ctk.CTkOptionMenu(frame_nav, values=list(CONFIG_EFFETS.keys()), command=changer_effet, width=120)
    menu_effet.pack(side="left", padx=10)

    btn_mute_mono = ctk.CTkButton(frame_nav, text="MUTE", width=60, command=lambda: Activation_mute(0))
    btn_mute_mono.pack(side="left", padx=20)

# endregion

# region 4. Grille des Potentiomètres (2x3) et Boutons de commandes

frame_grid_potards = ctk.CTkFrame(center_container)
frame_grid_potards.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

frame_bouton = ctk.CTkFrame(center_container)
frame_bouton.grid(row=2, column=1, padx=10, pady=10, sticky="nsew")

ctk.CTkButton(frame_bouton, text="RANDOM", command=action_random, fg_color="#7022A1").pack(pady=15, padx=10)
ctk.CTkButton(frame_bouton, text="SAVE A", command=lambda: sauvegarder_dans_preset("A"), fg_color="#2c3e50").pack(pady=5, padx=10)
ctk.CTkButton(frame_bouton, text="SAVE B", command=lambda: sauvegarder_dans_preset("B"), fg_color="#2c3e50").pack(pady=5, padx=10)

# Génération de la disposition matérielle épurée
param_count = max(len(cfg["params"]) for cfg in CONFIG_EFFETS.values())
for i in range(param_count):
    ligne = 0 if i < 3 else 1
    colonne = i if i < 3 else i - 3
    
    cellule = ctk.CTkFrame(frame_grid_potards, fg_color="transparent")
    cellule.grid(row=ligne, column=colonne, padx=15, pady=20, sticky="nsew")
    
    # Label purement matériel (P1, P2...)
    lbl = ctk.CTkLabel(cellule, text=f"P{i+1} : --", font=("Arial", 14, "bold"))
    lbl.pack()
    slider_labels.append(lbl)
    
    s = ctk.CTkSlider(cellule, from_=0, to=127, orientation="horizontal", width=160,
                      command=lambda v, idx=i: slider_callback(v, idx))
    s.set(64)
    s.pack(pady=8)
    sliders.append(s)

# endregion

# region 5. Footswitches

frame_sw = ctk.CTkFrame(center_container, fg_color="transparent")
frame_sw.grid(row=3, column=0, columnspan=2, pady=40, sticky="ew")

btn_bypass = ctk.CTkButton(frame_sw, text="BYPASS", fg_color="#555555", width=160, height=70, corner_radius=35, command=Activation_bypass)
btn_bypass.pack(side="left", padx=20, expand=True)
ctk.CTkButton(frame_sw, text="PRESET A", command=lambda: charger_preset("A"), width=160, height=70, corner_radius=35).pack(side="left", padx=20, expand=True)
ctk.CTkButton(frame_sw, text="PRESET B", command=lambda: charger_preset("B"), width=160, height=70, corner_radius=35).pack(side="left", padx=20, expand=True)

# endregion

maj_leds()
win.mainloop()