import pandas as pd
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt

def select_file():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(title="Select XPS Data", 
                                    filetypes=[("Excel files", "*.xlsx *.xls")])

def plot_xps_clean(file_path):
    # Load data
    df = pd.read_excel(file_path, header=None)
    
    # Raw Data
    be_full = df.iloc[:, 0].values
    raw_full = df.iloc[:, 1].values
    
    # Deconvolution Components
    bg_full = df.iloc[:, 6].values
    total_fit_full = df.iloc[:, 7].values
    peaks_full = [df.iloc[:, i].values for i in range(2, 6)]

    # --- RADIOCAL CLIPPING ---
    # Find indices where the background is active (non-zero)
    # We use a very small threshold to catch the exact start/end of the fit
    active = np.where(bg_full > 1)[0] # Assuming intensity > 1 means active
    
    if len(active) == 0:
        messagebox.showerror("Error", "Could not find active deconvolution region in column 6.")
        return

    # Slice everything to the exact active window
    start, end = active[0], active[-1]
    
    be = be_full[start:end]
    raw = raw_full[start:end]
    bg = bg_full[start:end]
    total_fit = total_fit_full[start:end]
    peaks = [p[start:end] for p in peaks_full]

    # Plotting
    fig, ax = plt.subplots(figsize=(7, 5), dpi=300)
    
    # 1. Experimental (Hollow Circles)
    ax.scatter(be, raw, s=20, facecolors='none', edgecolors='silver', 
               linewidth=0.7, label='Experimental', alpha=0.8)
    
    # 2. Baseline (Dashed)
    ax.plot(be, bg, color='black', linestyle='--', linewidth=1.2, label='Baseline')

    # 3. Individual Peaks (Plotting on top of baseline)
    colors = ['#d62728', '#1f77b4', '#9467bd', '#2ca02c'] 
    for i, peak in enumerate(peaks):
        # We plot the peak itself
        ax.plot(be, peak, color=colors[i], linewidth=1.5)
        # Fill strictly between the baseline and the peak curve
        ax.fill_between(be, bg, peak, color=colors[i], alpha=0.3)
    
    # 4. Total Fit (Bold Black)
    ax.plot(be, total_fit, color='black', linewidth=2.2, label='Total Fit', zorder=10)

    # Styling for Publication
    ax.invert_xaxis()
    ax.set_xlabel('Binding Energy (eV)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Intensity (a.u.)', fontsize=12, fontweight='bold')
    
    # Scientific Box Look
    ax.tick_params(which='both', direction='in', top=True, right=True)
    ax.legend(frameon=False, loc='upper left', fontsize=9)
    
    plt.tight_layout()
    
    # Save as PDF
    output_name = file_path.rsplit('.', 1)[0] + "_Clean_XPS.pdf"
    plt.savefig(output_name, bbox_inches='tight')
    plt.show()

if __name__ == "__main__":
    path = select_file()
    if path:
        try:
            plot_xps_clean(path)
        except Exception as e:
            messagebox.showerror("Error", f"Processing error: {e}")