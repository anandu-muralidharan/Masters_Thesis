import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
from scipy.signal import savgol_filter
from galvani import BioLogic
import os
import re
import matplotlib.cm as cm

# ================= SCIENTIFIC SETTINGS =================
E_SHIFT = 1.024  # Potential shift to RHE
AREA = 0.196     # Geometric area of electrode (cm^2)
# Levich Constants: F (C/mol), D (cm^2/s), nu (cm^2/s), C (mol/cm^3)
F, D, nu, C = 96485, 1.9e-5, 0.01, 1.2e-6 

# Potentials for K-L analysis
POTENTIALS = [0.20, 0.30, 0.40, 0.50, 0.60, 0.70] 

SMOOTH = True
WINDOW = 21
POLY = 3
# =======================================================

def format_chem(text):
    """Subscripts numbers in chemical formulas for Matplotlib."""
    return re.sub(r'(\d+)', r'$_{\1}$', text)

def smooth(y):
    """Applies Savitzky-Golay filter."""
    if SMOOTH and len(y) > WINDOW:
        return savgol_filter(y, WINDOW, POLY)
    return y

def detect_columns(df):
    """Identifies Voltage and Current columns in BioLogic data."""
    E_col = next((c for c in df.columns if "Ewe" in c or "E/V" in c), None)
    I_col = next((c for c in df.columns if ("I" in c and "mA" in c) or c.strip() == "I"), None)
    return E_col, I_col

def extract_rpm(filename):
    """Extracts rotation speed from filename."""
    name = os.path.basename(filename).lower()
    for rpm in ["400", "625", "900", "1225", "1600", "2025", "2500"]:
        if rpm in name: return int(rpm)
    return 0

def plot_smart_no_avg():
    mat_name = simpledialog.askstring("Input", "Material Name (e.g., Pt/C):")
    if not mat_name: return
    save_name = mat_name.replace("/", "-").replace("\\", "-")
    
    files = filedialog.askopenfilenames(title="Select .mpr Files", filetypes=[("MPR files", "*.mpr")])
    if not files: return

    data = {}
    for file in files:
        rpm = extract_rpm(file)
        if rpm > 0:
            mpr = BioLogic.MPRfile(file)
            df = pd.DataFrame(mpr.data).dropna()
            E_col, I_col = detect_columns(df)
            
            # Apply shift and normalize by area
            E = df[E_col].values + E_SHIFT
            I = df[I_col].values / AREA
            
            idx = np.argsort(E)
            data[rpm] = (E[idx], smooth(I[idx]))

    if not data:
        messagebox.showerror("Error", "No valid RPM data found in filenames.")
        return

    plt.rcParams['font.family'] = 'serif'
    plt.rcParams['font.serif'] = ['Times New Roman']
    
    # --- PLOT 1: LSV CURVES ---
    fig1, ax1 = plt.subplots(figsize=(3.3, 3.0), dpi=300)
    sorted_rpms = sorted(data.keys())
    colors = cm.viridis(np.linspace(0.1, 0.9, len(sorted_rpms)))
    
    for i, rpm in enumerate(sorted_rpms):
        E, I = data[rpm]
        c = "black" if rpm == 1600 else colors[i]
        lw = 2.0 if rpm == 1600 else 1.2
        ax1.plot(E, I, color=c, linewidth=lw)

    ax1.set_xlabel("Potential (V vs. RHE)", fontsize=11, fontweight='bold')
    ax1.set_ylabel("Current Density (mA cm$^{-2}$)", fontsize=11, fontweight='bold')
    ax1.set_xlim(0.2, 1.05)
    
    ymin = min([min(data[r][1]) for r in data])
    ax1.set_ylim(ymin - 0.5, 1.5) 

    ax1.tick_params(direction='in', length=5, width=1.2, top=True, right=True, labelsize=9)
    ax1.xaxis.set_minor_locator(AutoMinorLocator())
    ax1.yaxis.set_minor_locator(AutoMinorLocator())
    for s in ax1.spines.values(): s.set_linewidth(1.2)
    
    ax1.text(0.05, 0.92, format_chem(mat_name), transform=ax1.transAxes, fontsize=12, fontweight='bold', va='top')
    ax1.legend(["1600 rpm"], frameon=False, loc='lower right', fontsize=8)
    plt.tight_layout()
    fig1.savefig(f"LSV_{save_name}.png", dpi=600)

    # --- PLOT 2: K-L PLOT ---
    fig2, ax2 = plt.subplots(figsize=(3.3, 3.0), dpi=300)
    kl_colors = cm.plasma(np.linspace(0, 0.8, len(POTENTIALS)))
    n_list = []
    
    for i, pot in enumerate(POTENTIALS):
        inv_j, inv_sqrt_w = [], []
        for rpm in sorted_rpms:
            E, I = data[rpm]
            # Convert mA/cm2 to A/cm2 for the formula calculation
            I_val = np.abs(np.interp(pot, E, I)) / 1000 
            omega = 2 * np.pi * rpm / 60 # rpm to rad/s
            inv_j.append(1/I_val)
            inv_sqrt_w.append(1/np.sqrt(omega))
        
        coeffs = np.polyfit(inv_sqrt_w, inv_j, 1)
        slope = coeffs[0]
        
        # Calculate n using the Levich equation
        B = 0.62 * F * (D**(2/3)) * (nu**(-1/6)) * C
        n = (1/slope) / B
        n_list.append(abs(n))
        
        # Plot points (converted back to mA-1 for axis display)
        ax2.scatter(inv_sqrt_w, np.array(inv_j)/1000, s=25, color=kl_colors[i], edgecolors='k', linewidths=0.3)
        ax2.plot(inv_sqrt_w, np.poly1d(coeffs)(inv_sqrt_w)/1000, color=kl_colors[i], linewidth=1.2, alpha=0.7)

    avg_n = np.mean(n_list)

    # --- LOGIC FOR N-VALUE DISPLAY & NOTIFICATIONS ---
    if avg_n > 5.5:
        messagebox.showwarning("Anomalous Result", 
                               f"Calculated n = {avg_n:.2f}\n\nThis value is physically unlikely (>5.5). "
                               "Check for capacitive current interference or incorrect constants (C, D, Area).")
        display_n = rf"$n$ = {avg_n:.2f}"
    
    elif 3.5 <= avg_n <= 5.5:
        # Values in this range are treated as the 4-electron pathway
        display_n = r"$n \approx 4$"
        
    elif avg_n < 2.5:
        messagebox.showinfo("Result", f"Calculated n = {avg_n:.2f}\n(Close to 2-electron peroxide pathway)")
        display_n = rf"$n$ = {avg_n:.2f}"
        
    else:
        display_n = rf"$n$ = {avg_n:.2f}"

    ax2.set_xlabel(r'$\omega^{-1/2}$ (rad$^{-1/2}$ s$^{1/2}$)', fontsize=11, fontweight='bold')
    ax2.set_ylabel(r'$j^{-1}$ (mA$^{-1}$ cm$^{2}$)', fontsize=11, fontweight='bold')
    ax2.tick_params(direction='in', length=5, width=1.2, top=True, right=True, labelsize=9)
    ax2.xaxis.set_minor_locator(AutoMinorLocator())
    ax2.yaxis.set_minor_locator(AutoMinorLocator())
    for s in ax2.spines.values(): s.set_linewidth(1.2)
    
    # Place text label
    ax2.text(0.95, 0.05, display_n, transform=ax2.transAxes, 
             fontsize=10, fontweight='bold', ha='right', va='bottom',
             bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))

    ax2.set_ylim(0, ax2.get_ylim()[1] * 1.3)
    plt.tight_layout()
    fig2.savefig(f"KL_{save_name}.png", dpi=600)

    plt.show()

# --- GUI EXECUTION ---
root = tk.Tk()
root.title("ORR Plotter (Final Clean)")
tk.Button(root, text="Launch Final Analysis", command=plot_smart_no_avg, 
          bg="#1B2631", fg="white", font=("Arial", 10, "bold"), padx=20, pady=10).pack(pady=40)
root.mainloop()