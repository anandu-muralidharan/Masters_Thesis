import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
import json
import os
import numpy as np
import re  # Added for automatic subscript formatting

# ---------------- CONSTANTS ----------------
THZ_TO_EV = 0.00413567

# Table S2 — Ritacco et al. 2025
TS_H2  = 0.41
TS_H2O = 0.58

# Table S1 — tabulated gas-phase ZPEs
ZPE_H2_ref  = 0.27
ZPE_H2O_ref = 0.55

U_EQ      = 1.23
ORR_TOTAL = 4.92  # eV

# Placeholder for solvation corrections
SOLV_OOH = 0.0
SOLV_OH  = 0.0

CONFIG_FILE = "config.json"
data = {}

H2_PATH  = r"Y:\scratch\H2"
H2O_PATH = r"Y:\scratch\H2O"

# ---------------- CONFIG ----------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

config = load_config()

# ---------------- FILE HANDLING ----------------
def build_entry(path):
    energy = os.path.join(path, "OUTCAR")
    freq   = os.path.join(path, "ZPE", "OUTCAR")
    if not os.path.exists(energy) or not os.path.exists(freq):
        return None
    return {"energy": energy, "freq": freq}

def load_default_constants():
    config["H2"]  = build_entry(H2_PATH)
    config["H2O"] = build_entry(H2O_PATH)
    save_config(config)

def constants_loaded():
    return config.get("H2") and config.get("H2O")

# ---------------- PARSERS ----------------
def get_toten(file):
    with open(file) as f:
        for line in reversed(f.readlines()):
            if "free  energy   TOTEN" in line:
                return float(line.split()[-2])
    return None

def get_freq(file):
    freqs = []
    with open(file) as f:
        for line in f:
            if "f  =" in line and "THz" in line:
                parts = line.split()
                try:
                    val = float(parts[3])
                    if val > 0:
                        freqs.append(val)
                except:
                    pass
    return freqs

def compute_zpe(freqs):
    return sum([0.5 * f * THZ_TO_EV for f in freqs])

# ---------------- LOAD ORR ----------------
def load_orr_folder(base_path):
    systems = {
        "OOH": os.path.join(base_path, "2"),
        "O":   os.path.join(base_path, "3"),
        "OH":  os.path.join(base_path, "4"),
    }
    results = {}
    for key, path in systems.items():
        scf_path    = os.path.join(path, "scf")
        energy_file = os.path.join(scf_path, "OUTCAR")
        zpe_file    = os.path.join(scf_path, "ZPE", "OUTCAR")
        if not os.path.exists(energy_file):
            raise Exception(f"Missing SCF OUTCAR in {scf_path}")
        if not os.path.exists(zpe_file):
            raise Exception(f"Missing ZPE OUTCAR in {scf_path}/ZPE")
        E   = get_toten(energy_file)
        ZPE = compute_zpe(get_freq(zpe_file))
        results[key] = (E, ZPE)
    return results

# ---------------- PLOT (PUBLICATION STYLE) ----------------
def plot_orr(G_states, eta, system_name):
    labels = ["O$_2$", "*OOH", "*O", "*OH", "H$_2$O"]
    x = np.arange(len(labels))
    n = len(G_states)

    # Cumulative states at U = 1.23 V 
    G_eq = np.array([G_states[i] - (n - 1 - i) * U_EQ for i in range(n)])

    # Use a clean, publication-ready style
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
    plt.rcParams['axes.linewidth'] = 1.5

    fig, ax = plt.subplots(figsize=(8, 6))
    bar = 0.35  

    def draw_path(G, color, lw, ls):
        for i in range(n):
            ax.hlines(G[i], x[i] - bar, x[i] + bar,
                      color=color, linewidth=lw, linestyle='solid')
        for i in range(n - 1):
            ax.plot([x[i] + bar, x[i+1] - bar],
                    [G[i],       G[i+1]],
                    color=color, linewidth=lw * 0.6,
                    linestyle=ls)

    # U = 0 V (Bold Black)
    draw_path(G_states, "black", 2.5, "--")
    
    # U = 1.23 V (Crimson Red)
    draw_path(G_eq, "#c00000", 2.0, "--")

    # Value Labels
    for i in range(n):
        ax.text(x[i], G_states[i] + 0.15, f"{G_states[i]:.2f}",
                ha="center", fontsize=11, fontweight='bold', color="black")
        ax.text(x[i], G_eq[i] - 0.25, f"{G_eq[i]:.2f}",
                ha="center", fontsize=11, fontweight='bold', color="#c00000")

    # Axis styling
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=14, fontweight='bold')
    ax.set_ylabel("Free Energy (eV)", fontsize=14, fontweight='bold')
    
    # Auto-format chemical formulas (e.g., Pt5/BC6N -> Pt$_5$/BC$_6$N)
    formatted_name = re.sub(r'([A-Za-z])(\d+)', r'\1$_{\2}$', system_name)
    ax.set_title(f"Oxygen Reduction Pathway on {formatted_name}", fontsize=16, fontweight='bold', pad=15)

    ax.axhline(0, linestyle=":", color="#7f7f7f", linewidth=1.5, zorder=0)
    ax.tick_params(axis='both', which='major', direction='in', length=6, width=1.5, labelsize=12)
    ax.tick_params(axis='x', bottom=False) 

    ax.plot([], [], color="black",   lw=2.5, label="U = 0.00 V")
    ax.plot([], [], color="#c00000", lw=2.0, label="U = 1.23 V")
    ax.legend(frameon=False, fontsize=12, loc='best')

    plt.tight_layout()
    plt.savefig("ORR_diagram_publication.tif", dpi=600, bbox_inches="tight", format='tiff')
    plt.savefig("ORR_diagram_publication.png", dpi=600, bbox_inches="tight")
    plt.show()

# ---------------- COMPUTE ----------------
def compute():
    try:
        if not constants_loaded():
            messagebox.showerror("Error", "H2 / H2O OUTCARs missing")
            return
        if "clean_energy" not in data or "orr_folder" not in data:
            messagebox.showerror("Error", "Select clean OUTCAR and ORR folder")
            return

        support_name = system_var.get().strip()
        if not support_name:
            support_name = "C" # Default fallback
            
        full_system_name = f"Pt5/{support_name}"

        # Raw DFT energies
        E_clean = get_toten(data["clean_energy"])
        orr     = load_orr_folder(data["orr_folder"])

        E_OOH, ZPE_OOH = orr["OOH"]
        E_O,   ZPE_O   = orr["O"]
        E_OH,  ZPE_OH  = orr["OH"]

        E_H2  = get_toten(config["H2"]["energy"])
        E_H2O = get_toten(config["H2O"]["energy"])

        ZPE_H2_vasp  = compute_zpe(get_freq(config["H2"]["freq"]))
        ZPE_H2O_vasp = compute_zpe(get_freq(config["H2O"]["freq"]))

        # Free energies
        G_H2  = E_H2  + ZPE_H2_ref  - TS_H2
        G_H2O = E_H2O + ZPE_H2O_ref - TS_H2O

        G_OOH_slab = E_OOH + ZPE_OOH
        G_O_slab   = E_O   + ZPE_O
        G_OH_slab  = E_OH  + ZPE_OH

        # Adsorption free energies (CHE)
        G_OOH_ads = G_OOH_slab + 1.5 * G_H2 - E_clean - 2.0 * G_H2O + SOLV_OOH
        G_O_ads   = G_O_slab   + 1.0 * G_H2 - E_clean - 1.0 * G_H2O
        G_OH_ads  = G_OH_slab  + 0.5 * G_H2 - E_clean - 1.0 * G_H2O + SOLV_OH

        # Elementary reaction steps @ U = 0
        dG1 = G_OOH_ads - ORR_TOTAL   
        dG2 = G_O_ads   - G_OOH_ads   
        dG3 = G_OH_ads  - G_O_ads     
        dG4 = -G_OH_ads               

        sum_check = dG1 + dG2 + dG3 + dG4

        # Overpotential
        dG_0   = np.array([dG1, dG2, dG3, dG4])
        max_dG = float(np.max(dG_0))
        UL     = -max_dG              
        eta    = U_EQ - UL            

        steps = ["O2→*OOH", "*OOH→*O+H2O", "*O→*OH", "*OH→H2O"]
        pds   = steps[int(np.argmax(dG_0))]

        # Output
        output = f"""
================ RAW ENERGIES ({full_system_name}) ================
E_clean  : {E_clean:.6f} eV

E_OOH    : {E_OOH:.6f} eV   ZPE (VASP): {ZPE_OOH:.6f} eV
E_O      : {E_O:.6f} eV   ZPE (VASP): {ZPE_O:.6f} eV
E_OH     : {E_OH:.6f} eV   ZPE (VASP): {ZPE_OH:.6f} eV

E_H2     : {E_H2:.6f} eV   ZPE (VASP): {ZPE_H2_vasp:.6f} eV  [tabulated: {ZPE_H2_ref}]
E_H2O    : {E_H2O:.6f} eV   ZPE (VASP): {ZPE_H2O_vasp:.6f} eV  [tabulated: {ZPE_H2O_ref}]

G_H2     : {G_H2:.6f} eV  (E + ZPE_tab - TS)
G_H2O    : {G_H2O:.6f} eV  (E + ZPE_tab - TS)
==============================================

================ ORR RESULTS ================
Adsorption Free Energies (eV):
  G_OOH* : {G_OOH_ads:.4f}
  G_O* : {G_O_ads:.4f}
  G_OH* : {G_OH_ads:.4f}

Reaction Free Energies @ U = 0 V:
  ΔG1 (O2→*OOH)      : {dG1:.4f} eV
  ΔG2 (*OOH→*O+H2O)  : {dG2:.4f} eV
  ΔG3 (*O→*OH)       : {dG3:.4f} eV
  ΔG4 (*OH→H2O)      : {dG4:.4f} eV
  Sum (should = -4.92): {sum_check:.4f} eV

Potential-Determining Step : {pds}
Limiting Potential   UL    : {UL:.4f} V
Overpotential        η     : {eta:.4f} V
==============================================
""".strip()

        result_box.delete("1.0", tk.END)
        result_box.insert(tk.END, output)

        # Plot
        G_states = np.array([ORR_TOTAL, G_OOH_ads, G_O_ads, G_OH_ads, 0.0])
        plot_orr(G_states, eta, full_system_name)

    except Exception as e:
        messagebox.showerror("Error", str(e))

# ---------------- UI ----------------
root = tk.Tk()
root.title("ORR Calculator — Conventional Pathway")
root.geometry("640x590")  # Slightly taller to fit the new input

# GUI Variable for the support material
system_var = tk.StringVar(value="C")

# Clean layout for file selection
tk.Button(root, text="Select CLEAN OUTCAR",
          command=lambda: data.update(
              {"clean_energy": filedialog.askopenfilename(
                  title="Select clean slab OUTCAR")}
          )).pack(pady=5)

tk.Button(root, text="Select ORR Folder",
          command=lambda: data.update(
              {"orr_folder": filedialog.askdirectory(
                  title="Select ORR folder (contains 2/, 3/, 4/)")}
          )).pack(pady=5)

# New Support Material Input Frame
input_frame = tk.Frame(root)
input_frame.pack(pady=8)
tk.Label(input_frame, text="Support Material (e.g., C, BC6N, BN):", font=("Arial", 10)).pack(side=tk.LEFT)
tk.Entry(input_frame, textvariable=system_var, width=12, font=("Arial", 10), justify="center").pack(side=tk.LEFT, padx=5)

tk.Button(root, text="Compute ORR",
          command=compute,
          bg="#2C3E50", fg="white", font=("Arial", 11, "bold")).pack(pady=10)

result_box = tk.Text(root, height=24, font=("Consolas", 10))
result_box.pack(fill="both", expand=True, padx=8, pady=4)

load_default_constants()
root.mainloop()