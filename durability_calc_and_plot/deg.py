import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
from scipy.signal import savgol_filter
from galvani import BioLogic
import os

# ================= SETTINGS =================
E_SHIFT = 1.024
AREA = 0.196
SMOOTH = True
WINDOW = 21
POLY = 3
# ============================================

def smooth(y):
    if SMOOTH and len(y) > WINDOW:
        return savgol_filter(y, WINDOW, POLY)
    return y

def calculate_half_wave(E, I):
    # Plateau calculated from the deep diffusion-limited region (0.2 - 0.5V)
    I_lim = np.mean(I[(E > 0.2) & (E < 0.5)]) 
    I_half = I_lim / 2
    idx = (np.abs(I - I_half)).argmin()
    return E[idx], I_half

def process_file(filepath):
    mpr = BioLogic.MPRfile(filepath)
    df = pd.DataFrame(mpr.data).dropna()
    
    E_col, I_col = None, None
    for col in df.columns:
        if "Ewe" in col or "E/V" in col: E_col = col
        if ("I" in col and "mA" in col) or col.strip() == "I": I_col = col
    
    if not E_col or not I_col:
        raise ValueError(f"Columns not found in {os.path.basename(filepath)}")

    E = df[E_col].values + E_SHIFT
    I = df[I_col].values / AREA
    
    idx = np.argsort(E)
    E, I = E[idx], I[idx]
    I = smooth(I)
    return E, I

def run_durability_analysis():
    file_before = filedialog.askopenfilename(title="1. Select INITIAL LSV")
    if not file_before: return
    
    file_after = filedialog.askopenfilename(title="2. Select AFTER 10k LSV")
    if not file_after: return

    try:
        E_bef, I_bef = process_file(file_before)
        E_aft, I_aft = process_file(file_after)
        
        Eb_half, Ib_half = calculate_half_wave(E_bef, I_bef)
        Ea_half, Ia_half = calculate_half_wave(E_aft, I_aft)
        
        delta_E = (Eb_half - Ea_half) * 1000 

        # ================= STYLING =================
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Arial']
        plt.rcParams['axes.linewidth'] = 1.5
        
        fig, ax = plt.subplots(figsize=(3.5, 3.2))

        ax.plot(E_bef, I_bef, color='black', linewidth=1.8, label='Initial', zorder=2)
        ax.plot(E_aft, I_aft, color='red', linewidth=1.8, linestyle='--', label='After 8k cycles', zorder=3)

        # Highlight E1/2 points
        ax.scatter([Eb_half, Ea_half], [Ib_half, Ia_half], color=['black', 'red'], s=30, zorder=5)
        
        # Annotation placed in the upper-center "white space"
        ax.text(0.65, -1.5, f"$\Delta E_{{1/2}}$ = {delta_E:.1f} mV", 
                fontsize=10, fontweight='bold', ha='center', color='black')

        # ================= AXIS & TICKS =================
        # Full view limits
        ax.set_xlim(0.2, 1.1) 
        ax.set_ylim(-6.0, 0.5) 

        ax.set_xlabel("Potential (V vs. RHE)", fontsize=11, fontweight='bold')
        ax.set_ylabel("Current Density (mA cm$^{-2}$)", fontsize=11, fontweight='bold')

        ax.tick_params(direction='in', length=5, width=1.5, top=True, right=True, labelsize=10)
        ax.xaxis.set_minor_locator(AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(AutoMinorLocator(2))

        # Legend placed where it won't block the kinetic region
        ax.legend(frameon=False, fontsize=9, loc='lower left')
        
        plt.tight_layout()
        plt.savefig("Durability_Full_Diagram.png", dpi=600)
        plt.show()

    except Exception as e:
        messagebox.showerror("Error", str(e))

# ================= GUI =================
root = tk.Tk()
root.title("Full Range Durability Tool")
root.geometry("300x100")
btn = tk.Button(root, text="Generate Full Plot", command=run_durability_analysis, bg="#1B4F72", fg="white", font=("Arial", 10, "bold"))
btn.pack(expand=True)
root.mainloop()