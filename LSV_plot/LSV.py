import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
from scipy.signal import savgol_filter
from galvani import BioLogic
import os
import matplotlib.cm as cm

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
    n = int(0.1 * len(E))  # lowest 10% → plateau
    # I_lim = np.mean(I[:n])
    I_lim = np.mean(I[E <0.6])
    I_half = I_lim / 2
    I_half = I_lim / 2
    idx = (np.abs(I - I_half)).argmin()
    return E[idx], I_half

def calculate_onset(E, I):
    baseline = np.mean(I[E > 1.0])
    for e, i in zip(E, I):
        if i < baseline - 0.1:
            return e
    return None

def extract_rpm(filename):
    name = os.path.basename(filename)
    for rpm in ["400", "625", "900", "1225", "1600", "2025", "2500"]:
        if rpm in name:
            return int(rpm)
    return 0

def detect_columns(df):
    E_col, I_col = None, None
    for col in df.columns:
        if "Ewe" in col or "E/V" in col:
            E_col = col
        if ("I" in col and "mA" in col) or col.strip() == "I":
            I_col = col
    if E_col is None or I_col is None:
        raise ValueError(f"Columns not found:\n{df.columns}")
    return E_col, I_col

def plot_files(files):
    # ================= GLOBAL PUBLICATION STYLING =================
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
    plt.rcParams['axes.linewidth'] = 1.5 
    plt.rcParams['mathtext.default'] = 'regular' # Keeps text in math mode matching regular font
    
    # 3.5x3.2 inches is perfect for a 1-column layout in an ACS/RSC journal
    fig, ax = plt.subplots(figsize=(3.5, 3.2))

    files_sorted = sorted(files, key=lambda x: extract_rpm(x))
    colors = cm.viridis(np.linspace(0.15, 0.85, len(files_sorted)))

    results = []
    filtered_currents = []

    for i, file in enumerate(files_sorted):
        try:
            mpr = BioLogic.MPRfile(file)
            df = pd.DataFrame(mpr.data).dropna()

            E_col, I_col = detect_columns(df)

            E = df[E_col].values + E_SHIFT
            I = df[I_col].values / AREA

            idx = np.argsort(E)
            E, I = E[idx], I[idx]
            I = smooth(I)
            rpm = extract_rpm(file)

            mask = E >= 0.8
            filtered_currents.extend(I[mask])

            # Background curves (Thicker lines for scale)
            ax.plot(E, I, color=colors[i], linewidth=2.0, alpha=0.8)

            # Highlight 1600 rpm
            if rpm == 1600:
                ax.plot(E, I, color="black", linewidth=2.5, label="1600 rpm", zorder=4)

                E_half, I_half = calculate_half_wave(E, I)
                onset = calculate_onset(E, I)
                eta = 1.23 - E_half

                ax.scatter(E_half, I_half, color="black", s=40, zorder=5)

                # Robust relative annotation
                ax.annotate(f"E$_{{1/2}}$ = {E_half:.2f} V",
                            xy=(E_half, I_half),
                            xytext=(15, -25), # Offset in points, prevents flying off-screen
                            textcoords="offset points",
                            arrowprops=dict(arrowstyle="->", lw=1.2, color='black'),
                            fontsize=10,
                            fontweight='bold')

                results.append((rpm, onset, E_half, eta))

        except Exception as e:
            messagebox.showerror("Error", f"{file}\n\n{str(e)}")
            return

    # ================= AXIS & TICK FORMATTING =================
    ymin = min(filtered_currents)
    ax.set_ylim(ymin - 0.5, 0.5)
    ax.set_xlim(0.8, 1.02)

    ax.set_xlabel("Potential (V vs. RHE)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Current Density (mA cm$^{-2}$)", fontsize=11, fontweight='bold')

    # Inward, thick major ticks on all sides
    ax.tick_params(which='major', direction='in', length=5, width=1.5,
                   bottom=True, top=True, left=True, right=True, labelsize=10)
    
    # Minor ticks
    ax.xaxis.set_minor_locator(AutoMinorLocator(4))
    ax.yaxis.set_minor_locator(AutoMinorLocator(4))
    ax.tick_params(which='minor', direction='in', length=3, width=1.0,
                   bottom=True, top=True, left=True, right=True)

    # Clean legend
    ax.legend(frameon=False, fontsize=10, loc='lower left')

    plt.tight_layout()
    
    # High-Res Exports (TIFF for submission, PNG for quick sharing)
    plt.savefig("LSV_final_publication.tif", dpi=600, bbox_inches="tight", format='tiff', pil_kwargs={"compression": "tiff_lzw"})
    plt.savefig("LSV_final_publication.png", dpi=600, bbox_inches="tight")

    plt.show()

    # ================= RESULTS =================
    print("\n===== FINAL RESULTS =====")
    for r in results:
        print(f"{r[0]} rpm:")
        print(f"  Onset = {r[1]:.3f} V")
        print(f"  E1/2  = {r[2]:.3f} V")
        print(f"  Overpotential = {r[3]:.3f} V\n")

def select_files():
    files = filedialog.askopenfilenames(
        title="Select LSV (.mpr) files",
        filetypes=[("MPR files", "*.mpr")]
    )
    if files:
        plot_files(files)

# ================= GUI =================

root = tk.Tk()
root.title("LSV Final Tool (Publication Ready)")
root.geometry("420x220")

label = tk.Label(root, text="Select LSV (.mpr) files", font=("Arial", 12))
label.pack(pady=20)

btn = tk.Button(root, text="Browse Files",
                command=select_files,
                bg="#2E4053", fg="white", font=("Arial", 10, "bold"),
                padx=12, pady=6)
btn.pack()

root.mainloop()