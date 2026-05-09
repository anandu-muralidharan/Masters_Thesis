import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
from galvani import BioLogic
import re
import os

# ================= PUBLICATION SETTINGS =================
E_SHIFT = 1.024  
AREA = 0.196     

# Updated Color Palette: Distinct and Professional
# (Red, Blue, Green, Purple, Dark Grey)
COLORS = ['#D62728', '#1F77B4', '#2CA02C', '#9467BD', '#333333']
MARKERS = ['o', '^', 'v', 's', 'D']

plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman'],
    'mathtext.fontset': 'stix',
    'axes.linewidth': 1.5,
    'xtick.major.width': 1.5,
    'ytick.major.width': 1.5,
})
# ========================================================

def format_chem(text):
    return re.sub(r'(\d+)', r'$_{\1}$', text)

def detect_columns(df):
    E_col = next((c for c in df.columns if "Ewe" in c or "E/V" in c), None)
    I_col = next((c for c in df.columns if ("I" in c and "mA" in c) or c.strip() == "I"), None)
    return E_col, I_col

def plot_final_publication_tafel():
    num_systems = simpledialog.askinteger("Input", "Number of materials:", minvalue=1, maxvalue=5)
    if not num_systems: return

    fig, ax = plt.subplots(figsize=(5.5, 4.5), dpi=300)
    
    for i in range(num_systems):
        messagebox.showinfo("Select", f"Select file for System {i+1}")
        file_path = filedialog.askopenfilename(filetypes=[("MPR files", "*.mpr")])
        if not file_path: continue
        
        raw_name = simpledialog.askstring("Name", f"Name for {os.path.basename(file_path)}:")
        e_low = simpledialog.askfloat("Fit", f"{raw_name} Lower E limit (V):", initialvalue=0.88)
        e_high = simpledialog.askfloat("Fit", f"{raw_name} Upper E limit (V):", initialvalue=0.94)

        try:
            mpr = BioLogic.MPRfile(file_path)
            df = pd.DataFrame(mpr.data).dropna()
            E_col, I_col = detect_columns(df)
            
            E = df[E_col].values + E_SHIFT
            I = np.abs(df[I_col].values / AREA)
            idx = np.argsort(E)
            E, I = E[idx], I[idx]
            
            # Mass Transport Correction
            j_L_region = I[(E > 0.3) & (E < 0.6)]
            j_L = np.abs(np.mean(j_L_region)) if len(j_L_region) > 0 else np.max(I)
            j_k = (I * j_L) / (np.maximum(j_L - I, 1e-9))
            
            # Fit Window
            mask = (E >= e_low) & (E <= e_high) & (j_k > 0)
            plot_E, log_jk = E[mask], np.log10(j_k[mask])
            
            if len(log_jk) < 5: continue

            coeffs = np.polyfit(log_jk, plot_E, 1)
            slope = abs(coeffs[0] * 1000)
            fit_func = np.poly1d(coeffs)
            
            c = COLORS[i % len(COLORS)]
            m = MARKERS[i % len(MARKERS)]
            label_name = f"{format_chem(raw_name)} ({slope:.0f} mV dec$^{{-1}}$)"
            
            # 1. Linear Fit Lines (Extended)
            x_ext = np.linspace(min(log_jk) - 0.05, max(log_jk) + 0.05, 100)
            ax.plot(x_ext, fit_func(x_ext), color=c, linewidth=1.8, zorder=2)
            
            # 2. Refined Symbols: Smaller size (s=35) and thinner edges
            # Plotted every 15th point to keep it very clean
            ax.scatter(log_jk[::15], plot_E[::15], s=35, color=c, marker=m, 
                       label=label_name, edgecolors='k', linewidths=0.6, zorder=3)
                       
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    # --- FINAL REFINEMENTS ---
    ax.set_xlabel(r'$\log |j_k| \ \mathrm{(mA \ cm^{-2})}$', fontsize=14, labelpad=8)
    ax.set_ylabel('Potential (V vs. RHE)', fontsize=14, labelpad=8)
    
    ax.tick_params(direction='in', length=6, width=1.2, top=True, right=True, labelsize=11)
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())
    
    ax.set_ylim(0.80, 1.05) 
    ax.set_xlim(left=0)
    
    # Legend: No border (frameon=False)
    ax.legend(frameon=False, loc='upper right', fontsize=9, handletextpad=0.5)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    plot_final_publication_tafel()